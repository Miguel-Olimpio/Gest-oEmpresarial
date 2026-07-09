"""Repositorios de vendas, máquinas de cartão e conferencia."""

from __future__ import annotations

from app.config.paths import get_sales_db_path
from app.config.settings import (
    SHEET_CARD_MACHINES,
    SHEET_MACHINE_CONDITIONS,
    SHEET_RECEIVABLE_RECONCILIATION,
    SHEET_SALES,
)
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import (
    CARD_MACHINE_HEADERS,
    MACHINE_CONDITION_HEADERS,
    RECEIVABLE_RECONCILIATION_HEADERS,
    SALES_HEADERS,
    SALES_SHEETS_CONFIG,
)


class SalesRepository:
    def __init__(self, database: ExcelDatabase | None = None):
        self.database = database or ExcelDatabase(get_sales_db_path(), SALES_SHEETS_CONFIG)

    def list_machines(self) -> list[dict]:
        return self.database.read_sheet(SHEET_CARD_MACHINES)

    def add_machine(self, row: dict) -> dict:
        return self.database.append_row(SHEET_CARD_MACHINES, CARD_MACHINE_HEADERS, row)

    def update_machine(self, maquina_cartao_id: str, changes: dict) -> dict:
        return self.database.update_row(SHEET_CARD_MACHINES, CARD_MACHINE_HEADERS, "maquina_cartao_id", maquina_cartao_id, changes)

    def list_conditions(self) -> list[dict]:
        return self.database.read_sheet(SHEET_MACHINE_CONDITIONS)

    def add_condition(self, row: dict) -> dict:
        return self.database.append_row(SHEET_MACHINE_CONDITIONS, MACHINE_CONDITION_HEADERS, row)

    def replace_conditions_for_machine(self, maquina_cartao_id: str, rows: list[dict]) -> None:
        existing = [row for row in self.list_conditions() if str(row.get("maquina_cartao_id", "")) != str(maquina_cartao_id)]
        self.database.write_sheet(SHEET_MACHINE_CONDITIONS, MACHINE_CONDITION_HEADERS, existing + rows)

    def update_conditions_for_machine(self, maquina_cartao_id: str, changes: dict) -> None:
        rows = self.list_conditions()
        for row in rows:
            if str(row.get("maquina_cartao_id", "")) == str(maquina_cartao_id):
                row.update(changes)
        self.database.write_sheet(SHEET_MACHINE_CONDITIONS, MACHINE_CONDITION_HEADERS, rows)

    def list_sales(self) -> list[dict]:
        return self.database.read_sheet(SHEET_SALES)

    def add_sale(self, row: dict) -> dict:
        return self.database.append_row(SHEET_SALES, SALES_HEADERS, row)

    def update_sale(self, venda_id: str, changes: dict) -> dict:
        return self.database.update_row(SHEET_SALES, SALES_HEADERS, "venda_id", venda_id, changes)

    def list_reconciliations(self) -> list[dict]:
        return self.database.read_sheet(SHEET_RECEIVABLE_RECONCILIATION)

    def add_reconciliation(self, row: dict) -> dict:
        return self.database.append_row(SHEET_RECEIVABLE_RECONCILIATION, RECEIVABLE_RECONCILIATION_HEADERS, row)

    def update_reconciliation(self, conferencia_id: str, changes: dict) -> dict:
        return self.database.update_row(
            SHEET_RECEIVABLE_RECONCILIATION,
            RECEIVABLE_RECONCILIATION_HEADERS,
            "conferencia_id",
            conferencia_id,
            changes,
        )
