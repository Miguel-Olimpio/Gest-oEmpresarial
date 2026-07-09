"""Regras de vendas, máquinas de cartão e conferencia de recebiveis."""

from __future__ import annotations

import uuid
import unicodedata
from typing import TYPE_CHECKING

from app.models.sales import CardMachine, CardMachineCondition, ReceivableReconciliation, Sale
from app.repositories.sales_repository import SalesRepository
from app.utils.dates import add_business_days, format_date, parse_date
from app.utils.formatting import clean_text
from app.utils.months import same_month
from app.utils.numbers import parse_decimal
from app.utils.validators import required_text

if TYPE_CHECKING:
    from app.services.financial_service import FinancialService

RECEIVABLE_STATUS_PENDING = "pendente"
RECEIVABLE_STATUS_OK = "correto"
RECEIVABLE_STATUS_DIVERGENT = "divergente"

CARD_FLAGS = ("Visa", "Mastercard", "Elo", "Amex", "Hipercard", "Outros")
CARD_MODALITIES = ("PIX", "Débito", "Crédito")
MAX_INSTALLMENTS = 12
PAYMENT_CASH = "Dinheiro"
PAYMENT_CARD = "Máquina de Cartão"


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_payment_method(value) -> str:
    text = clean_text(value) or PAYMENT_CARD
    normalized = _strip_accents(text).lower()
    if normalized == "dinheiro":
        return PAYMENT_CASH
    if normalized in {"maquina de cartao", "cartao"}:
        return PAYMENT_CARD
    raise ValueError("Forma de pagamento inválida. Use Dinheiro ou Máquina de Cartão.")

def _is_cash_payment(value) -> bool:
    return _normalize_payment_method(value) == PAYMENT_CASH

def _has_value(value) -> bool:
    return value is not None and str(value).strip() != ""
def _active(value) -> bool:
    if isinstance(value, str):
        return clean_text(value).lower() not in {"false", "0", "não", "nao", "inativo"}
    return bool(value if value != "" else True)


def _normalize_flag(value) -> str:
    text = required_text(value, "Bandeira")
    for flag in CARD_FLAGS:
        if clean_text(flag).lower() == clean_text(text).lower():
            return flag
    raise ValueError("Bandeira inválida. Use Visa, Mastercard, Elo, Amex, Hipercard ou Outros.")


def _normalize_modality(value) -> str:
    text = required_text(value, "Modalidade")
    normalized = clean_text(text).lower().replace("é", "e")
    mapping = {"pix": "PIX", "debito": "Débito", "credito": "Crédito"}
    if normalized not in mapping:
        raise ValueError("Modalidade inválida. Use PIX, Débito ou Crédito.")
    return mapping[normalized]


def _parse_installments(value, modality: str) -> int:
    if modality != "Crédito":
        return 1
    text = clean_text(value).lower().replace("x", "")
    installments = int(parse_decimal(text or 1))
    if installments < 1 or installments > MAX_INSTALLMENTS:
        raise ValueError(f"Parcelas de crédito devem estar entre 1x e {MAX_INSTALLMENTS}x.")
    return installments


def _condition_key(row: dict) -> tuple[str, str, int]:
    modality = _normalize_modality(row.get("modalidade"))
    return (
        clean_text(row.get("bandeira")).lower(),
        modality.lower(),
        _parse_installments(row.get("parcelas"), modality),
    )


class SalesService:
    def __init__(self, repository: SalesRepository | None = None, financial_service: "FinancialService | None" = None):
        self.repository = repository or SalesRepository()
        self.financial_service = financial_service

    def card_flags(self) -> list[str]:
        return list(CARD_FLAGS)

    def card_modalities(self) -> list[str]:
        return list(CARD_MODALITIES)

    def installment_options(self) -> list[str]:
        return [f"{value}x" for value in range(1, MAX_INSTALLMENTS + 1)]

    def normalize_condition_data(self, data: dict, maquina_cartao_id: str = "") -> dict:
        flag = _normalize_flag(data.get("bandeira"))
        modality = _normalize_modality(data.get("modalidade"))
        installments = _parse_installments(data.get("parcelas"), modality)
        if not _has_value(data.get("taxa_percentual")):
            raise ValueError("Taxa percentual é obrigatória.")
        if not _has_value(data.get("prazo_dias_uteis")):
            raise ValueError("Prazo de recebimento é obrigatório.")
        rate = parse_decimal(data.get("taxa_percentual"))
        fixed_fee = parse_decimal(data.get("taxa_fixa"), 0)
        days_value = parse_decimal(data.get("prazo_dias_uteis"))
        days = int(days_value)
        if days_value != days:
            raise ValueError("Prazo de recebimento deve ser um número inteiro de dias úteis.")
        if rate < 0 or fixed_fee < 0 or days < 0:
            raise ValueError("Taxas e prazo não podem ser negativos.")
        return {
            "condicao_id": clean_text(data.get("condicao_id")) or uuid.uuid4().hex[:12],
            "maquina_cartao_id": maquina_cartao_id or clean_text(data.get("maquina_cartao_id")),
            "bandeira": flag,
            "modalidade": modality,
            "parcelas": installments,
            "taxa_percentual": rate,
            "taxa_fixa": fixed_fee,
            "prazo_dias_uteis": days,
            "active": _active(data.get("active", True)),
        }

    def _normalize_machine_row(self, row: dict) -> dict:
        return {
            "maquina_cartao_id": clean_text(row.get("maquina_cartao_id") or row.get("maquina_cartao_config_id")),
            "nome": clean_text(row.get("nome") or row.get("nome_maquina_cartao")),
            "observacoes": clean_text(row.get("observacoes")),
            "active": _active(row.get("active", True)),
            "data_cadastro": clean_text(row.get("data_cadastro")),
            "data_atualizacao": clean_text(row.get("data_atualizacao")),
        }

    def _normalize_condition_row(self, row: dict) -> dict:
        return self.normalize_condition_data(row, clean_text(row.get("maquina_cartao_id")))

    def list_machines(self, active_only: bool = True) -> list[dict]:
        rows = [self._normalize_machine_row(row) for row in self.repository.list_machines()]
        deduped: dict[str, dict] = {}
        for row in rows:
            if not row.get("nome"):
                continue
            key = clean_text(row.get("nome")).lower()
            if key not in deduped:
                deduped[key] = row
        values = list(deduped.values())
        if active_only:
            values = [row for row in values if _active(row.get("active", True))]
        return sorted(values, key=lambda row: clean_text(row.get("nome")).lower())

    def get_machine(self, maquina_cartao_id: str) -> dict | None:
        for row in self.list_machines(active_only=False):
            if str(row.get("maquina_cartao_id", "")) == str(maquina_cartao_id):
                return row
        return None

    def find_machine_by_name(self, name: str) -> dict | None:
        wanted = clean_text(name).lower()
        for row in self.list_machines():
            if clean_text(row.get("nome")).lower() == wanted:
                return row
        return None

    def list_conditions(self, maquina_cartao_id: str | None = None, active_only: bool = True) -> list[dict]:
        rows = []
        for row in self.repository.list_conditions():
            try:
                normalized = self._normalize_condition_row(row)
            except ValueError:
                continue
            if maquina_cartao_id and str(normalized.get("maquina_cartao_id")) != str(maquina_cartao_id):
                continue
            if active_only and not _active(normalized.get("active", True)):
                continue
            rows.append(normalized)
        return rows

    def _validate_unique_machine_name(self, name: str, current_id: str = "") -> None:
        wanted = clean_text(name).lower()
        for row in self.list_machines(active_only=True):
            if str(row.get("maquina_cartao_id", "")) == str(current_id):
                continue
            if clean_text(row.get("nome")).lower() == wanted:
                raise ValueError("Já existe uma máquina de cartão ativa com este nome.")

    def _normalize_conditions_for_machine(self, maquina_cartao_id: str, conditions: list[dict]) -> list[dict]:
        if not conditions:
            raise ValueError("Informe pelo menos uma condição da maquina_cartao.")
        normalized = [self.normalize_condition_data(row, maquina_cartao_id) for row in conditions]
        keys: set[tuple[str, str, int]] = set()
        for row in normalized:
            key = _condition_key(row)
            if key in keys:
                raise ValueError("Já existe uma condição para esta bandeira, modalidade e parcelas nesta máquina de cartão.")
            keys.add(key)
        return normalized

    def create_machine(self, *, nome, observacoes="", active=True, conditions: list[dict] | None = None) -> dict:
        name = required_text(nome, "Nome da máquina de cartão")
        self._validate_unique_machine_name(name)
        machine_id = uuid.uuid4().hex[:12]
        now_text = format_date()
        condition_rows = self._normalize_conditions_for_machine(machine_id, conditions or [])
        machine = CardMachine(
            maquina_cartao_id=machine_id,
            nome=name,
            observacoes=clean_text(observacoes),
            active=bool(active),
            data_cadastro=now_text,
            data_atualizacao=now_text,
        )
        saved = self.repository.add_machine(machine.to_dict())
        self.repository.replace_conditions_for_machine(machine_id, condition_rows)
        return saved

    def update_machine(self, maquina_cartao_id: str, *, nome, observacoes="", active=True, conditions: list[dict] | None = None) -> dict:
        if not self.get_machine(maquina_cartao_id):
            raise KeyError("Máquina de Cartão não encontrada.")
        name = required_text(nome, "Nome da máquina de cartão")
        self._validate_unique_machine_name(name, maquina_cartao_id)
        condition_rows = self._normalize_conditions_for_machine(maquina_cartao_id, conditions or [])
        saved = self.repository.update_machine(
            maquina_cartao_id,
            {
                "nome": name,
                "observacoes": clean_text(observacoes),
                "active": bool(active),
                "data_atualizacao": format_date(),
            },
        )
        self.repository.replace_conditions_for_machine(maquina_cartao_id, condition_rows)
        return saved

    def inactivate_machine(self, maquina_cartao_id: str) -> dict:
        saved = self.repository.update_machine(maquina_cartao_id, {"active": False, "data_atualizacao": format_date()})
        self.repository.update_conditions_for_machine(maquina_cartao_id, {"active": False})
        return saved

    def create_machine_rule(self, **data) -> dict:
        """Compatibilidade: cria a máquina de cartão se não existir e adiciona uma condição."""
        name = required_text(data.get("nome_maquina_cartao") or data.get("nome"), "Nome da máquina de cartão")
        existing = self.find_machine_by_name(name)
        condition = self.normalize_condition_data(data, existing.get("maquina_cartao_id") if existing else "")
        if not existing:
            return self.create_machine(nome=name, observacoes=data.get("observacoes", ""), conditions=[condition])
        conditions = self.list_conditions(existing["maquina_cartao_id"])
        conditions.append(condition)
        self.update_machine(existing["maquina_cartao_id"], nome=existing["nome"], observacoes=existing.get("observacoes", ""), conditions=conditions)
        return condition

    def list_machine_rules(self) -> list[dict]:
        rows = []
        machines = {str(row.get("maquina_cartao_id")): row for row in self.list_machines()}
        for condition in self.list_conditions():
            machine = machines.get(str(condition.get("maquina_cartao_id")))
            if not machine:
                continue
            merged = dict(condition)
            merged["nome_maquina_cartao"] = machine.get("nome", "")
            rows.append(merged)
        return rows

    def machine_names(self) -> list[str]:
        return [str(row.get("nome", "")) for row in self.list_machines() if row.get("nome")]

    def flags_for_machine(self, machine_name: str) -> list[str]:
        machine = self.find_machine_by_name(machine_name)
        if not machine:
            return []
        return sorted({str(row.get("bandeira", "")) for row in self.list_conditions(machine["maquina_cartao_id"]) if row.get("bandeira")})

    def modalities_for_machine_flag(self, machine_name: str, flag: str) -> list[str]:
        machine = self.find_machine_by_name(machine_name)
        if not machine:
            return []
        available = {
            clean_text(row.get("modalidade")).lower()
            for row in self.list_conditions(machine["maquina_cartao_id"])
            if clean_text(row.get("bandeira")).lower() == clean_text(flag).lower()
        }
        return [modality for modality in CARD_MODALITIES if clean_text(modality).lower() in available]

    def installments_for_machine_flag_modality(self, machine_name: str, flag: str, modality: str) -> list[int]:
        normalized_modality = _normalize_modality(modality)
        if normalized_modality != "Crédito":
            return [1]
        machine = self.find_machine_by_name(machine_name)
        if not machine:
            return []
        values = sorted(
            {
                int(row.get("parcelas", 1))
                for row in self.list_conditions(machine["maquina_cartao_id"])
                if clean_text(row.get("bandeira")).lower() == clean_text(flag).lower()
                and clean_text(row.get("modalidade")).lower() == clean_text(normalized_modality).lower()
            }
        )
        return values

    def find_condition(self, machine_name: str, flag: str, modality: str, installments=1) -> dict | None:
        machine = self.find_machine_by_name(machine_name)
        if not machine:
            return None
        normalized_modality = _normalize_modality(modality)
        wanted_installments = _parse_installments(installments, normalized_modality)
        for row in self.list_conditions(machine["maquina_cartao_id"]):
            if clean_text(row.get("bandeira")).lower() != clean_text(flag).lower():
                continue
            if clean_text(row.get("modalidade")).lower() != clean_text(normalized_modality).lower():
                continue
            if int(row.get("parcelas", 1)) != wanted_installments:
                continue
            return row
        return None

    def calculate_sale(self, *, data_venda, valor_bruto, maquina_cartao="", bandeira="", modalidade="", parcelas=1, forma_pagamento=PAYMENT_CARD) -> dict:
        sale_date = parse_date(str(data_venda))
        gross = parse_decimal(valor_bruto)
        if gross <= 0:
            raise ValueError("Valor bruto deve ser maior que zero.")
        payment_method = _normalize_payment_method(forma_pagamento)
        if payment_method == PAYMENT_CASH:
            return {
                "forma_pagamento": PAYMENT_CASH,
                "taxa_percentual": 0.0,
                "taxa_fixa": 0.0,
                "prazo_dias_uteis": 0,
                "valor_taxa": 0.0,
                "valor_liquido": gross,
                "data_prevista_recebimento": format_date(sale_date),
                "parcelas": 1,
            }
        condition = self.find_condition(maquina_cartao, bandeira, modalidade, parcelas)
        if not condition:
            raise ValueError("Condição de máquina de cartão não encontrada para esta bandeira/modalidade/parcelas.")
        percent = parse_decimal(condition.get("taxa_percentual"))
        fixed = parse_decimal(condition.get("taxa_fixa"))
        days = int(parse_decimal(condition.get("prazo_dias_uteis")))
        fee = gross * (percent / 100) + fixed
        net = gross - fee
        expected_date = add_business_days(sale_date, days)
        return {
            "forma_pagamento": PAYMENT_CARD,
            "taxa_percentual": percent,
            "taxa_fixa": fixed,
            "prazo_dias_uteis": days,
            "valor_taxa": fee,
            "valor_liquido": net,
            "data_prevista_recebimento": format_date(expected_date),
            "parcelas": _parse_installments(parcelas, _normalize_modality(modalidade)),
        }

    def create_sale(self, **data) -> dict:
        calc = self.calculate_sale(
            data_venda=data.get("data_venda"),
            valor_bruto=data.get("valor_bruto"),
            maquina_cartao=data.get("maquina_cartao"),
            bandeira=data.get("bandeira"),
            modalidade=data.get("modalidade"),
            parcelas=data.get("parcelas", 1),
            forma_pagamento=data.get("forma_pagamento", PAYMENT_CARD),
        )
        is_cash = calc["forma_pagamento"] == PAYMENT_CASH
        sale = Sale(
            venda_id=uuid.uuid4().hex[:12],
            data_venda=format_date(str(data.get("data_venda"))),
            descricao=clean_text(data.get("descricao")),
            valor_bruto=parse_decimal(data.get("valor_bruto")),
            forma_pagamento=calc["forma_pagamento"],
            maquina_cartao="" if is_cash else required_text(data.get("maquina_cartao"), "Máquina de Cartão"),
            bandeira="" if is_cash else _normalize_flag(data.get("bandeira")),
            modalidade=PAYMENT_CASH if is_cash else _normalize_modality(data.get("modalidade")),
            parcelas=calc["parcelas"],
            taxa_percentual=calc["taxa_percentual"],
            taxa_fixa=calc["taxa_fixa"],
            valor_taxa=calc["valor_taxa"],
            valor_liquido=calc["valor_liquido"],
            data_prevista_recebimento=calc["data_prevista_recebimento"],
            status_recebimento=RECEIVABLE_STATUS_OK if is_cash else RECEIVABLE_STATUS_PENDING,
            observacoes=clean_text(data.get("observacoes")),
        )
        saved = self.repository.add_sale(sale.to_dict())
        if not is_cash:
            reconciliation = ReceivableReconciliation(
                conferencia_id=uuid.uuid4().hex[:12],
                venda_id=saved["venda_id"],
                data_prevista=saved["data_prevista_recebimento"],
                valor_esperado=saved["valor_liquido"],
                status=RECEIVABLE_STATUS_PENDING,
            )
            self.repository.add_reconciliation(reconciliation.to_dict())
        if self.financial_service is not None:
            if not is_cash:
                self.financial_service.create_machine_fee_variable_cost(saved)
            self.financial_service.create_sale_cash_flow_entry(saved)
        return saved

    def list_sales(self) -> list[dict]:
        return self.repository.list_sales()

    def list_sales_for_month(self, month_ref=None) -> list[dict]:
        return [row for row in self.list_sales() if same_month(row.get("data_venda"), month_ref)]

    def list_reconciliations(self) -> list[dict]:
        return self.repository.list_reconciliations()

    def pending_reconciliations(self) -> list[dict]:
        return [row for row in self.list_reconciliations() if clean_text(row.get("status")).lower() == RECEIVABLE_STATUS_PENDING]

    def reconcile(self, venda_id: str, valor_recebido) -> dict:
        received = parse_decimal(valor_recebido)
        target = None
        for row in self.list_reconciliations():
            if str(row.get("venda_id", "")) == str(venda_id):
                target = row
                break
        if not target:
            raise KeyError("Conferência não encontrada para esta venda.")
        expected = parse_decimal(target.get("valor_esperado"))
        diff = received - expected
        status = RECEIVABLE_STATUS_OK if abs(diff) < 0.01 else RECEIVABLE_STATUS_DIVERGENT
        updated = self.repository.update_reconciliation(
            str(target.get("conferencia_id")),
            {"valor_recebido": received, "diferenca": diff, "status": status},
        )
        self.repository.update_sale(venda_id, {"status_recebimento": status})
        if self.financial_service is not None:
            self.financial_service.mark_sale_cash_flow_received(venda_id, received)
        return updated

    def sales_summary(self, month_ref=None) -> dict:
        rows = self.list_sales_for_month(month_ref)
        gross = sum(parse_decimal(row.get("valor_bruto")) for row in rows)
        fees = sum(parse_decimal(row.get("valor_taxa")) for row in rows)
        net = sum(parse_decimal(row.get("valor_liquido")) for row in rows)
        return {"faturamento_bruto": gross, "taxas": fees, "faturamento_liquido": net}

    def sales_by_field(self, field: str, month_ref=None) -> list[dict]:
        totals: dict[str, float] = {}
        for row in self.list_sales_for_month(month_ref):
            key = str(row.get(field, "") or "Sem informação")
            totals[key] = totals.get(key, 0.0) + parse_decimal(row.get("valor_liquido"))
        return [{"nome": name, "valor": value} for name, value in sorted(totals.items())]

    def reconciliation_rows(self) -> list[dict]:
        sales_by_id = {str(row.get("venda_id")): row for row in self.list_sales()}
        rows = []
        for rec in self.list_reconciliations():
            merged = dict(rec)
            merged.update({f"venda_{key}": value for key, value in sales_by_id.get(str(rec.get("venda_id")), {}).items()})
            rows.append(merged)
        return rows

    def expected_receipts_for_month(self, month_ref=None) -> list[dict]:
        return [row for row in self.reconciliation_rows() if same_month(row.get("data_prevista"), month_ref)]

    def expected_net_receipts(self, month_ref=None) -> float:
        return sum(parse_decimal(row.get("valor_esperado")) for row in self.expected_receipts_for_month(month_ref))

    def received_value(self, month_ref=None) -> float:
        return sum(parse_decimal(row.get("valor_recebido")) for row in self.expected_receipts_for_month(month_ref))

    def pending_value(self, month_ref=None) -> float:
        return sum(
            parse_decimal(row.get("valor_esperado"))
            for row in self.expected_receipts_for_month(month_ref)
            if clean_text(row.get("status")).lower() == RECEIVABLE_STATUS_PENDING
        )

    def divergent_reconciliations(self, month_ref=None) -> list[dict]:
        return [
            row
            for row in self.expected_receipts_for_month(month_ref)
            if clean_text(row.get("status")).lower() == RECEIVABLE_STATUS_DIVERGENT
        ]



