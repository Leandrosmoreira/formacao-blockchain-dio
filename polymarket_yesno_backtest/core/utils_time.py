"""
Utilitários para manipulação de datas e timestamps.

Funções auxiliares para conversão entre formatos de data/hora,
cálculo de intervalos e validação temporal.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from dateutil.parser import parse as parse_date
from dateutil.tz import tzutc


def to_timestamp(dt: datetime) -> int:
    """
    Converte datetime para Unix timestamp (segundos).

    Args:
        dt: Objeto datetime

    Returns:
        Unix timestamp em segundos
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def to_timestamp_ms(dt: datetime) -> int:
    """
    Converte datetime para Unix timestamp (milissegundos).

    Args:
        dt: Objeto datetime

    Returns:
        Unix timestamp em milissegundos
    """
    return to_timestamp(dt) * 1000


def from_timestamp(ts: int) -> datetime:
    """
    Converte Unix timestamp (segundos) para datetime UTC.

    Args:
        ts: Unix timestamp em segundos

    Returns:
        Objeto datetime com timezone UTC
    """
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def from_timestamp_ms(ts_ms: int) -> datetime:
    """
    Converte Unix timestamp (milissegundos) para datetime UTC.

    Args:
        ts_ms: Unix timestamp em milissegundos

    Returns:
        Objeto datetime com timezone UTC
    """
    return from_timestamp(ts_ms // 1000)


def parse_iso_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse uma string de data ISO 8601.

    Args:
        date_str: String de data em formato ISO

    Returns:
        Objeto datetime ou None se inválido
    """
    if not date_str:
        return None
    try:
        dt = parse_date(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def now_utc() -> datetime:
    """Retorna o momento atual em UTC."""
    return datetime.now(timezone.utc)


def days_between(start: datetime, end: datetime) -> int:
    """
    Calcula o número de dias entre duas datas.

    Args:
        start: Data inicial
        end: Data final

    Returns:
        Número de dias (positivo se end > start)
    """
    return (end - start).days


def timeframe_to_seconds(timeframe: str) -> int:
    """
    Converte string de timeframe para segundos.

    Args:
        timeframe: String como "1m", "5m", "1h", "4h", "1d"

    Returns:
        Duração em segundos
    """
    multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
        "w": 604800,
    }

    if not timeframe:
        raise ValueError("Timeframe cannot be empty")

    unit = timeframe[-1].lower()
    if unit not in multipliers:
        raise ValueError(f"Unknown timeframe unit: {unit}")

    try:
        value = int(timeframe[:-1])
    except ValueError:
        raise ValueError(f"Invalid timeframe value: {timeframe}")

    return value * multipliers[unit]


def timeframe_to_timedelta(timeframe: str) -> timedelta:
    """
    Converte string de timeframe para timedelta.

    Args:
        timeframe: String como "1m", "5m", "1h", "4h", "1d"

    Returns:
        Objeto timedelta
    """
    return timedelta(seconds=timeframe_to_seconds(timeframe))


def round_to_interval(dt: datetime, timeframe: str) -> datetime:
    """
    Arredonda datetime para o início do intervalo.

    Args:
        dt: Datetime a arredondar
        timeframe: Intervalo de tempo

    Returns:
        Datetime arredondado
    """
    seconds = timeframe_to_seconds(timeframe)

    # Converte para timestamp e arredonda
    ts = to_timestamp(dt)
    rounded_ts = (ts // seconds) * seconds

    return from_timestamp(rounded_ts)


def generate_time_range(
    start: datetime,
    end: datetime,
    timeframe: str
) -> list[datetime]:
    """
    Gera uma lista de timestamps entre start e end.

    Args:
        start: Data/hora inicial
        end: Data/hora final
        timeframe: Intervalo entre pontos

    Returns:
        Lista de datetimes
    """
    delta = timeframe_to_timedelta(timeframe)
    timestamps = []

    current = round_to_interval(start, timeframe)
    while current <= end:
        timestamps.append(current)
        current += delta

    return timestamps


def get_market_duration(
    start_date: Optional[datetime],
    end_date: Optional[datetime]
) -> Tuple[Optional[int], Optional[timedelta]]:
    """
    Calcula a duração de um mercado.

    Args:
        start_date: Data de início
        end_date: Data de término

    Returns:
        Tupla (dias, timedelta) ou (None, None)
    """
    if not start_date or not end_date:
        return None, None

    delta = end_date - start_date
    return delta.days, delta


def is_within_last_n_days(dt: datetime, n_days: int) -> bool:
    """
    Verifica se uma data está dentro dos últimos N dias.

    Args:
        dt: Data a verificar
        n_days: Número de dias

    Returns:
        True se está dentro do período
    """
    cutoff = now_utc() - timedelta(days=n_days)
    return dt >= cutoff


def format_duration(delta: timedelta) -> str:
    """
    Formata um timedelta em string legível.

    Args:
        delta: Duração

    Returns:
        String formatada (ex: "5d 3h 20m")
    """
    total_seconds = int(delta.total_seconds())

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")

    return " ".join(parts) if parts else "0m"
