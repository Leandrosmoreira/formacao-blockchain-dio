"""
Cliente de API para Polymarket/Gamma.

Implementa métodos para buscar mercados resolvidos, detalhes de mercados
e histórico de preços.
"""

import time
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import (
    POLYMARKET_GAMMA_API_BASE_URL,
    POLYMARKET_CLOB_API_BASE_URL,
    API_TIMEOUT_SECONDS,
    API_MAX_RETRIES,
    API_RETRY_DELAY_SECONDS,
    API_DEFAULT_LIMIT,
    API_MAX_LIMIT,
)
from core.models import Market, Token, MarketStatus, Resolution
from core.utils_time import parse_iso_date, from_timestamp, to_timestamp

logger = logging.getLogger(__name__)


class PolymarketAPIError(Exception):
    """Erro genérico da API Polymarket."""
    pass


class PolymarketRateLimitError(PolymarketAPIError):
    """Erro de rate limit da API."""
    pass


class PolymarketAPIClient:
    """
    Cliente para interagir com APIs Polymarket/Gamma.

    Attributes:
        gamma_base_url: URL base da API Gamma
        clob_base_url: URL base da API CLOB
        timeout: Timeout para requisições em segundos
        session: Sessão HTTP reutilizável
    """

    def __init__(
        self,
        gamma_base_url: str = POLYMARKET_GAMMA_API_BASE_URL,
        clob_base_url: str = POLYMARKET_CLOB_API_BASE_URL,
        timeout: int = API_TIMEOUT_SECONDS,
    ):
        """
        Inicializa o cliente de API.

        Args:
            gamma_base_url: URL base da API Gamma
            clob_base_url: URL base da API CLOB
            timeout: Timeout para requisições
        """
        self.gamma_base_url = gamma_base_url.rstrip("/")
        self.clob_base_url = clob_base_url.rstrip("/")
        self.timeout = timeout
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Cria sessão HTTP com retry automático."""
        session = requests.Session()

        retry_strategy = Retry(
            total=API_MAX_RETRIES,
            backoff_factor=API_RETRY_DELAY_SECONDS,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        session.headers.update({
            "Accept": "application/json",
            "User-Agent": "PolymarketBacktest/1.0",
        })

        return session

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Faz uma requisição HTTP.

        Args:
            method: Método HTTP (GET, POST, etc.)
            url: URL completa
            params: Parâmetros de query
            **kwargs: Argumentos adicionais para requests

        Returns:
            Resposta JSON parseada

        Raises:
            PolymarketAPIError: Em caso de erro na API
            PolymarketRateLimitError: Em caso de rate limit
        """
        try:
            response = self.session.request(
                method,
                url,
                params=params,
                timeout=self.timeout,
                **kwargs
            )

            if response.status_code == 429:
                raise PolymarketRateLimitError("Rate limit exceeded")

            response.raise_for_status()

            return response.json()

        except requests.exceptions.Timeout:
            raise PolymarketAPIError(f"Request timeout: {url}")
        except requests.exceptions.RequestException as e:
            raise PolymarketAPIError(f"Request failed: {e}")

    def _get_gamma(
        self,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Faz GET na API Gamma."""
        url = f"{self.gamma_base_url}/{endpoint.lstrip('/')}"
        return self._make_request("GET", url, params=params)

    def _get_clob(
        self,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Faz GET na API CLOB."""
        url = f"{self.clob_base_url}/{endpoint.lstrip('/')}"
        return self._make_request("GET", url, params=params)

    def fetch_markets_resolved(
        self,
        limit: int = API_MAX_LIMIT,
        offset: int = 0,
    ) -> List[Market]:
        """
        Busca mercados resolvidos da API Gamma.

        Args:
            limit: Número máximo de mercados por página
            offset: Offset para paginação

        Returns:
            Lista de objetos Market
        """
        markets = []

        params = {
            "closed": "true",
            "limit": min(limit, API_MAX_LIMIT),
            "offset": offset,
        }

        logger.info(f"Fetching resolved markets (offset={offset}, limit={limit})")

        try:
            data = self._get_gamma("markets", params=params)
        except PolymarketAPIError as e:
            logger.error(f"Failed to fetch markets: {e}")
            return markets

        if not isinstance(data, list):
            data = data.get("markets", []) if isinstance(data, dict) else []

        for item in data:
            market = self._parse_market(item)
            if market and market.resolved:
                markets.append(market)

        logger.info(f"Fetched {len(markets)} resolved markets")
        return markets

    def fetch_all_resolved_markets(
        self,
        max_pages: int = 100,
    ) -> List[Market]:
        """
        Busca todos os mercados resolvidos (com paginação automática).

        Args:
            max_pages: Número máximo de páginas para buscar

        Returns:
            Lista completa de mercados resolvidos
        """
        all_markets = []
        offset = 0
        page = 0

        while page < max_pages:
            markets = self.fetch_markets_resolved(
                limit=API_MAX_LIMIT,
                offset=offset,
            )

            if not markets:
                break

            all_markets.extend(markets)
            offset += len(markets)
            page += 1

            # Rate limit protection
            time.sleep(0.5)

            logger.info(f"Page {page}: Total markets so far: {len(all_markets)}")

        return all_markets

    def fetch_market_details(self, market_id: str) -> Optional[Market]:
        """
        Busca detalhes de um mercado específico.

        Args:
            market_id: ID (condition_id) do mercado

        Returns:
            Objeto Market ou None se não encontrado
        """
        try:
            data = self._get_gamma(f"markets/{market_id}")
            return self._parse_market(data)
        except PolymarketAPIError as e:
            logger.error(f"Failed to fetch market {market_id}: {e}")
            return None

    def fetch_market_by_slug(self, slug: str) -> Optional[Market]:
        """
        Busca mercado pelo slug.

        Args:
            slug: Slug URL do mercado

        Returns:
            Objeto Market ou None se não encontrado
        """
        try:
            params = {"slug": slug}
            data = self._get_gamma("markets", params=params)

            if isinstance(data, list) and len(data) > 0:
                return self._parse_market(data[0])
            return None
        except PolymarketAPIError as e:
            logger.error(f"Failed to fetch market by slug {slug}: {e}")
            return None

    def fetch_price_history(
        self,
        token_id: str,
        start_ts: int,
        end_ts: int,
        interval: str = "1h",
    ) -> List[Tuple[datetime, float]]:
        """
        Busca histórico de preços de um token.

        Args:
            token_id: ID do token (YES ou NO)
            start_ts: Timestamp Unix de início (segundos)
            end_ts: Timestamp Unix de fim (segundos)
            interval: Intervalo de tempo (1m, 5m, 1h, etc.)

        Returns:
            Lista de tuplas (timestamp, price)
        """
        prices = []

        # Mapeia intervalo para parâmetro da API
        fidelity_map = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "1h": 60,
            "4h": 240,
            "1d": 1440,
        }

        fidelity = fidelity_map.get(interval, 60)

        params = {
            "market": token_id,
            "startTs": start_ts,
            "endTs": end_ts,
            "fidelity": fidelity,
        }

        try:
            data = self._get_clob("prices-history", params=params)

            history = data.get("history", [])
            for point in history:
                ts = point.get("t")
                price = point.get("p")
                if ts is not None and price is not None:
                    dt = from_timestamp(int(ts))
                    prices.append((dt, float(price)))

        except PolymarketAPIError as e:
            logger.error(f"Failed to fetch price history for {token_id}: {e}")

        return prices

    def get_token_ids_for_market(
        self,
        market_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Obtém os token IDs (YES e NO) para um mercado.

        Args:
            market_id: ID do mercado

        Returns:
            Tupla (yes_token_id, no_token_id)
        """
        market = self.fetch_market_details(market_id)
        if market:
            return market.yes_token_id, market.no_token_id
        return None, None

    def _parse_market(self, data: Dict[str, Any]) -> Optional[Market]:
        """
        Parse dados JSON de mercado para objeto Market.

        Args:
            data: Dicionário com dados do mercado

        Returns:
            Objeto Market ou None se inválido
        """
        if not data:
            return None

        try:
            # Parse tokens
            tokens = []
            tokens_data = data.get("tokens", [])

            if tokens_data:
                for token_data in tokens_data:
                    token = Token(
                        token_id=token_data.get("token_id", ""),
                        outcome=token_data.get("outcome", ""),
                        price=float(token_data.get("price", 0)),
                        winner=token_data.get("winner", False),
                    )
                    tokens.append(token)

            # Parse clob_token_ids se tokens não estiver disponível
            clob_token_ids = data.get("clobTokenIds", [])
            if not tokens and clob_token_ids:
                # Assume ordem: YES, NO
                if len(clob_token_ids) >= 1:
                    tokens.append(Token(token_id=clob_token_ids[0], outcome="Yes"))
                if len(clob_token_ids) >= 2:
                    tokens.append(Token(token_id=clob_token_ids[1], outcome="No"))

            # Determina status
            closed = data.get("closed", False)
            resolved = data.get("resolved", False) or data.get("resolutionSource") is not None

            if resolved:
                status = MarketStatus.RESOLVED
            elif closed:
                status = MarketStatus.CLOSED
            else:
                status = MarketStatus.ACTIVE

            # Determina resolução
            resolution = Resolution.UNKNOWN
            if resolved:
                outcome = data.get("outcome", "")
                if outcome.lower() == "yes":
                    resolution = Resolution.YES
                elif outcome.lower() == "no":
                    resolution = Resolution.NO

            # Verifica se é binário
            outcomes = data.get("outcomes", [])
            is_binary = len(outcomes) == 2 or len(tokens) == 2

            market = Market(
                id=data.get("condition_id", data.get("id", "")),
                slug=data.get("slug", data.get("market_slug", "")),
                question=data.get("question", data.get("title", "")),
                description=data.get("description", ""),
                category=data.get("category", ""),
                volume=float(data.get("volume", 0) or 0),
                liquidity=float(data.get("liquidity", 0) or 0),
                start_date=parse_iso_date(data.get("startDate") or data.get("start_date_iso")),
                end_date=parse_iso_date(data.get("endDate") or data.get("end_date_iso")),
                status=status,
                resolved=resolved,
                resolution=resolution,
                is_binary=is_binary,
                neg_risk=data.get("negRisk", False),
                tokens=tokens,
            )

            return market

        except Exception as e:
            logger.error(f"Failed to parse market data: {e}")
            return None


# Singleton para uso conveniente
_default_client: Optional[PolymarketAPIClient] = None


def get_api_client() -> PolymarketAPIClient:
    """Retorna instância singleton do cliente de API."""
    global _default_client
    if _default_client is None:
        _default_client = PolymarketAPIClient()
    return _default_client
