"""Modelo de colaboradores e socios."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class Collaborator:
    colaborador_id: str
    nome: str
    telefone: str
    tipo: str
    salario_base: float
    active: bool = True
    observacoes: str = ""
    data_cadastro: str = ""
    data_atualizacao: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
