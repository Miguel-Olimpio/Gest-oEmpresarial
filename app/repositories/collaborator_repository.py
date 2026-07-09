"""Repositorio de colaboradores e socios."""

from __future__ import annotations

from app.config.paths import get_collaborators_db_path
from app.config.settings import SHEET_COLLABORATORS
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import COLLABORATOR_HEADERS, COLLABORATORS_SHEETS_CONFIG


class CollaboratorRepository:
    def __init__(self, database: ExcelDatabase | None = None):
        self.database = database or ExcelDatabase(get_collaborators_db_path(), COLLABORATORS_SHEETS_CONFIG)

    def list_all(self) -> list[dict]:
        return self.database.read_sheet(SHEET_COLLABORATORS)

    def add(self, row: dict) -> dict:
        return self.database.append_row(SHEET_COLLABORATORS, COLLABORATOR_HEADERS, row)

    def update(self, item_id: str, changes: dict) -> dict:
        return self.database.update_row(SHEET_COLLABORATORS, COLLABORATOR_HEADERS, "colaborador_id", item_id, changes)
