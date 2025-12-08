"""
Fase 3 - Análise de Séries de Arbitragem

Funções para identificar e analisar oportunidades de arbitragem
nas séries de preço YES/NO.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

import pandas as pd
import numpy as np

from config.settings import ARBITRAGE_THRESHOLD, DATA_RAW_DIR, DATA_PROCESSED_DIR
from core.models import ArbitragePoint, MarketStats

logger = logging.getLogger(__name__)


def calculate_spread_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula a série de spreads a partir de preços YES/NO.

    Args:
        df: DataFrame com colunas timestamp, price_yes, price_no

    Returns:
        DataFrame com coluna 'spread' adicionada
    """
    df = df.copy()
    df["total"] = df["price_yes"].fillna(0) + df["price_no"].fillna(0)
    df["spread"] = 1.0 - df["total"]
    return df


def identify_arbitrage_points(
    df: pd.DataFrame,
    threshold: float = 0.0,
) -> List[ArbitragePoint]:
    """
    Identifica pontos com oportunidade de arbitragem.

    Arbitragem ocorre quando spread > threshold (YES + NO < 1 - threshold).

    Args:
        df: DataFrame com spread calculado
        threshold: Threshold mínimo de spread para considerar arbitragem

    Returns:
        Lista de ArbitragePoint
    """
    if "spread" not in df.columns:
        df = calculate_spread_series(df)

    arb_points = []
    mask = df["spread"] > threshold

    for _, row in df[mask].iterrows():
        point = ArbitragePoint(
            timestamp=row["timestamp"],
            yes_price=row["price_yes"],
            no_price=row["price_no"],
        )
        arb_points.append(point)

    return arb_points


def calculate_arbitrage_stats(df: pd.DataFrame, market_id: str) -> MarketStats:
    """
    Calcula estatísticas de arbitragem para um mercado.

    Args:
        df: DataFrame com spread calculado
        market_id: ID do mercado

    Returns:
        Objeto MarketStats
    """
    if "spread" not in df.columns:
        df = calculate_spread_series(df)

    total_points = len(df)
    arb_mask = df["spread"] > 0

    stats = MarketStats(
        market_id=market_id,
        avg_spread=float(df["spread"].mean()),
        min_spread=float(df["spread"].min()),
        max_spread=float(df["spread"].max()),
        std_spread=float(df["spread"].std()),
        arbitrage_count=int(arb_mask.sum()),
        arbitrage_percentage=float(arb_mask.sum() / total_points * 100) if total_points > 0 else 0,
        total_data_points=total_points,
    )

    return stats


def run_phase3_pipeline(market_ids: Optional[List[str]] = None) -> Dict[str, MarketStats]:
    """
    Executa o pipeline da Fase 3.

    Args:
        market_ids: Lista de IDs de mercados (carrega todos se None)

    Returns:
        Dicionário {market_id: MarketStats}
    """
    logger.info("=" * 50)
    logger.info("Starting Phase 3: Arbitrage Series Analysis")
    logger.info("=" * 50)

    # TODO: Implementar carregamento de CSVs e análise
    results = {}

    logger.info("Phase 3 completed!")
    return results
