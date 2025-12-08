"""
Fase 4 - Estatísticas Descritivas do Spread

Funções para medir frequência, magnitude, duração e distribuição
do spread de arbitragem por mercado/timeframe.
"""

import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict

import pandas as pd
import numpy as np

from config.settings import (
    DATA_PROCESSED_DIR,
    DATA_STATS_DIR,
    DEFAULT_TIMEFRAME,
    ensure_data_dirs_exist,
)
from core.utils_time import timeframe_to_seconds
from pipeline.phase3_arbitrage_series import (
    load_arbitrage_series,
    DEFAULT_BUFFERS,
)
from pipeline.phase1_market_selection import load_markets_from_json

logger = logging.getLogger(__name__)


@dataclass
class FrequencyStats:
    """Estatísticas de frequência de arbitragem."""
    total_points: int
    positive_count: int
    positive_pct: float
    buffer_stats: Dict[float, Dict[str, float]]  # {buffer: {count, pct}}


@dataclass
class MagnitudeStats:
    """Estatísticas de magnitude do spread."""
    mean: float
    median: float
    std: float
    min: float
    max: float
    p25: float
    p75: float
    p90: float
    p95: float
    p99: float


@dataclass
class RunStats:
    """Estatísticas de duração de janelas contínuas."""
    total_runs: int
    mean_duration: float
    median_duration: float
    std_duration: float
    min_duration: float
    max_duration: float
    p90_duration: float
    p95_duration: float
    total_time_in_arbitrage: float
    pct_time_in_arbitrage: float


@dataclass
class MarketSpreadStats:
    """Estatísticas completas de spread para um mercado."""
    market_id: str
    timeframe: str
    total_points: int
    duration_hours: float
    frequency: FrequencyStats
    magnitude_all: MagnitudeStats
    magnitude_positive: Optional[MagnitudeStats]
    run_stats: Dict[float, RunStats]  # {threshold: RunStats}


# =============================================================================
# Funções de Frequência
# =============================================================================

def compute_frequency_stats(
    df: pd.DataFrame,
    buffers: List[float] = None,
) -> FrequencyStats:
    """
    Calcula estatísticas de frequência de arbitragem.

    Args:
        df: DataFrame com coluna arbitrage_spread
        buffers: Lista de thresholds para análise

    Returns:
        Objeto FrequencyStats
    """
    if buffers is None:
        buffers = DEFAULT_BUFFERS

    total = len(df)
    spread = df["arbitrage_spread"]

    # Contagem de spread > 0
    positive_count = int((spread > 0).sum())
    positive_pct = (positive_count / total * 100) if total > 0 else 0.0

    # Estatísticas por buffer
    buffer_stats = {}
    for buffer in buffers:
        count = int((spread > buffer).sum())
        pct = (count / total * 100) if total > 0 else 0.0
        buffer_stats[buffer] = {"count": count, "pct": pct}

    return FrequencyStats(
        total_points=total,
        positive_count=positive_count,
        positive_pct=positive_pct,
        buffer_stats=buffer_stats,
    )


# =============================================================================
# Funções de Magnitude
# =============================================================================

def compute_magnitude_stats(
    spread_series: pd.Series,
) -> MagnitudeStats:
    """
    Calcula estatísticas de magnitude do spread.

    Args:
        spread_series: Série com valores de spread

    Returns:
        Objeto MagnitudeStats
    """
    if len(spread_series) == 0:
        return MagnitudeStats(
            mean=0, median=0, std=0, min=0, max=0,
            p25=0, p75=0, p90=0, p95=0, p99=0,
        )

    return MagnitudeStats(
        mean=float(spread_series.mean()),
        median=float(spread_series.median()),
        std=float(spread_series.std()),
        min=float(spread_series.min()),
        max=float(spread_series.max()),
        p25=float(spread_series.quantile(0.25)),
        p75=float(spread_series.quantile(0.75)),
        p90=float(spread_series.quantile(0.90)),
        p95=float(spread_series.quantile(0.95)),
        p99=float(spread_series.quantile(0.99)),
    )


def compute_magnitude_by_buffer(
    df: pd.DataFrame,
    buffers: List[float] = None,
) -> Dict[float, MagnitudeStats]:
    """
    Calcula estatísticas de magnitude para cada buffer.

    Args:
        df: DataFrame com coluna arbitrage_spread
        buffers: Lista de thresholds

    Returns:
        Dicionário {buffer: MagnitudeStats}
    """
    if buffers is None:
        buffers = DEFAULT_BUFFERS

    results = {}
    spread = df["arbitrage_spread"]

    for buffer in buffers:
        filtered = spread[spread > buffer]
        results[buffer] = compute_magnitude_stats(filtered)

    return results


# =============================================================================
# Funções de Duração (Runs)
# =============================================================================

def detect_arbitrage_runs(
    df: pd.DataFrame,
    threshold: float = 0.0,
) -> List[Dict]:
    """
    Detecta sequências contínuas onde spread > threshold.

    Uma "run" é uma janela contínua de arbitragem.

    Args:
        df: DataFrame com timestamp e arbitrage_spread
        threshold: Threshold mínimo para considerar arbitragem

    Returns:
        Lista de dicionários com informações de cada run:
        [{"start_idx", "end_idx", "start_time", "end_time", "duration_candles", "duration_seconds", "avg_spread", "max_spread"}]
    """
    if len(df) == 0:
        return []

    spread = df["arbitrage_spread"].values
    timestamps = df["timestamp"].values

    runs = []
    in_run = False
    start_idx = 0

    for i, s in enumerate(spread):
        if s > threshold:
            if not in_run:
                # Início de uma nova run
                in_run = True
                start_idx = i
        else:
            if in_run:
                # Fim da run atual
                in_run = False
                end_idx = i - 1

                run_spread = spread[start_idx:end_idx + 1]
                run_times = timestamps[start_idx:end_idx + 1]

                duration_candles = end_idx - start_idx + 1
                duration_seconds = (
                    pd.Timestamp(run_times[-1]) - pd.Timestamp(run_times[0])
                ).total_seconds()

                runs.append({
                    "start_idx": start_idx,
                    "end_idx": end_idx,
                    "start_time": pd.Timestamp(run_times[0]),
                    "end_time": pd.Timestamp(run_times[-1]),
                    "duration_candles": duration_candles,
                    "duration_seconds": duration_seconds,
                    "avg_spread": float(np.mean(run_spread)),
                    "max_spread": float(np.max(run_spread)),
                })

    # Verifica se terminou em uma run
    if in_run:
        end_idx = len(spread) - 1
        run_spread = spread[start_idx:end_idx + 1]
        run_times = timestamps[start_idx:end_idx + 1]

        duration_candles = end_idx - start_idx + 1
        duration_seconds = (
            pd.Timestamp(run_times[-1]) - pd.Timestamp(run_times[0])
        ).total_seconds()

        runs.append({
            "start_idx": start_idx,
            "end_idx": end_idx,
            "start_time": pd.Timestamp(run_times[0]),
            "end_time": pd.Timestamp(run_times[-1]),
            "duration_candles": duration_candles,
            "duration_seconds": duration_seconds,
            "avg_spread": float(np.mean(run_spread)),
            "max_spread": float(np.max(run_spread)),
        })

    return runs


def compute_arbitrage_runs(
    df: pd.DataFrame,
    threshold: float = 0.0,
    timeframe: str = DEFAULT_TIMEFRAME,
) -> RunStats:
    """
    Calcula estatísticas das janelas contínuas de arbitragem.

    Args:
        df: DataFrame com timestamp e arbitrage_spread
        threshold: Threshold mínimo para considerar arbitragem
        timeframe: Intervalo de tempo (para calcular duração em minutos)

    Returns:
        Objeto RunStats com estatísticas de duração
    """
    runs = detect_arbitrage_runs(df, threshold)

    if not runs:
        return RunStats(
            total_runs=0,
            mean_duration=0,
            median_duration=0,
            std_duration=0,
            min_duration=0,
            max_duration=0,
            p90_duration=0,
            p95_duration=0,
            total_time_in_arbitrage=0,
            pct_time_in_arbitrage=0,
        )

    # Duração em número de candles
    durations = [r["duration_candles"] for r in runs]
    durations_arr = np.array(durations)

    # Tempo total do dataset
    total_candles = len(df)

    # Tempo total em arbitragem (soma das durações)
    total_time = sum(durations)
    pct_time = (total_time / total_candles * 100) if total_candles > 0 else 0

    # Converte duração de candles para minutos
    candle_seconds = timeframe_to_seconds(timeframe)
    candle_minutes = candle_seconds / 60

    return RunStats(
        total_runs=len(runs),
        mean_duration=float(np.mean(durations_arr) * candle_minutes),
        median_duration=float(np.median(durations_arr) * candle_minutes),
        std_duration=float(np.std(durations_arr) * candle_minutes),
        min_duration=float(np.min(durations_arr) * candle_minutes),
        max_duration=float(np.max(durations_arr) * candle_minutes),
        p90_duration=float(np.percentile(durations_arr, 90) * candle_minutes),
        p95_duration=float(np.percentile(durations_arr, 95) * candle_minutes),
        total_time_in_arbitrage=float(total_time * candle_minutes),
        pct_time_in_arbitrage=float(pct_time),
    )


def compute_runs_by_threshold(
    df: pd.DataFrame,
    thresholds: List[float] = None,
    timeframe: str = DEFAULT_TIMEFRAME,
) -> Dict[float, RunStats]:
    """
    Calcula estatísticas de runs para múltiplos thresholds.

    Args:
        df: DataFrame com arbitrage_spread
        thresholds: Lista de thresholds
        timeframe: Intervalo de tempo

    Returns:
        Dicionário {threshold: RunStats}
    """
    if thresholds is None:
        thresholds = DEFAULT_BUFFERS

    results = {}
    for threshold in thresholds:
        results[threshold] = compute_arbitrage_runs(df, threshold, timeframe)

    return results


# =============================================================================
# Função Principal de Estatísticas
# =============================================================================

def compute_market_stats(
    df: pd.DataFrame,
    market_id: str,
    timeframe: str = DEFAULT_TIMEFRAME,
    buffers: List[float] = None,
) -> MarketSpreadStats:
    """
    Calcula todas as estatísticas de spread para um mercado.

    Args:
        df: DataFrame com arbitrage_spread
        market_id: ID do mercado
        timeframe: Intervalo de tempo
        buffers: Lista de thresholds

    Returns:
        Objeto MarketSpreadStats
    """
    if buffers is None:
        buffers = DEFAULT_BUFFERS

    spread = df["arbitrage_spread"]

    # Frequência
    frequency = compute_frequency_stats(df, buffers)

    # Magnitude - todos os pontos
    magnitude_all = compute_magnitude_stats(spread)

    # Magnitude - apenas positivos
    positive_spread = spread[spread > 0]
    magnitude_positive = (
        compute_magnitude_stats(positive_spread)
        if len(positive_spread) > 0 else None
    )

    # Runs por threshold
    run_stats = compute_runs_by_threshold(df, buffers, timeframe)

    # Duração total do dataset
    if "timestamp" in df.columns and len(df) > 0:
        duration_seconds = (
            df["timestamp"].max() - df["timestamp"].min()
        ).total_seconds()
        duration_hours = duration_seconds / 3600
    else:
        duration_hours = 0

    return MarketSpreadStats(
        market_id=market_id,
        timeframe=timeframe,
        total_points=len(df),
        duration_hours=duration_hours,
        frequency=frequency,
        magnitude_all=magnitude_all,
        magnitude_positive=magnitude_positive,
        run_stats=run_stats,
    )


# =============================================================================
# Export e Agregação
# =============================================================================

def stats_to_flat_dict(stats: MarketSpreadStats) -> Dict:
    """
    Converte MarketSpreadStats para dicionário plano (para CSV).

    Args:
        stats: Objeto MarketSpreadStats

    Returns:
        Dicionário com chaves planas
    """
    flat = {
        "market_id": stats.market_id,
        "timeframe": stats.timeframe,
        "total_points": stats.total_points,
        "duration_hours": stats.duration_hours,
        # Frequência
        "freq_positive_count": stats.frequency.positive_count,
        "freq_positive_pct": stats.frequency.positive_pct,
    }

    # Frequência por buffer
    for buffer, bstats in stats.frequency.buffer_stats.items():
        key = f"freq_gt_{buffer:.3f}".replace(".", "_")
        flat[f"{key}_count"] = bstats["count"]
        flat[f"{key}_pct"] = bstats["pct"]

    # Magnitude - todos
    flat["mag_all_mean"] = stats.magnitude_all.mean
    flat["mag_all_median"] = stats.magnitude_all.median
    flat["mag_all_std"] = stats.magnitude_all.std
    flat["mag_all_min"] = stats.magnitude_all.min
    flat["mag_all_max"] = stats.magnitude_all.max
    flat["mag_all_p90"] = stats.magnitude_all.p90
    flat["mag_all_p95"] = stats.magnitude_all.p95

    # Magnitude - positivos
    if stats.magnitude_positive:
        flat["mag_pos_mean"] = stats.magnitude_positive.mean
        flat["mag_pos_median"] = stats.magnitude_positive.median
        flat["mag_pos_max"] = stats.magnitude_positive.max
        flat["mag_pos_p90"] = stats.magnitude_positive.p90
        flat["mag_pos_p95"] = stats.magnitude_positive.p95
    else:
        flat["mag_pos_mean"] = None
        flat["mag_pos_median"] = None
        flat["mag_pos_max"] = None
        flat["mag_pos_p90"] = None
        flat["mag_pos_p95"] = None

    # Runs - apenas para threshold 0
    if 0.0 in stats.run_stats:
        rs = stats.run_stats[0.0]
        flat["runs_total"] = rs.total_runs
        flat["runs_mean_duration_min"] = rs.mean_duration
        flat["runs_median_duration_min"] = rs.median_duration
        flat["runs_max_duration_min"] = rs.max_duration
        flat["runs_p90_duration_min"] = rs.p90_duration
        flat["runs_p95_duration_min"] = rs.p95_duration
        flat["runs_total_time_min"] = rs.total_time_in_arbitrage
        flat["runs_pct_time"] = rs.pct_time_in_arbitrage

    return flat


def save_stats_to_csv(
    stats_list: List[MarketSpreadStats],
    filename: str = "market_spread_stats.csv",
    output_dir: Path = DATA_STATS_DIR,
) -> Path:
    """
    Salva estatísticas de múltiplos mercados em arquivo CSV.

    Args:
        stats_list: Lista de MarketSpreadStats
        filename: Nome do arquivo
        output_dir: Diretório de saída

    Returns:
        Caminho do arquivo salvo
    """
    ensure_data_dirs_exist()

    records = [stats_to_flat_dict(s) for s in stats_list]
    df = pd.DataFrame(records)

    # Ordena por frequência de arbitragem (decrescente)
    if "freq_positive_pct" in df.columns:
        df = df.sort_values("freq_positive_pct", ascending=False)

    filepath = output_dir / filename
    df.to_csv(filepath, index=False)

    logger.info(f"Saved {len(stats_list)} market stats to {filepath}")
    return filepath


def load_stats_from_csv(
    filename: str = "market_spread_stats.csv",
    data_dir: Path = DATA_STATS_DIR,
) -> Optional[pd.DataFrame]:
    """
    Carrega estatísticas de arquivo CSV.

    Args:
        filename: Nome do arquivo
        data_dir: Diretório dos dados

    Returns:
        DataFrame ou None se não existir
    """
    filepath = data_dir / filename

    if not filepath.exists():
        logger.warning(f"Stats file not found: {filepath}")
        return None

    df = pd.read_csv(filepath)
    logger.info(f"Loaded stats for {len(df)} markets from {filepath}")
    return df


# =============================================================================
# Pipeline
# =============================================================================

def run_phase4_pipeline(
    market_ids: Optional[List[str]] = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    buffers: List[float] = None,
) -> Tuple[List[MarketSpreadStats], pd.DataFrame]:
    """
    Executa o pipeline completo da Fase 4.

    Args:
        market_ids: Lista de IDs de mercados (carrega do JSON se None)
        timeframe: Intervalo de tempo
        buffers: Lista de thresholds

    Returns:
        Tupla (lista de MarketSpreadStats, DataFrame resumo)
    """
    logger.info("=" * 50)
    logger.info("Starting Phase 4: Spread Statistics")
    logger.info("=" * 50)

    # Carrega mercados se não especificados
    if market_ids is None:
        try:
            groups = load_markets_from_json()
            market_ids = [
                m.id for m in groups["A"] + groups["B"] + groups["C"]
            ]
        except FileNotFoundError:
            logger.error("Markets JSON not found. Run Phase 1 first.")
            return [], pd.DataFrame()

    stats_list = []
    total = len(market_ids)

    for i, market_id in enumerate(market_ids, 1):
        logger.info(f"Processing market {i}/{total}: {market_id}")

        # Carrega série de arbitragem (da Fase 3)
        df = load_arbitrage_series(market_id, timeframe)

        if df is None:
            logger.warning(f"Skipping {market_id} - no arbitrage data")
            continue

        # Calcula estatísticas
        stats = compute_market_stats(df, market_id, timeframe, buffers)
        stats_list.append(stats)

    # Salva resultados
    if stats_list:
        filepath = save_stats_to_csv(stats_list)
        df_summary = load_stats_from_csv()
    else:
        df_summary = pd.DataFrame()

    # Mostra resumo
    if stats_list:
        avg_positive_pct = np.mean([s.frequency.positive_pct for s in stats_list])
        max_positive_pct = max(s.frequency.positive_pct for s in stats_list)

        logger.info(f"\nProcessed {len(stats_list)} markets")
        logger.info(f"Average positive arbitrage: {avg_positive_pct:.2f}%")
        logger.info(f"Max positive arbitrage: {max_positive_pct:.2f}%")

    logger.info("=" * 50)
    logger.info("Phase 4 completed!")
    logger.info("=" * 50)

    return stats_list, df_summary


def print_stats_summary(stats: MarketSpreadStats) -> None:
    """
    Imprime resumo legível das estatísticas de um mercado.

    Args:
        stats: Objeto MarketSpreadStats
    """
    print(f"\n{'='*60}")
    print(f"Market: {stats.market_id}")
    print(f"Timeframe: {stats.timeframe}")
    print(f"Total Points: {stats.total_points:,}")
    print(f"Duration: {stats.duration_hours:.1f} hours")

    print(f"\n--- Frequency ---")
    print(f"Positive (>0): {stats.frequency.positive_count:,} ({stats.frequency.positive_pct:.2f}%)")
    for buffer, bstats in sorted(stats.frequency.buffer_stats.items()):
        if buffer > 0:
            print(f">{buffer*100:.1f}%: {bstats['count']:,} ({bstats['pct']:.2f}%)")

    print(f"\n--- Magnitude (all) ---")
    m = stats.magnitude_all
    print(f"Mean: {m.mean*100:.3f}% | Median: {m.median*100:.3f}%")
    print(f"Min: {m.min*100:.3f}% | Max: {m.max*100:.3f}%")
    print(f"P90: {m.p90*100:.3f}% | P95: {m.p95*100:.3f}%")

    if stats.magnitude_positive:
        print(f"\n--- Magnitude (positive only) ---")
        mp = stats.magnitude_positive
        print(f"Mean: {mp.mean*100:.3f}% | Median: {mp.median*100:.3f}%")
        print(f"Max: {mp.max*100:.3f}% | P95: {mp.p95*100:.3f}%")

    if 0.0 in stats.run_stats:
        print(f"\n--- Runs (spread > 0) ---")
        r = stats.run_stats[0.0]
        print(f"Total runs: {r.total_runs}")
        print(f"Mean duration: {r.mean_duration:.1f} min | Median: {r.median_duration:.1f} min")
        print(f"Max duration: {r.max_duration:.1f} min")
        print(f"Time in arbitrage: {r.total_time_in_arbitrage:.1f} min ({r.pct_time_in_arbitrage:.2f}%)")


if __name__ == "__main__":
    # Configura logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Executa pipeline
    stats_list, df_summary = run_phase4_pipeline()

    # Mostra resumo dos top 5 mercados
    print("\n" + "=" * 60)
    print("TOP 5 MARKETS BY ARBITRAGE FREQUENCY")
    print("=" * 60)

    # Ordena por frequência positiva
    sorted_stats = sorted(
        stats_list,
        key=lambda s: s.frequency.positive_pct,
        reverse=True
    )

    for stats in sorted_stats[:5]:
        print_stats_summary(stats)
