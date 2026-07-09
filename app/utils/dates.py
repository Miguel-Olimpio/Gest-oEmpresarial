"""Datas em formato brasileiro."""

from __future__ import annotations

from datetime import date, datetime

from app.config.settings import DATE_FORMAT, DATETIME_FORMAT


def today() -> date:
    return date.today()


def now_datetime() -> datetime:
    return datetime.now()


def format_date(value: date | datetime | str | None = None) -> str:
    if value is None:
        value = today()
    if isinstance(value, str):
        parse_date(value)
        return value
    return value.strftime(DATE_FORMAT)


def format_datetime(value: datetime | None = None) -> str:
    return (value or now_datetime()).strftime(DATETIME_FORMAT)


def parse_date(value: str) -> date:
    try:
        return datetime.strptime(str(value).strip(), DATE_FORMAT).date()
    except ValueError as exc:
        raise ValueError("Data inválida. Use dd/mm/aaaa.") from exc


def add_business_days(value: date | datetime | str, days: int) -> date:
    if days < 0:
        raise ValueError("Dias úteis não pode ser negativo.")
    current = parse_date(value) if isinstance(value, str) else value
    if isinstance(current, datetime):
        current = current.date()
    added = 0
    while added < days:
        current = date.fromordinal(current.toordinal() + 1)
        if current.weekday() < 5:
            added += 1
    return current
