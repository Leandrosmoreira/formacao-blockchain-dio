"""
Configurações globais do projeto Polymarket YES/NO Backtest.

Este módulo contém todas as constantes e parâmetros configuráveis
para seleção de mercados, coleta de dados e análise.
"""

# =============================================================================
# API Configuration
# =============================================================================

# Base URLs para APIs Polymarket/Gamma
POLYMARKET_GAMMA_API_BASE_URL = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_API_BASE_URL = "https://clob.polymarket.com"

# Timeouts e retry settings
API_TIMEOUT_SECONDS = 30
API_MAX_RETRIES = 3
API_RETRY_DELAY_SECONDS = 1

# Paginação padrão
API_DEFAULT_LIMIT = 100
API_MAX_LIMIT = 500

# =============================================================================
# Market Selection Criteria (Fase 1)
# =============================================================================

# Volume mínimo em USD para considerar um mercado
MIN_VOLUME_USD = 50_000

# Duração mínima do mercado em dias (do início ao fim)
MIN_LIFETIME_DAYS = 7

# Apenas mercados binários (YES/NO)
BINARY_ONLY = True

# Apenas mercados resolvidos
RESOLVED_ONLY = True

# =============================================================================
# Market Grouping (A/B/C)
# =============================================================================

# Grupo A: Top N mercados por volume (grandes)
TOP_N_LARGE_MARKETS = 50

# Grupo B: Mercados de volume médio
# - Volume entre MEDIUM_VOLUME_MIN e MEDIUM_VOLUME_MAX
MEDIUM_VOLUME_MIN_USD = 100_000
MEDIUM_VOLUME_MAX_USD = 1_000_000
N_SAMPLE_MEDIUM_MARKETS = 100  # Quantos mercados médios amostrar

# Grupo C: Mercados pequenos
# - Volume entre MIN_VOLUME_USD e SMALL_VOLUME_MAX
SMALL_VOLUME_MAX_USD = 100_000
N_SAMPLE_SMALL_MARKETS = 100  # Quantos mercados pequenos amostrar

# =============================================================================
# Price History Collection (Fase 2)
# =============================================================================

# Intervalos de tempo disponíveis para séries de preço
TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]

# Timeframe padrão para análise
DEFAULT_TIMEFRAME = "1h"

# Fidelidade máxima (menor intervalo)
HIGH_FIDELITY_TIMEFRAME = "1m"

# =============================================================================
# Data Storage Paths
# =============================================================================

import os
from pathlib import Path

# Diretório raiz do projeto
PROJECT_ROOT = Path(__file__).parent.parent

# Diretórios de dados
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
DATA_PROCESSED_DIR = DATA_DIR / "processed"
DATA_STATS_DIR = DATA_DIR / "stats"

# Arquivos de output da Fase 1
MARKETS_ABC_JSON = DATA_PROCESSED_DIR / "markets_A_B_C.json"
MARKETS_ALL_CSV = DATA_PROCESSED_DIR / "all_filtered_markets.csv"

# =============================================================================
# Arbitrage Analysis (Fases 3-4)
# =============================================================================

# Threshold para considerar arbitragem (YES + NO < 1 - THRESHOLD)
ARBITRAGE_THRESHOLD = 0.98

# Spread mínimo para ser considerado significativo
MIN_SPREAD_PERCENT = 1.0  # 1%

# =============================================================================
# Cost Model (Fase 7)
# =============================================================================

# Taxa de trading (Polymarket)
TRADING_FEE_PERCENT = 0.0  # Polymarket não cobra taxa por trade

# Slippage estimado para mercados de baixa liquidez
ESTIMATED_SLIPPAGE_PERCENT = 0.5

# =============================================================================
# Risk Framework (Fase 9)
# =============================================================================

# Máximo de capital por mercado (%)
MAX_CAPITAL_PER_MARKET_PERCENT = 10

# Drawdown máximo aceitável (%)
MAX_DRAWDOWN_PERCENT = 20

# =============================================================================
# Logging Configuration
# =============================================================================

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# =============================================================================
# Helper Functions
# =============================================================================

def ensure_data_dirs_exist():
    """Cria os diretórios de dados se não existirem."""
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    DATA_STATS_DIR.mkdir(parents=True, exist_ok=True)
