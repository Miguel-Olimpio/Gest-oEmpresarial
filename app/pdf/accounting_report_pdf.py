"""PDF consolidado para contador."""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.utils.formatting import format_money


def _paragraph(text, style):
    return Paragraph(str(text or ""), style)


def _money(value) -> str:
    return format_money(value or 0)


def build_accounting_report_pdf(path: str, data: dict) -> str:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleBlue",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0B5CAB"),
        fontSize=18,
        leading=22,
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "SectionBlue",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#0B5CAB"),
        fontSize=12,
        leading=15,
        spaceBefore=12,
        spaceAfter=6,
    )
    normal = ParagraphStyle("Cell", parent=styles["BodyText"], fontSize=7.5, leading=9)
    header = ParagraphStyle("Header", parent=normal, alignment=TA_CENTER, textColor=colors.white, fontName="Helvetica-Bold")

    doc = SimpleDocTemplate(
        path,
        pagesize=landscape(A4),
        leftMargin=1 * cm,
        rightMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )
    story = [
        Paragraph("Relatório Financeiro para Contador", title_style),
        Paragraph(f"Mês/ano: {data['month_ref']}<br/>Data de geração: {data['generated_at']}", normal),
        Spacer(1, 8),
    ]

    def add_section(title: str, headers: list[str], rows: list[list], widths: list[float] | None = None):
        story.append(Paragraph(title, section_style))
        if not rows:
            story.append(Paragraph("Nenhum registro encontrado para este período.", normal))
            story.append(Spacer(1, 6))
            return
        table_rows = [[_paragraph(col, header) for col in headers]]
        table_rows.extend([[_paragraph(value, normal) for value in row] for row in rows])
        table = Table(table_rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B5CAB")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D0D7E2")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F8FC")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 8))

    summary = data["summary"]
    add_section(
        "Resumo do mês",
        ["Indicador", "Valor"],
        [
            ["Faturamento bruto", _money(summary["faturamento_bruto"])],
            ["Taxas de máquina de cartão", _money(summary["taxas_maquinas_cartao"])],
            ["Custos fixos", _money(summary["custos_fixos"])],
            ["Custos variáveis", _money(summary["custos_variaveis"])],
            ["Entradas totais", _money(summary["entradas_totais"])],
            ["Saídas totais", _money(summary["saidas_totais"])],
            ["Saldo de caixa", _money(summary["saldo_caixa"])],
            ["Lucro líquido estimado", _money(summary["lucro_liquido"])],
        ],
        [8 * cm, 5 * cm],
    )
    add_section(
        "Vendas / Entradas",
        ["Data", "Descrição", "Forma", "Bruto", "Taxa", "Líquido", "Recebimento"],
        [[row.get("data_venda", ""), row.get("descricao", ""), row.get("forma_pagamento", ""), _money(row.get("valor_bruto")), _money(row.get("valor_taxa")), _money(row.get("valor_liquido")), row.get("data_prevista_recebimento", "")] for row in data["sales"]],
        [2.2 * cm, 6.0 * cm, 3.2 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm, 3.0 * cm],
    )
    add_section(
        "Fluxo de Caixa",
        ["Data", "Tipo", "Categoria", "Descrição", "Valor", "Status", "Origem"],
        [[row.get("data", ""), row.get("tipo", ""), row.get("categoria", ""), row.get("descricao", ""), _money(row.get("valor")), row.get("status", ""), row.get("origem", "")] for row in data["cash_flow"]],
        [2.0 * cm, 2.0 * cm, 4.0 * cm, 6.0 * cm, 2.4 * cm, 2.3 * cm, 2.4 * cm],
    )
    add_section(
        "Custos Fixos",
        ["Mês", "Categoria", "Valor"],
        [[row.get("data", ""), row.get("categoria", ""), _money(row.get("valor"))] for row in data["fixed_costs"]],
        [3 * cm, 8 * cm, 3 * cm],
    )
    add_section(
        "Custos Variáveis",
        ["Mês/Data", "Categoria", "Valor", "Origem"],
        [[row.get("data", ""), row.get("categoria", ""), _money(row.get("valor")), row.get("origem", "")] for row in data["variable_costs"]],
        [3 * cm, 8 * cm, 3 * cm, 3 * cm],
    )
    add_section(
        "Máquinas de Cartão / Recebíveis",
        ["Máquina", "Bandeira", "Modalidade", "Bruto", "Taxa", "Líquido", "Data prevista", "Status"],
        [[row.get("maquina_cartao", ""), row.get("bandeira", ""), row.get("modalidade", ""), _money(row.get("valor_bruto")), _money(row.get("valor_taxa")), _money(row.get("valor_liquido")), row.get("data_prevista_recebimento", ""), row.get("status_recebimento", "")] for row in data["card_receivables"]],
        [3.2 * cm, 2.5 * cm, 2.5 * cm, 2.3 * cm, 2.3 * cm, 2.3 * cm, 3.0 * cm, 2.4 * cm],
    )
    doc.build(story)
    return path
