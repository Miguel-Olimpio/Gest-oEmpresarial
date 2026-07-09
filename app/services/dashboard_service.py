"""Resumo para o dashboard."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.financial_service import FinancialService
from app.services.sales_service import SalesService
from app.utils.formatting import clean_text
from app.utils.months import normalize_month
from app.utils.numbers import parse_decimal

if TYPE_CHECKING:
    from app.services.collaborator_service import CollaboratorService


EMPLOYEE_EXPENSE_CATEGORIES = {
    "salários",
    "salarios",
    "pró-labore",
    "pro-labore",
    "pro labore",
    "colaboradores",
    "socios",
    "sócios",
}

SUPPLY_EXPENSE_CATEGORIES = {
    "matéria-prima",
    "materia-prima",
    "materia prima",
    "embalagens",
    "compras de insumos",
    "insumos",
}

FIXED_EXPENSE_CATEGORIES = {
    "aluguel",
    "internet",
    "contabilidade",
    "sistemas",
    "financiamentos",
}


def _month_parts(month_ref) -> tuple[int, int]:
    month_text = normalize_month(month_ref)
    month, year = month_text.split("/")
    return int(month), int(year)


def _shift_month(month_ref, offset: int) -> str:
    month, year = _month_parts(month_ref)
    month += offset
    while month <= 0:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return f"{month:02d}/{year:04d}"


class DashboardService:
    def __init__(
        self,
        financial_service: FinancialService,
        sales_service: SalesService,
        collaborator_service: "CollaboratorService | None" = None,
    ):
        self.financial_service = financial_service
        self.sales_service = sales_service
        self.collaborator_service = collaborator_service

    @staticmethod
    def _break_even(fixed: float, revenue: float, variable: float) -> float:
        if revenue <= 0:
            return 0.0
        contribution_margin = (revenue - variable) / revenue
        if contribution_margin <= 0:
            return 0.0
        return fixed / contribution_margin

    def occupied_people_count(self) -> int:
        if self.collaborator_service is None:
            return 0
        return len(self.collaborator_service.list_collaborators(active_only=True))

    def calculate_productivity(self, month_ref=None) -> float | None:
        people_count = self.occupied_people_count()
        if people_count <= 0:
            return None
        sales = self.sales_service.sales_summary(month_ref)
        variable = self.financial_service.total_variable_costs(month_ref)
        return (sales["faturamento_bruto"] - variable) / people_count

    def get_month_summary(self, month_ref=None) -> dict:
        data = self.summary(month_ref)
        data["produtividade"] = self.calculate_productivity(month_ref)
        data["numero_pessoas_ocupadas"] = self.occupied_people_count()
        data["ponto_equilibrio_calculavel"] = data["ponto_equilibrio"] > 0
        return data

    @staticmethod
    def _expense_group(category: str, source: str) -> str:
        key = clean_text(category).lower()
        if key in EMPLOYEE_EXPENSE_CATEGORIES:
            return "Funcionários"
        if key in SUPPLY_EXPENSE_CATEGORIES:
            return "Insumos"
        if source == "fixo" or key in FIXED_EXPENSE_CATEGORIES:
            return "Custos fixos"
        return "Custos variáveis"

    def get_expense_distribution(self, month_ref=None) -> list[dict]:
        totals = {
            "Custos fixos": 0.0,
            "Custos variáveis": 0.0,
            "Funcionários": 0.0,
            "Insumos": 0.0,
        }
        for row in self.financial_service.list_effective_fixed_costs_for_month(month_ref):
            group = self._expense_group(str(row.get("categoria", "")), "fixo")
            totals[group] += parse_decimal(row.get("valor"))
        for row in self.financial_service.variable_costs_by_category(month_ref):
            group = self._expense_group(str(row.get("categoria", "")), "variavel")
            totals[group] += parse_decimal(row.get("valor"))
        return [{"categoria": name, "valor": value} for name, value in totals.items() if value > 0]

    def get_productivity_last_6_months(self, month_ref=None) -> list[dict]:
        base = normalize_month(month_ref)
        rows = []
        for offset in range(-5, 1):
            month_text = _shift_month(base, offset)
            productivity = self.calculate_productivity(month_text)
            rows.append({"mes": month_text, "produtividade": productivity if productivity is not None else 0.0})
        return rows

    def summary(self, month_ref=None) -> dict:
        sales = self.sales_service.sales_summary(month_ref)
        fixed = self.financial_service.total_fixed_costs(month_ref)
        variable = self.financial_service.total_variable_costs(month_ref)
        gross_profit = sales["faturamento_bruto"] - variable
        net_profit = gross_profit - fixed
        financial_cash = self.financial_service.cash_summary(month_ref)
        received = self.sales_service.received_value(month_ref)
        pending = self.sales_service.pending_value(month_ref)
        expected = self.sales_service.expected_net_receipts(month_ref)
        divergences = self.sales_service.divergent_reconciliations(month_ref)
        break_even = self._break_even(fixed, sales["faturamento_bruto"], variable)

        alerts: list[str] = []
        if sales["faturamento_bruto"] == 0:
            alerts.append("Registre vendas / entradas para acompanhar faturamento, caixa e recebíveis.")
        if divergences:
            alerts.append(f"Há {len(divergences)} recebimento divergente para conferir.")
        if break_even and sales["faturamento_bruto"] < break_even:
            alerts.append("O faturamento ainda está abaixo do ponto de equilíbrio.")
        return {
            "faturamento": sales["faturamento_bruto"],
            "vendas_brutas": sales["faturamento_bruto"],
            "taxas_maquinas_cartao": sales["taxas"],
            "faturamento_liquido": sales["faturamento_liquido"],
            "valor_liquido_a_receber": expected,
            "valor_ja_recebido": received,
            "recebimentos_pendentes": pending,
            "divergencias_recebiveis": len(divergences),
            "custos_fixos": fixed,
            "custos_variaveis": variable,
            "lucro_bruto": gross_profit,
            "lucro_liquido": net_profit,
            "saldo_atual": financial_cash["saldo_atual"],
            "saldo_projetado": financial_cash["saldo_projetado"],
            "entradas_totais": financial_cash["entradas"],
            "saidas_totais": financial_cash["saidas"],
            "contas_vencidas": financial_cash["contas_vencidas"],
            "ponto_equilibrio": break_even,
            "alertas": alerts,
        }
