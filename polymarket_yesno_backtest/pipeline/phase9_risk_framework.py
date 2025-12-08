"""
Fase 9 - Framework de Risco

Funções para gerenciamento de risco e sizing de posições.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

import numpy as np

from config.settings import MAX_CAPITAL_PER_MARKET_PERCENT, MAX_DRAWDOWN_PERCENT

logger = logging.getLogger(__name__)


@dataclass
class RiskParameters:
    """Parâmetros de risco."""
    max_capital_per_market_pct: float
    max_drawdown_pct: float
    max_concurrent_positions: int
    position_size_method: str


@dataclass
class PositionSize:
    """Tamanho de posição calculado."""
    market_id: str
    recommended_size: float
    max_size: float
    risk_score: float


def calculate_kelly_fraction(
    win_probability: float,
    win_amount: float,
    loss_amount: float,
) -> float:
    """
    Calcula a fração de Kelly para sizing ótimo.

    Args:
        win_probability: Probabilidade de ganho (0 a 1)
        win_amount: Ganho em caso de vitória
        loss_amount: Perda em caso de derrota

    Returns:
        Fração de Kelly (0 a 1)
    """
    if loss_amount == 0:
        return 0

    b = win_amount / loss_amount
    p = win_probability
    q = 1 - p

    kelly = (b * p - q) / b

    # Limita entre 0 e 1
    return max(0, min(1, kelly))


def calculate_position_size(
    capital: float,
    win_probability: float,
    expected_spread: float,
    max_capital_pct: float = MAX_CAPITAL_PER_MARKET_PERCENT,
    kelly_fraction: float = 0.25,  # Fração do Kelly (mais conservador)
) -> float:
    """
    Calcula o tamanho de posição recomendado.

    Args:
        capital: Capital total disponível
        win_probability: Probabilidade de ganho
        expected_spread: Spread esperado
        max_capital_pct: Máximo por mercado (%)
        kelly_fraction: Fração do Kelly a usar

    Returns:
        Tamanho de posição recomendado
    """
    max_position = capital * (max_capital_pct / 100)

    if win_probability <= 0 or expected_spread <= 0:
        return 0

    # Kelly ajustado
    kelly = calculate_kelly_fraction(
        win_probability=win_probability,
        win_amount=expected_spread,
        loss_amount=1 - expected_spread,
    )

    kelly_size = capital * kelly * kelly_fraction

    # Retorna o menor entre Kelly e máximo
    return min(kelly_size, max_position)


def calculate_max_drawdown_risk(
    positions: List[Dict],
    max_drawdown_pct: float = MAX_DRAWDOWN_PERCENT,
) -> Dict:
    """
    Avalia risco de drawdown de um portfolio de posições.

    Args:
        positions: Lista de posições {size, loss_probability}
        max_drawdown_pct: Drawdown máximo aceitável

    Returns:
        Dicionário com análise de risco
    """
    if not positions:
        return {"risk_level": "low", "expected_drawdown": 0}

    total_exposure = sum(p.get("size", 0) for p in positions)

    # Estimativa simplificada de drawdown
    expected_losses = sum(
        p.get("size", 0) * p.get("loss_probability", 0.5)
        for p in positions
    )

    expected_drawdown_pct = (expected_losses / total_exposure * 100) if total_exposure > 0 else 0

    if expected_drawdown_pct > max_drawdown_pct:
        risk_level = "high"
    elif expected_drawdown_pct > max_drawdown_pct * 0.5:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "expected_drawdown_pct": expected_drawdown_pct,
        "total_exposure": total_exposure,
        "max_drawdown_pct": max_drawdown_pct,
    }


def get_default_risk_parameters() -> RiskParameters:
    """Retorna parâmetros de risco padrão."""
    return RiskParameters(
        max_capital_per_market_pct=MAX_CAPITAL_PER_MARKET_PERCENT,
        max_drawdown_pct=MAX_DRAWDOWN_PERCENT,
        max_concurrent_positions=10,
        position_size_method="fractional_kelly",
    )


def run_phase9_pipeline(capital: float = 10000) -> Dict:
    """
    Executa o pipeline da Fase 9.

    Args:
        capital: Capital inicial para simulação

    Returns:
        Dicionário com framework de risco
    """
    logger.info("=" * 50)
    logger.info("Starting Phase 9: Risk Framework")
    logger.info("=" * 50)

    params = get_default_risk_parameters()

    results = {
        "risk_parameters": {
            "max_capital_per_market_pct": params.max_capital_per_market_pct,
            "max_drawdown_pct": params.max_drawdown_pct,
            "max_concurrent_positions": params.max_concurrent_positions,
            "position_size_method": params.position_size_method,
        },
        "capital": capital,
        "max_position_size": capital * (params.max_capital_per_market_pct / 100),
    }

    logger.info(f"Max position size: ${results['max_position_size']:.2f}")
    logger.info("Phase 9 completed!")

    return results
