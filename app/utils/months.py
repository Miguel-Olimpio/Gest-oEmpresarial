"""Helpers para períodos mensais no formato MM/AAAA."""

from __future__ import annotations

from datetime import date, datetime

from app.utils.dates import parse_date, today
from app.utils.formatting import clean_text


def current_month() -> str:
    return today().strftime("%m/%Y")


def normalize_month(value: date | datetime | str | None = None) -> str:
    if value is None:
        return current_month()
    if isinstance(value, datetime):
        return value.strftime("%m/%Y")
    if isinstance(value, date):
        return value.strftime("%m/%Y")

    text = clean_text(value)
    if not text:
        return current_month()
    parts = text.split("/")
    if len(parts) == 2:
        month, year = parts
        if not (month.isdigit() and year.isdigit() and len(year) == 4):
            raise ValueError("Informe o mês no formato MM/AAAA.")
        month_number = int(month)
        if month_number < 1 or month_number > 12:
            raise ValueError("Informe o mês no formato MM/AAAA.")
        return f"{month_number:02d}/{int(year):04d}"
    if len(parts) == 3:
        parsed = parse_date(text)
        return parsed.strftime("%m/%Y")
    raise ValueError("Informe o mês no formato MM/AAAA.")


def same_month(value: date | datetime | str | None, month_ref: date | datetime | str | None = None) -> bool:
    return normalize_month(value) == normalize_month(month_ref)


def month_options(count: int = 13) -> list[str]:
    base = today()
    options: list[str] = []
    year = base.year
    month = base.month
    for _ in range(count):
        options.append(f"{month:02d}/{year:04d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return options
