"""
Fase 5 - Comparação entre Mercados

Funções para rankear mercados por potencial de arbitragem e
analisar padrões por categoria.
"""

import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd
import numpy as np

from config.settings import (
    DATA_STATS_DIR,
    DATA_PROCESSED_DIR,
    DEFAULT_TIMEFRAME,
    ensure_data_dirs_exist,
)
from pipeline.phase1_market_selection import load_markets_from_json
from pipeline.phase4_stats_spread import (
    load_stats_from_csv,
    MarketSpreadStats,
)
from core.models import Market, MarketGroup

logger = logging.getLogger(__name__)


class MarketCategory(Enum):
    """Categorias de mercados."""
    POLITICS = "politics"
    SPORTS = "sports"
    CRYPTO = "crypto"
    FINANCE = "finance"
    ENTERTAINMENT = "entertainment"
    SCIENCE = "science"
    OTHER = "other"


class EventDuration(Enum):
    """Classificação por duração do evento."""
    SHORT = "short"      # < 7 dias
    MEDIUM = "medium"    # 7-30 dias
    LONG = "long"        # 30-90 dias
    VERY_LONG = "very_long"  # > 90 dias


@dataclass
class MarketScore:
    """Score de potencial de arbitragem de um mercado."""
    market_id: str
    question: str
    category: str
    volume: float

    # Componentes do score
    frequency_score: float      # % de tempo em arbitragem
    magnitude_score: float      # Spread médio quando positivo
    volume_score: float         # Log do volume normalizado
    recurrence_score: float     # Número de runs (janelas)

    # Score composto
    composite_score: float

    # Ranking
    rank: int = 0

    # Metadados
    lifetime_days: Optional[int] = None
    event_duration: Optional[EventDuration] = None
    group: Optional[str] = None


@dataclass
class CategoryStats:
    """Estatísticas agregadas por categoria."""
    category: str
    market_count: int

    # Frequência
    avg_frequency: float
    median_frequency: float
    max_frequency: float

    # Magnitude
    avg_magnitude: float
    median_magnitude: float
    max_magnitude: float

    # Volume
    total_volume: float
    avg_volume: float

    # Scores
    avg_composite_score: float
    best_market_id: str
    best_market_score: float


# =============================================================================
# Funções de Categorização
# =============================================================================

def categorize_market(market: Market) -> MarketCategory:
    """
    Categoriza um mercado baseado no título e categoria.

    Args:
        market: Objeto Market

    Returns:
        MarketCategory
    """
    # Usa categoria da API se disponível
    cat = market.category.lower() if market.category else ""
    question = market.question.lower() if market.question else ""

    # Keywords por categoria
    politics_keywords = [
        "election", "president", "congress", "senate", "governor",
        "trump", "biden", "democrat", "republican", "vote", "poll",
        "political", "politics", "legislation", "bill", "law"
    ]

    sports_keywords = [
        "nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball",
        "baseball", "hockey", "championship", "super bowl", "world cup",
        "olympics", "ufc", "boxing", "tennis", "golf", "race", "match"
    ]

    crypto_keywords = [
        "bitcoin", "ethereum", "crypto", "btc", "eth", "token", "blockchain",
        "defi", "nft", "solana", "cardano", "dogecoin", "altcoin"
    ]

    finance_keywords = [
        "stock", "market", "s&p", "nasdaq", "dow", "fed", "interest rate",
        "inflation", "gdp", "economy", "recession", "earnings", "ipo"
    ]

    entertainment_keywords = [
        "oscar", "grammy", "emmy", "movie", "film", "music", "album",
        "celebrity", "tv show", "netflix", "streaming", "award"
    ]

    science_keywords = [
        "ai", "artificial intelligence", "spacex", "nasa", "climate",
        "vaccine", "covid", "scientific", "research", "discovery"
    ]

    # Checa categoria da API primeiro
    if "politic" in cat:
        return MarketCategory.POLITICS
    elif "sport" in cat:
        return MarketCategory.SPORTS
    elif "crypto" in cat or "blockchain" in cat:
        return MarketCategory.CRYPTO
    elif "finance" in cat or "econ" in cat:
        return MarketCategory.FINANCE

    # Checa keywords no título
    text = f"{cat} {question}"

    if any(kw in text for kw in politics_keywords):
        return MarketCategory.POLITICS
    elif any(kw in text for kw in sports_keywords):
        return MarketCategory.SPORTS
    elif any(kw in text for kw in crypto_keywords):
        return MarketCategory.CRYPTO
    elif any(kw in text for kw in finance_keywords):
        return MarketCategory.FINANCE
    elif any(kw in text for kw in entertainment_keywords):
        return MarketCategory.ENTERTAINMENT
    elif any(kw in text for kw in science_keywords):
        return MarketCategory.SCIENCE

    return MarketCategory.OTHER


def classify_event_duration(lifetime_days: Optional[int]) -> EventDuration:
    """
    Classifica um mercado pela duração do evento.

    Args:
        lifetime_days: Duração em dias

    Returns:
        EventDuration
    """
    if lifetime_days is None:
        return EventDuration.MEDIUM

    if lifetime_days < 7:
        return EventDuration.SHORT
    elif lifetime_days < 30:
        return EventDuration.MEDIUM
    elif lifetime_days < 90:
        return EventDuration.LONG
    else:
        return EventDuration.VERY_LONG


# =============================================================================
# Funções de Scoring
# =============================================================================

def calculate_market_score(
    market: Market,
    stats_row: pd.Series,
    volume_max: float,
) -> MarketScore:
    """
    Calcula o score de potencial de arbitragem de um mercado.

    Score = frequência * magnitude * log(volume) * recorrência

    Args:
        market: Objeto Market
        stats_row: Linha do DataFrame de estatísticas
        volume_max: Volume máximo para normalização

    Returns:
        MarketScore
    """
    # Componentes
    frequency = stats_row.get("freq_positive_pct", 0) / 100  # 0-1
    magnitude = stats_row.get("mag_pos_mean", 0)  # spread médio positivo
    runs = stats_row.get("runs_total", 0)
    volume = market.volume

    # Normalização
    frequency_score = min(frequency, 1.0)  # Já está em 0-1
    magnitude_score = min(magnitude * 10, 1.0)  # 10% spread = 1.0
    volume_score = np.log10(max(volume, 1)) / np.log10(max(volume_max, 1))
    recurrence_score = min(runs / 100, 1.0)  # 100 runs = 1.0

    # Score composto (média geométrica ponderada)
    weights = {
        "frequency": 0.35,
        "magnitude": 0.30,
        "volume": 0.20,
        "recurrence": 0.15,
    }

    composite = (
        (frequency_score ** weights["frequency"]) *
        (max(magnitude_score, 0.001) ** weights["magnitude"]) *
        (max(volume_score, 0.001) ** weights["volume"]) *
        (max(recurrence_score, 0.001) ** weights["recurrence"])
    )

    # Categorização
    category = categorize_market(market)
    event_duration = classify_event_duration(market.lifetime_days)

    return MarketScore(
        market_id=market.id,
        question=market.question[:100] if market.question else "",
        category=category.value,
        volume=volume,
        frequency_score=frequency_score,
        magnitude_score=magnitude_score,
        volume_score=volume_score,
        recurrence_score=recurrence_score,
        composite_score=composite,
        lifetime_days=market.lifetime_days,
        event_duration=event_duration,
        group=market.group.value if market.group else None,
    )


def rank_markets_by_potential(
    scores: List[MarketScore],
) -> List[MarketScore]:
    """
    Ordena mercados por potencial de arbitragem.

    Args:
        scores: Lista de MarketScore

    Returns:
        Lista ordenada com ranks atribuídos
    """
    sorted_scores = sorted(
        scores,
        key=lambda s: s.composite_score,
        reverse=True
    )

    for i, score in enumerate(sorted_scores, 1):
        score.rank = i

    return sorted_scores


# =============================================================================
# Análise por Categoria
# =============================================================================

def compute_category_stats(
    scores: List[MarketScore],
) -> Dict[str, CategoryStats]:
    """
    Calcula estatísticas agregadas por categoria.

    Args:
        scores: Lista de MarketScore

    Returns:
        Dicionário {categoria: CategoryStats}
    """
    # Agrupa por categoria
    by_category: Dict[str, List[MarketScore]] = {}
    for score in scores:
        cat = score.category
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(score)

    results = {}

    for category, cat_scores in by_category.items():
        frequencies = [s.frequency_score * 100 for s in cat_scores]
        magnitudes = [s.magnitude_score for s in cat_scores]
        volumes = [s.volume for s in cat_scores]
        composites = [s.composite_score for s in cat_scores]

        best = max(cat_scores, key=lambda s: s.composite_score)

        results[category] = CategoryStats(
            category=category,
            market_count=len(cat_scores),
            avg_frequency=np.mean(frequencies),
            median_frequency=np.median(frequencies),
            max_frequency=max(frequencies),
            avg_magnitude=np.mean(magnitudes),
            median_magnitude=np.median(magnitudes),
            max_magnitude=max(magnitudes),
            total_volume=sum(volumes),
            avg_volume=np.mean(volumes),
            avg_composite_score=np.mean(composites),
            best_market_id=best.market_id,
            best_market_score=best.composite_score,
        )

    return results


def compute_duration_stats(
    scores: List[MarketScore],
) -> Dict[str, Dict]:
    """
    Calcula estatísticas por duração do evento.

    Args:
        scores: Lista de MarketScore

    Returns:
        Dicionário {duração: stats}
    """
    by_duration: Dict[str, List[MarketScore]] = {}

    for score in scores:
        dur = score.event_duration.value if score.event_duration else "unknown"
        if dur not in by_duration:
            by_duration[dur] = []
        by_duration[dur].append(score)

    results = {}

    for duration, dur_scores in by_duration.items():
        results[duration] = {
            "count": len(dur_scores),
            "avg_frequency": np.mean([s.frequency_score * 100 for s in dur_scores]),
            "avg_magnitude": np.mean([s.magnitude_score for s in dur_scores]),
            "avg_composite": np.mean([s.composite_score for s in dur_scores]),
        }

    return results


# =============================================================================
# Export
# =============================================================================

def scores_to_dataframe(scores: List[MarketScore]) -> pd.DataFrame:
    """
    Converte lista de scores para DataFrame.

    Args:
        scores: Lista de MarketScore

    Returns:
        DataFrame
    """
    records = []
    for s in scores:
        records.append({
            "rank": s.rank,
            "market_id": s.market_id,
            "question": s.question,
            "category": s.category,
            "event_duration": s.event_duration.value if s.event_duration else None,
            "group": s.group,
            "volume": s.volume,
            "lifetime_days": s.lifetime_days,
            "frequency_score": s.frequency_score,
            "magnitude_score": s.magnitude_score,
            "volume_score": s.volume_score,
            "recurrence_score": s.recurrence_score,
            "composite_score": s.composite_score,
        })

    return pd.DataFrame(records)


def save_rankings_to_csv(
    scores: List[MarketScore],
    filename: str = "market_rankings.csv",
    output_dir: Path = DATA_STATS_DIR,
) -> Path:
    """
    Salva rankings em arquivo CSV.

    Args:
        scores: Lista de MarketScore rankeados
        filename: Nome do arquivo
        output_dir: Diretório de saída

    Returns:
        Caminho do arquivo salvo
    """
    ensure_data_dirs_exist()

    df = scores_to_dataframe(scores)
    filepath = output_dir / filename
    df.to_csv(filepath, index=False)

    logger.info(f"Saved {len(scores)} market rankings to {filepath}")
    return filepath


def save_category_analysis_to_csv(
    category_stats: Dict[str, CategoryStats],
    filename: str = "category_analysis.csv",
    output_dir: Path = DATA_STATS_DIR,
) -> Path:
    """
    Salva análise por categoria em CSV.

    Args:
        category_stats: Dicionário de estatísticas por categoria
        filename: Nome do arquivo
        output_dir: Diretório de saída

    Returns:
        Caminho do arquivo
    """
    ensure_data_dirs_exist()

    records = []
    for cat, stats in category_stats.items():
        records.append({
            "category": stats.category,
            "market_count": stats.market_count,
            "avg_frequency_pct": stats.avg_frequency,
            "median_frequency_pct": stats.median_frequency,
            "max_frequency_pct": stats.max_frequency,
            "avg_magnitude": stats.avg_magnitude,
            "median_magnitude": stats.median_magnitude,
            "max_magnitude": stats.max_magnitude,
            "total_volume": stats.total_volume,
            "avg_volume": stats.avg_volume,
            "avg_composite_score": stats.avg_composite_score,
            "best_market_id": stats.best_market_id,
            "best_market_score": stats.best_market_score,
        })

    df = pd.DataFrame(records)
    df = df.sort_values("avg_composite_score", ascending=False)

    filepath = output_dir / filename
    df.to_csv(filepath, index=False)

    logger.info(f"Saved category analysis to {filepath}")
    return filepath


# =============================================================================
# Pipeline
# =============================================================================

def run_phase5_pipeline(
    timeframe: str = DEFAULT_TIMEFRAME,
) -> Tuple[List[MarketScore], Dict[str, CategoryStats], Dict[str, Dict]]:
    """
    Executa o pipeline completo da Fase 5.

    Args:
        timeframe: Intervalo de tempo

    Returns:
        Tupla (rankings, category_stats, duration_stats)
    """
    logger.info("=" * 50)
    logger.info("Starting Phase 5: Market Comparison")
    logger.info("=" * 50)

    # Carrega mercados
    try:
        groups = load_markets_from_json()
        all_markets = groups["A"] + groups["B"] + groups["C"]
        market_dict = {m.id: m for m in all_markets}
    except FileNotFoundError:
        logger.error("Markets JSON not found. Run Phase 1 first.")
        return [], {}, {}

    # Carrega estatísticas
    stats_df = load_stats_from_csv()
    if stats_df is None or len(stats_df) == 0:
        logger.error("Stats CSV not found. Run Phase 4 first.")
        return [], {}, {}

    # Calcula volume máximo para normalização
    volume_max = max(m.volume for m in all_markets) if all_markets else 1

    # Calcula scores
    scores = []
    for _, row in stats_df.iterrows():
        market_id = row["market_id"]
        if market_id in market_dict:
            market = market_dict[market_id]
            score = calculate_market_score(market, row, volume_max)
            scores.append(score)

    # Rankeia
    ranked_scores = rank_markets_by_potential(scores)

    # Análise por categoria
    category_stats = compute_category_stats(ranked_scores)

    # Análise por duração
    duration_stats = compute_duration_stats(ranked_scores)

    # Salva resultados
    save_rankings_to_csv(ranked_scores)
    save_category_analysis_to_csv(category_stats)

    # Log resumo
    logger.info(f"\nProcessed {len(ranked_scores)} markets")
    logger.info(f"\nTop 5 markets by potential:")
    for score in ranked_scores[:5]:
        logger.info(
            f"  #{score.rank}: {score.market_id[:16]}... "
            f"(score={score.composite_score:.4f}, cat={score.category})"
        )

    logger.info(f"\nCategory analysis:")
    for cat, stats in sorted(category_stats.items(),
                             key=lambda x: x[1].avg_composite_score,
                             reverse=True):
        logger.info(
            f"  {cat}: {stats.market_count} markets, "
            f"avg_freq={stats.avg_frequency:.2f}%, "
            f"avg_score={stats.avg_composite_score:.4f}"
        )

    logger.info(f"\nDuration analysis:")
    for dur, stats in duration_stats.items():
        logger.info(
            f"  {dur}: {stats['count']} markets, "
            f"avg_freq={stats['avg_frequency']:.2f}%"
        )

    logger.info("=" * 50)
    logger.info("Phase 5 completed!")
    logger.info("=" * 50)

    return ranked_scores, category_stats, duration_stats


def print_comparison_report(
    rankings: List[MarketScore],
    category_stats: Dict[str, CategoryStats],
    duration_stats: Dict[str, Dict],
    top_n: int = 10,
) -> None:
    """
    Imprime relatório de comparação entre mercados.

    Args:
        rankings: Lista de MarketScore rankeados
        category_stats: Estatísticas por categoria
        duration_stats: Estatísticas por duração
        top_n: Número de top mercados a mostrar
    """
    print("\n" + "=" * 70)
    print("RELATÓRIO DE COMPARAÇÃO ENTRE MERCADOS")
    print("=" * 70)

    # Top mercados
    print(f"\n{'='*70}")
    print(f"TOP {top_n} MERCADOS POR POTENCIAL DE ARBITRAGEM")
    print("=" * 70)
    print(f"{'Rank':<5} {'Score':<8} {'Freq%':<8} {'Mag':<8} {'Cat':<12} {'Pergunta':<30}")
    print("-" * 70)

    for score in rankings[:top_n]:
        print(
            f"{score.rank:<5} "
            f"{score.composite_score:<8.4f} "
            f"{score.frequency_score*100:<8.2f} "
            f"{score.magnitude_score:<8.4f} "
            f"{score.category:<12} "
            f"{score.question[:30]}"
        )

    # Por categoria
    print(f"\n{'='*70}")
    print("ANÁLISE POR CATEGORIA")
    print("=" * 70)
    print(f"{'Categoria':<15} {'#Mkts':<8} {'Freq%':<10} {'Mag':<10} {'Score':<10}")
    print("-" * 70)

    sorted_cats = sorted(
        category_stats.items(),
        key=lambda x: x[1].avg_composite_score,
        reverse=True
    )

    for cat, stats in sorted_cats:
        print(
            f"{cat:<15} "
            f"{stats.market_count:<8} "
            f"{stats.avg_frequency:<10.2f} "
            f"{stats.avg_magnitude:<10.4f} "
            f"{stats.avg_composite_score:<10.4f}"
        )

    # Por duração
    print(f"\n{'='*70}")
    print("ANÁLISE POR DURAÇÃO DO EVENTO")
    print("=" * 70)
    print(f"{'Duração':<15} {'#Mkts':<8} {'Freq%':<10} {'Score':<10}")
    print("-" * 70)

    duration_order = ["short", "medium", "long", "very_long"]
    for dur in duration_order:
        if dur in duration_stats:
            stats = duration_stats[dur]
            print(
                f"{dur:<15} "
                f"{stats['count']:<8} "
                f"{stats['avg_frequency']:<10.2f} "
                f"{stats['avg_composite']:<10.4f}"
            )

    # Insights
    print(f"\n{'='*70}")
    print("INSIGHTS")
    print("=" * 70)

    if sorted_cats:
        best_cat = sorted_cats[0][0]
        worst_cat = sorted_cats[-1][0]
        print(f"• Melhor categoria para arbitragem: {best_cat}")
        print(f"• Pior categoria para arbitragem: {worst_cat}")

    if duration_stats:
        best_dur = max(duration_stats.items(), key=lambda x: x[1]["avg_frequency"])
        print(f"• Eventos {best_dur[0]} têm maior frequência de arbitragem ({best_dur[1]['avg_frequency']:.2f}%)")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    rankings, category_stats, duration_stats = run_phase5_pipeline()

    if rankings:
        print_comparison_report(rankings, category_stats, duration_stats)
