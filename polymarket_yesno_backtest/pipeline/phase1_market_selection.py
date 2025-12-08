"""
Fase 1 - Seleção de Mercados

Funções para buscar mercados via API, filtrar por critérios e agrupar em A/B/C.

Grupos:
- A: Top mercados por volume (grandes)
- B: Mercados de volume médio
- C: Mercados pequenos
"""

import json
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import pandas as pd

from config.settings import (
    MIN_VOLUME_USD,
    MIN_LIFETIME_DAYS,
    BINARY_ONLY,
    TOP_N_LARGE_MARKETS,
    MEDIUM_VOLUME_MIN_USD,
    MEDIUM_VOLUME_MAX_USD,
    N_SAMPLE_MEDIUM_MARKETS,
    SMALL_VOLUME_MAX_USD,
    N_SAMPLE_SMALL_MARKETS,
    DATA_PROCESSED_DIR,
    MARKETS_ABC_JSON,
    MARKETS_ALL_CSV,
    ensure_data_dirs_exist,
)
from core.api_client import PolymarketAPIClient, get_api_client
from core.models import Market, MarketGroup

logger = logging.getLogger(__name__)


def load_all_resolved_markets(
    api_client: Optional[PolymarketAPIClient] = None,
    max_pages: int = 100,
) -> List[Market]:
    """
    Carrega todos os mercados resolvidos via API.

    Args:
        api_client: Cliente de API (usa singleton se None)
        max_pages: Número máximo de páginas para paginar

    Returns:
        Lista de todos os mercados resolvidos
    """
    client = api_client or get_api_client()

    logger.info("Loading all resolved markets from API...")
    markets = client.fetch_all_resolved_markets(max_pages=max_pages)
    logger.info(f"Loaded {len(markets)} resolved markets")

    return markets


def filter_markets_by_criteria(
    markets: List[Market],
    volume_min: float = MIN_VOLUME_USD,
    min_lifetime_days: int = MIN_LIFETIME_DAYS,
    binary_only: bool = BINARY_ONLY,
) -> List[Market]:
    """
    Filtra mercados pelos critérios definidos.

    Args:
        markets: Lista de mercados para filtrar
        volume_min: Volume mínimo em USD
        min_lifetime_days: Duração mínima em dias
        binary_only: Se True, apenas mercados binários (YES/NO)

    Returns:
        Lista de mercados que passam nos critérios
    """
    filtered = []

    for market in markets:
        # Filtro de volume
        if market.volume < volume_min:
            continue

        # Filtro de duração
        lifetime = market.lifetime_days
        if lifetime is not None and lifetime < min_lifetime_days:
            continue

        # Filtro binário
        if binary_only and not market.is_binary:
            continue

        # Verifica se tem tokens YES/NO
        if not market.yes_token_id or not market.no_token_id:
            continue

        filtered.append(market)

    logger.info(
        f"Filtered {len(markets)} markets to {len(filtered)} "
        f"(volume >= ${volume_min:,.0f}, lifetime >= {min_lifetime_days}d, "
        f"binary_only={binary_only})"
    )

    return filtered


def split_markets_into_ABC(
    markets: List[Market],
    top_n_large: int = TOP_N_LARGE_MARKETS,
    medium_volume_min: float = MEDIUM_VOLUME_MIN_USD,
    medium_volume_max: float = MEDIUM_VOLUME_MAX_USD,
    n_sample_medium: int = N_SAMPLE_MEDIUM_MARKETS,
    small_volume_max: float = SMALL_VOLUME_MAX_USD,
    n_sample_small: int = N_SAMPLE_SMALL_MARKETS,
) -> Dict[str, List[Market]]:
    """
    Divide mercados em grupos A, B, C por volume.

    Args:
        markets: Lista de mercados filtrados
        top_n_large: Quantidade de mercados no grupo A (top por volume)
        medium_volume_min: Volume mínimo para grupo B
        medium_volume_max: Volume máximo para grupo B
        n_sample_medium: Quantidade de mercados a amostrar para grupo B
        small_volume_max: Volume máximo para grupo C
        n_sample_small: Quantidade de mercados a amostrar para grupo C

    Returns:
        Dicionário com grupos {"A": [...], "B": [...], "C": [...]}
    """
    # Ordena por volume decrescente
    sorted_markets = sorted(markets, key=lambda m: m.volume, reverse=True)

    # Grupo A: Top N por volume
    group_a = sorted_markets[:top_n_large]
    for market in group_a:
        market.group = MarketGroup.A

    # Mercados restantes
    remaining = sorted_markets[top_n_large:]

    # Grupo B: Volume médio
    group_b_candidates = [
        m for m in remaining
        if medium_volume_min <= m.volume <= medium_volume_max
    ]
    # Amostra ou pega todos se houver menos
    group_b = group_b_candidates[:n_sample_medium]
    for market in group_b:
        market.group = MarketGroup.B

    # IDs já usados
    used_ids = {m.id for m in group_a + group_b}

    # Grupo C: Volume pequeno (não usado em A ou B)
    group_c_candidates = [
        m for m in remaining
        if m.id not in used_ids and m.volume < small_volume_max
    ]
    group_c = group_c_candidates[:n_sample_small]
    for market in group_c:
        market.group = MarketGroup.C

    logger.info(
        f"Split markets into groups: "
        f"A={len(group_a)}, B={len(group_b)}, C={len(group_c)}"
    )

    return {
        "A": group_a,
        "B": group_b,
        "C": group_c,
    }


def save_markets_to_json(
    groups: Dict[str, List[Market]],
    filepath: Path = MARKETS_ABC_JSON,
) -> None:
    """
    Salva grupos de mercados em arquivo JSON.

    Args:
        groups: Dicionário com grupos A/B/C
        filepath: Caminho do arquivo de saída
    """
    ensure_data_dirs_exist()

    output = {
        group_name: [m.to_dict() for m in markets]
        for group_name, markets in groups.items()
    }

    # Adiciona metadados
    output["_metadata"] = {
        "total_markets": sum(len(m) for m in groups.values()),
        "group_counts": {k: len(v) for k, v in groups.items()},
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved markets to {filepath}")


def save_markets_to_csv(
    markets: List[Market],
    filepath: Path = MARKETS_ALL_CSV,
) -> None:
    """
    Salva lista de mercados em CSV.

    Args:
        markets: Lista de mercados
        filepath: Caminho do arquivo de saída
    """
    ensure_data_dirs_exist()

    records = [m.to_dict() for m in markets]
    df = pd.DataFrame(records)

    df.to_csv(filepath, index=False)

    logger.info(f"Saved {len(markets)} markets to {filepath}")


def load_markets_from_json(
    filepath: Path = MARKETS_ABC_JSON,
) -> Dict[str, List[Market]]:
    """
    Carrega grupos de mercados de arquivo JSON.

    Args:
        filepath: Caminho do arquivo

    Returns:
        Dicionário com grupos A/B/C
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    groups = {}
    for group_name in ["A", "B", "C"]:
        if group_name in data:
            groups[group_name] = [
                Market.from_dict(m) for m in data[group_name]
            ]
        else:
            groups[group_name] = []

    logger.info(
        f"Loaded markets from {filepath}: "
        f"A={len(groups['A'])}, B={len(groups['B'])}, C={len(groups['C'])}"
    )

    return groups


def get_market_summary(markets: List[Market]) -> Dict:
    """
    Gera resumo estatístico de uma lista de mercados.

    Args:
        markets: Lista de mercados

    Returns:
        Dicionário com estatísticas
    """
    if not markets:
        return {"count": 0}

    volumes = [m.volume for m in markets]
    lifetimes = [m.lifetime_days for m in markets if m.lifetime_days]

    return {
        "count": len(markets),
        "volume": {
            "total": sum(volumes),
            "mean": sum(volumes) / len(volumes),
            "min": min(volumes),
            "max": max(volumes),
        },
        "lifetime_days": {
            "mean": sum(lifetimes) / len(lifetimes) if lifetimes else None,
            "min": min(lifetimes) if lifetimes else None,
            "max": max(lifetimes) if lifetimes else None,
        },
        "categories": list(set(m.category for m in markets if m.category)),
    }


def run_phase1_pipeline(
    api_client: Optional[PolymarketAPIClient] = None,
    save_results: bool = True,
) -> Tuple[Dict[str, List[Market]], Dict]:
    """
    Executa o pipeline completo da Fase 1.

    Args:
        api_client: Cliente de API (opcional)
        save_results: Se True, salva resultados em arquivos

    Returns:
        Tupla (grupos A/B/C, resumo estatístico)
    """
    logger.info("=" * 50)
    logger.info("Starting Phase 1: Market Selection")
    logger.info("=" * 50)

    # 1. Carrega todos os mercados resolvidos
    all_markets = load_all_resolved_markets(api_client)

    # 2. Filtra por critérios
    filtered = filter_markets_by_criteria(all_markets)

    # 3. Divide em grupos A/B/C
    groups = split_markets_into_ABC(filtered)

    # 4. Gera resumo
    all_selected = groups["A"] + groups["B"] + groups["C"]
    summary = {
        "total_raw": len(all_markets),
        "total_filtered": len(filtered),
        "total_selected": len(all_selected),
        "groups": {
            "A": get_market_summary(groups["A"]),
            "B": get_market_summary(groups["B"]),
            "C": get_market_summary(groups["C"]),
        },
    }

    # 5. Salva resultados
    if save_results:
        save_markets_to_json(groups)
        save_markets_to_csv(all_selected)

    logger.info("=" * 50)
    logger.info("Phase 1 completed!")
    logger.info(f"Selected {len(all_selected)} markets in total")
    logger.info("=" * 50)

    return groups, summary


if __name__ == "__main__":
    # Configura logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Executa pipeline
    groups, summary = run_phase1_pipeline()

    # Mostra resumo
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total raw markets: {summary['total_raw']}")
    print(f"Total after filter: {summary['total_filtered']}")
    print(f"Total selected: {summary['total_selected']}")
    print()
    for group_name, group_summary in summary["groups"].items():
        print(f"Group {group_name}: {group_summary['count']} markets")
        if group_summary["count"] > 0:
            vol = group_summary["volume"]
            print(f"  Volume: ${vol['min']:,.0f} - ${vol['max']:,.0f}")
