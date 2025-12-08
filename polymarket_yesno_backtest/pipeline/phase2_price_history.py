"""
Fase 2 - Coleta das Séries Históricas de Preço

Funções para baixar histórico de preços YES e NO para cada mercado.
"""

import time
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime

import pandas as pd

from config.settings import (
    TIMEFRAMES,
    DEFAULT_TIMEFRAME,
    DATA_RAW_DIR,
    ensure_data_dirs_exist,
)
from core.api_client import PolymarketAPIClient, get_api_client
from core.models import Market, PriceHistory, PricePoint
from core.utils_time import to_timestamp, now_utc
from pipeline.phase1_market_selection import load_markets_from_json

logger = logging.getLogger(__name__)


def get_yes_no_token_ids(market: Market) -> Tuple[Optional[str], Optional[str]]:
    """
    Obtém os token_ids de YES e NO para um mercado.

    Args:
        market: Objeto Market

    Returns:
        Tupla (yes_token_id, no_token_id)
    """
    return market.yes_token_id, market.no_token_id


def download_token_price_history(
    api_client: PolymarketAPIClient,
    token_id: str,
    start_ts: int,
    end_ts: int,
    interval: str = DEFAULT_TIMEFRAME,
) -> List[PricePoint]:
    """
    Baixa histórico de preços para um token específico.

    Args:
        api_client: Cliente de API
        token_id: ID do token
        start_ts: Timestamp de início (segundos)
        end_ts: Timestamp de fim (segundos)
        interval: Intervalo de tempo

    Returns:
        Lista de PricePoint
    """
    prices = []

    raw_prices = api_client.fetch_price_history(
        token_id=token_id,
        start_ts=start_ts,
        end_ts=end_ts,
        interval=interval,
    )

    for timestamp, price in raw_prices:
        prices.append(PricePoint(timestamp=timestamp, price=price))

    return prices


def download_market_price_history(
    market: Market,
    timeframe: str = DEFAULT_TIMEFRAME,
    api_client: Optional[PolymarketAPIClient] = None,
) -> Optional[PriceHistory]:
    """
    Baixa histórico de preços YES e NO para um mercado.

    Args:
        market: Objeto Market com dados do mercado
        timeframe: Intervalo de tempo
        api_client: Cliente de API (usa singleton se None)

    Returns:
        Objeto PriceHistory ou None se falhar
    """
    client = api_client or get_api_client()

    yes_id, no_id = get_yes_no_token_ids(market)

    if not yes_id or not no_id:
        logger.warning(f"Market {market.id} missing token IDs")
        return None

    if not market.start_date or not market.end_date:
        logger.warning(f"Market {market.id} missing date range")
        return None

    start_ts = to_timestamp(market.start_date)
    end_ts = to_timestamp(market.end_date)

    logger.info(
        f"Downloading price history for {market.id} "
        f"({market.question[:50]}...) [{timeframe}]"
    )

    # Baixa preços YES
    yes_prices = download_token_price_history(
        client, yes_id, start_ts, end_ts, timeframe
    )

    # Rate limit protection
    time.sleep(0.5)

    # Baixa preços NO
    no_prices = download_token_price_history(
        client, no_id, start_ts, end_ts, timeframe
    )

    price_history = PriceHistory(
        market_id=market.id,
        timeframe=timeframe,
        yes_prices=yes_prices,
        no_prices=no_prices,
    )

    logger.info(
        f"Downloaded {len(yes_prices)} YES and {len(no_prices)} NO price points"
    )

    return price_history


def save_price_history_to_csv(
    price_history: PriceHistory,
    output_dir: Path = DATA_RAW_DIR,
) -> Path:
    """
    Salva histórico de preços em arquivo CSV.

    Args:
        price_history: Objeto PriceHistory
        output_dir: Diretório de saída

    Returns:
        Caminho do arquivo salvo
    """
    ensure_data_dirs_exist()

    # Cria DataFrame a partir dos preços
    yes_data = {
        pp.timestamp: pp.price for pp in price_history.yes_prices
    }
    no_data = {
        pp.timestamp: pp.price for pp in price_history.no_prices
    }

    # Combina timestamps únicos
    all_timestamps = sorted(set(yes_data.keys()) | set(no_data.keys()))

    records = []
    for ts in all_timestamps:
        records.append({
            "timestamp": ts,
            "price_yes": yes_data.get(ts),
            "price_no": no_data.get(ts),
        })

    df = pd.DataFrame(records)

    # Calcula spread e total
    if len(df) > 0:
        df["total"] = df["price_yes"].fillna(0) + df["price_no"].fillna(0)
        df["spread"] = 1.0 - df["total"]

    # Nome do arquivo
    filename = f"{price_history.market_id}_{price_history.timeframe}.csv"
    filepath = output_dir / filename

    df.to_csv(filepath, index=False)

    logger.info(f"Saved price history to {filepath}")

    return filepath


def load_price_history_from_csv(
    market_id: str,
    timeframe: str = DEFAULT_TIMEFRAME,
    data_dir: Path = DATA_RAW_DIR,
) -> Optional[pd.DataFrame]:
    """
    Carrega histórico de preços de arquivo CSV.

    Args:
        market_id: ID do mercado
        timeframe: Intervalo de tempo
        data_dir: Diretório dos dados

    Returns:
        DataFrame com histórico ou None se não existir
    """
    filename = f"{market_id}_{timeframe}.csv"
    filepath = data_dir / filename

    if not filepath.exists():
        logger.warning(f"Price history file not found: {filepath}")
        return None

    df = pd.read_csv(filepath, parse_dates=["timestamp"])

    logger.info(f"Loaded {len(df)} price points from {filepath}")

    return df


def download_all_markets_price_history(
    markets: List[Market],
    timeframe: str = DEFAULT_TIMEFRAME,
    api_client: Optional[PolymarketAPIClient] = None,
    delay_between_markets: float = 1.0,
    skip_existing: bool = True,
) -> Dict[str, Path]:
    """
    Baixa histórico de preços para múltiplos mercados.

    Args:
        markets: Lista de mercados
        timeframe: Intervalo de tempo
        api_client: Cliente de API
        delay_between_markets: Delay entre mercados (segundos)
        skip_existing: Se True, pula mercados com CSV existente

    Returns:
        Dicionário {market_id: filepath}
    """
    client = api_client or get_api_client()
    results = {}

    total = len(markets)
    for i, market in enumerate(markets, 1):
        logger.info(f"Processing market {i}/{total}: {market.id}")

        # Verifica se já existe
        if skip_existing:
            existing_path = DATA_RAW_DIR / f"{market.id}_{timeframe}.csv"
            if existing_path.exists():
                logger.info(f"Skipping {market.id} - already exists")
                results[market.id] = existing_path
                continue

        # Baixa histórico
        price_history = download_market_price_history(
            market, timeframe, client
        )

        if price_history and price_history.has_data:
            filepath = save_price_history_to_csv(price_history)
            results[market.id] = filepath
        else:
            logger.warning(f"No price data for market {market.id}")

        # Rate limit protection
        if i < total:
            time.sleep(delay_between_markets)

    logger.info(f"Downloaded price history for {len(results)} markets")

    return results


def run_phase2_pipeline(
    groups: Optional[Dict[str, List[Market]]] = None,
    timeframes: List[str] = None,
    api_client: Optional[PolymarketAPIClient] = None,
) -> Dict[str, Dict[str, Path]]:
    """
    Executa o pipeline completo da Fase 2.

    Args:
        groups: Grupos de mercados (carrega do JSON se None)
        timeframes: Lista de timeframes para baixar
        api_client: Cliente de API

    Returns:
        Dicionário {timeframe: {market_id: filepath}}
    """
    logger.info("=" * 50)
    logger.info("Starting Phase 2: Price History Collection")
    logger.info("=" * 50)

    # Carrega mercados se não fornecidos
    if groups is None:
        groups = load_markets_from_json()

    # Timeframes a processar
    if timeframes is None:
        timeframes = [DEFAULT_TIMEFRAME]

    # Combina todos os mercados
    all_markets = groups["A"] + groups["B"] + groups["C"]

    logger.info(f"Processing {len(all_markets)} markets for {len(timeframes)} timeframes")

    results = {}

    for timeframe in timeframes:
        logger.info(f"\nProcessing timeframe: {timeframe}")

        result = download_all_markets_price_history(
            markets=all_markets,
            timeframe=timeframe,
            api_client=api_client,
        )

        results[timeframe] = result

    logger.info("=" * 50)
    logger.info("Phase 2 completed!")
    logger.info("=" * 50)

    return results


def get_price_history_stats(df: pd.DataFrame) -> Dict:
    """
    Calcula estatísticas de um DataFrame de histórico de preços.

    Args:
        df: DataFrame com colunas timestamp, price_yes, price_no

    Returns:
        Dicionário com estatísticas
    """
    if df is None or len(df) == 0:
        return {"count": 0}

    stats = {
        "count": len(df),
        "start_date": df["timestamp"].min(),
        "end_date": df["timestamp"].max(),
        "price_yes": {
            "mean": df["price_yes"].mean(),
            "min": df["price_yes"].min(),
            "max": df["price_yes"].max(),
            "std": df["price_yes"].std(),
        },
        "price_no": {
            "mean": df["price_no"].mean(),
            "min": df["price_no"].min(),
            "max": df["price_no"].max(),
            "std": df["price_no"].std(),
        },
    }

    if "spread" in df.columns:
        stats["spread"] = {
            "mean": df["spread"].mean(),
            "min": df["spread"].min(),
            "max": df["spread"].max(),
            "std": df["spread"].std(),
        }

    return stats


if __name__ == "__main__":
    # Configura logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Executa pipeline
    results = run_phase2_pipeline(timeframes=[DEFAULT_TIMEFRAME])

    # Mostra resumo
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for timeframe, market_results in results.items():
        print(f"\nTimeframe: {timeframe}")
        print(f"  Markets processed: {len(market_results)}")
