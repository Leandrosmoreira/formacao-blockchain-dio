"""
Fase 7 - Modelo de Custos

Funções para calcular custos de trading e impacto no lucro.
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass

from config.settings import TRADING_FEE_PERCENT, ESTIMATED_SLIPPAGE_PERCENT

logger = logging.getLogger(__name__)


@dataclass
class TradeCost:
    """Representa os custos de uma operação."""
    trading_fee: float
    slippage: float
    total: float


def calculate_trade_cost(
    amount: float,
    trading_fee_pct: float = TRADING_FEE_PERCENT,
    slippage_pct: float = ESTIMATED_SLIPPAGE_PERCENT,
) -> TradeCost:
    """
    Calcula o custo total de uma operação.

    Args:
        amount: Valor da operação em USD
        trading_fee_pct: Taxa de trading (%)
        slippage_pct: Slippage estimado (%)

    Returns:
        Objeto TradeCost
    """
    trading_fee = amount * (trading_fee_pct / 100)
    slippage = amount * (slippage_pct / 100)
    total = trading_fee + slippage

    return TradeCost(
        trading_fee=trading_fee,
        slippage=slippage,
        total=total,
    )


def calculate_net_profit(
    gross_profit: float,
    trade_cost: TradeCost,
) -> float:
    """
    Calcula lucro líquido após custos.

    Args:
        gross_profit: Lucro bruto
        trade_cost: Custos da operação

    Returns:
        Lucro líquido
    """
    return gross_profit - trade_cost.total


def estimate_arbitrage_profit(
    spread: float,
    position_size: float,
    trading_fee_pct: float = TRADING_FEE_PERCENT,
    slippage_pct: float = ESTIMATED_SLIPPAGE_PERCENT,
) -> Dict:
    """
    Estima o lucro de uma operação de arbitragem.

    Args:
        spread: Spread de arbitragem (0 a 1)
        position_size: Tamanho da posição em USD
        trading_fee_pct: Taxa de trading
        slippage_pct: Slippage estimado

    Returns:
        Dicionário com detalhes do lucro
    """
    # Lucro bruto = spread * position
    gross_profit = spread * position_size

    # Custo (entrada + saída)
    entry_cost = calculate_trade_cost(position_size, trading_fee_pct, slippage_pct)
    exit_cost = calculate_trade_cost(position_size, trading_fee_pct, slippage_pct)
    total_cost = entry_cost.total + exit_cost.total

    net_profit = gross_profit - total_cost
    roi = (net_profit / position_size) * 100 if position_size > 0 else 0

    return {
        "gross_profit": gross_profit,
        "total_cost": total_cost,
        "net_profit": net_profit,
        "roi_percent": roi,
        "profitable": net_profit > 0,
    }


def calculate_breakeven_spread(
    trading_fee_pct: float = TRADING_FEE_PERCENT,
    slippage_pct: float = ESTIMATED_SLIPPAGE_PERCENT,
) -> float:
    """
    Calcula o spread mínimo para breakeven.

    Args:
        trading_fee_pct: Taxa de trading
        slippage_pct: Slippage estimado

    Returns:
        Spread mínimo (0 a 1)
    """
    # Custo total = 2 * (fee + slippage) para entrada e saída
    total_cost_pct = 2 * (trading_fee_pct + slippage_pct)
    return total_cost_pct / 100


def run_phase7_pipeline() -> Dict:
    """
    Executa o pipeline da Fase 7.

    Returns:
        Dicionário com modelo de custos
    """
    logger.info("=" * 50)
    logger.info("Starting Phase 7: Cost Model")
    logger.info("=" * 50)

    breakeven = calculate_breakeven_spread()
    logger.info(f"Breakeven spread: {breakeven*100:.2f}%")

    results = {
        "breakeven_spread": breakeven,
        "trading_fee_pct": TRADING_FEE_PERCENT,
        "slippage_pct": ESTIMATED_SLIPPAGE_PERCENT,
    }

    logger.info("Phase 7 completed!")
    return results
