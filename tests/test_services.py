from __future__ import annotations

from datetime import date

import pytest

from app.services.sales_service import RECEIVABLE_STATUS_DIVERGENT, RECEIVABLE_STATUS_OK
from app.utils.dates import add_business_days
from app.utils.months import normalize_month


def _create_default_machine_rule(services):
    return services.sales.create_machine(
        nome="Stone",
        conditions=[
            {
                "bandeira": "Visa",
                "modalidade": "Crédito",
                "parcelas": "1x",
                "taxa_percentual": "4",
                "taxa_fixa": "1",
                "prazo_dias_uteis": "2",
            }
        ],
    )


def _create_default_sale(services, valor="100"):
    _create_default_machine_rule(services)
    return services.sales.create_sale(
        data_venda="08/05/2026",
        descricao="Venda teste",
        valor_bruto=valor,
        maquina_cartao="Stone",
        bandeira="Visa",
        modalidade="Crédito",
        parcelas="1",
    )


def test_current_month_format():
    assert normalize_month(date(2026, 5, 7)) == "05/2026"


def test_month_validation_message_is_friendly():
    with pytest.raises(ValueError, match="Informe o mês no formato MM/AAAA"):
        normalize_month("2026/05")


def test_business_days_skip_weekend():
    assert add_business_days("08/05/2026", 2).strftime("%d/%m/%Y") == "12/05/2026"


def test_machine_is_created_once_with_many_conditions(services):
    machine = services.sales.create_machine(
        nome="Stone",
        observacoes="Máquina de Cartão principal",
        conditions=[
            {"bandeira": "Visa", "modalidade": "PIX", "parcelas": "1x", "taxa_percentual": "0", "taxa_fixa": "0", "prazo_dias_uteis": "0"},
            {"bandeira": "Visa", "modalidade": "Débito", "parcelas": "1x", "taxa_percentual": "1,99", "taxa_fixa": "0", "prazo_dias_uteis": "1"},
            {"bandeira": "Visa", "modalidade": "Crédito", "parcelas": "1x", "taxa_percentual": "3,99", "taxa_fixa": "0", "prazo_dias_uteis": "1"},
            {"bandeira": "Visa", "modalidade": "Crédito", "parcelas": "2x", "taxa_percentual": "4,50", "taxa_fixa": "0", "prazo_dias_uteis": "2"},
            {"bandeira": "Mastercard", "modalidade": "Crédito", "parcelas": "2x", "taxa_percentual": "4,40", "taxa_fixa": "0", "prazo_dias_uteis": "2"},
        ],
    )

    assert services.sales.machine_names() == ["Stone"]
    assert len(services.sales.list_machines()) == 1
    assert len(services.sales.list_conditions(machine["maquina_cartao_id"])) == 5
    assert services.sales.flags_for_machine("Stone") == ["Mastercard", "Visa"]
    assert services.sales.modalities_for_machine_flag("Stone", "Visa") == ["PIX", "Débito", "Crédito"]
    assert services.sales.installments_for_machine_flag_modality("Stone", "Visa", "Crédito") == [1, 2]


def test_duplicate_active_machine_name_is_blocked(services):
    _create_default_machine_rule(services)

    with pytest.raises(ValueError, match="Já existe uma máquina de cartão ativa"):
        services.sales.create_machine(
            nome="stone",
            conditions=[
                {"bandeira": "Visa", "modalidade": "PIX", "parcelas": "1x", "taxa_percentual": "0", "taxa_fixa": "0", "prazo_dias_uteis": "0"}
            ],
        )


def test_duplicate_condition_inside_machine_is_blocked(services):
    with pytest.raises(ValueError, match="Já existe uma condição"):
        services.sales.create_machine(
            nome="Stone",
            conditions=[
                {"bandeira": "Visa", "modalidade": "Crédito", "parcelas": "2x", "taxa_percentual": "4", "taxa_fixa": "0", "prazo_dias_uteis": "2"},
                {"bandeira": "visa", "modalidade": "credito", "parcelas": "2", "taxa_percentual": "5", "taxa_fixa": "0", "prazo_dias_uteis": "3"},
            ],
        )


def test_pix_and_debit_force_one_installment(services):
    machine = services.sales.create_machine(
        nome="Stone",
        conditions=[
            {"bandeira": "Visa", "modalidade": "PIX", "parcelas": "8x", "taxa_percentual": "0", "taxa_fixa": "0", "prazo_dias_uteis": "0"},
            {"bandeira": "Visa", "modalidade": "Débito", "parcelas": "3x", "taxa_percentual": "1", "taxa_fixa": "0", "prazo_dias_uteis": "1"},
        ],
    )

    rows = services.sales.list_conditions(machine["maquina_cartao_id"])
    assert [row["parcelas"] for row in rows] == [1, 1]


def test_credit_accepts_different_installments_and_sale_uses_correct_one(services):
    services.sales.create_machine(
        nome="Stone",
        conditions=[
            {"bandeira": "Visa", "modalidade": "Crédito", "parcelas": "1x", "taxa_percentual": "3,99", "taxa_fixa": "0", "prazo_dias_uteis": "1"},
            {"bandeira": "Visa", "modalidade": "Crédito", "parcelas": "2x", "taxa_percentual": "4,50", "taxa_fixa": "0", "prazo_dias_uteis": "2"},
        ],
    )

    result = services.sales.calculate_sale(
        data_venda="08/05/2026",
        valor_bruto="100",
        maquina_cartao="Stone",
        bandeira="Visa",
        modalidade="Crédito",
        parcelas="2x",
    )

    assert round(result["valor_taxa"], 2) == 4.5
    assert result["data_prevista_recebimento"] == "12/05/2026"

def test_sales_fee_and_net_value_calculation(services):
    _create_default_machine_rule(services)

    result = services.sales.calculate_sale(
        data_venda="08/05/2026",
        valor_bruto="100",
        maquina_cartao="Stone",
        bandeira="Visa",
        modalidade="Crédito",
    )

    assert result["valor_taxa"] == 5
    assert result["valor_liquido"] == 95
    assert result["data_prevista_recebimento"] == "12/05/2026"


def test_create_sale_creates_pending_receivable(services):
    sale = _create_default_sale(services)

    reconciliations = services.sales.list_reconciliations()

    assert sale["valor_bruto"] == 100
    assert sale["valor_taxa"] == 5
    assert sale["valor_liquido"] == 95
    assert sale["data_prevista_recebimento"] == "12/05/2026"
    assert len(reconciliations) == 1
    assert reconciliations[0]["venda_id"] == sale["venda_id"]
    assert reconciliations[0]["status"] == "pendente"


def test_cash_sale_saves_without_card_machine(services):
    sale = services.sales.create_sale(
        data_venda="08/05/2026",
        descricao="Venda em dinheiro",
        valor_bruto="100",
        forma_pagamento="Dinheiro",
    )

    assert sale["forma_pagamento"] == "Dinheiro"
    assert sale["maquina_cartao"] == ""
    assert sale["bandeira"] == ""
    assert sale["modalidade"] == "Dinheiro"
    assert sale["parcelas"] == 1
    assert sale["valor_taxa"] == 0
    assert sale["valor_liquido"] == 100
    assert sale["data_prevista_recebimento"] == "08/05/2026"
    assert services.sales.list_reconciliations() == []
    assert services.financial.list_variable_costs_for_month("05/2026") == []


def test_cash_sale_feeds_cash_flow_immediately(services):
    sale = services.sales.create_sale(
        data_venda="08/05/2026",
        descricao="Venda balcão",
        valor_bruto="150,50",
        forma_pagamento="Dinheiro",
    )

    entries = services.financial.list_cash_flow_for_month("05/2026")

    assert len(entries) == 1
    assert entries[0]["data"] == "08/05/2026"
    assert entries[0]["tipo"] == "entrada"
    assert entries[0]["categoria"] == "Venda"
    assert entries[0]["valor"] == 150.5
    assert entries[0]["status"] == "pago"
    assert entries[0]["origem"] == "venda"
    assert entries[0]["venda_id"] == sale["venda_id"]


def test_card_sale_with_payment_method_keeps_machine_flow(services):
    _create_default_machine_rule(services)

    sale = services.sales.create_sale(
        data_venda="08/05/2026",
        descricao="Venda crédito",
        valor_bruto="100",
        forma_pagamento="Máquina de Cartão",
        maquina_cartao="Stone",
        bandeira="Visa",
        modalidade="Crédito",
        parcelas="1x",
    )
    entries = services.financial.list_cash_flow_for_month("05/2026")

    assert sale["forma_pagamento"] == "Máquina de Cartão"
    assert sale["valor_taxa"] == 5
    assert sale["valor_liquido"] == 95
    assert sale["data_prevista_recebimento"] == "12/05/2026"
    assert len(services.sales.list_reconciliations()) == 1
    assert entries[0]["data"] == "12/05/2026"
    assert entries[0]["valor"] == 95


def test_credit_sale_creates_automatic_variable_cost(services):
    sale = _create_default_sale(services)

    costs = services.financial.list_variable_costs_for_month("05/2026")

    assert len(costs) == 1
    assert costs[0]["categoria"] == "Taxa de máquina de cartão"
    assert costs[0]["valor"] == 5
    assert costs[0]["origem"] == "venda"
    assert costs[0]["venda_id"] == sale["venda_id"]
    assert services.financial.total_variable_costs("05/2026") == 5


def test_debit_sale_creates_automatic_variable_cost(services):
    services.sales.create_machine(
        nome="Stone",
        conditions=[
            {"bandeira": "Visa", "modalidade": "Débito", "parcelas": "1x", "taxa_percentual": "2", "taxa_fixa": "0", "prazo_dias_uteis": "1"}
        ],
    )

    services.sales.create_sale(
        data_venda="08/05/2026",
        valor_bruto="100",
        maquina_cartao="Stone",
        bandeira="Visa",
        modalidade="Débito",
    )

    assert services.financial.total_variable_costs("05/2026") == 2


def test_pix_with_fee_creates_automatic_variable_cost(services):
    services.sales.create_machine(
        nome="Stone",
        conditions=[
            {"bandeira": "Visa", "modalidade": "PIX", "parcelas": "1x", "taxa_percentual": "1", "taxa_fixa": "0", "prazo_dias_uteis": "0"}
        ],
    )

    services.sales.create_sale(
        data_venda="08/05/2026",
        valor_bruto="100",
        maquina_cartao="Stone",
        bandeira="Visa",
        modalidade="PIX",
    )

    assert services.financial.total_variable_costs("05/2026") == 1


def test_sale_without_fee_does_not_create_variable_cost(services):
    services.sales.create_machine(
        nome="Stone",
        conditions=[
            {"bandeira": "Visa", "modalidade": "PIX", "parcelas": "1x", "taxa_percentual": "0", "taxa_fixa": "0", "prazo_dias_uteis": "0"}
        ],
    )

    services.sales.create_sale(
        data_venda="08/05/2026",
        valor_bruto="100",
        maquina_cartao="Stone",
        bandeira="Visa",
        modalidade="PIX",
    )

    assert services.financial.list_variable_costs_for_month("05/2026") == []
    assert services.financial.total_variable_costs("05/2026") == 0


def test_monthly_variable_cost_accumulates_machine_fees(services):
    services.sales.create_machine(
        nome="Stone",
        conditions=[
            {"bandeira": "Visa", "modalidade": "Crédito", "parcelas": "1x", "taxa_percentual": "4", "taxa_fixa": "0", "prazo_dias_uteis": "2"},
            {"bandeira": "Visa", "modalidade": "Débito", "parcelas": "1x", "taxa_percentual": "2", "taxa_fixa": "0", "prazo_dias_uteis": "1"},
        ],
    )
    services.sales.create_sale(data_venda="08/05/2026", valor_bruto="100", maquina_cartao="Stone", bandeira="Visa", modalidade="Crédito", parcelas="1x")
    services.sales.create_sale(data_venda="09/05/2026", valor_bruto="50", maquina_cartao="Stone", bandeira="Visa", modalidade="Débito")

    totals = {row["categoria"]: row["valor"] for row in services.financial.variable_costs_by_category("05/2026")}

    assert totals["Taxa de máquina de cartão"] == 5
    assert services.financial.total_variable_costs("05/2026") == 5


def test_machine_fee_variable_cost_is_not_duplicated(services):
    sale = _create_default_sale(services)

    services.financial.create_machine_fee_variable_cost(sale)

    costs = services.financial.list_variable_costs_for_month("05/2026")
    assert len(costs) == 1
    assert services.financial.total_variable_costs("05/2026") == 5

def test_reconciliation_correct(services):
    sale = _create_default_sale(services)

    result = services.sales.reconcile(sale["venda_id"], "95")

    assert result["status"] == RECEIVABLE_STATUS_OK
    assert result["diferenca"] == 0
    assert services.sales.received_value("05/2026") == 95


def test_reconciliation_divergent(services):
    sale = _create_default_sale(services)

    result = services.sales.reconcile(sale["venda_id"], "90")

    assert result["status"] == RECEIVABLE_STATUS_DIVERGENT
    assert result["diferenca"] == -5
    assert len(services.sales.divergent_reconciliations("05/2026")) == 1


def test_sales_summary_feeds_revenue_indicators(services):
    _create_default_sale(services)

    summary = services.sales.sales_summary("05/2026")

    assert summary["faturamento_bruto"] == 100
    assert summary["taxas"] == 5
    assert summary["faturamento_liquido"] == 95


def test_cash_flow_expected_receipts_from_sales(services):
    sale = _create_default_sale(services)
    entries = services.financial.list_cash_flow_for_month("05/2026")

    assert services.sales.expected_net_receipts("05/2026") == 95
    assert services.sales.pending_value("05/2026") == 95
    assert len(entries) == 1
    assert entries[0]["data"] == "12/05/2026"
    assert entries[0]["tipo"] == "entrada"
    assert entries[0]["categoria"] == "Venda"
    assert entries[0]["valor"] == 95
    assert entries[0]["origem"] == "venda"
    assert entries[0]["venda_id"] == sale["venda_id"]


def test_sale_cash_flow_is_not_duplicated(services):
    sale = _create_default_sale(services)

    services.financial.create_sale_cash_flow_entry(sale)

    entries = [row for row in services.financial.list_cash_flow_for_month("05/2026") if row.get("origem") == "venda"]
    assert len(entries) == 1

def test_pix_receipt_can_be_immediate(services):
    services.sales.create_machine(
        nome="Stone",
        conditions=[
            {"bandeira": "Visa", "modalidade": "PIX", "parcelas": "1x", "taxa_percentual": "0", "taxa_fixa": "0", "prazo_dias_uteis": "0"}
        ],
    )

    sale = services.sales.create_sale(
        data_venda="08/05/2026",
        descricao="Venda PIX",
        valor_bruto="100",
        maquina_cartao="Stone",
        bandeira="Visa",
        modalidade="PIX",
    )

    entries = services.financial.list_cash_flow_for_month("05/2026")

    assert sale["valor_liquido"] == 100
    assert sale["data_prevista_recebimento"] == "08/05/2026"
    assert entries[0]["data"] == "08/05/2026"
    assert entries[0]["valor"] == 100
    assert entries[0]["status"] == "pago"

def test_net_profit_calculation_from_integrated_financial_flow(services):
    services.financial.create_fixed_cost(data="05/2026", categoria="Aluguel", descricao="Aluguel", valor="1000")
    services.sales.create_machine(
        nome="Stone",
        conditions=[
            {"bandeira": "Visa", "modalidade": "PIX", "parcelas": "1x", "taxa_percentual": "0", "taxa_fixa": "0", "prazo_dias_uteis": "0"}
        ],
    )
    services.sales.create_sale(data_venda="02/05/2026", valor_bruto="2500", maquina_cartao="Stone", bandeira="Visa", modalidade="PIX")
    services.financial.create_cash_flow(
        data="03/05/2026",
        tipo="saida",
        categoria="Taxa de m" + chr(0x00e1) + "quina de cart" + chr(0x00e3) + "o",
        descricao="Taxa máquina de cartão",
        valor="300",
        status="pago",
    )

    summary = services.financial.profit_summary("05/2026")

    assert summary["lucro_bruto"] == 2200
    assert summary["lucro_liquido"] == 1200


def test_create_fixed_cost_with_month_reference(services):
    cost = services.financial.create_fixed_cost(
        data="05/2026",
        categoria="Internet",
        descricao="Plano empresarial",
        valor="150,50",
        recorrente="sim",
    )

    assert cost["custo_id"]
    assert cost["data"] == "05/2026"
    assert cost["categoria"] == "Internet"
    assert cost["valor"] == 150.5


def test_manual_cash_flow_entries_are_not_sales_categories(services):
    categories = services.financial.revenue_categories()

    assert "Vendas à vista" not in categories
    assert "Vendas no cartão" not in categories
    assert "Recebimentos futuros" not in categories
    assert "Aporte" in categories
    assert "Outros recebimentos" in categories

    with pytest.raises(ValueError, match="Vendas devem"):
        services.financial.create_cash_flow(
            data="02/05/2026",
            tipo="entrada",
            categoria="Vendas no cartão",
            descricao="Venda manual indevida",
            valor="700",
            status="pago",
        )


def test_manual_cash_flow_revenue_categories_still_work(services):
    services.financial.create_cash_flow(
        data="02/05/2026",
        tipo="entrada",
        categoria="Aporte",
        descricao="Aporte do sócio",
        valor="700",
        status="pago",
    )
    services.financial.create_cash_flow(
        data="03/05/2026",
        tipo="entrada",
        categoria="Outros recebimentos",
        descricao="Reembolso",
        valor="300",
        status="pendente",
    )

    assert services.financial.revenue("05/2026") == 1000
    totals = {row["categoria"]: row["valor"] for row in services.financial.revenue_by_category("05/2026")}
    assert totals["Aporte"] == 700
    assert totals["Outros recebimentos"] == 300


def test_cash_flow_variable_outflow_feeds_variable_costs(services):
    services.financial.create_cash_flow(
        data="10/05/2026",
        tipo="saida",
        categoria="Taxa de m" + chr(0x00e1) + "quina de cart" + chr(0x00e3) + "o",
        descricao="Taxa máquina de cartão",
        valor="100",
        status="pago",
    )
    services.financial.create_cash_flow(
        data="11/05/2026",
        tipo="saida",
        categoria="Investimentos",
        descricao="Computador",
        valor="900",
        status="pago",
    )

    assert services.financial.total_variable_costs("05/2026") == 100
    totals = {row["categoria"]: row["valor"] for row in services.financial.variable_costs_by_category("05/2026")}
    assert totals["Taxa de máquina de cartão"] == 100


def test_monthly_fixed_total(services):
    services.financial.create_fixed_cost(data="05/2026", categoria="Aluguel", descricao="Maio", valor="1000")
    services.financial.create_fixed_cost(data="06/2026", categoria="Aluguel", descricao="Junho", valor="1200")

    assert services.financial.total_fixed_costs("05/2026") == 1000

def test_sync_fixed_cost_updates_existing_month_category(services):
    services.financial.sync_fixed_costs_for_month(
        "05/2026",
        [
            {"categoria": "Aluguel", "valor": "1500"},
            {"categoria": "Internet", "valor": "120"},
        ],
    )
    services.financial.sync_fixed_costs_for_month(
        "05/2026",
        [
            {"categoria": "Aluguel", "valor": "1500"},
            {"categoria": "Internet", "valor": "150"},
        ],
    )

    rows = services.financial.list_fixed_costs_for_month("05/2026")
    totals = {row["categoria"]: row["valor"] for row in rows}

    assert len(rows) == 2
    assert totals["Aluguel"] == 1500
    assert totals["Internet"] == 150
    assert services.financial.total_fixed_costs("05/2026") == 1650


def test_sync_fixed_cost_zeroes_existing_cost_without_duplicate(services):
    services.financial.sync_fixed_costs_for_month(
        "05/2026",
        [{"categoria": "Internet", "valor": "120"}],
    )
    services.financial.sync_fixed_costs_for_month(
        "05/2026",
        [{"categoria": "Internet", "valor": "0"}],
    )

    rows = services.financial.list_fixed_costs_for_month("05/2026")

    assert len(rows) == 1
    assert rows[0]["categoria"] == "Internet"
    assert rows[0]["valor"] == 0
    assert services.financial.total_fixed_costs("05/2026") == 0


def test_sync_fixed_cost_custom_category(services):
    services.financial.sync_fixed_costs_for_month(
        "05/2026",
        [{"categoria": "Seguro", "valor": "200"}],
    )

    assert "Seguro" in services.financial.category_names("fixo")
    assert services.financial.total_fixed_costs("05/2026") == 200


def test_create_collaborator_and_partner(services):
    employee = services.collaborator.create_collaborator(nome="Ana", telefone="31999990000", tipo="colaborador", salario_base="2000")
    partner = services.collaborator.create_collaborator(nome="Bruno", tipo="sócio", salario_base="1500")

    assert employee["tipo"] == "colaborador"
    assert partner["tipo"] == "sócio"
    assert services.collaborator.employee_salary_total() == 2000
    assert services.collaborator.partner_pro_labore_total() == 1500


def test_collaborators_feed_fixed_costs(services):
    services.collaborator.create_collaborator(nome="Ana", tipo="colaborador", salario_base="2000")
    services.collaborator.create_collaborator(nome="Bruno", tipo="socio", salario_base="1500")
    services.financial.create_fixed_cost(data="05/2026", categoria="Aluguel", descricao="Aluguel", valor="500")

    rows = {row["categoria"]: row["valor"] for row in services.financial.list_effective_fixed_costs_for_month("05/2026")}

    assert rows["Salários"] == 2000
    assert rows["Pró-labore"] == 1500
    assert services.financial.total_fixed_costs("05/2026") == 4000


def test_custom_variable_category_appears_in_cash_flow_outflow_categories(services):
    services.financial.create_category("variavel", "Combustível")

    assert "Combustível" in services.financial.category_names("variavel")
    assert "Combustível" in services.financial.outflow_categories()


def test_accounts_payable_is_not_an_outflow_category(services):
    categories = services.financial.outflow_categories()

    assert "Contas a pagar" not in categories
    assert "Taxa de máquina de cartão" in categories
    assert "Aluguel" in categories
    assert "Impostos" in categories


def test_cash_balance_from_cash_flow(services):
    services.financial.create_cash_flow(data="01/05/2026", tipo="entrada", categoria="Outros recebimentos", descricao="Reembolso", valor="1000", status="pago")
    services.financial.create_cash_flow(data="02/05/2026", tipo="saida", categoria="Compras", descricao="Compra", valor="250", status="pago")

    assert services.financial.cash_summary("05/2026")["saldo_atual"] == 750


def test_custom_cost_category_is_saved(services):
    category = services.financial.create_category("fixo", "Gasto com móveis")

    assert category["nome_categoria"] == "Gasto com móveis"
    assert "Gasto com móveis" in services.financial.category_names("fixo")


def test_dashboard_integrated_sales_indicators(services):
    services.financial.create_fixed_cost(data="05/2026", categoria="Aluguel", descricao="Aluguel", valor="1000")
    services.financial.create_cash_flow(data="02/05/2026", tipo="saida", categoria="Matéria-prima", descricao="Insumos", valor="20")
    _create_default_sale(services)

    summary = services.dashboard.summary("05/2026")

    assert summary["vendas_brutas"] == 100
    assert summary["taxas_maquinas_cartao"] == 5
    assert summary["faturamento_liquido"] == 95
    assert summary["custos_fixos"] == 1000
    assert summary["custos_variaveis"] == 25
    assert summary["lucro_bruto"] == 75
    assert summary["lucro_liquido"] == -925
    assert summary["valor_liquido_a_receber"] == 95
    assert summary["recebimentos_pendentes"] == 95


def test_dashboard_includes_collaborator_fixed_costs(services):
    services.collaborator.create_collaborator(nome="Ana", tipo="colaborador", salario_base="1000")
    services.sales.create_sale(data_venda="08/05/2026", descricao="Venda dinheiro", valor_bruto="2000", forma_pagamento="Dinheiro")

    summary = services.dashboard.summary("05/2026")

    assert summary["custos_fixos"] == 1000
    assert summary["lucro_liquido"] == 1000


def test_default_variable_cost_categories_are_clean(services):
    fee_category = "Taxa de m" + chr(0x00e1) + "quina de cart" + chr(0x00e3) + "o"
    old_machine_category = "Taxa de maqui" + "ninha"
    old_card_category = "Taxa de cart" + chr(0x00e3) + "o"
    categories = services.financial.category_names("variavel")

    assert fee_category in categories
    assert old_card_category not in categories
    assert old_machine_category not in categories


def test_dashboard_break_even_is_automatic(services):
    services.financial.create_fixed_cost(data="05/2026", categoria="Aluguel", descricao="Aluguel", valor="1000")
    services.financial.create_cash_flow(data="03/05/2026", tipo="saida", categoria="Frete", descricao="Entrega", valor="2000")
    services.sales.create_machine(
        nome="Stone",
        conditions=[
            {"bandeira": "Visa", "modalidade": "PIX", "parcelas": "1x", "taxa_percentual": "0", "taxa_fixa": "0", "prazo_dias_uteis": "0"}
        ],
    )
    services.sales.create_sale(data_venda="08/05/2026", valor_bruto="5000", maquina_cartao="Stone", bandeira="Visa", modalidade="PIX")

    summary = services.dashboard.summary("05/2026")

    assert round(summary["ponto_equilibrio"], 2) == 1666.67


def test_dashboard_month_summary_calculates_core_indicators(services):
    services.collaborator.create_collaborator(nome="Ana", tipo="colaborador", salario_base="1000")
    services.collaborator.create_collaborator(nome="Bruno", tipo="sócio", salario_base="500")
    services.financial.create_fixed_cost(data="05/2026", categoria="Aluguel", descricao="Aluguel", valor="500")
    services.financial.create_cash_flow(data="03/05/2026", tipo="saida", categoria="Frete", descricao="Entrega", valor="400")
    services.sales.create_sale(data_venda="08/05/2026", descricao="Venda dinheiro", valor_bruto="3000", forma_pagamento="Dinheiro")

    summary = services.dashboard.get_month_summary("05/2026")

    assert summary["vendas_brutas"] == 3000
    assert summary["custos_variaveis"] == 400
    assert summary["custos_fixos"] == 2000
    assert summary["lucro_liquido"] == 600
    assert round(summary["ponto_equilibrio"], 2) == 2307.69
    assert summary["produtividade"] == 1300


def test_dashboard_productivity_is_none_without_occupied_people(services):
    services.sales.create_sale(data_venda="08/05/2026", descricao="Venda dinheiro", valor_bruto="1000", forma_pagamento="Dinheiro")

    summary = services.dashboard.get_month_summary("05/2026")

    assert summary["numero_pessoas_ocupadas"] == 0
    assert summary["produtividade"] is None


def test_dashboard_break_even_is_not_calculable_without_revenue(services):
    services.financial.create_fixed_cost(data="05/2026", categoria="Aluguel", descricao="Aluguel", valor="1000")

    summary = services.dashboard.get_month_summary("05/2026")

    assert summary["ponto_equilibrio"] == 0
    assert summary["ponto_equilibrio_calculavel"] is False


def test_dashboard_accepts_month_without_data(services):
    summary = services.dashboard.get_month_summary("12/2030")

    assert summary["vendas_brutas"] == 0
    assert summary["custos_variaveis"] == 0
    assert summary["custos_fixos"] == 0
    assert summary["lucro_liquido"] == 0
    assert summary["ponto_equilibrio_calculavel"] is False
    assert services.dashboard.get_expense_distribution("12/2030") == []


def test_dashboard_expense_distribution_groups_categories(services):
    services.collaborator.create_collaborator(nome="Ana", tipo="colaborador", salario_base="1000")
    services.collaborator.create_collaborator(nome="Bruno", tipo="sócio", salario_base="500")
    services.financial.create_fixed_cost(data="05/2026", categoria="Aluguel", descricao="Aluguel", valor="700")
    services.financial.create_cash_flow(data="03/05/2026", tipo="saida", categoria="Matéria-prima", descricao="Insumo", valor="200")
    services.financial.create_cash_flow(data="04/05/2026", tipo="saida", categoria="Frete", descricao="Entrega", valor="100")

    distribution = {row["categoria"]: row["valor"] for row in services.dashboard.get_expense_distribution("05/2026")}

    assert distribution["Funcionários"] == 1500
    assert distribution["Custos fixos"] == 700
    assert distribution["Insumos"] == 200
    assert distribution["Custos variáveis"] == 100


def test_dashboard_productivity_last_6_months(services):
    services.collaborator.create_collaborator(nome="Ana", tipo="colaborador", salario_base="1000")
    services.sales.create_sale(data_venda="10/03/2026", descricao="Venda março", valor_bruto="900", forma_pagamento="Dinheiro")
    services.sales.create_sale(data_venda="08/05/2026", descricao="Venda maio", valor_bruto="1000", forma_pagamento="Dinheiro")
    services.financial.create_cash_flow(data="09/05/2026", tipo="saida", categoria="Frete", descricao="Entrega", valor="200")

    rows = services.dashboard.get_productivity_last_6_months("05/2026")
    values = {row["mes"]: row["produtividade"] for row in rows}

    assert [row["mes"] for row in rows] == ["12/2025", "01/2026", "02/2026", "03/2026", "04/2026", "05/2026"]
    assert values["03/2026"] == 900
    assert values["05/2026"] == 800

def test_sidebar_final_scope_has_only_active_main_menus():
    import inspect

    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow._build_content)
    assert "Dashboard" in source
    assert "Vendas / Entradas" in source
    assert "Fluxo de Caixa" in source
    assert "Custo Fixo" in source
    assert ("Custo Vari" + chr(0x00e1) + "vel") in source or "Custo Vari\\u00e1vel" in source
    assert "Colaboradores" in source
    assert "Clientes" not in source
    assert "Precifica" + chr(0x00e7) + chr(0x00e3) + "o" not in source
    assert "Faturamento" not in source
    assert "Ponto de Equil" + chr(0x00ed) + "brio" not in source


def test_accounting_report_pdf_is_generated_for_selected_month(services):
    from pathlib import Path

    services.financial.create_fixed_cost(data="05/2026", categoria="Aluguel", descricao="Aluguel", valor="1000")
    services.sales.create_sale(data_venda="08/05/2026", descricao="Venda dinheiro", valor_bruto="500", forma_pagamento="Dinheiro")

    path = Path(services.accounting_report.generate_pdf("05/2026"))
    data = services.accounting_report.collect_data("05/2026")

    assert path.exists()
    assert path.parent.name == "contador"
    assert path.name == "relatorio_contador_05_2026.pdf"
    assert path.stat().st_size > 0
    assert data["month_ref"] == "05/2026"
    assert data["summary"]["faturamento_bruto"] == 500
    assert data["summary"]["custos_fixos"] == 1000
    assert data["summary"]["lucro_liquido"] == -500


def test_accounting_report_pdf_handles_empty_sections(services):
    from pathlib import Path

    path = Path(services.accounting_report.generate_pdf("06/2026"))
    data = services.accounting_report.collect_data("06/2026")

    assert path.exists()
    assert path.stat().st_size > 0
    assert data["sales"] == []
    assert data["cash_flow"] == []
    assert data["fixed_costs"] == []
    assert data["variable_costs"] == []
