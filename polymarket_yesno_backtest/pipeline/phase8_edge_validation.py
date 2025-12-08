"""
Fase 8 - Validação de Edge

Funções para validar se as oportunidades de arbitragem são reais
e estatisticamente significativas.
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

import numpy as np
from scipy import stats

from core.models import MarketStats
from pipeline.phase7_cost_model import calculate_breakeven_spread

logger = logging.getLogger(__name__)


@dataclass
class EdgeValidation:
    """Resultado da validação de edge."""
    market_id: str
    has_edge: bool
    edge_magnitude: float
    confidence_level: float
    sample_size: int
    message: str


def validate_statistical_significance(
    spreads: List[float],
    threshold: float = 0.0,
    confidence: float = 0.95,
) -> Dict:
    """
    Valida se o spread médio é estatisticamente maior que o threshold.

    Args:
        spreads: Lista de spreads observados
        threshold: Threshold a testar
        confidence: Nível de confiança

    Returns:
        Dicionário com resultados do teste
    """
    if len(spreads) < 30:
        return {
            "valid": False,
            "reason": "Insufficient sample size (< 30)",
        }

    spreads = np.array(spreads)
    mean_spread = np.mean(spreads)
    std_spread = np.std(spreads, ddof=1)

    # Teste t unilateral: H0: mean <= threshold, H1: mean > threshold
    t_stat, p_value = stats.ttest_1samp(spreads, threshold)
    p_value_one_sided = p_value / 2 if t_stat > 0 else 1 - p_value / 2

    is_significant = p_value_one_sided < (1 - confidence)

    return {
        "valid": is_significant,
        "mean_spread": mean_spread,
        "std_spread": std_spread,
        "t_statistic": t_stat,
        "p_value": p_value_one_sided,
        "confidence": confidence,
        "sample_size": len(spreads),
    }


def validate_edge_after_costs(
    avg_spread: float,
    std_spread: float,
    sample_size: int,
) -> EdgeValidation:
    """
    Valida se o edge existe após custos de trading.

    Args:
        avg_spread: Spread médio observado
        std_spread: Desvio padrão do spread
        sample_size: Tamanho da amostra

    Returns:
        Objeto EdgeValidation
    """
    breakeven = calculate_breakeven_spread()

    # Edge = spread médio - breakeven
    edge = avg_spread - breakeven

    # Intervalo de confiança de 95%
    if sample_size > 1:
        se = std_spread / np.sqrt(sample_size)
        ci_lower = avg_spread - 1.96 * se
    else:
        ci_lower = avg_spread

    has_edge = ci_lower > breakeven

    if has_edge:
        message = f"Edge válido: {edge*100:.2f}% acima do breakeven"
    else:
        message = f"Edge insuficiente: spread médio ({avg_spread*100:.2f}%) <= breakeven ({breakeven*100:.2f}%)"

    return EdgeValidation(
        market_id="",
        has_edge=has_edge,
        edge_magnitude=edge,
        confidence_level=0.95,
        sample_size=sample_size,
        message=message,
    )


def run_phase8_pipeline(stats_list: List[MarketStats]) -> Dict:
    """
    Executa o pipeline da Fase 8.

    Args:
        stats_list: Lista de estatísticas de mercados

    Returns:
        Dicionário com validações
    """
    logger.info("=" * 50)
    logger.info("Starting Phase 8: Edge Validation")
    logger.info("=" * 50)

    validations = []

    for market_stats in stats_list:
        validation = validate_edge_after_costs(
            avg_spread=market_stats.avg_spread,
            std_spread=market_stats.std_spread,
            sample_size=market_stats.total_data_points,
        )
        validation.market_id = market_stats.market_id
        validations.append(validation)

    valid_count = sum(1 for v in validations if v.has_edge)

    results = {
        "total_markets": len(stats_list),
        "markets_with_edge": valid_count,
        "edge_rate": valid_count / len(stats_list) * 100 if stats_list else 0,
        "validations": validations,
    }

    logger.info(f"Markets with valid edge: {valid_count}/{len(stats_list)}")
    logger.info("Phase 8 completed!")

    return results
