"""Schemas dos workbooks Excel."""

from __future__ import annotations

from app.config.settings import (
    SHEET_AUDIT_LOG,
    SHEET_CASH_FLOW,
    SHEET_CARD_MACHINES,
    SHEET_COLLABORATORS,
    SHEET_COST_CATEGORIES,
    SHEET_FIXED_COSTS,
    SHEET_MACHINE_CONDITIONS,
    SHEET_RECEIVABLE_RECONCILIATION,
    SHEET_SALES,
    SHEET_VARIABLE_COSTS,
)

FIXED_COST_HEADERS = ["custo_id", "data", "categoria", "descricao", "valor", "recorrente", "observacoes", "data_cadastro"]
VARIABLE_COST_HEADERS = ["custo_id", "data", "categoria", "descricao", "valor", "observacoes", "origem", "venda_id", "data_cadastro"]
CASH_FLOW_HEADERS = ["lancamento_id", "data", "tipo", "categoria", "descricao", "valor", "status", "origem", "venda_id", "observacoes", "data_cadastro"]
COST_CATEGORY_HEADERS = ["categoria_id", "tipo_custo", "nome_categoria", "active", "data_criacao"]
AUDIT_LOG_HEADERS = ["log_id", "entidade", "entidade_id", "acao", "descricao", "data_hora"]
COLLABORATOR_HEADERS = [
    "colaborador_id",
    "nome",
    "telefone",
    "tipo",
    "salario_base",
    "active",
    "observacoes",
    "data_cadastro",
    "data_atualizacao",
]
CARD_MACHINE_HEADERS = ["maquina_cartao_id", "nome", "observacoes", "active", "data_cadastro", "data_atualizacao"]
MACHINE_CONDITION_HEADERS = ["condicao_id", "maquina_cartao_id", "bandeira", "modalidade", "parcelas", "taxa_percentual", "taxa_fixa", "prazo_dias_uteis", "active"]
SALES_HEADERS = [
    "venda_id",
    "data_venda",
    "descricao",
    "valor_bruto",
    "forma_pagamento",
    "maquina_cartao",
    "bandeira",
    "modalidade",
    "parcelas",
    "taxa_percentual",
    "taxa_fixa",
    "valor_taxa",
    "valor_liquido",
    "data_prevista_recebimento",
    "status_recebimento",
    "observacoes",
]
RECEIVABLE_RECONCILIATION_HEADERS = ["conferencia_id", "venda_id", "data_prevista", "valor_esperado", "valor_recebido", "diferenca", "status"]

FINANCIAL_SHEETS_CONFIG = {
    SHEET_FIXED_COSTS: FIXED_COST_HEADERS,
    SHEET_VARIABLE_COSTS: VARIABLE_COST_HEADERS,
    SHEET_CASH_FLOW: CASH_FLOW_HEADERS,
    SHEET_COST_CATEGORIES: COST_CATEGORY_HEADERS,
}
AUDIT_SHEETS_CONFIG = {SHEET_AUDIT_LOG: AUDIT_LOG_HEADERS}
COLLABORATORS_SHEETS_CONFIG = {SHEET_COLLABORATORS: COLLABORATOR_HEADERS}
SALES_SHEETS_CONFIG = {
    SHEET_CARD_MACHINES: CARD_MACHINE_HEADERS,
    SHEET_MACHINE_CONDITIONS: MACHINE_CONDITION_HEADERS,
    SHEET_SALES: SALES_HEADERS,
    SHEET_RECEIVABLE_RECONCILIATION: RECEIVABLE_RECONCILIATION_HEADERS,
}
