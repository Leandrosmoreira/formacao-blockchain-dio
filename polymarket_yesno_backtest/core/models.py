"""
Modelos de dados para o projeto Polymarket YES/NO Backtest.

Define dataclasses para representar mercados, tokens, históricos de preço, etc.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class MarketStatus(Enum):
    """Status de um mercado."""
    ACTIVE = "active"
    CLOSED = "closed"
    RESOLVED = "resolved"


class MarketGroup(Enum):
    """Grupo de classificação de mercado por volume."""
    A = "A"  # Top mercados (alto volume)
    B = "B"  # Mercados médios
    C = "C"  # Mercados pequenos


class Resolution(Enum):
    """Resultado da resolução de um mercado."""
    YES = "Yes"
    NO = "No"
    UNKNOWN = "Unknown"


@dataclass
class Token:
    """
    Representa um token YES ou NO de um mercado.

    Attributes:
        token_id: Identificador único do token
        outcome: "Yes" ou "No"
        price: Preço atual do token (0 a 1)
        winner: Se este token foi o vencedor na resolução
    """
    token_id: str
    outcome: str
    price: float = 0.0
    winner: bool = False

    @property
    def is_yes(self) -> bool:
        """Retorna True se for token YES."""
        return self.outcome.lower() == "yes"

    @property
    def is_no(self) -> bool:
        """Retorna True se for token NO."""
        return self.outcome.lower() == "no"


@dataclass
class Market:
    """
    Representa um mercado binário (YES/NO) da Polymarket.

    Attributes:
        id: Identificador único do mercado (condition_id)
        slug: Slug URL do mercado
        question: Pergunta/título do mercado
        description: Descrição completa
        category: Categoria do mercado (politics, crypto, sports, etc.)
        volume: Volume total negociado em USD
        liquidity: Liquidez atual do mercado
        start_date: Data de início do mercado
        end_date: Data de término/resolução
        status: Status atual (active, closed, resolved)
        resolved: Se o mercado já foi resolvido
        resolution: Resultado da resolução (YES/NO)
        is_binary: Se é um mercado binário simples
        neg_risk: Se usa modelo negRisk
        tokens: Lista de tokens (YES e NO)
        group: Grupo de classificação (A, B, C)
    """
    id: str
    slug: str
    question: str
    description: str = ""
    category: str = ""
    volume: float = 0.0
    liquidity: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: MarketStatus = MarketStatus.ACTIVE
    resolved: bool = False
    resolution: Resolution = Resolution.UNKNOWN
    is_binary: bool = True
    neg_risk: bool = False
    tokens: List[Token] = field(default_factory=list)
    group: Optional[MarketGroup] = None

    @property
    def lifetime_days(self) -> Optional[int]:
        """Calcula a duração do mercado em dias."""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None

    @property
    def yes_token(self) -> Optional[Token]:
        """Retorna o token YES do mercado."""
        for token in self.tokens:
            if token.is_yes:
                return token
        return None

    @property
    def no_token(self) -> Optional[Token]:
        """Retorna o token NO do mercado."""
        for token in self.tokens:
            if token.is_no:
                return token
        return None

    @property
    def yes_token_id(self) -> Optional[str]:
        """Retorna o ID do token YES."""
        token = self.yes_token
        return token.token_id if token else None

    @property
    def no_token_id(self) -> Optional[str]:
        """Retorna o ID do token NO."""
        token = self.no_token
        return token.token_id if token else None

    def to_dict(self) -> dict:
        """Converte o mercado para dicionário."""
        return {
            "id": self.id,
            "slug": self.slug,
            "question": self.question,
            "description": self.description,
            "category": self.category,
            "volume": self.volume,
            "liquidity": self.liquidity,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status.value,
            "resolved": self.resolved,
            "resolution": self.resolution.value,
            "is_binary": self.is_binary,
            "neg_risk": self.neg_risk,
            "lifetime_days": self.lifetime_days,
            "yes_token_id": self.yes_token_id,
            "no_token_id": self.no_token_id,
            "group": self.group.value if self.group else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Market":
        """Cria um Market a partir de um dicionário."""
        from dateutil.parser import parse as parse_date

        tokens = []
        if data.get("yes_token_id"):
            tokens.append(Token(token_id=data["yes_token_id"], outcome="Yes"))
        if data.get("no_token_id"):
            tokens.append(Token(token_id=data["no_token_id"], outcome="No"))

        return cls(
            id=data["id"],
            slug=data.get("slug", ""),
            question=data.get("question", ""),
            description=data.get("description", ""),
            category=data.get("category", ""),
            volume=float(data.get("volume", 0)),
            liquidity=float(data.get("liquidity", 0)),
            start_date=parse_date(data["start_date"]) if data.get("start_date") else None,
            end_date=parse_date(data["end_date"]) if data.get("end_date") else None,
            status=MarketStatus(data.get("status", "active")),
            resolved=data.get("resolved", False),
            resolution=Resolution(data.get("resolution", "Unknown")),
            is_binary=data.get("is_binary", True),
            neg_risk=data.get("neg_risk", False),
            tokens=tokens,
            group=MarketGroup(data["group"]) if data.get("group") else None,
        )


@dataclass
class PricePoint:
    """
    Um ponto de preço em uma série temporal.

    Attributes:
        timestamp: Momento do preço
        price: Valor do preço (0 a 1)
    """
    timestamp: datetime
    price: float

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "price": self.price
        }


@dataclass
class PriceHistory:
    """
    Histórico de preços para um par YES/NO de um mercado.

    Attributes:
        market_id: ID do mercado
        timeframe: Intervalo de tempo (1m, 5m, 1h, etc.)
        yes_prices: Lista de preços YES
        no_prices: Lista de preços NO
    """
    market_id: str
    timeframe: str
    yes_prices: List[PricePoint] = field(default_factory=list)
    no_prices: List[PricePoint] = field(default_factory=list)

    @property
    def has_data(self) -> bool:
        """Verifica se há dados de preço."""
        return len(self.yes_prices) > 0 or len(self.no_prices) > 0

    @property
    def data_points(self) -> int:
        """Número total de pontos de dados."""
        return max(len(self.yes_prices), len(self.no_prices))


@dataclass
class ArbitragePoint:
    """
    Um ponto de arbitragem identificado.

    Attributes:
        timestamp: Momento da oportunidade
        yes_price: Preço do YES
        no_price: Preço do NO
        total: Soma YES + NO
        spread: Diferença de 1.0 (1 - total)
    """
    timestamp: datetime
    yes_price: float
    no_price: float

    @property
    def total(self) -> float:
        """Soma dos preços YES + NO."""
        return self.yes_price + self.no_price

    @property
    def spread(self) -> float:
        """Spread de arbitragem (negativo = oportunidade)."""
        return 1.0 - self.total

    @property
    def is_arbitrage(self) -> bool:
        """Verifica se há oportunidade de arbitragem."""
        return self.total < 1.0


@dataclass
class MarketStats:
    """
    Estatísticas agregadas de um mercado.

    Attributes:
        market_id: ID do mercado
        avg_spread: Spread médio
        min_spread: Spread mínimo
        max_spread: Spread máximo
        std_spread: Desvio padrão do spread
        arbitrage_count: Número de pontos com arbitragem
        arbitrage_percentage: Percentual de tempo em arbitragem
        total_data_points: Total de pontos analisados
    """
    market_id: str
    avg_spread: float = 0.0
    min_spread: float = 0.0
    max_spread: float = 0.0
    std_spread: float = 0.0
    arbitrage_count: int = 0
    arbitrage_percentage: float = 0.0
    total_data_points: int = 0

    def to_dict(self) -> dict:
        return {
            "market_id": self.market_id,
            "avg_spread": self.avg_spread,
            "min_spread": self.min_spread,
            "max_spread": self.max_spread,
            "std_spread": self.std_spread,
            "arbitrage_count": self.arbitrage_count,
            "arbitrage_percentage": self.arbitrage_percentage,
            "total_data_points": self.total_data_points,
        }
