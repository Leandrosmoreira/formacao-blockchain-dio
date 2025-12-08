"""
Fase 4 - Estatísticas de Spread

Funções para calcular e agregar estatísticas de spread entre mercados.
"""

import logging
from typing import List, Dict
from pathlib import Path

import pandas as pd
import numpy as np

from config.settings import DATA_STATS_DIR, ensure_data_dirs_exist
from core.models import MarketStats

logger = logging.getLogger(__name__)


def aggregate_spread_stats(stats_list: List[MarketStats]) -> Dict:
    """
    Agrega estatísticas de spread de múltiplos mercados.

    Args:
        stats_list: Lista de MarketStats

    Returns:
        Dicionário com estatísticas agregadas
    """
    if not stats_list:
        return {}

    avg_spreads = [s.avg_spread for s in stats_list]
    arb_percentages = [s.arbitrage_percentage for s in stats_list]

    return {
        "total_markets": len(stats_list),
        "avg_spread": {
            "mean": np.mean(avg_spreads),
            "std": np.std(avg_spreads),
            "min": np.min(avg_spreads),
            "max": np.max(avg_spreads),
        },
        "arbitrage_percentage": {
            "mean": np.mean(arb_percentages),
            "std": np.std(arb_percentages),
            "min": np.min(arb_percentages),
            "max": np.max(arb_percentages),
        },
    }


def save_stats_to_csv(stats_list: List[MarketStats], filename: str = "spread_stats.csv") -> Path:
    """
    Salva estatísticas em arquivo CSV.

    Args:
        stats_list: Lista de MarketStats
        filename: Nome do arquivo

    Returns:
        Caminho do arquivo salvo
    """
    ensure_data_dirs_exist()

    records = [s.to_dict() for s in stats_list]
    df = pd.DataFrame(records)

    filepath = DATA_STATS_DIR / filename
    df.to_csv(filepath, index=False)

    logger.info(f"Saved stats to {filepath}")
    return filepath


def run_phase4_pipeline() -> Dict:
    """
    Executa o pipeline da Fase 4.

    Returns:
        Dicionário com estatísticas agregadas
    """
    logger.info("=" * 50)
    logger.info("Starting Phase 4: Spread Statistics")
    logger.info("=" * 50)

    # TODO: Implementar agregação de estatísticas
    results = {}

    logger.info("Phase 4 completed!")
    return results
