"""
Fase 8 - Validação de Edge

Responde às três perguntas fundamentais sobre arbitragem:
1. O edge existe? (% de mercados, ganho médio ajustado)
2. O edge é capturável? (janelas longas, liquidez, frequência)
3. O edge é escalável? (capital acceptance, book depth, inventory risk)
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import pandas as pd
import numpy as np
from scipy import stats

from config.settings import (
    DATA_STATS_DIR,
    DATA_PROCESSED_DIR,
    DEFAULT_TIMEFRAME,
    ensure_data_dirs_exist,
)
from pipeline.phase3_arbitrage_series import load_arbitrage_series
from pipeline.phase4_stats_spread import (
    load_market_spread_stats,
    MarketSpreadStats,
)
from pipeline.phase7_cost_model import (
    calculate_breakeven_spread,
    COST_SCENARIOS,
    CostScenario,
    POLYMARKET_FEE_PCT,
)
from pipeline.phase1_market_selection import load_markets_from_json

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

# Janela mínima (em candles) para ser considerada capturável
MIN_WINDOW_CANDLES = 3  # Pelo menos 3 candles para execução humana

# Janela ideal (em candles) para bot automatizado
IDEAL_WINDOW_CANDLES = 10

# Frequência mínima de oportunidades por dia para ser interessante
MIN_DAILY_OPPORTUNITIES = 1

# Volume mínimo para considerar liquidez aceitável (USD)
MIN_LIQUIDITY_USD = 10_000

# Capital máximo como % do volume diário
MAX_CAPITAL_AS_PCT_OF_VOLUME = 0.05  # 5% do volume diário


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class EdgeExistence:
    """Análise: O edge existe?"""
    edge_exists: bool
    markets_with_positive_spread: int
    total_markets: int
    pct_markets_with_edge: float

    # Ajustado por custos
    markets_with_net_positive: int
    pct_markets_net_positive: float

    # Magnitude
    avg_gross_spread: float          # Spread bruto médio
    avg_net_spread: float            # Spread líquido médio (após custos)
    median_gross_spread: float
    median_net_spread: float

    # Estatística
    is_statistically_significant: bool
    t_statistic: float
    p_value: float
    confidence_level: float

    summary: str


@dataclass
class EdgeCapturability:
    """Análise: O edge é capturável?"""
    is_capturable: bool

    # Janelas de oportunidade
    avg_window_duration_candles: float
    median_window_duration_candles: float
    pct_windows_gte_min: float       # % de janelas >= MIN_WINDOW_CANDLES
    pct_windows_gte_ideal: float     # % de janelas >= IDEAL_WINDOW_CANDLES

    # Frequência
    avg_opportunities_per_day: float
    markets_with_daily_opportunities: int

    # Liquidez
    markets_with_sufficient_liquidity: int
    avg_volume_usd: float

    summary: str


@dataclass
class EdgeScalability:
    """Análise: O edge é escalável?"""
    is_scalable: bool

    # Capital acceptance
    max_capital_per_trade_usd: float
    avg_max_capital_usd: float

    # Profundidade
    estimated_book_depth_usd: float

    # Risco de inventário
    inventory_turnover_days: float
    max_holding_period_days: float

    # Capacidade total
    total_addressable_capital_usd: float
    daily_expected_profit_usd: float

    summary: str


@dataclass
class EdgeValidationResult:
    """Resultado completo da validação de edge."""
    timeframe: str
    scenario: str

    existence: EdgeExistence
    capturability: EdgeCapturability
    scalability: EdgeScalability

    # Conclusão
    overall_viable: bool
    recommendation: str


# =============================================================================
# FUNÇÕES DE ANÁLISE
# =============================================================================

def analyze_edge_existence(
    stats_list: List[MarketSpreadStats],
    scenario: CostScenario,
    trade_size_usd: float = 100.0,
    confidence: float = 0.95,
) -> EdgeExistence:
    """
    Analisa se o edge existe e é estatisticamente significativo.

    Args:
        stats_list: Lista de estatísticas de spread por mercado
        scenario: Cenário de custos
        trade_size_usd: Tamanho do trade para cálculo de breakeven
        confidence: Nível de confiança para teste estatístico

    Returns:
        EdgeExistence com análise completa
    """
    if not stats_list:
        return EdgeExistence(
            edge_exists=False,
            markets_with_positive_spread=0,
            total_markets=0,
            pct_markets_with_edge=0.0,
            markets_with_net_positive=0,
            pct_markets_net_positive=0.0,
            avg_gross_spread=0.0,
            avg_net_spread=0.0,
            median_gross_spread=0.0,
            median_net_spread=0.0,
            is_statistically_significant=False,
            t_statistic=0.0,
            p_value=1.0,
            confidence_level=confidence,
            summary="Sem dados para análise",
        )

    # Calcula breakeven
    breakeven = calculate_breakeven_spread(trade_size_usd, scenario)

    # Spreads brutos (média positiva de cada mercado)
    gross_spreads = []
    for s in stats_list:
        if s.frequency.positive_pct > 0:
            gross_spreads.append(s.magnitude.avg_positive)

    # Spreads líquidos (após custos)
    net_spreads = [s - breakeven for s in gross_spreads]

    # Contagens
    markets_with_positive = len([s for s in stats_list if s.frequency.positive_pct > 0])
    markets_with_net_positive = len([n for n in net_spreads if n > 0])

    # Médias
    avg_gross = np.mean(gross_spreads) if gross_spreads else 0.0
    avg_net = np.mean(net_spreads) if net_spreads else 0.0
    median_gross = np.median(gross_spreads) if gross_spreads else 0.0
    median_net = np.median(net_spreads) if net_spreads else 0.0

    # Teste estatístico: spread líquido > 0?
    is_significant = False
    t_stat = 0.0
    p_val = 1.0

    if len(net_spreads) >= 30:
        t_stat, p_two_sided = stats.ttest_1samp(net_spreads, 0)
        p_val = p_two_sided / 2 if t_stat > 0 else 1.0
        is_significant = (p_val < (1 - confidence)) and (t_stat > 0)

    # Edge existe?
    edge_exists = (
        markets_with_net_positive >= 3 and
        avg_net > 0 and
        (is_significant or len(net_spreads) < 30)
    )

    # Resumo
    if edge_exists:
        summary = (
            f"EDGE EXISTE: {markets_with_net_positive}/{len(stats_list)} mercados "
            f"({markets_with_net_positive/len(stats_list)*100:.1f}%) com spread líquido positivo. "
            f"Média líquida: {avg_net*100:.3f}%"
        )
    else:
        summary = (
            f"EDGE INSUFICIENTE: Apenas {markets_with_net_positive}/{len(stats_list)} mercados "
            f"com spread líquido positivo após custos. "
            f"Breakeven: {breakeven*100:.3f}%"
        )

    return EdgeExistence(
        edge_exists=edge_exists,
        markets_with_positive_spread=markets_with_positive,
        total_markets=len(stats_list),
        pct_markets_with_edge=markets_with_positive / len(stats_list) * 100,
        markets_with_net_positive=markets_with_net_positive,
        pct_markets_net_positive=markets_with_net_positive / len(stats_list) * 100,
        avg_gross_spread=avg_gross,
        avg_net_spread=avg_net,
        median_gross_spread=median_gross,
        median_net_spread=median_net,
        is_statistically_significant=is_significant,
        t_statistic=t_stat,
        p_value=p_val,
        confidence_level=confidence,
        summary=summary,
    )


def analyze_edge_capturability(
    stats_list: List[MarketSpreadStats],
    timeframe: str = DEFAULT_TIMEFRAME,
) -> EdgeCapturability:
    """
    Analisa se o edge é capturável na prática.

    Considera:
    - Duração das janelas de oportunidade
    - Frequência das oportunidades
    - Liquidez dos mercados

    Args:
        stats_list: Lista de estatísticas
        timeframe: Timeframe para calcular oportunidades por dia

    Returns:
        EdgeCapturability com análise
    """
    if not stats_list:
        return EdgeCapturability(
            is_capturable=False,
            avg_window_duration_candles=0.0,
            median_window_duration_candles=0.0,
            pct_windows_gte_min=0.0,
            pct_windows_gte_ideal=0.0,
            avg_opportunities_per_day=0.0,
            markets_with_daily_opportunities=0,
            markets_with_sufficient_liquidity=0,
            avg_volume_usd=0.0,
            summary="Sem dados para análise",
        )

    # Converte timeframe para candles por dia
    timeframe_to_candles = {
        "1m": 1440,
        "5m": 288,
        "15m": 96,
        "1h": 24,
        "4h": 6,
        "1d": 1,
    }
    candles_per_day = timeframe_to_candles.get(timeframe, 24)

    # Coleta dados de runs (janelas)
    all_run_durations = []
    opportunities_per_day = []

    for s in stats_list:
        if s.runs.total_runs > 0:
            all_run_durations.append(s.runs.avg_run_length)
            # Estima oportunidades por dia
            total_candles = s.frequency.total_candles
            if total_candles > 0:
                days = total_candles / candles_per_day
                if days > 0:
                    opps = s.runs.total_runs / days
                    opportunities_per_day.append(opps)

    # Estatísticas de duração
    avg_duration = np.mean(all_run_durations) if all_run_durations else 0.0
    median_duration = np.median(all_run_durations) if all_run_durations else 0.0
    pct_gte_min = len([d for d in all_run_durations if d >= MIN_WINDOW_CANDLES]) / len(all_run_durations) * 100 if all_run_durations else 0.0
    pct_gte_ideal = len([d for d in all_run_durations if d >= IDEAL_WINDOW_CANDLES]) / len(all_run_durations) * 100 if all_run_durations else 0.0

    # Frequência
    avg_opps = np.mean(opportunities_per_day) if opportunities_per_day else 0.0
    markets_with_daily = len([o for o in opportunities_per_day if o >= MIN_DAILY_OPPORTUNITIES])

    # Liquidez (baseado no volume do mercado - placeholder)
    markets_with_liquidity = len(stats_list)  # Assumimos liquidez se temos dados
    avg_volume = 100_000  # Placeholder - seria necessário dados reais

    # É capturável?
    is_capturable = (
        avg_duration >= MIN_WINDOW_CANDLES and
        pct_gte_min >= 50 and
        avg_opps >= 0.5  # Pelo menos uma a cada 2 dias
    )

    # Resumo
    if is_capturable:
        summary = (
            f"CAPTURÁVEL: Janelas médias de {avg_duration:.1f} candles "
            f"({pct_gte_min:.1f}% >= {MIN_WINDOW_CANDLES}). "
            f"~{avg_opps:.1f} oportunidades/dia."
        )
    else:
        summary = (
            f"DIFÍCIL CAPTURAR: Janelas curtas ({avg_duration:.1f} candles) "
            f"ou pouco frequentes ({avg_opps:.1f}/dia)."
        )

    return EdgeCapturability(
        is_capturable=is_capturable,
        avg_window_duration_candles=avg_duration,
        median_window_duration_candles=median_duration,
        pct_windows_gte_min=pct_gte_min,
        pct_windows_gte_ideal=pct_gte_ideal,
        avg_opportunities_per_day=avg_opps,
        markets_with_daily_opportunities=markets_with_daily,
        markets_with_sufficient_liquidity=markets_with_liquidity,
        avg_volume_usd=avg_volume,
        summary=summary,
    )


def analyze_edge_scalability(
    stats_list: List[MarketSpreadStats],
    existence: EdgeExistence,
    capturability: EdgeCapturability,
    scenario: CostScenario,
    timeframe: str = DEFAULT_TIMEFRAME,
) -> EdgeScalability:
    """
    Analisa se o edge é escalável para capital significativo.

    Considera:
    - Quanto capital pode ser alocado por trade
    - Profundidade do order book
    - Risco de inventário

    Args:
        stats_list: Lista de estatísticas
        existence: Resultado da análise de existência
        capturability: Resultado da análise de capturabilidade
        scenario: Cenário de custos
        timeframe: Timeframe

    Returns:
        EdgeScalability com análise
    """
    if not stats_list or not existence.edge_exists:
        return EdgeScalability(
            is_scalable=False,
            max_capital_per_trade_usd=0.0,
            avg_max_capital_usd=0.0,
            estimated_book_depth_usd=0.0,
            inventory_turnover_days=float('inf'),
            max_holding_period_days=float('inf'),
            total_addressable_capital_usd=0.0,
            daily_expected_profit_usd=0.0,
            summary="Edge não existe ou não há dados",
        )

    # Estimativas baseadas em volume típico de Polymarket
    # (em produção, usaríamos dados reais de order book)

    # Capital máximo por trade: 5% do volume médio diário estimado
    estimated_daily_volume = capturability.avg_volume_usd
    max_capital_per_trade = estimated_daily_volume * MAX_CAPITAL_AS_PCT_OF_VOLUME

    # Profundidade estimada do book (placeholder)
    estimated_depth = max_capital_per_trade * 2

    # Turnover: quanto tempo para girar o inventário
    # Se temos N oportunidades por dia com capital C, giramos N*C por dia
    if capturability.avg_opportunities_per_day > 0 and max_capital_per_trade > 0:
        daily_turnover = capturability.avg_opportunities_per_day * max_capital_per_trade
        inventory_turnover = max_capital_per_trade / daily_turnover if daily_turnover > 0 else float('inf')
    else:
        inventory_turnover = float('inf')

    # Holding period máximo (baseado na duração média das janelas)
    timeframe_to_hours = {
        "1m": 1/60,
        "5m": 5/60,
        "15m": 15/60,
        "1h": 1,
        "4h": 4,
        "1d": 24,
    }
    hours_per_candle = timeframe_to_hours.get(timeframe, 1)
    max_holding = capturability.avg_window_duration_candles * hours_per_candle / 24  # em dias

    # Capital total endereçável
    num_viable_markets = existence.markets_with_net_positive
    total_capital = num_viable_markets * max_capital_per_trade

    # Lucro diário esperado
    if existence.avg_net_spread > 0 and capturability.avg_opportunities_per_day > 0:
        profit_per_trade = existence.avg_net_spread * max_capital_per_trade
        daily_profit = profit_per_trade * capturability.avg_opportunities_per_day * num_viable_markets
        # Ajusta pela taxa de sucesso
        daily_profit *= (1 - scenario.execution_failure_rate)
    else:
        daily_profit = 0.0

    # É escalável?
    is_scalable = (
        max_capital_per_trade >= 50 and  # Mínimo $50 por trade
        total_capital >= 1000 and         # Mínimo $1000 total
        daily_profit >= 1                  # Mínimo $1/dia
    )

    # Resumo
    if is_scalable:
        summary = (
            f"ESCALÁVEL: ~${max_capital_per_trade:.0f}/trade, "
            f"${total_capital:.0f} total endereçável, "
            f"~${daily_profit:.2f}/dia esperado."
        )
    else:
        summary = (
            f"BAIXA ESCALABILIDADE: ${max_capital_per_trade:.0f}/trade, "
            f"${daily_profit:.2f}/dia esperado."
        )

    return EdgeScalability(
        is_scalable=is_scalable,
        max_capital_per_trade_usd=max_capital_per_trade,
        avg_max_capital_usd=max_capital_per_trade,
        estimated_book_depth_usd=estimated_depth,
        inventory_turnover_days=inventory_turnover,
        max_holding_period_days=max_holding,
        total_addressable_capital_usd=total_capital,
        daily_expected_profit_usd=daily_profit,
        summary=summary,
    )


def validate_edge_complete(
    stats_list: List[MarketSpreadStats],
    timeframe: str = DEFAULT_TIMEFRAME,
    scenario_name: str = "median",
    trade_size_usd: float = 100.0,
) -> EdgeValidationResult:
    """
    Executa validação completa de edge.

    Args:
        stats_list: Lista de estatísticas de spread
        timeframe: Timeframe
        scenario_name: Cenário de custos
        trade_size_usd: Tamanho do trade

    Returns:
        EdgeValidationResult com todas as análises
    """
    scenario = COST_SCENARIOS[scenario_name]

    # 1. O edge existe?
    existence = analyze_edge_existence(
        stats_list=stats_list,
        scenario=scenario,
        trade_size_usd=trade_size_usd,
    )

    # 2. O edge é capturável?
    capturability = analyze_edge_capturability(
        stats_list=stats_list,
        timeframe=timeframe,
    )

    # 3. O edge é escalável?
    scalability = analyze_edge_scalability(
        stats_list=stats_list,
        existence=existence,
        capturability=capturability,
        scenario=scenario,
        timeframe=timeframe,
    )

    # Conclusão geral
    overall_viable = existence.edge_exists and capturability.is_capturable

    # Recomendação
    if overall_viable and scalability.is_scalable:
        recommendation = (
            "RECOMENDADO: Edge existe, é capturável e escalável. "
            f"Potencial de ${scalability.daily_expected_profit_usd:.2f}/dia."
        )
    elif overall_viable:
        recommendation = (
            "VIÁVEL COM LIMITAÇÕES: Edge existe e é capturável, mas "
            "escalabilidade limitada. Considere como renda extra, não principal."
        )
    elif existence.edge_exists:
        recommendation = (
            "NÃO RECOMENDADO: Edge existe mas é difícil de capturar. "
            "Janelas muito curtas ou infrequentes para execução prática."
        )
    else:
        recommendation = (
            "INVIÁVEL: Não há edge após custos de transação. "
            f"Breakeven requer spread > {calculate_breakeven_spread(trade_size_usd, scenario)*100:.3f}%."
        )

    return EdgeValidationResult(
        timeframe=timeframe,
        scenario=scenario_name,
        existence=existence,
        capturability=capturability,
        scalability=scalability,
        overall_viable=overall_viable,
        recommendation=recommendation,
    )


def save_edge_validation(
    result: EdgeValidationResult,
    output_dir: Path = DATA_STATS_DIR,
) -> Path:
    """
    Salva resultado da validação em arquivo.

    Args:
        result: Resultado da validação
        output_dir: Diretório de saída

    Returns:
        Path do arquivo salvo
    """
    ensure_data_dirs_exist()

    # Cria dicionário para salvar
    data = {
        "metadata": {
            "timeframe": result.timeframe,
            "scenario": result.scenario,
            "overall_viable": result.overall_viable,
            "recommendation": result.recommendation,
        },
        "existence": {
            "edge_exists": result.existence.edge_exists,
            "markets_with_positive_spread": result.existence.markets_with_positive_spread,
            "total_markets": result.existence.total_markets,
            "pct_markets_with_edge": result.existence.pct_markets_with_edge,
            "markets_with_net_positive": result.existence.markets_with_net_positive,
            "pct_markets_net_positive": result.existence.pct_markets_net_positive,
            "avg_gross_spread": result.existence.avg_gross_spread,
            "avg_net_spread": result.existence.avg_net_spread,
            "is_statistically_significant": result.existence.is_statistically_significant,
            "p_value": result.existence.p_value,
        },
        "capturability": {
            "is_capturable": result.capturability.is_capturable,
            "avg_window_duration_candles": result.capturability.avg_window_duration_candles,
            "pct_windows_gte_min": result.capturability.pct_windows_gte_min,
            "avg_opportunities_per_day": result.capturability.avg_opportunities_per_day,
            "markets_with_daily_opportunities": result.capturability.markets_with_daily_opportunities,
        },
        "scalability": {
            "is_scalable": result.scalability.is_scalable,
            "max_capital_per_trade_usd": result.scalability.max_capital_per_trade_usd,
            "total_addressable_capital_usd": result.scalability.total_addressable_capital_usd,
            "daily_expected_profit_usd": result.scalability.daily_expected_profit_usd,
        },
    }

    # Salva como JSON
    import json
    filename = f"edge_validation_{result.scenario}_{result.timeframe}.json"
    filepath = output_dir / filename

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Saved edge validation to {filepath}")
    return filepath


# =============================================================================
# PIPELINE
# =============================================================================

def run_phase8_pipeline(
    timeframe: str = DEFAULT_TIMEFRAME,
    scenario_name: str = "median",
    trade_size_usd: float = 100.0,
) -> EdgeValidationResult:
    """
    Executa o pipeline completo da Fase 8.

    Args:
        timeframe: Timeframe para análise
        scenario_name: Cenário de custos
        trade_size_usd: Tamanho do trade

    Returns:
        EdgeValidationResult com todas as análises
    """
    logger.info("=" * 60)
    logger.info("Starting Phase 8: Edge Validation")
    logger.info("=" * 60)
    logger.info(f"Timeframe: {timeframe}")
    logger.info(f"Scenario: {scenario_name}")
    logger.info(f"Trade size: ${trade_size_usd:.2f}")

    # Carrega estatísticas da Fase 4
    try:
        stats_list, _ = load_market_spread_stats(timeframe)
        logger.info(f"Loaded stats for {len(stats_list)} markets")
    except Exception as e:
        logger.error(f"Error loading stats: {e}")
        logger.info("Run Phase 4 first to generate spread statistics")
        stats_list = []

    # Executa validação
    result = validate_edge_complete(
        stats_list=stats_list,
        timeframe=timeframe,
        scenario_name=scenario_name,
        trade_size_usd=trade_size_usd,
    )

    # Salva resultado
    save_edge_validation(result)

    # Log resultados
    logger.info("\n" + "=" * 50)
    logger.info("EDGE VALIDATION RESULTS")
    logger.info("=" * 50)

    logger.info(f"\n1. O EDGE EXISTE?")
    logger.info(f"   {result.existence.summary}")

    logger.info(f"\n2. O EDGE É CAPTURÁVEL?")
    logger.info(f"   {result.capturability.summary}")

    logger.info(f"\n3. O EDGE É ESCALÁVEL?")
    logger.info(f"   {result.scalability.summary}")

    logger.info(f"\n" + "=" * 50)
    logger.info(f"CONCLUSÃO: {result.recommendation}")
    logger.info("=" * 50)

    logger.info("\nPhase 8 completed!")

    return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Executa para diferentes cenários
    for scenario in ["optimistic", "median", "pessimistic"]:
        print(f"\n{'='*60}")
        print(f"SCENARIO: {scenario.upper()}")
        print(f"{'='*60}")

        result = run_phase8_pipeline(scenario_name=scenario)

        print(f"\nExistence: {result.existence.edge_exists}")
        print(f"Capturability: {result.capturability.is_capturable}")
        print(f"Scalability: {result.scalability.is_scalable}")
        print(f"Overall: {result.overall_viable}")
        print(f"\n{result.recommendation}")
