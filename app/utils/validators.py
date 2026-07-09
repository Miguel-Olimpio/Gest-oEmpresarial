"""Validacoes de entrada."""

from __future__ import annotations

from app.utils.dates import parse_date
from app.utils.formatting import clean_text
from app.utils.numbers import parse_decimal


def required_text(value, field_name: str) -> str:
    text = clean_text(value)
    if not text:
        raise ValueError(f"{field_name} é obrigatório.")
    return text


def non_negative_money(value, field_name: str) -> float:
    number = parse_decimal(value)
    if number < 0:
        raise ValueError(f"{field_name} não pode ser negativo.")
    return number


def positive_money(value, field_name: str) -> float:
    number = parse_decimal(value)
    if number <= 0:
        raise ValueError(f"{field_name} deve ser maior que zero.")
    return number


def non_negative_percent(value, field_name: str) -> float:
    number = parse_decimal(value)
    if number < 0:
        raise ValueError(f"{field_name} não pode ser negativo.")
    return number


def optional_date(value, field_name: str = "Data") -> str:
    text = clean_text(value)
    if not text:
        return ""
    parse_date(text)
    return text

