"""Formatacao de valores para a UI."""

from __future__ import annotations


def format_money(value) -> str:
    number = float(value or 0)
    text = f"R$ {number:,.2f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(value) -> str:
    return f"{float(value or 0) * 100:.2f}%".replace(".", ",")


def clean_text(value) -> str:
    return str(value or "").strip()

