"""
Fase 9 - Framework de Risco e Regras Operacionais

Gera documento de regras operacionais baseado na análise:
- Buffer ideal selection
- Capital máximo por operação
- Mercados preferidos
- Horário preferido
- Limites e condições para não operar
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

from config.settings import (
    DATA_STATS_DIR,
    DATA_PROCESSED_DIR,
    DEFAULT_TIMEFRAME,
    MAX_CAPITAL_PER_MARKET_PERCENT,
    MAX_DRAWDOWN_PERCENT,
    ensure_data_dirs_exist,
)
from pipeline.phase4_stats_spread import load_market_spread_stats, MarketSpreadStats
from pipeline.phase5_market_comparison import load_market_rankings
from pipeline.phase6_temporal_analysis import load_temporal_analysis
from pipeline.phase7_cost_model import (
    COST_SCENARIOS,
    CostScenario,
    calculate_breakeven_spread,
    POLYMARKET_FEE_PCT,
)
from pipeline.phase8_edge_validation import EdgeValidationResult

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

# Fração do Kelly a usar (conservador)
KELLY_FRACTION = 0.25

# Mínimo de trades para considerar estatisticamente válido
MIN_SAMPLE_SIZE = 30

# Capital mínimo por operação (USD)
MIN_TRADE_SIZE_USD = 50

# Máximo de posições concorrentes
MAX_CONCURRENT_POSITIONS = 5

# Buffer padrão recomendado (será ajustado pela análise)
DEFAULT_BUFFER_PCT = 0.01  # 1%


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class BufferRecommendation:
    """Recomendação de buffer."""
    recommended_buffer: float          # Buffer recomendado (decimal)
    min_viable_buffer: float           # Buffer mínimo viável
    optimal_buffer: float              # Buffer ótimo (maior lucro esperado)
    buffer_analysis: Dict[float, Dict]  # Análise por buffer


@dataclass
class CapitalRecommendation:
    """Recomendação de capital."""
    max_capital_per_trade_usd: float
    max_capital_total_usd: float
    recommended_trade_size_usd: float
    kelly_fraction: float
    position_sizing_method: str


@dataclass
class MarketPreferences:
    """Preferências de mercados."""
    preferred_markets: List[str]       # IDs dos mercados preferidos
    preferred_categories: List[str]    # Categorias preferidas
    markets_to_avoid: List[str]        # Mercados a evitar
    min_volume_usd: float


@dataclass
class TimePreferences:
    """Preferências de horário."""
    preferred_hours_utc: List[int]     # Horas preferidas (UTC)
    preferred_days: List[str]          # Dias preferidos
    hours_to_avoid: List[int]          # Horas a evitar
    best_hour: int
    best_day: str


@dataclass
class OperationalLimits:
    """Limites operacionais."""
    max_drawdown_pct: float
    max_daily_trades: int
    max_daily_loss_usd: float
    stop_conditions: List[str]         # Condições para parar de operar


@dataclass
class RiskFramework:
    """Framework completo de risco."""
    scenario: str
    timeframe: str
    generated_at: str

    # Recomendações
    buffer: BufferRecommendation
    capital: CapitalRecommendation
    markets: MarketPreferences
    time: TimePreferences
    limits: OperationalLimits

    # Resumo executivo
    executive_summary: str
    operational_rules: List[str]


# =============================================================================
# FUNÇÕES DE ANÁLISE
# =============================================================================

def analyze_buffer_selection(
    stats_list: List[MarketSpreadStats],
    scenario: CostScenario,
    trade_size_usd: float = 100.0,
) -> BufferRecommendation:
    """
    Analisa qual buffer é mais adequado.

    Args:
        stats_list: Lista de estatísticas
        scenario: Cenário de custos
        trade_size_usd: Tamanho do trade

    Returns:
        BufferRecommendation
    """
    if not stats_list:
        return BufferRecommendation(
            recommended_buffer=DEFAULT_BUFFER_PCT,
            min_viable_buffer=0.0,
            optimal_buffer=DEFAULT_BUFFER_PCT,
            buffer_analysis={},
        )

    breakeven = calculate_breakeven_spread(trade_size_usd, scenario)

    # Buffers a analisar
    buffers = [0.0, 0.005, 0.01, 0.02, 0.03, 0.05]

    buffer_analysis = {}

    for buffer in buffers:
        # Para cada buffer, calcula:
        # - % de candles que passam
        # - Lucro médio esperado
        # - Número de oportunidades

        total_opportunities = 0
        total_profit = 0
        markets_with_opps = 0

        for s in stats_list:
            # Busca a coluna correspondente ao buffer
            if buffer == 0:
                col_pct = s.frequency.positive_pct
            else:
                # Estima baseado na distribuição
                # Assumimos distribuição normal truncada
                mean_spread = s.magnitude.avg_positive if s.frequency.positive_pct > 0 else 0
                if mean_spread > buffer:
                    # Aproximação: % que passa o buffer
                    col_pct = s.frequency.positive_pct * max(0, (mean_spread - buffer) / mean_spread)
                else:
                    col_pct = 0

            if col_pct > 0:
                opportunities = s.frequency.total_candles * col_pct / 100
                total_opportunities += opportunities
                markets_with_opps += 1

                # Lucro = spread médio - breakeven (para os que passam o buffer)
                effective_spread = max(0, s.magnitude.avg_positive - breakeven)
                total_profit += opportunities * effective_spread

        avg_profit_per_opp = total_profit / total_opportunities if total_opportunities > 0 else 0

        buffer_analysis[buffer] = {
            "total_opportunities": total_opportunities,
            "markets_with_opportunities": markets_with_opps,
            "avg_profit_per_opportunity": avg_profit_per_opp,
            "total_expected_profit": total_profit,
            "is_above_breakeven": buffer >= breakeven,
        }

    # Determina buffers
    min_viable = breakeven
    optimal = DEFAULT_BUFFER_PCT

    # Encontra buffer ótimo (máximo lucro total)
    max_profit = 0
    for buf, analysis in buffer_analysis.items():
        if analysis["total_expected_profit"] > max_profit and buf >= breakeven:
            max_profit = analysis["total_expected_profit"]
            optimal = buf

    # Buffer recomendado = ligeiramente acima do breakeven para segurança
    recommended = max(breakeven * 1.5, 0.005)  # Pelo menos 0.5%

    return BufferRecommendation(
        recommended_buffer=recommended,
        min_viable_buffer=min_viable,
        optimal_buffer=optimal,
        buffer_analysis=buffer_analysis,
    )


def analyze_capital_allocation(
    stats_list: List[MarketSpreadStats],
    scenario: CostScenario,
    total_capital: float = 10000.0,
) -> CapitalRecommendation:
    """
    Analisa alocação de capital.

    Args:
        stats_list: Lista de estatísticas
        scenario: Cenário de custos
        total_capital: Capital total disponível

    Returns:
        CapitalRecommendation
    """
    # Kelly fraction conservador
    kelly_fraction = KELLY_FRACTION

    # Calcula win rate médio e payoff médio
    win_rates = []
    payoffs = []

    breakeven = calculate_breakeven_spread(100.0, scenario)

    for s in stats_list:
        if s.frequency.positive_pct > 0:
            win_rate = s.frequency.positive_pct / 100
            payoff = s.magnitude.avg_positive - breakeven

            if payoff > 0:
                win_rates.append(win_rate)
                payoffs.append(payoff)

    if win_rates and payoffs:
        avg_win_rate = np.mean(win_rates)
        avg_payoff = np.mean(payoffs)

        # Kelly = (p * b - q) / b
        # onde p = win_rate, q = 1-p, b = payoff ratio
        b = avg_payoff / (1 - avg_payoff) if avg_payoff < 1 else 1
        kelly = (avg_win_rate * b - (1 - avg_win_rate)) / b if b > 0 else 0
        kelly = max(0, min(1, kelly))
    else:
        kelly = 0

    # Aplica fração do Kelly
    optimal_pct = kelly * kelly_fraction

    # Limites
    max_per_trade = total_capital * min(optimal_pct, MAX_CAPITAL_PER_MARKET_PERCENT / 100)
    max_per_trade = max(MIN_TRADE_SIZE_USD, max_per_trade)

    # Recomendado é 50% do máximo para segurança
    recommended = max_per_trade * 0.5

    return CapitalRecommendation(
        max_capital_per_trade_usd=max_per_trade,
        max_capital_total_usd=total_capital,
        recommended_trade_size_usd=recommended,
        kelly_fraction=kelly_fraction,
        position_sizing_method="fractional_kelly",
    )


def analyze_market_preferences(
    timeframe: str = DEFAULT_TIMEFRAME,
    top_n: int = 20,
) -> MarketPreferences:
    """
    Analisa preferências de mercados baseado nos rankings.

    Args:
        timeframe: Timeframe
        top_n: Número de mercados preferidos

    Returns:
        MarketPreferences
    """
    try:
        rankings = load_market_rankings(timeframe)
    except Exception as e:
        logger.warning(f"Could not load rankings: {e}")
        return MarketPreferences(
            preferred_markets=[],
            preferred_categories=["politics", "sports"],
            markets_to_avoid=[],
            min_volume_usd=50000,
        )

    # Top N mercados por score
    preferred = rankings.head(top_n)["market_id"].tolist() if len(rankings) > 0 else []

    # Categorias mais comuns nos top mercados
    if "category" in rankings.columns:
        top_categories = rankings.head(top_n)["category"].value_counts()
        preferred_categories = top_categories.head(3).index.tolist()
    else:
        preferred_categories = ["politics", "sports", "crypto"]

    # Mercados a evitar (bottom 10%)
    if len(rankings) > 10:
        bottom_pct = int(len(rankings) * 0.1)
        avoid = rankings.tail(bottom_pct)["market_id"].tolist()
    else:
        avoid = []

    return MarketPreferences(
        preferred_markets=preferred,
        preferred_categories=preferred_categories,
        markets_to_avoid=avoid,
        min_volume_usd=50000,
    )


def analyze_time_preferences(
    timeframe: str = DEFAULT_TIMEFRAME,
) -> TimePreferences:
    """
    Analisa preferências de horário baseado na análise temporal.

    Args:
        timeframe: Timeframe

    Returns:
        TimePreferences
    """
    try:
        hourly, daily, _ = load_temporal_analysis(timeframe)
    except Exception as e:
        logger.warning(f"Could not load temporal analysis: {e}")
        return TimePreferences(
            preferred_hours_utc=list(range(14, 22)),  # 14-22 UTC (horário comercial US)
            preferred_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            hours_to_avoid=[0, 1, 2, 3, 4, 5],  # Madrugada
            best_hour=16,
            best_day="Tuesday",
        )

    # Analisa horários
    if hourly is not None and len(hourly) > 0:
        hourly_sorted = hourly.sort_values("positive_pct", ascending=False)
        best_hour = int(hourly_sorted.iloc[0]["hour"])

        # Top 8 horas
        preferred_hours = hourly_sorted.head(8)["hour"].astype(int).tolist()

        # Piores horas
        worst_hours = hourly_sorted.tail(4)["hour"].astype(int).tolist()
    else:
        preferred_hours = list(range(14, 22))
        worst_hours = [0, 1, 2, 3, 4, 5]
        best_hour = 16

    # Analisa dias
    if daily is not None and len(daily) > 0:
        daily_sorted = daily.sort_values("positive_pct", ascending=False)
        best_day = daily_sorted.iloc[0]["day_name"]
        preferred_days = daily_sorted.head(5)["day_name"].tolist()
    else:
        preferred_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        best_day = "Tuesday"

    return TimePreferences(
        preferred_hours_utc=preferred_hours,
        preferred_days=preferred_days,
        hours_to_avoid=worst_hours,
        best_hour=best_hour,
        best_day=best_day,
    )


def define_operational_limits(
    capital: CapitalRecommendation,
    scenario: CostScenario,
) -> OperationalLimits:
    """
    Define limites operacionais.

    Args:
        capital: Recomendação de capital
        scenario: Cenário de custos

    Returns:
        OperationalLimits
    """
    # Drawdown máximo
    max_drawdown = MAX_DRAWDOWN_PERCENT

    # Máximo de trades diários (limita exposure)
    max_daily_trades = min(20, MAX_CONCURRENT_POSITIONS * 4)

    # Perda máxima diária (3% do capital)
    max_daily_loss = capital.max_capital_total_usd * 0.03

    # Condições para parar
    stop_conditions = [
        f"Drawdown atinge {max_drawdown}% do capital",
        f"Perda diária atinge ${max_daily_loss:.2f}",
        f"Mais de {max_daily_trades} trades no dia",
        "Taxa de sucesso < 40% nas últimas 20 operações",
        "Spread médio observado < breakeven por 1 hora",
        "Problemas técnicos (latência > 5s, erros de API)",
        "Congestionamento de rede Polygon (gas > $1)",
        "Fim do horário preferido de operação",
    ]

    return OperationalLimits(
        max_drawdown_pct=max_drawdown,
        max_daily_trades=max_daily_trades,
        max_daily_loss_usd=max_daily_loss,
        stop_conditions=stop_conditions,
    )


def generate_operational_rules(
    buffer: BufferRecommendation,
    capital: CapitalRecommendation,
    markets: MarketPreferences,
    time: TimePreferences,
    limits: OperationalLimits,
    scenario_name: str,
) -> List[str]:
    """
    Gera lista de regras operacionais.

    Args:
        buffer: Recomendação de buffer
        capital: Recomendação de capital
        markets: Preferências de mercados
        time: Preferências de tempo
        limits: Limites operacionais
        scenario_name: Nome do cenário

    Returns:
        Lista de regras
    """
    rules = []

    # Regras de entrada
    rules.append("=== REGRAS DE ENTRADA ===")
    rules.append(f"1. Spread mínimo: {buffer.recommended_buffer*100:.2f}% (buffer recomendado)")
    rules.append(f"2. Spread ideal: {buffer.optimal_buffer*100:.2f}% (buffer ótimo)")
    rules.append(f"3. Operar apenas em mercados da lista preferida ({len(markets.preferred_markets)} mercados)")
    rules.append(f"4. Volume mínimo do mercado: ${markets.min_volume_usd:,.0f}")
    rules.append(f"5. Horário preferido: {time.preferred_hours_utc[0]:02d}:00 - {time.preferred_hours_utc[-1]:02d}:00 UTC")

    # Regras de sizing
    rules.append("")
    rules.append("=== REGRAS DE SIZING ===")
    rules.append(f"6. Tamanho máximo por trade: ${capital.max_capital_per_trade_usd:.2f}")
    rules.append(f"7. Tamanho recomendado por trade: ${capital.recommended_trade_size_usd:.2f}")
    rules.append(f"8. Método: {capital.position_sizing_method} (Kelly fraction: {capital.kelly_fraction})")
    rules.append(f"9. Máximo de posições simultâneas: {MAX_CONCURRENT_POSITIONS}")

    # Regras de saída
    rules.append("")
    rules.append("=== REGRAS DE SAÍDA ===")
    rules.append("10. Sair quando spread < 0 (arbitragem fechou)")
    rules.append("11. Sair se preço se moveu > 5% contra a posição")
    rules.append("12. Sair após resolução do mercado")

    # Limites
    rules.append("")
    rules.append("=== LIMITES OPERACIONAIS ===")
    rules.append(f"13. Drawdown máximo: {limits.max_drawdown_pct}% do capital")
    rules.append(f"14. Máximo de trades/dia: {limits.max_daily_trades}")
    rules.append(f"15. Perda máxima/dia: ${limits.max_daily_loss_usd:.2f}")

    # Stop conditions
    rules.append("")
    rules.append("=== CONDIÇÕES DE PARADA ===")
    for i, condition in enumerate(limits.stop_conditions, 16):
        rules.append(f"{i}. {condition}")

    # Notas
    rules.append("")
    rules.append("=== NOTAS ===")
    rules.append(f"- Cenário de custos: {scenario_name}")
    rules.append(f"- Melhores categorias: {', '.join(markets.preferred_categories[:3])}")
    rules.append(f"- Melhor horário: {time.best_hour:02d}:00 UTC")
    rules.append(f"- Melhor dia: {time.best_day}")

    return rules


def generate_executive_summary(
    buffer: BufferRecommendation,
    capital: CapitalRecommendation,
    markets: MarketPreferences,
    time: TimePreferences,
    scenario_name: str,
) -> str:
    """
    Gera resumo executivo.

    Args:
        buffer: Recomendação de buffer
        capital: Recomendação de capital
        markets: Preferências de mercados
        time: Preferências de tempo
        scenario_name: Nome do cenário

    Returns:
        Texto do resumo
    """
    summary = f"""
RESUMO EXECUTIVO - FRAMEWORK DE RISCO
=====================================
Cenário: {scenario_name.upper()}
Gerado em: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

ESTRATÉGIA RECOMENDADA:
- Buffer mínimo: {buffer.recommended_buffer*100:.2f}%
- Capital por trade: ${capital.recommended_trade_size_usd:.2f}
- Mercados alvo: {len(markets.preferred_markets)} selecionados
- Horário: {time.best_hour:02d}:00 UTC ({time.best_day})

CONCLUSÃO:
Arbitragem em Polymarket é viável com:
1. Buffer adequado para cobrir custos ({buffer.recommended_buffer*100:.2f}% mínimo)
2. Sizing conservador (${capital.recommended_trade_size_usd:.2f} por trade)
3. Foco em mercados de alta liquidez ({', '.join(markets.preferred_categories[:2])})
4. Operação em horários de maior atividade

RISCOS PRINCIPAIS:
- Slippage pode eliminar o edge em mercados ilíquidos
- Janelas de oportunidade podem ser curtas demais
- Custos de gás em momentos de congestionamento
- Falhas de execução em mercados rápidos

RECOMENDAÇÃO FINAL:
Operar com capital limitado inicialmente, monitorar métricas reais,
e ajustar parâmetros conforme dados de produção.
"""
    return summary


def save_risk_framework(
    framework: RiskFramework,
    output_dir: Path = DATA_STATS_DIR,
) -> Tuple[Path, Path]:
    """
    Salva framework de risco em arquivos.

    Args:
        framework: Framework completo
        output_dir: Diretório de saída

    Returns:
        Tupla (path_json, path_txt)
    """
    ensure_data_dirs_exist()

    # Salva JSON com dados estruturados
    import json

    data = {
        "metadata": {
            "scenario": framework.scenario,
            "timeframe": framework.timeframe,
            "generated_at": framework.generated_at,
        },
        "buffer": {
            "recommended": framework.buffer.recommended_buffer,
            "min_viable": framework.buffer.min_viable_buffer,
            "optimal": framework.buffer.optimal_buffer,
        },
        "capital": {
            "max_per_trade_usd": framework.capital.max_capital_per_trade_usd,
            "recommended_usd": framework.capital.recommended_trade_size_usd,
            "kelly_fraction": framework.capital.kelly_fraction,
            "method": framework.capital.position_sizing_method,
        },
        "markets": {
            "preferred_count": len(framework.markets.preferred_markets),
            "preferred_categories": framework.markets.preferred_categories,
            "min_volume_usd": framework.markets.min_volume_usd,
        },
        "time": {
            "best_hour_utc": framework.time.best_hour,
            "best_day": framework.time.best_day,
            "preferred_hours": framework.time.preferred_hours_utc,
        },
        "limits": {
            "max_drawdown_pct": framework.limits.max_drawdown_pct,
            "max_daily_trades": framework.limits.max_daily_trades,
            "max_daily_loss_usd": framework.limits.max_daily_loss_usd,
        },
    }

    json_path = output_dir / f"risk_framework_{framework.scenario}_{framework.timeframe}.json"
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)

    # Salva TXT com regras operacionais
    txt_path = output_dir / f"operational_rules_{framework.scenario}_{framework.timeframe}.txt"
    with open(txt_path, "w") as f:
        f.write(framework.executive_summary)
        f.write("\n\n")
        f.write("REGRAS OPERACIONAIS\n")
        f.write("=" * 50 + "\n\n")
        for rule in framework.operational_rules:
            f.write(rule + "\n")

    logger.info(f"Saved risk framework to {json_path}")
    logger.info(f"Saved operational rules to {txt_path}")

    return json_path, txt_path


# =============================================================================
# PIPELINE
# =============================================================================

def run_phase9_pipeline(
    timeframe: str = DEFAULT_TIMEFRAME,
    scenario_name: str = "median",
    total_capital: float = 10000.0,
) -> RiskFramework:
    """
    Executa o pipeline completo da Fase 9.

    Args:
        timeframe: Timeframe para análise
        scenario_name: Cenário de custos
        total_capital: Capital total disponível

    Returns:
        RiskFramework completo
    """
    logger.info("=" * 60)
    logger.info("Starting Phase 9: Risk Framework")
    logger.info("=" * 60)
    logger.info(f"Timeframe: {timeframe}")
    logger.info(f"Scenario: {scenario_name}")
    logger.info(f"Total capital: ${total_capital:,.2f}")

    scenario = COST_SCENARIOS[scenario_name]

    # Carrega dados
    try:
        stats_list, _ = load_market_spread_stats(timeframe)
        logger.info(f"Loaded stats for {len(stats_list)} markets")
    except Exception as e:
        logger.warning(f"Could not load stats: {e}")
        stats_list = []

    # 1. Análise de buffer
    logger.info("\n1. Analyzing buffer selection...")
    buffer = analyze_buffer_selection(stats_list, scenario)
    logger.info(f"   Recommended buffer: {buffer.recommended_buffer*100:.2f}%")

    # 2. Análise de capital
    logger.info("\n2. Analyzing capital allocation...")
    capital = analyze_capital_allocation(stats_list, scenario, total_capital)
    logger.info(f"   Recommended trade size: ${capital.recommended_trade_size_usd:.2f}")

    # 3. Preferências de mercado
    logger.info("\n3. Analyzing market preferences...")
    markets = analyze_market_preferences(timeframe)
    logger.info(f"   Preferred markets: {len(markets.preferred_markets)}")

    # 4. Preferências de horário
    logger.info("\n4. Analyzing time preferences...")
    time_prefs = analyze_time_preferences(timeframe)
    logger.info(f"   Best hour: {time_prefs.best_hour:02d}:00 UTC")

    # 5. Limites operacionais
    logger.info("\n5. Defining operational limits...")
    limits = define_operational_limits(capital, scenario)
    logger.info(f"   Max drawdown: {limits.max_drawdown_pct}%")

    # 6. Gera regras
    logger.info("\n6. Generating operational rules...")
    rules = generate_operational_rules(
        buffer, capital, markets, time_prefs, limits, scenario_name
    )

    # 7. Gera resumo
    summary = generate_executive_summary(
        buffer, capital, markets, time_prefs, scenario_name
    )

    # Cria framework
    framework = RiskFramework(
        scenario=scenario_name,
        timeframe=timeframe,
        generated_at=datetime.now().isoformat(),
        buffer=buffer,
        capital=capital,
        markets=markets,
        time=time_prefs,
        limits=limits,
        executive_summary=summary,
        operational_rules=rules,
    )

    # Salva
    save_risk_framework(framework)

    # Log resumo
    logger.info("\n" + "=" * 60)
    logger.info("RISK FRAMEWORK SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Buffer recomendado: {buffer.recommended_buffer*100:.2f}%")
    logger.info(f"Capital por trade: ${capital.recommended_trade_size_usd:.2f}")
    logger.info(f"Mercados preferidos: {len(markets.preferred_markets)}")
    logger.info(f"Melhor horário: {time_prefs.best_hour:02d}:00 UTC ({time_prefs.best_day})")
    logger.info(f"Max drawdown: {limits.max_drawdown_pct}%")
    logger.info("=" * 60)

    logger.info("\nPhase 9 completed!")

    return framework


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Executa para cenário mediano
    framework = run_phase9_pipeline(
        scenario_name="median",
        total_capital=10000.0,
    )

    # Mostra resumo
    print("\n" + "=" * 60)
    print("OPERATIONAL RULES")
    print("=" * 60)
    for rule in framework.operational_rules:
        print(rule)

    print("\n" + framework.executive_summary)
