"""Conversao numerica tolerante a virgula brasileira."""

from __future__ import annotations


def parse_decimal(value, default: float = 0.0) -> float:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    text = text.replace("R$", "").replace("%", "").strip()
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"Valor numérico inválido: {value}")


def parse_percent(value, default: float = 0.0) -> float:
    return parse_decimal(value, default) / 100

