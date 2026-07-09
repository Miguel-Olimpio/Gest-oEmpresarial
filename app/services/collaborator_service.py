"""Regras de colaboradores e socios."""

from __future__ import annotations

import unicodedata
import uuid

from app.models.collaborator import Collaborator
from app.repositories.collaborator_repository import CollaboratorRepository
from app.utils.dates import format_date
from app.utils.formatting import clean_text
from app.utils.numbers import parse_decimal
from app.utils.validators import non_negative_money, required_text

COLLABORATOR_TYPE_EMPLOYEE = "colaborador"
COLLABORATOR_TYPE_PARTNER = "sócio"


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _active(value) -> bool:
    if isinstance(value, str):
        return clean_text(value).lower() not in {"false", "0", "não", "nao", "inativo"}
    return bool(value if value != "" else True)


def _normalize_type(value) -> str:
    text = _strip_accents(required_text(value, "Tipo")).lower()
    if text in {"colaborador", "funcionario", "funcionário"}:
        return COLLABORATOR_TYPE_EMPLOYEE
    if text in {"socio", "sócio"}:
        return COLLABORATOR_TYPE_PARTNER
    raise ValueError("Tipo deve ser colaborador ou sócio.")


class CollaboratorService:
    def __init__(self, repository: CollaboratorRepository | None = None):
        self.repository = repository or CollaboratorRepository()

    def create_collaborator(self, **data) -> dict:
        now = format_date()
        collaborator = Collaborator(
            colaborador_id=uuid.uuid4().hex[:12],
            nome=required_text(data.get("nome"), "Nome"),
            telefone=clean_text(data.get("telefone")),
            tipo=_normalize_type(data.get("tipo")),
            salario_base=non_negative_money(data.get("salario_base", 0), "Salário base"),
            active=_active(data.get("active", True)),
            observacoes=clean_text(data.get("observacoes")),
            data_cadastro=now,
            data_atualizacao=now,
        )
        return self.repository.add(collaborator.to_dict())

    def update_collaborator(self, colaborador_id: str, **data) -> dict:
        if not self.get_collaborator(colaborador_id):
            raise KeyError("Colaborador não encontrado.")
        changes = {
            "nome": required_text(data.get("nome"), "Nome"),
            "telefone": clean_text(data.get("telefone")),
            "tipo": _normalize_type(data.get("tipo")),
            "salario_base": non_negative_money(data.get("salario_base", 0), "Salário base"),
            "active": _active(data.get("active", True)),
            "observacoes": clean_text(data.get("observacoes")),
            "data_atualizacao": format_date(),
        }
        return self.repository.update(colaborador_id, changes)

    def inactivate_collaborator(self, colaborador_id: str) -> dict:
        return self.repository.update(colaborador_id, {"active": False, "data_atualizacao": format_date()})

    def list_collaborators(self, active_only: bool = False) -> list[dict]:
        rows = []
        for row in self.repository.list_all():
            item = dict(row)
            item["tipo"] = _normalize_type(item.get("tipo") or COLLABORATOR_TYPE_EMPLOYEE)
            item["salario_base"] = parse_decimal(item.get("salario_base"))
            item["active"] = _active(item.get("active", True))
            rows.append(item)
        if active_only:
            rows = [row for row in rows if row.get("active")]
        return sorted(rows, key=lambda row: clean_text(row.get("nome")).lower())

    def get_collaborator(self, colaborador_id: str) -> dict | None:
        for row in self.list_collaborators(active_only=False):
            if str(row.get("colaborador_id")) == str(colaborador_id):
                return row
        return None

    def salary_total(self, tipo: str) -> float:
        normalized = _normalize_type(tipo)
        return sum(
            parse_decimal(row.get("salario_base"))
            for row in self.list_collaborators(active_only=True)
            if row.get("tipo") == normalized
        )

    def employee_salary_total(self) -> float:
        return self.salary_total(COLLABORATOR_TYPE_EMPLOYEE)

    def partner_pro_labore_total(self) -> float:
        return self.salary_total(COLLABORATOR_TYPE_PARTNER)
