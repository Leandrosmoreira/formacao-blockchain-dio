"""
Fase 5 - Comparação entre Mercados

Funções para comparar métricas entre diferentes mercados e grupos.
"""

import logging
from typing import List, Dict, Optional

import pandas as pd
import numpy as np

from core.models import Market, MarketStats, MarketGroup
from config.settings import DATA_STATS_DIR

logger = logging.getLogger(__name__)


def compare_groups(
    group_a_stats: List[MarketStats],
    group_b_stats: List[MarketStats],
    group_c_stats: List[MarketStats],
) -> Dict:
    """
    Compara estatísticas entre grupos A, B e C.

    Args:
        group_a_stats: Estatísticas do grupo A
        group_b_stats: Estatísticas do grupo B
        group_c_stats: Estatísticas do grupo C

    Returns:
        Dicionário com comparação
    """
    def group_summary(stats: List[MarketStats]) -> Dict:
        if not stats:
            return {"count": 0}
        return {
            "count": len(stats),
            "avg_spread_mean": np.mean([s.avg_spread for s in stats]),
            "avg_arb_pct": np.mean([s.arbitrage_percentage for s in stats]),
        }

    return {
        "A": group_summary(group_a_stats),
        "B": group_summary(group_b_stats),
        "C": group_summary(group_c_stats),
    }


def rank_markets_by_opportunity(stats_list: List[MarketStats]) -> List[MarketStats]:
    """
    Ordena mercados por oportunidade de arbitragem.

    Args:
        stats_list: Lista de estatísticas

    Returns:
        Lista ordenada por potencial de arbitragem
    """
    return sorted(
        stats_list,
        key=lambda s: s.avg_spread * s.arbitrage_percentage,
        reverse=True,
    )


def run_phase5_pipeline() -> Dict:
    """
    Executa o pipeline da Fase 5.

    Returns:
        Dicionário com comparações
    """
    logger.info("=" * 50)
    logger.info("Starting Phase 5: Market Comparison")
    logger.info("=" * 50)

    # TODO: Implementar comparação
    results = {}

    logger.info("Phase 5 completed!")
    return results
