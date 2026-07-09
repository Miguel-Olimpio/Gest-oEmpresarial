"""Tela de fluxo de caixa."""

from __future__ import annotations

from tkinter import messagebox

import ttkbootstrap as ttk

from app.services.financial_service import FinancialService
from app.services.sales_service import SalesService
from app.ui.components import configure_treeview, help_label, section_title
from app.utils.dates import format_date, parse_date
from app.utils.formatting import format_money
from app.utils.months import month_options, normalize_month
from app.utils.numbers import parse_decimal


class CashFlowPanel(ttk.Frame):
    def __init__(self, master, financial_service: FinancialService, sales_service: SalesService):
        super().__init__(master, padding=18)
        self.financial_service = financial_service
        self.sales_service = sales_service
        section_title(
            self,
            "Fluxo de Caixa",
            "Venda hoje não significa dinheiro hoje. O caixa usa a data prevista ou real de recebimento.",
        ).pack(fill="x", pady=(0, 12))
        self._build()
        self.refresh()

    def _build(self) -> None:
        form = ttk.Labelframe(self, text="Novo lançamento manual", padding=12)
        form.pack(fill="x", pady=(0, 12))
        for col in range(4):
            form.columnconfigure(col, weight=1)

        self.data_entry = self._field(form, "Data", 0, 0, default=format_date())
        self.tipo_entry = ttk.Combobox(form, values=["entrada", "saída"], state="readonly")
        self.tipo_entry.set("entrada")
        self._place_field(form, "Tipo", self.tipo_entry, 0, 1)
        self.tipo_entry.bind("<<ComboboxSelected>>", lambda _event: self._update_categories())

        self.categoria_entry = ttk.Combobox(form, values=self.financial_service.revenue_categories())
        self.categoria_entry.set(self.financial_service.revenue_categories()[0])
        self._place_field(form, "Categoria", self.categoria_entry, 0, 2)

        self.valor_entry = self._field(form, "Valor", 0, 3)
        self.descricao_entry = self._field(form, "Descrição", 2, 0, columnspan=2)
        self.status_entry = ttk.Combobox(form, values=["pago", "pendente", "vencido"], state="readonly")
        self.status_entry.set("pago")
        self._place_field(form, "Status", self.status_entry, 2, 2)
        self.observacoes_entry = self._field(form, "Observações", 2, 3)

        footer = ttk.Frame(form)
        footer.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        ttk.Button(footer, text="Salvar lançamento", bootstyle="primary", command=self.save_entry).pack(side="right")
        help_label(footer, "Recebíveis de vendas aparecem automaticamente pela data prevista de repasse.", 650).pack(side="left", fill="x")

        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(filter_frame, text="Mês da listagem:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.month_entry = ttk.Combobox(filter_frame, values=month_options(), width=12)
        self.month_entry.set(normalize_month())
        self.month_entry.pack(side="left", padx=(8, 0))
        self.month_entry.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        self.month_entry.bind("<FocusOut>", lambda _event: self.refresh())
        self.summary_label = ttk.Label(filter_frame, text="", font=("Segoe UI", 10, "bold"), bootstyle="primary")
        self.summary_label.pack(side="right")

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(table_frame, height=13)
        configure_treeview(
            self.tree,
            [
                ("data", "Data", 100),
                ("tipo", "Tipo", 120),
                ("categoria", "Categoria", 200),
                ("descricao", "Descrição", 220),
                ("valor", "Valor", 110),
                ("status", "Status", 100),
                ("origem", "Origem", 100),
            ],
        )
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

    def _field(self, parent, label: str, row: int, col: int, *, default: str = "", columnspan: int = 1):
        entry = ttk.Entry(parent)
        entry.insert(0, default)
        self._place_field(parent, label, entry, row, col, columnspan=columnspan)
        return entry

    def _place_field(self, parent, label: str, widget, row: int, col: int, *, columnspan: int = 1) -> None:
        ttk.Label(parent, text=label, font=("Segoe UI", 9, "bold")).grid(row=row, column=col, sticky="w", padx=5, pady=(0, 2))
        widget.grid(row=row + 1, column=col, columnspan=columnspan, sticky="ew", padx=5, pady=(0, 8))

    def _update_categories(self) -> None:
        if self.tipo_entry.get() == "entrada":
            values = self.financial_service.revenue_categories()
        else:
            values = self.financial_service.outflow_categories()
        self.categoria_entry.configure(values=values)
        if values:
            self.categoria_entry.set(values[0])

    def save_entry(self) -> None:
        try:
            parse_date(self.data_entry.get())
            parse_decimal(self.valor_entry.get())
            self.financial_service.create_cash_flow(
                data=self.data_entry.get(),
                tipo=self.tipo_entry.get(),
                categoria=self.categoria_entry.get(),
                descricao=self.descricao_entry.get(),
                valor=self.valor_entry.get(),
                status=self.status_entry.get(),
                observacoes=self.observacoes_entry.get(),
            )
        except Exception as exc:
            messagebox.showerror("Não foi possível salvar", str(exc), parent=self)
            return
        self.valor_entry.delete(0, "end")
        self.descricao_entry.delete(0, "end")
        self.observacoes_entry.delete(0, "end")
        self.refresh()
        messagebox.showinfo("Lançamento salvo", "Fluxo de caixa atualizado.", parent=self)

    def refresh(self) -> None:
        try:
            month_text = normalize_month(self.month_entry.get())
        except ValueError:
            month_text = normalize_month()
            self.month_entry.set(month_text)
        current_category = self.categoria_entry.get()
        self._update_categories()
        values = list(self.categoria_entry.cget("values"))
        if current_category in values:
            self.categoria_entry.set(current_category)
        self.tree.delete(*self.tree.get_children())
        for row in self.financial_service.list_cash_flow_for_month(month_text):
            origem = "Venda" if str(row.get("origem", "")).lower() == "venda" else "Manual"
            self.tree.insert(
                "",
                "end",
                values=[
                    row.get("data", ""),
                    row.get("tipo", ""),
                    row.get("categoria", ""),
                    row.get("descricao", ""),
                    row.get("valor", ""),
                    row.get("status", ""),
                    origem,
                ],
            )
        summary = self.financial_service.cash_summary(month_text)
        self.summary_label.configure(
            text=f"Saldo atual: {format_money(summary['saldo_atual'])} | Projetado: {format_money(summary['saldo_projetado'])}"
        )

