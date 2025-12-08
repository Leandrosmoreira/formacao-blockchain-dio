"""
Fase 6 - Análise Temporal (Sazonalidade)

Funções para analisar quando a arbitragem acontece:
- Por horário do dia
- Por dia da semana
- Perto da resolução
"""

import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from config.settings import (
    DATA_PROCESSED_DIR,
    DATA_STATS_DIR,
    DEFAULT_TIMEFRAME,
    ensure_data_dirs_exist,
)
from core.utils_time import timeframe_to_seconds
from pipeline.phase3_arbitrage_series import load_arbitrage_series
from pipeline.phase1_market_selection import load_markets_from_json
from core.models import Market

logger = logging.getLogger(__name__)


@dataclass
class HourlyStats:
    """Estatísticas por hora do dia."""
    hour: int
    period: str  # morning, afternoon, evening, night
    total_points: int
    positive_count: int
    positive_pct: float
    avg_spread: float
    max_spread: float
    avg_spread_when_positive: float


@dataclass
class DayOfWeekStats:
    """Estatísticas por dia da semana."""
    day: int  # 0=Monday, 6=Sunday
    day_name: str
    is_weekend: bool
    total_points: int
    positive_count: int
    positive_pct: float
    avg_spread: float
    max_spread: float


@dataclass
class ResolutionProximityStats:
    """Estatísticas por proximidade da resolução."""
    days_to_resolution: str  # "0-1", "1-3", "3-7", "7-14", "14-30", "30+"
    total_points: int
    positive_count: int
    positive_pct: float
    avg_spread: float
    max_spread: float


@dataclass
class TemporalAnalysis:
    """Análise temporal completa de um mercado."""
    market_id: str
    hourly_stats: List[HourlyStats]
    daily_stats: List[DayOfWeekStats]
    resolution_stats: List[ResolutionProximityStats]


# =============================================================================
# Classificação de Período do Dia
# =============================================================================

def get_period_of_day(hour: int) -> str:
    """
    Classifica a hora em período do dia.

    Args:
        hour: Hora (0-23)

    Returns:
        Período: "night", "morning", "afternoon", "evening"
    """
    if 0 <= hour < 6:
        return "night"       # Madrugada (00:00-06:00)
    elif 6 <= hour < 12:
        return "morning"     # Manhã (06:00-12:00)
    elif 12 <= hour < 18:
        return "afternoon"   # Tarde (12:00-18:00)
    else:
        return "evening"     # Noite (18:00-00:00)


def get_day_name(day: int) -> str:
    """Retorna nome do dia da semana."""
    names = ["Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday", "Sunday"]
    return names[day]


# =============================================================================
# Análise por Hora do Dia
# =============================================================================

def analyze_by_hour(df: pd.DataFrame) -> List[HourlyStats]:
    """
    Analisa padrões de arbitragem por hora do dia.

    Args:
        df: DataFrame com timestamp e arbitrage_spread

    Returns:
        Lista de HourlyStats para cada hora (0-23)
    """
    if len(df) == 0:
        return []

    df = df.copy()
    df["hour"] = df["timestamp"].dt.hour

    results = []

    for hour in range(24):
        hour_data = df[df["hour"] == hour]

        if len(hour_data) == 0:
            continue

        spread = hour_data["arbitrage_spread"]
        positive_mask = spread > 0

        positive_spreads = spread[positive_mask]
        avg_when_positive = (
            positive_spreads.mean() if len(positive_spreads) > 0 else 0
        )

        stats = HourlyStats(
            hour=hour,
            period=get_period_of_day(hour),
            total_points=len(hour_data),
            positive_count=int(positive_mask.sum()),
            positive_pct=float(positive_mask.sum() / len(hour_data) * 100),
            avg_spread=float(spread.mean()),
            max_spread=float(spread.max()),
            avg_spread_when_positive=float(avg_when_positive),
        )
        results.append(stats)

    return results


def aggregate_by_period(hourly_stats: List[HourlyStats]) -> Dict[str, Dict]:
    """
    Agrega estatísticas por período do dia.

    Args:
        hourly_stats: Lista de HourlyStats

    Returns:
        Dicionário {período: stats}
    """
    by_period: Dict[str, List[HourlyStats]] = {}

    for stats in hourly_stats:
        period = stats.period
        if period not in by_period:
            by_period[period] = []
        by_period[period].append(stats)

    results = {}

    for period, stats_list in by_period.items():
        total_points = sum(s.total_points for s in stats_list)
        total_positive = sum(s.positive_count for s in stats_list)

        results[period] = {
            "total_points": total_points,
            "positive_count": total_positive,
            "positive_pct": (total_positive / total_points * 100) if total_points > 0 else 0,
            "avg_spread": np.mean([s.avg_spread for s in stats_list]),
            "max_spread": max(s.max_spread for s in stats_list),
            "hours": [s.hour for s in stats_list],
        }

    return results


# =============================================================================
# Análise por Dia da Semana
# =============================================================================

def analyze_by_day_of_week(df: pd.DataFrame) -> List[DayOfWeekStats]:
    """
    Analisa padrões de arbitragem por dia da semana.

    Args:
        df: DataFrame com timestamp e arbitrage_spread

    Returns:
        Lista de DayOfWeekStats para cada dia (0-6)
    """
    if len(df) == 0:
        return []

    df = df.copy()
    df["dayofweek"] = df["timestamp"].dt.dayofweek

    results = []

    for day in range(7):
        day_data = df[df["dayofweek"] == day]

        if len(day_data) == 0:
            continue

        spread = day_data["arbitrage_spread"]
        positive_mask = spread > 0

        stats = DayOfWeekStats(
            day=day,
            day_name=get_day_name(day),
            is_weekend=day >= 5,
            total_points=len(day_data),
            positive_count=int(positive_mask.sum()),
            positive_pct=float(positive_mask.sum() / len(day_data) * 100),
            avg_spread=float(spread.mean()),
            max_spread=float(spread.max()),
        )
        results.append(stats)

    return results


def compare_weekday_vs_weekend(daily_stats: List[DayOfWeekStats]) -> Dict:
    """
    Compara estatísticas de dias úteis vs fim de semana.

    Args:
        daily_stats: Lista de DayOfWeekStats

    Returns:
        Dicionário com comparação
    """
    weekday_stats = [s for s in daily_stats if not s.is_weekend]
    weekend_stats = [s for s in daily_stats if s.is_weekend]

    def aggregate(stats_list: List[DayOfWeekStats]) -> Dict:
        if not stats_list:
            return {"total_points": 0, "positive_pct": 0, "avg_spread": 0}

        total = sum(s.total_points for s in stats_list)
        positive = sum(s.positive_count for s in stats_list)

        return {
            "total_points": total,
            "positive_count": positive,
            "positive_pct": (positive / total * 100) if total > 0 else 0,
            "avg_spread": np.mean([s.avg_spread for s in stats_list]),
            "max_spread": max(s.max_spread for s in stats_list) if stats_list else 0,
        }

    weekday = aggregate(weekday_stats)
    weekend = aggregate(weekend_stats)

    # Diferença
    diff_pct = weekend["positive_pct"] - weekday["positive_pct"]

    return {
        "weekday": weekday,
        "weekend": weekend,
        "weekend_vs_weekday_diff_pct": diff_pct,
        "weekend_has_more_arb": diff_pct > 0,
    }


# =============================================================================
# Análise por Proximidade da Resolução
# =============================================================================

def analyze_by_resolution_proximity(
    df: pd.DataFrame,
    market_end_date: datetime,
) -> List[ResolutionProximityStats]:
    """
    Analisa padrões de arbitragem por proximidade da resolução.

    Args:
        df: DataFrame com timestamp e arbitrage_spread
        market_end_date: Data de resolução do mercado

    Returns:
        Lista de ResolutionProximityStats
    """
    if len(df) == 0:
        return []

    df = df.copy()

    # Calcula dias até a resolução
    df["days_to_resolution"] = (
        market_end_date - df["timestamp"]
    ).dt.total_seconds() / 86400

    # Buckets de proximidade
    buckets = [
        ("0-1", 0, 1),
        ("1-3", 1, 3),
        ("3-7", 3, 7),
        ("7-14", 7, 14),
        ("14-30", 14, 30),
        ("30+", 30, float("inf")),
    ]

    results = []

    for bucket_name, min_days, max_days in buckets:
        mask = (df["days_to_resolution"] >= min_days) & (df["days_to_resolution"] < max_days)
        bucket_data = df[mask]

        if len(bucket_data) == 0:
            continue

        spread = bucket_data["arbitrage_spread"]
        positive_mask = spread > 0

        stats = ResolutionProximityStats(
            days_to_resolution=bucket_name,
            total_points=len(bucket_data),
            positive_count=int(positive_mask.sum()),
            positive_pct=float(positive_mask.sum() / len(bucket_data) * 100),
            avg_spread=float(spread.mean()),
            max_spread=float(spread.max()),
        )
        results.append(stats)

    return results


def analyze_resolution_trend(
    resolution_stats: List[ResolutionProximityStats],
) -> Dict:
    """
    Analisa tendência de arbitragem conforme se aproxima da resolução.

    Args:
        resolution_stats: Lista de ResolutionProximityStats

    Returns:
        Dicionário com análise de tendência
    """
    if len(resolution_stats) < 2:
        return {"trend": "unknown", "message": "Insufficient data"}

    # Ordena por proximidade (0-1 é mais próximo)
    ordered = sorted(resolution_stats, key=lambda s: s.days_to_resolution)

    # Pega primeiro (mais próximo) e último (mais distante)
    closest = ordered[0]
    farthest = ordered[-1]

    diff = closest.positive_pct - farthest.positive_pct

    if diff > 5:
        trend = "increases_near_resolution"
        message = f"Arbitragem AUMENTA perto da resolução (+{diff:.1f}%)"
    elif diff < -5:
        trend = "decreases_near_resolution"
        message = f"Arbitragem DIMINUI perto da resolução ({diff:.1f}%)"
    else:
        trend = "stable"
        message = "Arbitragem se mantém estável ao longo do tempo"

    return {
        "trend": trend,
        "message": message,
        "closest_pct": closest.positive_pct,
        "farthest_pct": farthest.positive_pct,
        "diff_pct": diff,
    }


# =============================================================================
# Análise Completa de um Mercado
# =============================================================================

def analyze_market_temporal(
    market: Market,
    df: pd.DataFrame,
) -> Optional[TemporalAnalysis]:
    """
    Executa análise temporal completa de um mercado.

    Args:
        market: Objeto Market
        df: DataFrame com dados de arbitragem

    Returns:
        TemporalAnalysis ou None
    """
    if df is None or len(df) == 0:
        return None

    # Análise por hora
    hourly = analyze_by_hour(df)

    # Análise por dia da semana
    daily = analyze_by_day_of_week(df)

    # Análise por proximidade da resolução
    resolution = []
    if market.end_date:
        resolution = analyze_by_resolution_proximity(df, market.end_date)

    return TemporalAnalysis(
        market_id=market.id,
        hourly_stats=hourly,
        daily_stats=daily,
        resolution_stats=resolution,
    )


# =============================================================================
# Agregação Multi-Mercado
# =============================================================================

def aggregate_hourly_across_markets(
    analyses: List[TemporalAnalysis],
) -> Dict[int, Dict]:
    """
    Agrega estatísticas horárias de múltiplos mercados.

    Args:
        analyses: Lista de TemporalAnalysis

    Returns:
        Dicionário {hora: stats agregadas}
    """
    by_hour: Dict[int, List[HourlyStats]] = {}

    for analysis in analyses:
        for stats in analysis.hourly_stats:
            if stats.hour not in by_hour:
                by_hour[stats.hour] = []
            by_hour[stats.hour].append(stats)

    results = {}

    for hour, stats_list in by_hour.items():
        total_points = sum(s.total_points for s in stats_list)
        total_positive = sum(s.positive_count for s in stats_list)

        results[hour] = {
            "hour": hour,
            "period": get_period_of_day(hour),
            "market_count": len(stats_list),
            "total_points": total_points,
            "positive_count": total_positive,
            "positive_pct": (total_positive / total_points * 100) if total_points > 0 else 0,
            "avg_spread": np.mean([s.avg_spread for s in stats_list]),
            "avg_positive_pct": np.mean([s.positive_pct for s in stats_list]),
        }

    return results


def aggregate_daily_across_markets(
    analyses: List[TemporalAnalysis],
) -> Dict[int, Dict]:
    """
    Agrega estatísticas diárias de múltiplos mercados.

    Args:
        analyses: Lista de TemporalAnalysis

    Returns:
        Dicionário {dia: stats agregadas}
    """
    by_day: Dict[int, List[DayOfWeekStats]] = {}

    for analysis in analyses:
        for stats in analysis.daily_stats:
            if stats.day not in by_day:
                by_day[stats.day] = []
            by_day[stats.day].append(stats)

    results = {}

    for day, stats_list in by_day.items():
        total_points = sum(s.total_points for s in stats_list)
        total_positive = sum(s.positive_count for s in stats_list)

        results[day] = {
            "day": day,
            "day_name": get_day_name(day),
            "is_weekend": day >= 5,
            "market_count": len(stats_list),
            "total_points": total_points,
            "positive_count": total_positive,
            "positive_pct": (total_positive / total_points * 100) if total_points > 0 else 0,
            "avg_spread": np.mean([s.avg_spread for s in stats_list]),
            "avg_positive_pct": np.mean([s.positive_pct for s in stats_list]),
        }

    return results


# =============================================================================
# Export
# =============================================================================

def save_hourly_analysis_to_csv(
    hourly_agg: Dict[int, Dict],
    filename: str = "temporal_hourly.csv",
    output_dir: Path = DATA_STATS_DIR,
) -> Path:
    """Salva análise horária em CSV."""
    ensure_data_dirs_exist()

    records = [stats for stats in hourly_agg.values()]
    df = pd.DataFrame(records)
    df = df.sort_values("hour")

    filepath = output_dir / filename
    df.to_csv(filepath, index=False)

    logger.info(f"Saved hourly analysis to {filepath}")
    return filepath


def save_daily_analysis_to_csv(
    daily_agg: Dict[int, Dict],
    filename: str = "temporal_daily.csv",
    output_dir: Path = DATA_STATS_DIR,
) -> Path:
    """Salva análise diária em CSV."""
    ensure_data_dirs_exist()

    records = [stats for stats in daily_agg.values()]
    df = pd.DataFrame(records)
    df = df.sort_values("day")

    filepath = output_dir / filename
    df.to_csv(filepath, index=False)

    logger.info(f"Saved daily analysis to {filepath}")
    return filepath


# =============================================================================
# Pipeline
# =============================================================================

def run_phase6_pipeline(
    timeframe: str = DEFAULT_TIMEFRAME,
) -> Tuple[Dict[int, Dict], Dict[int, Dict], Dict]:
    """
    Executa o pipeline completo da Fase 6.

    Args:
        timeframe: Intervalo de tempo

    Returns:
        Tupla (hourly_agg, daily_agg, insights)
    """
    logger.info("=" * 50)
    logger.info("Starting Phase 6: Temporal Analysis")
    logger.info("=" * 50)

    # Carrega mercados
    try:
        groups = load_markets_from_json()
        all_markets = groups["A"] + groups["B"] + groups["C"]
    except FileNotFoundError:
        logger.error("Markets JSON not found. Run Phase 1 first.")
        return {}, {}, {}

    # Analisa cada mercado
    analyses = []
    total = len(all_markets)

    for i, market in enumerate(all_markets, 1):
        if i % 50 == 0:
            logger.info(f"Processing market {i}/{total}")

        df = load_arbitrage_series(market.id, timeframe)
        if df is not None:
            analysis = analyze_market_temporal(market, df)
            if analysis:
                analyses.append(analysis)

    logger.info(f"Analyzed {len(analyses)} markets")

    # Agrega resultados
    hourly_agg = aggregate_hourly_across_markets(analyses)
    daily_agg = aggregate_daily_across_markets(analyses)

    # Salva resultados
    save_hourly_analysis_to_csv(hourly_agg)
    save_daily_analysis_to_csv(daily_agg)

    # Gera insights
    insights = generate_temporal_insights(hourly_agg, daily_agg)

    # Log resumo
    logger.info("\nHourly Analysis (by period):")
    by_period = {}
    for hour, stats in hourly_agg.items():
        period = stats["period"]
        if period not in by_period:
            by_period[period] = []
        by_period[period].append(stats)

    for period in ["morning", "afternoon", "evening", "night"]:
        if period in by_period:
            avg_pct = np.mean([s["avg_positive_pct"] for s in by_period[period]])
            logger.info(f"  {period}: avg arbitrage {avg_pct:.2f}%")

    logger.info("\nDaily Analysis:")
    for day in range(7):
        if day in daily_agg:
            stats = daily_agg[day]
            logger.info(
                f"  {stats['day_name']}: {stats['avg_positive_pct']:.2f}% "
                f"({'weekend' if stats['is_weekend'] else 'weekday'})"
            )

    logger.info("=" * 50)
    logger.info("Phase 6 completed!")
    logger.info("=" * 50)

    return hourly_agg, daily_agg, insights


def generate_temporal_insights(
    hourly_agg: Dict[int, Dict],
    daily_agg: Dict[int, Dict],
) -> Dict:
    """
    Gera insights a partir da análise temporal.

    Args:
        hourly_agg: Estatísticas horárias agregadas
        daily_agg: Estatísticas diárias agregadas

    Returns:
        Dicionário com insights
    """
    insights = {}

    # Melhor hora do dia
    if hourly_agg:
        best_hour = max(hourly_agg.values(), key=lambda x: x["avg_positive_pct"])
        worst_hour = min(hourly_agg.values(), key=lambda x: x["avg_positive_pct"])

        insights["best_hour"] = {
            "hour": best_hour["hour"],
            "period": best_hour["period"],
            "positive_pct": best_hour["avg_positive_pct"],
        }
        insights["worst_hour"] = {
            "hour": worst_hour["hour"],
            "period": worst_hour["period"],
            "positive_pct": worst_hour["avg_positive_pct"],
        }

        # Por período
        by_period = {}
        for stats in hourly_agg.values():
            period = stats["period"]
            if period not in by_period:
                by_period[period] = []
            by_period[period].append(stats["avg_positive_pct"])

        insights["by_period"] = {
            period: np.mean(pcts) for period, pcts in by_period.items()
        }

        best_period = max(insights["by_period"].items(), key=lambda x: x[1])
        insights["best_period"] = best_period[0]
        insights["best_period_pct"] = best_period[1]

    # Melhor dia da semana
    if daily_agg:
        best_day = max(daily_agg.values(), key=lambda x: x["avg_positive_pct"])
        worst_day = min(daily_agg.values(), key=lambda x: x["avg_positive_pct"])

        insights["best_day"] = {
            "day": best_day["day"],
            "day_name": best_day["day_name"],
            "positive_pct": best_day["avg_positive_pct"],
        }
        insights["worst_day"] = {
            "day": worst_day["day"],
            "day_name": worst_day["day_name"],
            "positive_pct": worst_day["avg_positive_pct"],
        }

        # Weekday vs Weekend
        weekday_pcts = [s["avg_positive_pct"] for s in daily_agg.values() if not s["is_weekend"]]
        weekend_pcts = [s["avg_positive_pct"] for s in daily_agg.values() if s["is_weekend"]]

        weekday_avg = np.mean(weekday_pcts) if weekday_pcts else 0
        weekend_avg = np.mean(weekend_pcts) if weekend_pcts else 0

        insights["weekday_avg_pct"] = weekday_avg
        insights["weekend_avg_pct"] = weekend_avg
        insights["weekend_has_more_arb"] = weekend_avg > weekday_avg

    return insights


def print_temporal_report(
    hourly_agg: Dict[int, Dict],
    daily_agg: Dict[int, Dict],
    insights: Dict,
) -> None:
    """
    Imprime relatório de análise temporal.
    """
    print("\n" + "=" * 70)
    print("RELATÓRIO DE ANÁLISE TEMPORAL")
    print("=" * 70)

    # Por hora
    print(f"\n{'='*70}")
    print("ANÁLISE POR HORA DO DIA (UTC)")
    print("=" * 70)
    print(f"{'Hora':<6} {'Período':<12} {'Arb%':<10} {'Spread Médio':<15}")
    print("-" * 70)

    for hour in range(24):
        if hour in hourly_agg:
            stats = hourly_agg[hour]
            print(
                f"{hour:02d}:00  "
                f"{stats['period']:<12} "
                f"{stats['avg_positive_pct']:<10.2f} "
                f"{stats['avg_spread']*100:<15.4f}%"
            )

    # Por dia
    print(f"\n{'='*70}")
    print("ANÁLISE POR DIA DA SEMANA")
    print("=" * 70)
    print(f"{'Dia':<12} {'Tipo':<10} {'Arb%':<10} {'Spread Médio':<15}")
    print("-" * 70)

    for day in range(7):
        if day in daily_agg:
            stats = daily_agg[day]
            day_type = "Weekend" if stats["is_weekend"] else "Weekday"
            print(
                f"{stats['day_name']:<12} "
                f"{day_type:<10} "
                f"{stats['avg_positive_pct']:<10.2f} "
                f"{stats['avg_spread']*100:<15.4f}%"
            )

    # Insights
    print(f"\n{'='*70}")
    print("INSIGHTS")
    print("=" * 70)

    if "best_period" in insights:
        print(f"• Melhor período: {insights['best_period']} ({insights['best_period_pct']:.2f}% arbitragem)")

    if "best_hour" in insights:
        h = insights["best_hour"]
        print(f"• Melhor hora: {h['hour']:02d}:00 ({h['positive_pct']:.2f}% arbitragem)")

    if "best_day" in insights:
        d = insights["best_day"]
        print(f"• Melhor dia: {d['day_name']} ({d['positive_pct']:.2f}% arbitragem)")

    if "weekend_has_more_arb" in insights:
        if insights["weekend_has_more_arb"]:
            diff = insights["weekend_avg_pct"] - insights["weekday_avg_pct"]
            print(f"• Fim de semana tem MAIS arbitragem (+{diff:.2f}%)")
        else:
            diff = insights["weekday_avg_pct"] - insights["weekend_avg_pct"]
            print(f"• Dias úteis têm MAIS arbitragem (+{diff:.2f}%)")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    hourly_agg, daily_agg, insights = run_phase6_pipeline()

    if hourly_agg:
        print_temporal_report(hourly_agg, daily_agg, insights)
