"""Modelos financeiros."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class FixedCost:
    custo_id: str
    data: str
    categoria: str
    descricao: str
    valor: float
    recorrente: bool = True
    observacoes: str = ""
    data_cadastro: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class VariableCost:
    custo_id: str
    data: str
    categoria: str
    descricao: str
    valor: float
    observacoes: str = ""
    origem: str = ""
    venda_id: str = ""
    data_cadastro: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class CashFlowEntry:
    lancamento_id: str
    data: str
    tipo: str
    categoria: str
    descricao: str
    valor: float
    status: str = "pendente"
    origem: str = "manual"
    venda_id: str = ""
    observacoes: str = ""
    data_cadastro: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class CostCategory:
    categoria_id: str
    tipo_custo: str
    nome_categoria: str
    active: bool = True
    data_criacao: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

