"""Modelos de vendas e recebiveis."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class CardMachine:
    maquina_cartao_id: str
    nome: str
    observacoes: str = ""
    active: bool = True
    data_cadastro: str = ""
    data_atualizacao: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class CardMachineCondition:
    condicao_id: str
    maquina_cartao_id: str
    bandeira: str
    modalidade: str
    parcelas: int
    taxa_percentual: float
    taxa_fixa: float
    prazo_dias_uteis: int
    active: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class Sale:
    venda_id: str
    data_venda: str
    descricao: str
    valor_bruto: float
    forma_pagamento: str
    maquina_cartao: str
    bandeira: str
    modalidade: str
    parcelas: int
    taxa_percentual: float
    taxa_fixa: float
    valor_taxa: float
    valor_liquido: float
    data_prevista_recebimento: str
    status_recebimento: str = "pendente"
    observacoes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ReceivableReconciliation:
    conferencia_id: str
    venda_id: str
    data_prevista: str
    valor_esperado: float
    valor_recebido: float | str = ""
    diferenca: float | str = ""
    status: str = "pendente"

    def to_dict(self) -> dict:
        return asdict(self)
