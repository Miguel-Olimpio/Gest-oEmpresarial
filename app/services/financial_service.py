"""Regras financeiras."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from app.config.settings import CASH_STATUS_OVERDUE, CASH_STATUS_PAID, CASH_STATUS_PENDING
from app.models.financial import CashFlowEntry, CostCategory, FixedCost, VariableCost
from app.repositories.financial_repository import (
    CashFlowRepository,
    CostCategoryRepository,
    FixedCostRepository,
    VariableCostRepository,
)
from app.utils.dates import format_date, parse_date, today
from app.utils.formatting import clean_text
from app.utils.months import normalize_month, same_month
from app.utils.numbers import parse_decimal
from app.utils.validators import non_negative_money, optional_date, required_text

if TYPE_CHECKING:
    from app.services.collaborator_service import CollaboratorService

DEFAULT_FIXED_CATEGORIES = (
    "Aluguel",
    "Internet",
    "Salários",
    "Pró-labore",
    "Contabilidade",
    "Sistemas",
    "Financiamentos",
)

DEFAULT_VARIABLE_CATEGORIES = (
    "Imposto sobre venda e sobre lucro da empresa",
    "Comissão sobre venda",
    "Taxa de máquina de cartão",
    "Freelancer",
    "Matéria-prima",
    "Embalagens",
    "Frete",
    "Plataformas de delivery",
    "Energia",
    "Marketing",
    "Manutenção",
    "Outros custos variáveis",
)

SALE_CASH_CATEGORY = "Venda"

REVENUE_CATEGORIES = (
    "Aporte",
    "Empréstimo recebido",
    "Reembolso",
    "Outros recebimentos",
    "Ajuste manual de caixa",
)

OTHER_OUTFLOW_CATEGORIES = (
    "Impostos",
    "Investimentos",
    "Outros pagamentos",
)


def _required_non_negative_money(value, field_name: str) -> float:
    if not clean_text(value):
        raise ValueError(f"{field_name} é obrigatório.")
    return non_negative_money(value, field_name)


class FinancialService:
    def __init__(
        self,
        fixed_repository: FixedCostRepository | None = None,
        variable_repository: VariableCostRepository | None = None,
        cash_repository: CashFlowRepository | None = None,
        category_repository: CostCategoryRepository | None = None,
        collaborator_service: "CollaboratorService | None" = None,
    ):
        self.fixed_repository = fixed_repository or FixedCostRepository()
        self.variable_repository = variable_repository or VariableCostRepository()
        self.cash_repository = cash_repository or CashFlowRepository()
        self.category_repository = category_repository or CostCategoryRepository()
        self.collaborator_service = collaborator_service
        self.ensure_default_categories()

    def create_fixed_cost(self, **data) -> dict:
        month_text = normalize_month(data.get("mes") or data.get("data"))
        cost = FixedCost(
            custo_id=uuid.uuid4().hex[:12],
            data=month_text,
            categoria=required_text(data.get("categoria"), "Categoria"),
            descricao=required_text(data.get("descricao"), "Descrição"),
            valor=_required_non_negative_money(data.get("valor"), "Valor"),
            recorrente=str(data.get("recorrente", "sim")).lower() in {"sim", "true", "1", "yes"},
            observacoes=clean_text(data.get("observacoes")),
            data_cadastro=format_date(),
        )
        return self.fixed_repository.add(cost.to_dict())


    def fixed_costs_by_category_for_month(self, month_ref: date | str | None = None) -> dict[str, dict]:
        rows: dict[str, dict] = {}
        for row in self.list_fixed_costs_for_month(month_ref):
            category = clean_text(row.get("categoria"))
            if category:
                rows[category.lower()] = row
        return rows

    def sync_fixed_costs_for_month(self, month_ref: date | str, costs: list[dict]) -> list[dict]:
        month_text = normalize_month(month_ref)
        existing = self.fixed_costs_by_category_for_month(month_text)
        saved_rows: list[dict] = []
        seen: set[str] = set()
        for item in costs:
            category = required_text(item.get("categoria"), "Categoria")
            if self.is_automatic_fixed_category(category):
                continue
            key = category.lower()
            if key in seen:
                continue
            seen.add(key)
            value = non_negative_money(item.get("valor", 0), "Valor")
            description = clean_text(item.get("descricao")) or category
            notes = clean_text(item.get("observacoes"))
            if category not in DEFAULT_FIXED_CATEGORIES:
                self.create_category("fixo", category)
            if key in existing:
                saved_rows.append(
                    self.fixed_repository.update(
                        str(existing[key].get("custo_id")),
                        {
                            "data": month_text,
                            "categoria": category,
                            "descricao": description,
                            "valor": value,
                            "recorrente": True,
                            "observacoes": notes,
                        },
                    )
                )
            else:
                saved_rows.append(
                    self.create_fixed_cost(
                        data=month_text,
                        categoria=category,
                        descricao=description,
                        valor=value,
                        recorrente=True,
                        observacoes=notes,
                    )
                )
        return saved_rows

    def create_variable_cost(self, **data) -> dict:
        cost = VariableCost(
            custo_id=uuid.uuid4().hex[:12],
            data=optional_date(data.get("data")) or format_date(),
            categoria=required_text(data.get("categoria"), "Categoria"),
            descricao=required_text(data.get("descricao"), "Descrição"),
            valor=_required_non_negative_money(data.get("valor"), "Valor"),
            observacoes=clean_text(data.get("observacoes")),
            origem=clean_text(data.get("origem")),
            venda_id=clean_text(data.get("venda_id")),
            data_cadastro=format_date(),
        )
        return self.variable_repository.add(cost.to_dict())

    def create_machine_fee_variable_cost(self, sale: dict) -> dict | None:
        fee_value = parse_decimal(sale.get("valor_taxa"))
        if fee_value <= 0:
            return None
        sale_id = clean_text(sale.get("venda_id"))
        for row in self.list_variable_costs():
            if clean_text(row.get("origem")).lower() == "venda" and clean_text(row.get("venda_id")) == sale_id:
                return row
        category = "Taxa de máquina de cartão"
        self.create_category("variavel", category)
        description = f"Taxa automática da venda {sale_id}"
        if clean_text(sale.get("descricao")):
            description = f"Taxa automática da venda {sale_id} - {clean_text(sale.get('descricao'))}"
        cost = VariableCost(
            custo_id=uuid.uuid4().hex[:12],
            data=optional_date(sale.get("data_venda")) or format_date(),
            categoria=category,
            descricao=description,
            valor=fee_value,
            observacoes="Gerado automaticamente pelo módulo de Vendas.",
            origem="venda",
            venda_id=sale_id,
            data_cadastro=format_date(),
        )
        return self.variable_repository.add(cost.to_dict())

    def create_cash_flow(self, **data) -> dict:
        entry_type = clean_text(data.get("tipo")).lower()
        if entry_type in {"saída", "saida"}:
            entry_type = "saida"
        if entry_type not in {"entrada", "saida"}:
            raise ValueError("Tipo deve ser entrada ou saída.")
        status = clean_text(data.get("status")).lower() or CASH_STATUS_PENDING
        if status not in {CASH_STATUS_PAID, CASH_STATUS_PENDING, CASH_STATUS_OVERDUE}:
            raise ValueError("Status inválido.")
        origin = clean_text(data.get("origem")) or "manual"
        category = required_text(data.get("categoria"), "Categoria")
        category_key = clean_text(category).lower()
        is_sale_category = "venda" in category_key or category_key == "recebimentos futuros"
        if entry_type == "entrada" and origin.lower() != "venda" and is_sale_category:
            raise ValueError("Vendas devem ser lançadas na aba Vendas.")
        entry = CashFlowEntry(
            lancamento_id=uuid.uuid4().hex[:12],
            data=optional_date(data.get("data")) or format_date(),
            tipo=entry_type,
            categoria=category,
            descricao=required_text(data.get("descricao"), "Descrição"),
            valor=_required_non_negative_money(data.get("valor"), "Valor"),
            status=status,
            origem=origin,
            venda_id=clean_text(data.get("venda_id")),
            observacoes=clean_text(data.get("observacoes")),
            data_cadastro=format_date(),
        )
        return self.cash_repository.add(entry.to_dict())

    def find_cash_flow_by_sale(self, venda_id: str) -> dict | None:
        wanted = clean_text(venda_id)
        if not wanted:
            return None
        for row in self.list_cash_flow():
            if clean_text(row.get("origem")).lower() == "venda" and clean_text(row.get("venda_id")) == wanted:
                return row
        return None

    def create_sale_cash_flow_entry(self, sale: dict) -> dict | None:
        sale_id = clean_text(sale.get("venda_id"))
        if not sale_id:
            return None
        value = parse_decimal(sale.get("valor_liquido"))
        if value < 0:
            return None
        expected_date = optional_date(sale.get("data_prevista_recebimento")) or optional_date(sale.get("data_venda")) or format_date()
        sale_date = optional_date(sale.get("data_venda")) or expected_date
        status = CASH_STATUS_PAID if expected_date == sale_date else CASH_STATUS_PENDING
        description = f"Venda {sale_id}"
        if clean_text(sale.get("descricao")):
            description = f"Venda {sale_id} - {clean_text(sale.get('descricao'))}"
        row = {
            "data": expected_date,
            "tipo": "entrada",
            "categoria": SALE_CASH_CATEGORY,
            "descricao": description,
            "valor": value,
            "status": status,
            "origem": "venda",
            "venda_id": sale_id,
            "observacoes": "Gerado automaticamente pelo módulo de Vendas.",
        }
        existing = self.find_cash_flow_by_sale(sale_id)
        if existing:
            return self.cash_repository.update(str(existing.get("lancamento_id")), row)
        return self.create_cash_flow(**row)

    def mark_sale_cash_flow_received(self, venda_id: str, valor_recebido) -> dict | None:
        existing = self.find_cash_flow_by_sale(venda_id)
        if not existing:
            return None
        return self.cash_repository.update(
            str(existing.get("lancamento_id")),
            {
                "valor": parse_decimal(valor_recebido),
                "status": CASH_STATUS_PAID,
                "observacoes": "Recebimento conferido na Conferência de Máquina de Cartão.",
            },
        )

    def create_category(self, tipo_custo: str, nome_categoria: str) -> dict:
        cost_type = clean_text(tipo_custo).lower()
        if cost_type not in {"fixo", "variavel"}:
            raise ValueError("Tipo de custo deve ser fixo ou variavel.")
        name = required_text(nome_categoria, "Nome da categoria")
        for row in self.list_categories(cost_type):
            if clean_text(row.get("nome_categoria")).lower() == name.lower():
                return row
        category = CostCategory(
            categoria_id=uuid.uuid4().hex[:12],
            tipo_custo=cost_type,
            nome_categoria=name,
            active=True,
            data_criacao=format_date(),
        )
        return self.category_repository.add(category.to_dict())

    def ensure_default_categories(self) -> None:
        existing = {
            (clean_text(row.get("tipo_custo")).lower(), clean_text(row.get("nome_categoria")).lower())
            for row in self.category_repository.list_all()
        }
        for name in DEFAULT_FIXED_CATEGORIES:
            key = ("fixo", name.lower())
            if key not in existing:
                self.create_category("fixo", name)
                existing.add(key)
        for name in DEFAULT_VARIABLE_CATEGORIES:
            key = ("variavel", name.lower())
            if key not in existing:
                self.create_category("variavel", name)
                existing.add(key)

    def list_categories(self, tipo_custo: str | None = None) -> list[dict]:
        rows = [row for row in self.category_repository.list_all() if bool(row.get("active", True))]
        if tipo_custo:
            rows = [row for row in rows if clean_text(row.get("tipo_custo")).lower() == clean_text(tipo_custo).lower()]
        return sorted(rows, key=lambda row: clean_text(row.get("nome_categoria")).lower())

    def category_names(self, tipo_custo: str) -> list[str]:
        return [str(row.get("nome_categoria", "")) for row in self.list_categories(tipo_custo)]

    def revenue_categories(self) -> list[str]:
        return list(REVENUE_CATEGORIES)

    def outflow_categories(self) -> list[str]:
        categories = list(self.category_names("variavel"))
        for name in self.category_names("fixo"):
            if name not in categories:
                categories.append(name)
        for name in OTHER_OUTFLOW_CATEGORIES:
            if name not in categories:
                categories.append(name)
        return categories

    def list_fixed_costs(self) -> list[dict]:
        return self.fixed_repository.list_all()

    def list_fixed_costs_for_month(self, month_ref: date | str | None = None) -> list[dict]:
        return [row for row in self.list_fixed_costs() if same_month(row.get("data"), month_ref)]

    def is_automatic_fixed_category(self, category: str) -> bool:
        return clean_text(category).lower() in {"salários", "salarios", "pró-labore", "pro-labore", "pro labore"}

    def automatic_fixed_cost_values(self) -> dict[str, float]:
        if self.collaborator_service is None:
            return {"Salários": 0.0, "Pró-labore": 0.0}
        return {
            "Salários": self.collaborator_service.employee_salary_total(),
            "Pró-labore": self.collaborator_service.partner_pro_labore_total(),
        }

    def automatic_fixed_cost_rows(self, month_ref: date | str | None = None) -> list[dict]:
        month_text = normalize_month(month_ref)
        rows = []
        for category, value in self.automatic_fixed_cost_values().items():
            if parse_decimal(value) <= 0:
                continue
            rows.append(
                {
                    "custo_id": f"auto_{category.lower()}",
                    "data": month_text,
                    "categoria": category,
                    "descricao": category,
                    "valor": value,
                    "recorrente": True,
                    "observacoes": "Calculado automaticamente pela aba Colaboradores.",
                    "data_cadastro": "",
                }
            )
        return rows

    def list_effective_fixed_costs_for_month(self, month_ref: date | str | None = None) -> list[dict]:
        rows = [row for row in self.list_fixed_costs_for_month(month_ref) if not self.is_automatic_fixed_category(str(row.get("categoria", "")))]
        return rows + self.automatic_fixed_cost_rows(month_ref)

    def list_variable_costs(self) -> list[dict]:
        return self.variable_repository.list_all()

    def list_variable_costs_for_month(self, month_ref: date | str | None = None) -> list[dict]:
        return [row for row in self.list_variable_costs() if same_month(row.get("data"), month_ref)]

    def list_cash_flow(self) -> list[dict]:
        return self.cash_repository.list_all()

    def list_cash_flow_for_month(self, month_ref: date | str | None = None) -> list[dict]:
        return [row for row in self.list_cash_flow() if same_month(row.get("data"), month_ref)]

    def total_fixed_costs(self, month_ref: date | str | None = None) -> float:
        return sum(parse_decimal(row.get("valor")) for row in self.list_effective_fixed_costs_for_month(month_ref))

    def is_variable_cost_category(self, category: str) -> bool:
        category_text = clean_text(category).lower()
        return any(clean_text(name).lower() == category_text for name in self.category_names("variavel"))

    def variable_cash_flow_rows(self, month_ref: date | str | None = None) -> list[dict]:
        rows = []
        for row in self.list_cash_flow_for_month(month_ref):
            if clean_text(row.get("tipo")).lower() != "saida":
                continue
            if self.is_variable_cost_category(str(row.get("categoria", ""))):
                rows.append(row)
        return rows

    def total_variable_costs(self, month_ref: date | str | None = None) -> float:
        cash_total = sum(parse_decimal(row.get("valor")) for row in self.variable_cash_flow_rows(month_ref))
        direct_total = sum(parse_decimal(row.get("valor")) for row in self.list_variable_costs_for_month(month_ref))
        return cash_total + direct_total

    def variable_costs_by_category(self, month_ref: date | str | None = None) -> list[dict]:
        totals = {name: 0.0 for name in self.category_names("variavel")}
        for row in self.variable_cash_flow_rows(month_ref):
            category = str(row.get("categoria", ""))
            totals.setdefault(category, 0.0)
            totals[category] += parse_decimal(row.get("valor"))
        for row in self.list_variable_costs_for_month(month_ref):
            category = str(row.get("categoria", ""))
            totals.setdefault(category, 0.0)
            totals[category] += parse_decimal(row.get("valor"))
        return [{"categoria": name, "valor": value} for name, value in totals.items()]

    def revenue(self, month_ref: date | str | None = None) -> float:
        return sum(
            parse_decimal(row.get("valor"))
            for row in self.list_cash_flow_for_month(month_ref)
            if clean_text(row.get("tipo")).lower() == "entrada"
        )

    def revenue_by_category(self, month_ref: date | str | None = None) -> list[dict]:
        totals = {name: 0.0 for name in REVENUE_CATEGORIES}
        for row in self.list_cash_flow_for_month(month_ref):
            if clean_text(row.get("tipo")).lower() != "entrada":
                continue
            category = str(row.get("categoria", ""))
            totals.setdefault(category, 0.0)
            totals[category] += parse_decimal(row.get("valor"))
        return [{"categoria": name, "valor": value} for name, value in totals.items()]

    def cash_summary(self, month_ref: date | str | None = None) -> dict:
        projected_in = projected_out = paid_in = paid_out = overdue = 0.0
        current_date = today()
        for row in self.list_cash_flow_for_month(month_ref):
            value = parse_decimal(row.get("valor"))
            is_in = clean_text(row.get("tipo")).lower() == "entrada"
            is_paid = clean_text(row.get("status")).lower() == CASH_STATUS_PAID
            if is_in:
                projected_in += value
                if is_paid:
                    paid_in += value
            else:
                projected_out += value
                if is_paid:
                    paid_out += value
                else:
                    try:
                        if parse_date(str(row.get("data", ""))) < current_date:
                            overdue += value
                    except ValueError:
                        pass
        return {
            "entradas": projected_in,
            "saidas": projected_out,
            "saldo_atual": paid_in - paid_out,
            "saldo_projetado": projected_in - projected_out,
            "contas_vencidas": overdue,
        }

    def profit_summary(self, month_ref: date | str | None = None) -> dict:
        revenue = self.revenue(month_ref)
        fixed = self.total_fixed_costs(month_ref)
        variable = self.total_variable_costs(month_ref)
        gross_profit = revenue - variable
        net_profit = gross_profit - fixed
        return {
            "faturamento": revenue,
            "custos_fixos": fixed,
            "custos_variaveis": variable,
            "lucro_bruto": gross_profit,
            "lucro_liquido": net_profit,
        }


