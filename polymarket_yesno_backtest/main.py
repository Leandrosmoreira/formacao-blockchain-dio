#!/usr/bin/env python3
"""
Polymarket YES/NO Backtest - Main Entry Point

Script principal para executar o pipeline de backtesting de mercados
binários da Polymarket.

Uso:
    python main.py --phase 1        # Executa Fase 1 (seleção de mercados)
    python main.py --phase 2        # Executa Fase 2 (coleta de preços)
    python main.py --phase 3        # Executa Fase 3 (séries de arbitragem)
    python main.py --phase 4        # Executa Fase 4 (estatísticas de spread)
    python main.py --phase all      # Executa todas as fases
"""

import argparse
import logging
import sys
from typing import Optional

from config.settings import (
    LOG_LEVEL,
    LOG_FORMAT,
    DEFAULT_TIMEFRAME,
    TIMEFRAMES,
    ensure_data_dirs_exist,
)


def setup_logging(level: str = LOG_LEVEL) -> None:
    """Configura o sistema de logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )


def run_phase1() -> dict:
    """Executa Fase 1: Seleção de Mercados."""
    from pipeline.phase1_market_selection import run_phase1_pipeline

    groups, summary = run_phase1_pipeline()
    return {"groups": groups, "summary": summary}


def run_phase2(timeframes: Optional[list] = None) -> dict:
    """Executa Fase 2: Coleta de Histórico de Preços."""
    from pipeline.phase2_price_history import run_phase2_pipeline

    if timeframes is None:
        timeframes = [DEFAULT_TIMEFRAME]

    results = run_phase2_pipeline(timeframes=timeframes)
    return {"results": results}


def run_phase3(timeframes: Optional[list] = None) -> dict:
    """Executa Fase 3: Reconstrução de Séries de Arbitragem."""
    from pipeline.phase3_arbitrage_series import run_phase3_pipeline

    if timeframes is None:
        timeframes = [DEFAULT_TIMEFRAME]

    results = run_phase3_pipeline(timeframes=timeframes)
    return {"results": results}


def run_phase4(timeframe: str = DEFAULT_TIMEFRAME) -> dict:
    """Executa Fase 4: Estatísticas Descritivas de Spread."""
    from pipeline.phase4_stats_spread import run_phase4_pipeline

    stats_list, df_summary = run_phase4_pipeline(timeframe=timeframe)
    return {
        "stats_list": stats_list,
        "summary": df_summary,
        "count": len(stats_list),
    }


def run_all_phases(timeframes: Optional[list] = None) -> dict:
    """Executa todas as fases do pipeline."""
    results = {}

    if timeframes is None:
        timeframes = [DEFAULT_TIMEFRAME]

    # Fase 1
    print("\n" + "=" * 60)
    print("FASE 1: SELEÇÃO DE MERCADOS")
    print("=" * 60)
    phase1_result = run_phase1()
    results["phase1"] = phase1_result

    # Fase 2
    print("\n" + "=" * 60)
    print("FASE 2: COLETA DE HISTÓRICO DE PREÇOS")
    print("=" * 60)
    phase2_result = run_phase2(timeframes)
    results["phase2"] = phase2_result

    # Fase 3
    print("\n" + "=" * 60)
    print("FASE 3: RECONSTRUÇÃO DE SÉRIES DE ARBITRAGEM")
    print("=" * 60)
    phase3_result = run_phase3(timeframes)
    results["phase3"] = phase3_result

    # Fase 4
    print("\n" + "=" * 60)
    print("FASE 4: ESTATÍSTICAS DESCRITIVAS DE SPREAD")
    print("=" * 60)
    phase4_result = run_phase4(timeframes[0])
    results["phase4"] = phase4_result

    return results


def print_summary(results: dict) -> None:
    """Imprime resumo dos resultados."""
    print("\n" + "=" * 60)
    print("RESUMO FINAL")
    print("=" * 60)

    if "phase1" in results:
        summary = results["phase1"].get("summary", {})
        print(f"\nFase 1 - Seleção de Mercados:")
        print(f"  Total bruto: {summary.get('total_raw', 'N/A')}")
        print(f"  Total filtrado: {summary.get('total_filtered', 'N/A')}")
        print(f"  Total selecionado: {summary.get('total_selected', 'N/A')}")

        groups = summary.get("groups", {})
        for group_name, group_info in groups.items():
            count = group_info.get("count", 0)
            print(f"  Grupo {group_name}: {count} mercados")

    if "phase2" in results:
        phase2_results = results["phase2"].get("results", {})
        print(f"\nFase 2 - Coleta de Preços:")
        for timeframe, market_results in phase2_results.items():
            print(f"  Timeframe {timeframe}: {len(market_results)} mercados")

    if "phase3" in results:
        phase3_results = results["phase3"].get("results", {})
        print(f"\nFase 3 - Séries de Arbitragem:")
        for timeframe, market_results in phase3_results.items():
            print(f"  Timeframe {timeframe}: {len(market_results)} mercados processados")

    if "phase4" in results:
        count = results["phase4"].get("count", 0)
        print(f"\nFase 4 - Estatísticas de Spread:")
        print(f"  Mercados analisados: {count}")

        stats_list = results["phase4"].get("stats_list", [])
        if stats_list:
            import numpy as np
            avg_positive = np.mean([s.frequency.positive_pct for s in stats_list])
            max_positive = max(s.frequency.positive_pct for s in stats_list)
            print(f"  Arbitragem média (>0): {avg_positive:.2f}%")
            print(f"  Arbitragem máxima (>0): {max_positive:.2f}%")


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Polymarket YES/NO Backtest Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Fases disponíveis:
  1    Seleção de mercados (busca API, filtra, agrupa A/B/C)
  2    Coleta de histórico de preços YES/NO
  3    Reconstrução de séries de arbitragem (spread = 1 - YES - NO)
  4    Estatísticas descritivas de spread (frequência, magnitude, duração)
  all  Executa todas as fases em sequência
        """
    )

    parser.add_argument(
        "--phase",
        type=str,
        choices=["1", "2", "3", "4", "all"],
        default="all",
        help="Fase do pipeline a executar (1, 2, 3, 4, ou all)",
    )

    parser.add_argument(
        "--timeframe",
        type=str,
        choices=TIMEFRAMES,
        default=DEFAULT_TIMEFRAME,
        help=f"Timeframe para análise (default: {DEFAULT_TIMEFRAME})",
    )

    parser.add_argument(
        "--all-timeframes",
        action="store_true",
        help="Processa todos os timeframes disponíveis",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=LOG_LEVEL,
        help=f"Nível de logging (default: {LOG_LEVEL})",
    )

    args = parser.parse_args()

    # Setup
    setup_logging(args.log_level)
    ensure_data_dirs_exist()

    # Determina timeframes
    if args.all_timeframes:
        timeframes = TIMEFRAMES
    else:
        timeframes = [args.timeframe]

    # Executa fase(s)
    try:
        if args.phase == "1":
            results = {"phase1": run_phase1()}
        elif args.phase == "2":
            results = {"phase2": run_phase2(timeframes)}
        elif args.phase == "3":
            results = {"phase3": run_phase3(timeframes)}
        elif args.phase == "4":
            results = {"phase4": run_phase4(timeframes[0])}
        else:
            results = run_all_phases(timeframes)

        print_summary(results)
        return 0

    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuário.")
        return 130
    except Exception as e:
        logging.error(f"Erro fatal: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
