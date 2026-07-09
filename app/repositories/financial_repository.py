"""Repositorios financeiros."""

from __future__ import annotations

from app.config.paths import get_financial_db_path
from app.config.settings import SHEET_CASH_FLOW, SHEET_COST_CATEGORIES, SHEET_FIXED_COSTS, SHEET_VARIABLE_COSTS
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import (
    CASH_FLOW_HEADERS,
    COST_CATEGORY_HEADERS,
    FINANCIAL_SHEETS_CONFIG,
    FIXED_COST_HEADERS,
    VARIABLE_COST_HEADERS,
)


def _db() -> ExcelDatabase:
    return ExcelDatabase(get_financial_db_path(), FINANCIAL_SHEETS_CONFIG)


class FixedCostRepository:
    def __init__(self, database: ExcelDatabase | None = None):
        self.database = database or _db()

    def list_all(self) -> list[dict]:
        return self.database.read_sheet(SHEET_FIXED_COSTS)

    def add(self, row: dict) -> dict:
        return self.database.append_row(SHEET_FIXED_COSTS, FIXED_COST_HEADERS, row)

    def update(self, item_id: str, changes: dict) -> dict:
        return self.database.update_row(SHEET_FIXED_COSTS, FIXED_COST_HEADERS, "custo_id", item_id, changes)


class VariableCostRepository:
    def __init__(self, database: ExcelDatabase | None = None):
        self.database = database or _db()

    def list_all(self) -> list[dict]:
        return self.database.read_sheet(SHEET_VARIABLE_COSTS)

    def add(self, row: dict) -> dict:
        return self.database.append_row(SHEET_VARIABLE_COSTS, VARIABLE_COST_HEADERS, row)

    def update(self, item_id: str, changes: dict) -> dict:
        return self.database.update_row(SHEET_VARIABLE_COSTS, VARIABLE_COST_HEADERS, "custo_id", item_id, changes)


class CashFlowRepository:
    def __init__(self, database: ExcelDatabase | None = None):
        self.database = database or _db()

    def list_all(self) -> list[dict]:
        return self.database.read_sheet(SHEET_CASH_FLOW)

    def add(self, row: dict) -> dict:
        return self.database.append_row(SHEET_CASH_FLOW, CASH_FLOW_HEADERS, row)

    def update(self, item_id: str, changes: dict) -> dict:
        return self.database.update_row(SHEET_CASH_FLOW, CASH_FLOW_HEADERS, "lancamento_id", item_id, changes)


class CostCategoryRepository:
    def __init__(self, database: ExcelDatabase | None = None):
        self.database = database or _db()

    def list_all(self) -> list[dict]:
        return self.database.read_sheet(SHEET_COST_CATEGORIES)

    def add(self, row: dict) -> dict:
        return self.database.append_row(SHEET_COST_CATEGORIES, COST_CATEGORY_HEADERS, row)

    def update(self, item_id: str, changes: dict) -> dict:
        return self.database.update_row(SHEET_COST_CATEGORIES, COST_CATEGORY_HEADERS, "categoria_id", item_id, changes)
