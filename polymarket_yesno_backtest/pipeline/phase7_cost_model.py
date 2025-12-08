"""
Fase 7 - Modelo de Custos e Fricções

Calcula custos reais de operação para determinar lucro líquido:
- Fee do Polymarket (~2% sobre lucro)
- Custo de gás (Polygon)
- Slippage estimado (pior caso e mediano)
- Falhas de execução
- Net profit = spread - custos
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import pandas as pd
import numpy as np

from config.settings import (
    DATA_PROCESSED_DIR,
    DATA_STATS_DIR,
    DEFAULT_TIMEFRAME,
    ensure_data_dirs_exist,
)
from pipeline.phase3_arbitrage_series import load_arbitrage_series
from pipeline.phase1_market_selection import load_markets_from_json

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES DE CUSTO
# =============================================================================

# Fee do Polymarket (aproximadamente 2% sobre o lucro bruto)
POLYMARKET_FEE_PCT = 0.02

# Custos de gás na Polygon (em USD)
# Polygon é muito barato, mas precisamos somar
GAS_COST_USD_LOW = 0.01      # Cenário otimista
GAS_COST_USD_MEDIAN = 0.03   # Cenário mediano
GAS_COST_USD_HIGH = 0.10     # Cenário pessimista (congestionamento)

# Número de transações por arbitragem (compra YES + compra NO)
TRANSACTIONS_PER_ARBITRAGE = 2

# Slippage estimado (em % do valor negociado)
SLIPPAGE_PCT_LOW = 0.001     # 0.1% - cenário otimista
SLIPPAGE_PCT_MEDIAN = 0.005  # 0.5% - cenário mediano
SLIPPAGE_PCT_HIGH = 0.02     # 2.0% - cenário pessimista

# Taxa de falha de execução (% de operações que falham)
EXECUTION_FAILURE_RATE_LOW = 0.01     # 1%
EXECUTION_FAILURE_RATE_MEDIAN = 0.05  # 5%
EXECUTION_FAILURE_RATE_HIGH = 0.15    # 15%

# Capital mínimo para que os custos fixos sejam aceitáveis
MIN_TRADE_SIZE_USD = 50.0


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CostScenario:
    """Representa um cenário de custos."""
    name: str
    gas_cost_usd: float
    slippage_pct: float
    execution_failure_rate: float

    def total_fixed_cost_usd(self) -> float:
        """Custo fixo total por operação (gas × transações)."""
        return self.gas_cost_usd * TRANSACTIONS_PER_ARBITRAGE

    def total_variable_cost_pct(self, include_fee: bool = True) -> float:
        """Custo variável total como % do trade."""
        fee = POLYMARKET_FEE_PCT if include_fee else 0
        return fee + self.slippage_pct


@dataclass
class TradeAnalysis:
    """Análise de um trade individual."""
    spread: float                    # Spread bruto (1 - YES - NO)
    trade_size_usd: float           # Tamanho da operação em USD
    gross_profit_usd: float         # Lucro bruto = spread × trade_size

    # Custos
    fee_usd: float                  # Fee Polymarket
    gas_usd: float                  # Custo de gás
    slippage_usd: float             # Slippage estimado

    # Resultados
    total_cost_usd: float           # Custo total
    net_profit_usd: float           # Lucro líquido
    net_profit_pct: float           # Lucro líquido como % do capital
    is_profitable: bool             # Se o trade é lucrativo

    # Ajuste por falha
    expected_net_profit_usd: float  # Lucro esperado considerando falhas


@dataclass
class MarketCostAnalysis:
    """Análise de custos para um mercado completo."""
    market_id: str
    timeframe: str
    scenario: str

    # Estatísticas gerais
    total_candles: int
    positive_spread_candles: int

    # Análise de viabilidade
    viable_trades: int              # Trades com lucro líquido > 0
    non_viable_trades: int          # Trades com lucro líquido <= 0
    viability_rate: float           # % de trades viáveis

    # Lucros
    avg_gross_profit_pct: float     # Média do lucro bruto (% do capital)
    avg_net_profit_pct: float       # Média do lucro líquido (% do capital)
    total_gross_profit_pct: float   # Soma dos lucros brutos
    total_net_profit_pct: float     # Soma dos lucros líquidos

    # Custos
    avg_cost_pct: float             # Custo médio por trade (%)
    total_cost_pct: float           # Custo total acumulado

    # Breakeven
    min_spread_breakeven: float     # Spread mínimo para viabilidade

    # Ajustado por falhas
    expected_net_profit_pct: float  # Lucro esperado após falhas


@dataclass
class CostSummary:
    """Resumo consolidado de todos os mercados."""
    scenario: str
    timeframe: str

    # Contagens
    total_markets: int
    markets_with_viable_trades: int

    # Agregados
    total_viable_trades: int
    total_non_viable_trades: int
    overall_viability_rate: float

    # Lucros médios
    avg_net_profit_per_market_pct: float
    avg_net_profit_per_trade_pct: float

    # Breakeven
    avg_min_spread_breakeven: float

    # Top mercados
    top_markets: List[str] = field(default_factory=list)


# =============================================================================
# CENÁRIOS PRÉ-DEFINIDOS
# =============================================================================

COST_SCENARIOS = {
    "optimistic": CostScenario(
        name="optimistic",
        gas_cost_usd=GAS_COST_USD_LOW,
        slippage_pct=SLIPPAGE_PCT_LOW,
        execution_failure_rate=EXECUTION_FAILURE_RATE_LOW,
    ),
    "median": CostScenario(
        name="median",
        gas_cost_usd=GAS_COST_USD_MEDIAN,
        slippage_pct=SLIPPAGE_PCT_MEDIAN,
        execution_failure_rate=EXECUTION_FAILURE_RATE_MEDIAN,
    ),
    "pessimistic": CostScenario(
        name="pessimistic",
        gas_cost_usd=GAS_COST_USD_HIGH,
        slippage_pct=SLIPPAGE_PCT_HIGH,
        execution_failure_rate=EXECUTION_FAILURE_RATE_HIGH,
    ),
}


# =============================================================================
# FUNÇÕES DE CÁLCULO
# =============================================================================

def calculate_trade_costs(
    spread: float,
    trade_size_usd: float,
    scenario: CostScenario,
) -> TradeAnalysis:
    """
    Calcula custos e lucro líquido de um trade individual.

    Args:
        spread: Spread de arbitragem (1 - YES - NO)
        trade_size_usd: Valor investido em USD
        scenario: Cenário de custos

    Returns:
        TradeAnalysis com todos os custos e lucros
    """
    # Lucro bruto
    gross_profit_usd = spread * trade_size_usd

    # Custos
    fee_usd = gross_profit_usd * POLYMARKET_FEE_PCT
    gas_usd = scenario.total_fixed_cost_usd()
    slippage_usd = trade_size_usd * scenario.slippage_pct

    # Total de custos
    total_cost_usd = fee_usd + gas_usd + slippage_usd

    # Lucro líquido
    net_profit_usd = gross_profit_usd - total_cost_usd
    net_profit_pct = (net_profit_usd / trade_size_usd) * 100 if trade_size_usd > 0 else 0

    # É lucrativo?
    is_profitable = net_profit_usd > 0

    # Ajuste por taxa de falha
    success_rate = 1 - scenario.execution_failure_rate
    expected_net_profit_usd = net_profit_usd * success_rate

    return TradeAnalysis(
        spread=spread,
        trade_size_usd=trade_size_usd,
        gross_profit_usd=gross_profit_usd,
        fee_usd=fee_usd,
        gas_usd=gas_usd,
        slippage_usd=slippage_usd,
        total_cost_usd=total_cost_usd,
        net_profit_usd=net_profit_usd,
        net_profit_pct=net_profit_pct,
        is_profitable=is_profitable,
        expected_net_profit_usd=expected_net_profit_usd,
    )


def calculate_breakeven_spread(
    trade_size_usd: float,
    scenario: CostScenario,
) -> float:
    """
    Calcula o spread mínimo necessário para breakeven.

    Breakeven: gross_profit = total_cost
    spread × trade_size = (spread × trade_size × fee) + gas + (trade_size × slippage)
    spread × trade_size × (1 - fee) = gas + (trade_size × slippage)
    spread = (gas + trade_size × slippage) / (trade_size × (1 - fee))

    Args:
        trade_size_usd: Tamanho do trade
        scenario: Cenário de custos

    Returns:
        Spread mínimo para breakeven (em decimal, não %)
    """
    if trade_size_usd <= 0:
        return float('inf')

    gas = scenario.total_fixed_cost_usd()
    slippage = trade_size_usd * scenario.slippage_pct

    numerator = gas + slippage
    denominator = trade_size_usd * (1 - POLYMARKET_FEE_PCT)

    if denominator <= 0:
        return float('inf')

    return numerator / denominator


def analyze_market_costs(
    market_id: str,
    timeframe: str = DEFAULT_TIMEFRAME,
    trade_size_usd: float = 100.0,
    scenario_name: str = "median",
) -> Optional[MarketCostAnalysis]:
    """
    Analisa custos para todos os candles de um mercado.

    Args:
        market_id: ID do mercado
        timeframe: Timeframe
        trade_size_usd: Tamanho de cada trade
        scenario_name: Nome do cenário (optimistic/median/pessimistic)

    Returns:
        MarketCostAnalysis ou None se não houver dados
    """
    # Carrega série de arbitragem
    df = load_arbitrage_series(market_id, timeframe)
    if df is None or len(df) == 0:
        return None

    scenario = COST_SCENARIOS[scenario_name]

    # Filtra apenas candles com spread positivo
    df_positive = df[df["arbitrage_spread"] > 0].copy()

    if len(df_positive) == 0:
        return MarketCostAnalysis(
            market_id=market_id,
            timeframe=timeframe,
            scenario=scenario_name,
            total_candles=len(df),
            positive_spread_candles=0,
            viable_trades=0,
            non_viable_trades=0,
            viability_rate=0.0,
            avg_gross_profit_pct=0.0,
            avg_net_profit_pct=0.0,
            total_gross_profit_pct=0.0,
            total_net_profit_pct=0.0,
            avg_cost_pct=0.0,
            total_cost_pct=0.0,
            min_spread_breakeven=calculate_breakeven_spread(trade_size_usd, scenario),
            expected_net_profit_pct=0.0,
        )

    # Calcula custos para cada candle
    trades = []
    for _, row in df_positive.iterrows():
        trade = calculate_trade_costs(
            spread=row["arbitrage_spread"],
            trade_size_usd=trade_size_usd,
            scenario=scenario,
        )
        trades.append(trade)

    # Estatísticas
    viable = [t for t in trades if t.is_profitable]
    non_viable = [t for t in trades if not t.is_profitable]

    viability_rate = len(viable) / len(trades) * 100 if trades else 0

    # Lucros
    gross_profits = [t.gross_profit_usd / trade_size_usd * 100 for t in trades]
    net_profits = [t.net_profit_usd / trade_size_usd * 100 for t in trades]
    costs = [t.total_cost_usd / trade_size_usd * 100 for t in trades]

    # Breakeven
    min_spread_breakeven = calculate_breakeven_spread(trade_size_usd, scenario)

    # Expected profit (ajustado por falhas)
    success_rate = 1 - scenario.execution_failure_rate
    expected_net = sum(net_profits) * success_rate

    return MarketCostAnalysis(
        market_id=market_id,
        timeframe=timeframe,
        scenario=scenario_name,
        total_candles=len(df),
        positive_spread_candles=len(df_positive),
        viable_trades=len(viable),
        non_viable_trades=len(non_viable),
        viability_rate=viability_rate,
        avg_gross_profit_pct=float(np.mean(gross_profits)),
        avg_net_profit_pct=float(np.mean(net_profits)),
        total_gross_profit_pct=float(sum(gross_profits)),
        total_net_profit_pct=float(sum(net_profits)),
        avg_cost_pct=float(np.mean(costs)),
        total_cost_pct=float(sum(costs)),
        min_spread_breakeven=min_spread_breakeven,
        expected_net_profit_pct=expected_net,
    )


def analyze_all_markets_costs(
    market_ids: Optional[List[str]] = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    trade_size_usd: float = 100.0,
    scenario_name: str = "median",
) -> List[MarketCostAnalysis]:
    """
    Analisa custos para todos os mercados.

    Args:
        market_ids: Lista de IDs (se None, carrega do JSON)
        timeframe: Timeframe
        trade_size_usd: Tamanho de cada trade
        scenario_name: Cenário de custos

    Returns:
        Lista de MarketCostAnalysis
    """
    if market_ids is None:
        try:
            groups = load_markets_from_json()
            market_ids = [m.id for m in groups["A"] + groups["B"] + groups["C"]]
        except FileNotFoundError:
            logger.error("Markets JSON not found. Run Phase 1 first.")
            return []

    results = []
    total = len(market_ids)

    for i, market_id in enumerate(market_ids, 1):
        logger.info(f"Analyzing costs for market {i}/{total}: {market_id[:16]}...")

        analysis = analyze_market_costs(
            market_id=market_id,
            timeframe=timeframe,
            trade_size_usd=trade_size_usd,
            scenario_name=scenario_name,
        )

        if analysis is not None:
            results.append(analysis)

    logger.info(f"Analyzed {len(results)}/{total} markets")
    return results


def generate_cost_summary(
    analyses: List[MarketCostAnalysis],
    scenario_name: str,
    timeframe: str,
    top_n: int = 10,
) -> CostSummary:
    """
    Gera resumo consolidado de todas as análises.

    Args:
        analyses: Lista de análises por mercado
        scenario_name: Nome do cenário
        timeframe: Timeframe
        top_n: Número de top mercados a listar

    Returns:
        CostSummary
    """
    if not analyses:
        return CostSummary(
            scenario=scenario_name,
            timeframe=timeframe,
            total_markets=0,
            markets_with_viable_trades=0,
            total_viable_trades=0,
            total_non_viable_trades=0,
            overall_viability_rate=0.0,
            avg_net_profit_per_market_pct=0.0,
            avg_net_profit_per_trade_pct=0.0,
            avg_min_spread_breakeven=0.0,
            top_markets=[],
        )

    # Contagens
    markets_with_viable = [a for a in analyses if a.viable_trades > 0]
    total_viable = sum(a.viable_trades for a in analyses)
    total_non_viable = sum(a.non_viable_trades for a in analyses)

    total_trades = total_viable + total_non_viable
    overall_viability = (total_viable / total_trades * 100) if total_trades > 0 else 0

    # Médias
    avg_net_per_market = np.mean([a.total_net_profit_pct for a in analyses])

    # Média por trade (ponderada pelo número de trades)
    weighted_sum = sum(a.avg_net_profit_pct * a.positive_spread_candles for a in analyses)
    total_candles = sum(a.positive_spread_candles for a in analyses)
    avg_net_per_trade = weighted_sum / total_candles if total_candles > 0 else 0

    # Breakeven médio
    avg_breakeven = np.mean([a.min_spread_breakeven for a in analyses])

    # Top mercados por lucro líquido
    sorted_analyses = sorted(analyses, key=lambda x: x.total_net_profit_pct, reverse=True)
    top_markets = [a.market_id for a in sorted_analyses[:top_n]]

    return CostSummary(
        scenario=scenario_name,
        timeframe=timeframe,
        total_markets=len(analyses),
        markets_with_viable_trades=len(markets_with_viable),
        total_viable_trades=total_viable,
        total_non_viable_trades=total_non_viable,
        overall_viability_rate=overall_viability,
        avg_net_profit_per_market_pct=float(avg_net_per_market),
        avg_net_profit_per_trade_pct=float(avg_net_per_trade),
        avg_min_spread_breakeven=float(avg_breakeven),
        top_markets=top_markets,
    )


def compare_scenarios(
    market_ids: Optional[List[str]] = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    trade_size_usd: float = 100.0,
) -> Dict[str, CostSummary]:
    """
    Compara todos os cenários de custo.

    Args:
        market_ids: Lista de IDs de mercados
        timeframe: Timeframe
        trade_size_usd: Tamanho do trade

    Returns:
        Dicionário {scenario_name: CostSummary}
    """
    results = {}

    for scenario_name in COST_SCENARIOS.keys():
        logger.info(f"\n{'='*50}")
        logger.info(f"Analyzing scenario: {scenario_name.upper()}")
        logger.info(f"{'='*50}")

        analyses = analyze_all_markets_costs(
            market_ids=market_ids,
            timeframe=timeframe,
            trade_size_usd=trade_size_usd,
            scenario_name=scenario_name,
        )

        summary = generate_cost_summary(
            analyses=analyses,
            scenario_name=scenario_name,
            timeframe=timeframe,
        )

        results[scenario_name] = summary

        logger.info(f"  Viability rate: {summary.overall_viability_rate:.1f}%")
        logger.info(f"  Avg net profit/trade: {summary.avg_net_profit_per_trade_pct:.4f}%")
        logger.info(f"  Min breakeven spread: {summary.avg_min_spread_breakeven*100:.2f}%")

    return results


def save_cost_analysis(
    analyses: List[MarketCostAnalysis],
    output_dir: Path = DATA_STATS_DIR,
    scenario_name: str = "median",
    timeframe: str = DEFAULT_TIMEFRAME,
) -> Path:
    """
    Salva análise de custos em CSV.

    Args:
        analyses: Lista de análises
        output_dir: Diretório de saída
        scenario_name: Nome do cenário
        timeframe: Timeframe

    Returns:
        Path do arquivo salvo
    """
    ensure_data_dirs_exist()

    data = []
    for a in analyses:
        data.append({
            "market_id": a.market_id,
            "timeframe": a.timeframe,
            "scenario": a.scenario,
            "total_candles": a.total_candles,
            "positive_spread_candles": a.positive_spread_candles,
            "viable_trades": a.viable_trades,
            "non_viable_trades": a.non_viable_trades,
            "viability_rate": a.viability_rate,
            "avg_gross_profit_pct": a.avg_gross_profit_pct,
            "avg_net_profit_pct": a.avg_net_profit_pct,
            "total_gross_profit_pct": a.total_gross_profit_pct,
            "total_net_profit_pct": a.total_net_profit_pct,
            "avg_cost_pct": a.avg_cost_pct,
            "total_cost_pct": a.total_cost_pct,
            "min_spread_breakeven": a.min_spread_breakeven,
            "expected_net_profit_pct": a.expected_net_profit_pct,
        })

    df = pd.DataFrame(data)

    filename = f"cost_analysis_{scenario_name}_{timeframe}.csv"
    filepath = output_dir / filename
    df.to_csv(filepath, index=False)

    logger.info(f"Saved cost analysis to {filepath}")
    return filepath


# =============================================================================
# PIPELINE
# =============================================================================

def run_phase7_pipeline(
    market_ids: Optional[List[str]] = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    trade_size_usd: float = 100.0,
    scenarios: Optional[List[str]] = None,
) -> Tuple[Dict[str, List[MarketCostAnalysis]], Dict[str, CostSummary]]:
    """
    Executa o pipeline completo da Fase 7.

    Args:
        market_ids: Lista de IDs (carrega do JSON se None)
        timeframe: Timeframe para análise
        trade_size_usd: Tamanho de cada trade
        scenarios: Lista de cenários (todos se None)

    Returns:
        Tupla (analyses_by_scenario, summaries_by_scenario)
    """
    logger.info("=" * 60)
    logger.info("Starting Phase 7: Cost Model Analysis")
    logger.info("=" * 60)
    logger.info(f"Trade size: ${trade_size_usd:.2f}")
    logger.info(f"Polymarket fee: {POLYMARKET_FEE_PCT*100:.1f}%")

    if scenarios is None:
        scenarios = list(COST_SCENARIOS.keys())

    all_analyses = {}
    all_summaries = {}

    for scenario_name in scenarios:
        scenario = COST_SCENARIOS[scenario_name]
        logger.info(f"\n{'='*50}")
        logger.info(f"Scenario: {scenario_name.upper()}")
        logger.info(f"  Gas cost: ${scenario.gas_cost_usd:.2f} per tx")
        logger.info(f"  Slippage: {scenario.slippage_pct*100:.2f}%")
        logger.info(f"  Failure rate: {scenario.execution_failure_rate*100:.1f}%")
        logger.info(f"{'='*50}")

        # Analisa mercados
        analyses = analyze_all_markets_costs(
            market_ids=market_ids,
            timeframe=timeframe,
            trade_size_usd=trade_size_usd,
            scenario_name=scenario_name,
        )

        # Gera resumo
        summary = generate_cost_summary(
            analyses=analyses,
            scenario_name=scenario_name,
            timeframe=timeframe,
        )

        # Salva CSV
        save_cost_analysis(
            analyses=analyses,
            scenario_name=scenario_name,
            timeframe=timeframe,
        )

        all_analyses[scenario_name] = analyses
        all_summaries[scenario_name] = summary

        # Log resumo
        logger.info(f"\nSummary for {scenario_name}:")
        logger.info(f"  Markets analyzed: {summary.total_markets}")
        logger.info(f"  Markets with viable trades: {summary.markets_with_viable_trades}")
        logger.info(f"  Total viable trades: {summary.total_viable_trades}")
        logger.info(f"  Overall viability: {summary.overall_viability_rate:.1f}%")
        logger.info(f"  Avg net profit/trade: {summary.avg_net_profit_per_trade_pct:.4f}%")
        logger.info(f"  Min breakeven spread: {summary.avg_min_spread_breakeven*100:.3f}%")

    logger.info("\n" + "=" * 60)
    logger.info("Phase 7 completed!")
    logger.info("=" * 60)

    return all_analyses, all_summaries


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Executa pipeline
    analyses, summaries = run_phase7_pipeline(trade_size_usd=100.0)

    # Mostra comparação
    print("\n" + "=" * 60)
    print("SCENARIO COMPARISON")
    print("=" * 60)

    for scenario_name, summary in summaries.items():
        print(f"\n{scenario_name.upper()}:")
        print(f"  Viability rate: {summary.overall_viability_rate:.1f}%")
        print(f"  Avg net profit/trade: {summary.avg_net_profit_per_trade_pct:.4f}%")
        print(f"  Breakeven spread: {summary.avg_min_spread_breakeven*100:.3f}%")

        if summary.top_markets:
            print(f"  Top markets: {', '.join(m[:12] + '...' for m in summary.top_markets[:3])}")
