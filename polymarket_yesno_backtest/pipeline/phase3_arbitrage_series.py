"""
Fase 3 - Reconstrução da Série de Arbitragem

Funções para calcular arbitrage_spread = 1 - (price_yes + price_no)
para cada mercado/timeframe e identificar janelas de oportunidade.
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path

import pandas as pd
import numpy as np

from config.settings import (
    DATA_RAW_DIR,
    DATA_PROCESSED_DIR,
    DEFAULT_TIMEFRAME,
    TIMEFRAMES,
    ensure_data_dirs_exist,
)
from pipeline.phase1_market_selection import load_markets_from_json

logger = logging.getLogger(__name__)

# Buffers padrão para análise de arbitragem (em decimal, não %)
DEFAULT_BUFFERS = [0.0, 0.005, 0.01, 0.02, 0.03, 0.05]


def load_market_timeseries(
    market_id: str,
    timeframe: str = DEFAULT_TIMEFRAME,
    data_dir: Path = DATA_RAW_DIR,
) -> Optional[pd.DataFrame]:
    """
    Carrega a série temporal de preços YES/NO de um mercado.

    Args:
        market_id: ID do mercado
        timeframe: Intervalo de tempo (1m, 5m, 1h, etc.)
        data_dir: Diretório onde estão os CSVs raw

    Returns:
        DataFrame com colunas [timestamp, price_yes, price_no] ou None
    """
    filename = f"{market_id}_{timeframe}.csv"
    filepath = data_dir / filename

    if not filepath.exists():
        logger.warning(f"Price file not found: {filepath}")
        return None

    try:
        df = pd.read_csv(filepath, parse_dates=["timestamp"])
        logger.info(f"Loaded {len(df)} rows from {filepath}")
        return df
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return None


def add_arbitrage_spread(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona a coluna de arbitrage_spread ao DataFrame.

    arbitrage_spread = 1 - (price_yes + price_no)

    Quando arbitrage_spread > 0, há oportunidade de arbitragem
    (comprar YES e NO custa menos que $1, garantindo lucro).

    Args:
        df: DataFrame com colunas price_yes e price_no

    Returns:
        DataFrame com coluna arbitrage_spread adicionada
    """
    df = df.copy()

    # Preenche NaN com 0 para cálculo
    price_yes = df["price_yes"].fillna(0)
    price_no = df["price_no"].fillna(0)

    # Calcula o spread de arbitragem
    df["arbitrage_spread"] = 1.0 - (price_yes + price_no)

    # Calcula também o total para referência
    df["total_price"] = price_yes + price_no

    logger.debug(
        f"Added arbitrage_spread: mean={df['arbitrage_spread'].mean():.4f}, "
        f"min={df['arbitrage_spread'].min():.4f}, max={df['arbitrage_spread'].max():.4f}"
    )

    return df


def tag_buffers(
    df: pd.DataFrame,
    buffers: List[float] = None,
) -> pd.DataFrame:
    """
    Cria colunas booleanas indicando se o spread excede cada buffer.

    Cria colunas como:
    - spread_gt_0: spread > 0 (qualquer arbitragem)
    - spread_gt_0_005: spread > 0.5%
    - spread_gt_0_01: spread > 1%
    - spread_gt_0_02: spread > 2%

    Args:
        df: DataFrame com coluna arbitrage_spread
        buffers: Lista de thresholds (em decimal). Default: [0, 0.005, 0.01, 0.02, 0.03, 0.05]

    Returns:
        DataFrame com colunas booleanas adicionadas
    """
    if buffers is None:
        buffers = DEFAULT_BUFFERS

    df = df.copy()

    if "arbitrage_spread" not in df.columns:
        df = add_arbitrage_spread(df)

    for buffer in buffers:
        # Cria nome da coluna (ex: spread_gt_0, spread_gt_0_005, spread_gt_0_01)
        if buffer == 0:
            col_name = "spread_gt_0"
        else:
            # Converte 0.005 -> "0_005", 0.01 -> "0_01", etc.
            buffer_str = f"{buffer:.3f}".replace(".", "_").rstrip("0").rstrip("_")
            col_name = f"spread_gt_{buffer_str}"

        df[col_name] = df["arbitrage_spread"] > buffer

        count = df[col_name].sum()
        pct = (count / len(df) * 100) if len(df) > 0 else 0
        logger.debug(f"Buffer {buffer*100:.1f}%: {count} points ({pct:.2f}%)")

    return df


def process_market_arbitrage(
    market_id: str,
    timeframe: str = DEFAULT_TIMEFRAME,
    buffers: List[float] = None,
    input_dir: Path = DATA_RAW_DIR,
    output_dir: Path = DATA_PROCESSED_DIR,
    save: bool = True,
) -> Optional[pd.DataFrame]:
    """
    Processa um mercado: carrega dados, calcula spread e tags, salva resultado.

    Args:
        market_id: ID do mercado
        timeframe: Intervalo de tempo
        buffers: Lista de thresholds para tags
        input_dir: Diretório de entrada (raw)
        output_dir: Diretório de saída (processed)
        save: Se True, salva o resultado em CSV

    Returns:
        DataFrame processado ou None se falhar
    """
    # 1. Carrega série temporal
    df = load_market_timeseries(market_id, timeframe, input_dir)
    if df is None:
        return None

    # 2. Adiciona arbitrage_spread
    df = add_arbitrage_spread(df)

    # 3. Adiciona tags de buffer
    df = tag_buffers(df, buffers)

    # 4. Salva resultado
    if save:
        ensure_data_dirs_exist()
        filename = f"{market_id}_{timeframe}_arb.csv"
        filepath = output_dir / filename
        df.to_csv(filepath, index=False)
        logger.info(f"Saved arbitrage series to {filepath}")

    return df


def process_all_markets_arbitrage(
    market_ids: Optional[List[str]] = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    buffers: List[float] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Processa todos os mercados para calcular séries de arbitragem.

    Args:
        market_ids: Lista de IDs (se None, carrega do JSON da Fase 1)
        timeframe: Intervalo de tempo
        buffers: Lista de thresholds

    Returns:
        Dicionário {market_id: DataFrame}
    """
    # Se não especificado, carrega mercados do JSON
    if market_ids is None:
        try:
            groups = load_markets_from_json()
            market_ids = [
                m.id for m in groups["A"] + groups["B"] + groups["C"]
            ]
        except FileNotFoundError:
            logger.error("Markets JSON not found. Run Phase 1 first.")
            return {}

    results = {}
    total = len(market_ids)

    for i, market_id in enumerate(market_ids, 1):
        logger.info(f"Processing market {i}/{total}: {market_id}")

        df = process_market_arbitrage(
            market_id=market_id,
            timeframe=timeframe,
            buffers=buffers,
        )

        if df is not None:
            results[market_id] = df

    logger.info(f"Processed {len(results)}/{total} markets successfully")
    return results


def load_arbitrage_series(
    market_id: str,
    timeframe: str = DEFAULT_TIMEFRAME,
    data_dir: Path = DATA_PROCESSED_DIR,
) -> Optional[pd.DataFrame]:
    """
    Carrega série de arbitragem já processada.

    Args:
        market_id: ID do mercado
        timeframe: Intervalo de tempo
        data_dir: Diretório dos dados processados

    Returns:
        DataFrame ou None se não existir
    """
    filename = f"{market_id}_{timeframe}_arb.csv"
    filepath = data_dir / filename

    if not filepath.exists():
        logger.warning(f"Arbitrage file not found: {filepath}")
        return None

    try:
        df = pd.read_csv(filepath, parse_dates=["timestamp"])
        logger.info(f"Loaded arbitrage series: {len(df)} rows from {filepath}")
        return df
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return None


def get_arbitrage_summary(df: pd.DataFrame) -> Dict:
    """
    Gera resumo rápido de uma série de arbitragem.

    Args:
        df: DataFrame com arbitrage_spread

    Returns:
        Dicionário com estatísticas resumidas
    """
    if df is None or len(df) == 0:
        return {"valid": False, "count": 0}

    spread = df["arbitrage_spread"]

    summary = {
        "valid": True,
        "count": len(df),
        "spread_mean": float(spread.mean()),
        "spread_std": float(spread.std()),
        "spread_min": float(spread.min()),
        "spread_max": float(spread.max()),
        "spread_median": float(spread.median()),
        "positive_count": int((spread > 0).sum()),
        "positive_pct": float((spread > 0).sum() / len(df) * 100),
    }

    # Adiciona contagem por buffer se existirem as colunas
    for col in df.columns:
        if col.startswith("spread_gt_"):
            summary[f"{col}_count"] = int(df[col].sum())
            summary[f"{col}_pct"] = float(df[col].sum() / len(df) * 100)

    return summary


def run_phase3_pipeline(
    market_ids: Optional[List[str]] = None,
    timeframes: Optional[List[str]] = None,
    buffers: List[float] = None,
) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Executa o pipeline completo da Fase 3.

    Args:
        market_ids: Lista de IDs de mercados (carrega do JSON se None)
        timeframes: Lista de timeframes (usa default se None)
        buffers: Lista de thresholds para tags

    Returns:
        Dicionário {timeframe: {market_id: DataFrame}}
    """
    logger.info("=" * 50)
    logger.info("Starting Phase 3: Arbitrage Series Reconstruction")
    logger.info("=" * 50)

    if timeframes is None:
        timeframes = [DEFAULT_TIMEFRAME]

    results = {}

    for timeframe in timeframes:
        logger.info(f"\nProcessing timeframe: {timeframe}")

        market_results = process_all_markets_arbitrage(
            market_ids=market_ids,
            timeframe=timeframe,
            buffers=buffers,
        )

        results[timeframe] = market_results

        # Mostra resumo
        total_positive = 0
        for market_id, df in market_results.items():
            summary = get_arbitrage_summary(df)
            if summary["positive_pct"] > 0:
                total_positive += 1

        logger.info(
            f"Timeframe {timeframe}: {len(market_results)} markets, "
            f"{total_positive} with positive arbitrage"
        )

    logger.info("=" * 50)
    logger.info("Phase 3 completed!")
    logger.info("=" * 50)

    return results


if __name__ == "__main__":
    # Configura logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Executa pipeline
    results = run_phase3_pipeline()

    # Mostra resumo
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    for timeframe, market_results in results.items():
        print(f"\nTimeframe: {timeframe}")
        print(f"  Markets processed: {len(market_results)}")

        if market_results:
            # Mostra top 5 mercados com maior arbitragem
            summaries = [
                (mid, get_arbitrage_summary(df))
                for mid, df in market_results.items()
            ]
            summaries.sort(key=lambda x: x[1].get("positive_pct", 0), reverse=True)

            print("\n  Top 5 markets by arbitrage frequency:")
            for mid, summary in summaries[:5]:
                print(
                    f"    {mid[:16]}... : "
                    f"{summary['positive_pct']:.1f}% positive, "
                    f"avg spread {summary['spread_mean']*100:.2f}%"
                )
