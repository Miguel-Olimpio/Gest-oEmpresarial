"""Coleta e geração do relatório financeiro para contador."""

from __future__ import annotations

import os

from app.config.paths import get_pdfs_dir
from app.pdf.accounting_report_pdf import build_accounting_report_pdf
from app.services.financial_service import FinancialService
from app.services.sales_service import SalesService
from app.utils.dates import format_date
from app.utils.formatting import clean_text
from app.utils.months import normalize_month
from app.utils.numbers import parse_decimal


class AccountingReportService:
    def __init__(self, financial_service: FinancialService, sales_service: SalesService):
        self.financial_service = financial_service
        self.sales_service = sales_service

    def collect_data(self, month_ref=None) -> dict:
        month_text = normalize_month(month_ref)
        sales_summary = self.sales_service.sales_summary(month_text)
        cash_summary = self.financial_service.cash_summary(month_text)
        fixed = self.financial_service.total_fixed_costs(month_text)
        variable = self.financial_service.total_variable_costs(month_text)
        lucro_liquido = sales_summary["faturamento_bruto"] - variable - fixed
        sales = self.sales_service.list_sales_for_month(month_text)
        variable_rows = []
        for row in self.financial_service.list_variable_costs_for_month(month_text):
            item = dict(row)
            item["origem"] = clean_text(item.get("origem")) or "manual"
            variable_rows.append(item)
        for row in self.financial_service.variable_cash_flow_rows(month_text):
            item = dict(row)
            item["origem"] = clean_text(item.get("origem")) or "fluxo de caixa"
            variable_rows.append(item)
        return {
            "month_ref": month_text,
            "generated_at": format_date(),
            "summary": {
                "faturamento_bruto": sales_summary["faturamento_bruto"],
                "taxas_maquinas_cartao": sales_summary["taxas"],
                "custos_fixos": fixed,
                "custos_variaveis": variable,
                "entradas_totais": cash_summary["entradas"],
                "saidas_totais": cash_summary["saidas"],
                "saldo_caixa": cash_summary["saldo_projetado"],
                "lucro_liquido": lucro_liquido,
            },
            "sales": sales,
            "cash_flow": self.financial_service.list_cash_flow_for_month(month_text),
            "fixed_costs": self.financial_service.list_effective_fixed_costs_for_month(month_text),
            "variable_costs": variable_rows,
            "card_receivables": [row for row in sales if parse_decimal(row.get("valor_taxa")) > 0 or clean_text(row.get("maquina_cartao"))],
        }

    def generate_pdf(self, month_ref=None) -> str:
        data = self.collect_data(month_ref)
        output_dir = os.path.join(get_pdfs_dir(), "contador")
        os.makedirs(output_dir, exist_ok=True)
        filename = f"relatorio_contador_{data['month_ref'].replace('/', '_')}.pdf"
        path = os.path.join(output_dir, filename)
        return build_accounting_report_pdf(path, data)
