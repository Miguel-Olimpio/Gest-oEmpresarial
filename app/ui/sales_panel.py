"""Tela de vendas, máquinas de cartão e conferencia de recebiveis."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk

from app.services.sales_service import SalesService
from app.ui.components import configure_treeview, help_label, section_title
from app.utils.dates import format_date, parse_date
from app.utils.formatting import format_money
from app.utils.numbers import parse_decimal


class SalesPanel(ttk.Frame):
    def __init__(self, master, service: SalesService):
        super().__init__(master, padding=18)
        self.service = service
        section_title(
            self,
            "Vendas / Entradas",
            "Registre vendas / entradas em dinheiro ou por máquina de cartão e acompanhe recebimentos, taxas e prazos.",
        ).pack(fill="x", pady=(0, 12))
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        self.sales_tab = SaleRegisterTab(notebook, service)
        self.machine_tab = MachineRulesTab(notebook, service, self.sales_tab)
        self.conference_tab = ReceivableConferenceTab(notebook, service)
        notebook.add(self.sales_tab, text="Registrar venda / entrada")
        notebook.add(self.machine_tab, text="Configuração de Máquinas de Cartão")
        notebook.add(self.conference_tab, text="Conferência de Máquina de Cartão")

    def refresh(self) -> None:
        self.sales_tab.refresh()
        self.machine_tab.refresh()
        self.conference_tab.refresh()


class MachineRulesTab(ttk.Frame):
    def __init__(self, master, service: SalesService, sales_tab):
        super().__init__(master, padding=10)
        self.service = service
        self.sales_tab = sales_tab
        self._build()
        self.refresh()

    def _build(self) -> None:
        help_label(
            self,
            "Cadastre a máquina de cartão uma única vez. Dentro dela, configure as condições por bandeira, modalidade e parcelas.",
            900,
        ).pack(anchor="w", fill="x", pady=(0, 10))

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="Cadastrar máquina de cartão", bootstyle="primary", command=self.create_machine).pack(side="left")
        ttk.Button(actions, text="Editar máquina de cartão", bootstyle="secondary", command=self.edit_machine).pack(side="left", padx=8)
        ttk.Button(actions, text="Inativar máquina de cartão", bootstyle="danger", command=self.inactivate_machine).pack(side="left")

        content = ttk.Panedwindow(self, orient="horizontal")
        content.pack(fill="both", expand=True)

        left = ttk.Labelframe(content, text="Máquinas de Cartão cadastradas", padding=8)
        right = ttk.Labelframe(content, text="Condições da máquina de cartão selecionada", padding=8)
        content.add(left, weight=1)
        content.add(right, weight=2)

        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        self.machine_tree = ttk.Treeview(left, height=14)
        configure_treeview(
            self.machine_tree,
            [
                ("nome", "Máquina de Cartão", 180),
                ("active", "Status", 90),
                ("observacoes", "Observações", 220),
            ],
        )
        machine_scroll = ttk.Scrollbar(left, orient="vertical", command=self.machine_tree.yview)
        self.machine_tree.configure(yscrollcommand=machine_scroll.set)
        self.machine_tree.grid(row=0, column=0, sticky="nsew")
        machine_scroll.grid(row=0, column=1, sticky="ns")
        self.machine_tree.bind("<<TreeviewSelect>>", lambda _event: self.refresh_conditions())

        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)
        self.condition_tree = ttk.Treeview(right, height=14)
        configure_treeview(
            self.condition_tree,
            [
                ("bandeira", "Bandeira", 110),
                ("modalidade", "Modalidade", 100),
                ("parcelas", "Parcelas", 90),
                ("taxa_percentual", "Taxa %", 90),
                ("taxa_fixa", "Taxa fixa", 90),
                ("prazo_dias_uteis", "Dias úteis", 90),
            ],
        )
        cond_y = ttk.Scrollbar(right, orient="vertical", command=self.condition_tree.yview)
        cond_x = ttk.Scrollbar(right, orient="horizontal", command=self.condition_tree.xview)
        self.condition_tree.configure(yscrollcommand=cond_y.set, xscrollcommand=cond_x.set)
        self.condition_tree.grid(row=0, column=0, sticky="nsew")
        cond_y.grid(row=0, column=1, sticky="ns")
        cond_x.grid(row=1, column=0, sticky="ew")

    def _selected_machine_id(self) -> str | None:
        selected = self.machine_tree.selection()
        return str(selected[0]) if selected else None

    def create_machine(self) -> None:
        MachineEditorDialog(self, self.service, self._after_machine_saved).show()

    def edit_machine(self) -> None:
        machine_id = self._selected_machine_id()
        if not machine_id:
            messagebox.showwarning("Selecione uma máquina de cartão", "Selecione a máquina de cartão que deseja editar.", parent=self)
            return
        machine = self.service.get_machine(machine_id)
        if not machine:
            messagebox.showerror("Não encontrada", "Máquina de Cartão não encontrada.", parent=self)
            return
        MachineEditorDialog(self, self.service, self._after_machine_saved, machine).show()

    def inactivate_machine(self) -> None:
        machine_id = self._selected_machine_id()
        if not machine_id:
            messagebox.showwarning("Selecione uma máquina de cartão", "Selecione a máquina de cartão que deseja inativar.", parent=self)
            return
        if not messagebox.askyesno("Confirmar", "Deseja inativar esta máquina de cartão e suas condições?", parent=self):
            return
        try:
            self.service.inactivate_machine(machine_id)
        except Exception as exc:
            messagebox.showerror("Não foi possível inativar", str(exc), parent=self)
            return
        self._after_machine_saved()

    def _after_machine_saved(self) -> None:
        self.refresh()
        self.sales_tab.refresh_options()

    def refresh(self) -> None:
        self.machine_tree.delete(*self.machine_tree.get_children())
        for row in self.service.list_machines(active_only=False):
            status = "Ativa" if row.get("active", True) else "Inativa"
            self.machine_tree.insert(
                "",
                "end",
                iid=str(row.get("maquina_cartao_id")),
                values=[row.get("nome", ""), status, row.get("observacoes", "")],
            )
        self.refresh_conditions()

    def refresh_conditions(self) -> None:
        self.condition_tree.delete(*self.condition_tree.get_children())
        machine_id = self._selected_machine_id()
        if not machine_id:
            return
        for row in self.service.list_conditions(machine_id, active_only=False):
            if not row.get("active", True):
                continue
            self.condition_tree.insert(
                "",
                "end",
                values=[
                    row.get("bandeira", ""),
                    row.get("modalidade", ""),
                    f"{int(row.get('parcelas', 1))}x",
                    row.get("taxa_percentual", ""),
                    row.get("taxa_fixa", ""),
                    row.get("prazo_dias_uteis", ""),
                ],
            )


class MachineEditorDialog:
    def __init__(self, parent, service: SalesService, on_saved, machine: dict | None = None):
        self.parent = parent
        self.service = service
        self.on_saved = on_saved
        self.machine = machine
        self.conditions = [dict(row) for row in service.list_conditions(machine["maquina_cartao_id"]) ] if machine else []
        self.window: tk.Toplevel | None = None

    def show(self) -> None:
        win = tk.Toplevel(self.parent)
        self.window = win
        win.title("Editar máquina de cartão" if self.machine else "Cadastrar máquina de cartão")
        win.geometry("980x700")
        win.minsize(840, 560)
        win.resizable(True, True)
        try:
            win.transient(self.parent.winfo_toplevel())
        except tk.TclError:
            pass

        root = ttk.Frame(win, padding=12)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        help_label(root, "Cadastre a máquina de cartão uma vez e adicione abaixo as condições por bandeira, modalidade e parcelas.", 900).grid(
            row=0, column=0, sticky="ew", pady=(0, 10)
        )

        main = ttk.Labelframe(root, text="Dados da máquina de cartão", padding=10)
        main.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=2)
        ttk.Label(main, text="Nome da máquina de cartão", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=5)
        self.name_entry = ttk.Entry(main)
        self.name_entry.grid(row=1, column=0, sticky="ew", padx=5, pady=(2, 8))
        ttk.Label(main, text="Observações", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w", padx=5)
        self.notes_entry = ttk.Entry(main)
        self.notes_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=(2, 8))
        self.active_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main, text="Ativa", variable=self.active_var, bootstyle="round-toggle").grid(row=1, column=2, sticky="w", padx=5)
        if self.machine:
            self.name_entry.insert(0, str(self.machine.get("nome", "")))
            self.notes_entry.insert(0, str(self.machine.get("observacoes", "")))
            self.active_var.set(bool(self.machine.get("active", True)))

        body = ttk.Labelframe(root, text="Condições", padding=10)
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)

        form = ttk.Frame(body)
        form.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for col in range(6):
            form.columnconfigure(col, weight=1)
        self.flag_entry = ttk.Combobox(form, values=self.service.card_flags(), state="readonly")
        self.modality_entry = ttk.Combobox(form, values=self.service.card_modalities(), state="readonly")
        self.installments_entry = ttk.Combobox(form, values=self.service.installment_options(), state="disabled")
        self.rate_entry = ttk.Entry(form)
        self.fixed_fee_entry = ttk.Entry(form)
        self.days_entry = ttk.Entry(form)
        self.fixed_fee_entry.insert(0, "0")
        self.days_entry.insert(0, "0")
        self._place(form, "Bandeira", self.flag_entry, 0, 0)
        self._place(form, "Modalidade", self.modality_entry, 0, 1)
        self._place(form, "Parcelas", self.installments_entry, 0, 2)
        self._place(form, "Taxa %", self.rate_entry, 0, 3)
        self._place(form, "Taxa fixa", self.fixed_fee_entry, 0, 4)
        self._place(form, "Dias úteis", self.days_entry, 0, 5)
        self.flag_entry.set(self.service.card_flags()[0])
        self.modality_entry.set("PIX")
        self.installments_entry.set("1x")
        self.modality_entry.bind("<<ComboboxSelected>>", lambda _event: self._sync_installments())

        button_row = ttk.Frame(body)
        button_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(button_row, text="Adicionar condição", bootstyle="primary", command=self.add_condition).pack(side="left")
        ttk.Button(button_row, text="Remover condição", bootstyle="danger", command=self.remove_condition).pack(side="left", padx=8)
        help_label(button_row, "Para PIX e Débito, parcelas ficam fixas em 1x. Para Crédito, escolha de 1x a 12x.", 650).pack(side="left", padx=12)

        table_frame = ttk.Frame(body)
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.condition_tree = ttk.Treeview(table_frame, height=12)
        configure_treeview(
            self.condition_tree,
            [
                ("bandeira", "Bandeira", 110),
                ("modalidade", "Modalidade", 100),
                ("parcelas", "Parcelas", 90),
                ("taxa_percentual", "Taxa %", 90),
                ("taxa_fixa", "Taxa fixa", 90),
                ("prazo_dias_uteis", "Dias úteis", 90),
            ],
        )
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.condition_tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.condition_tree.xview)
        self.condition_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.condition_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        footer = ttk.Frame(root)
        footer.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(footer, text="Cancelar", bootstyle="secondary", command=win.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(footer, text="Salvar máquina de cartão", bootstyle="primary", command=self.save).pack(side="right")

        self._sync_installments()
        self.refresh_conditions()

    def _place(self, parent, label, widget, row, col):
        ttk.Label(parent, text=label, font=("Segoe UI", 9, "bold")).grid(row=row, column=col, sticky="w", padx=5)
        widget.grid(row=row + 1, column=col, sticky="ew", padx=5, pady=(2, 8))

    def _sync_installments(self) -> None:
        if self.modality_entry.get() == "Crédito":
            self.installments_entry.configure(state="readonly", values=self.service.installment_options())
            if not self.installments_entry.get():
                self.installments_entry.set("1x")
        else:
            self.installments_entry.configure(state="disabled", values=["1x"])
            self.installments_entry.set("1x")

    def add_condition(self) -> None:
        try:
            condition = self.service.normalize_condition_data(
                {
                    "bandeira": self.flag_entry.get(),
                    "modalidade": self.modality_entry.get(),
                    "parcelas": self.installments_entry.get(),
                    "taxa_percentual": self.rate_entry.get(),
                    "taxa_fixa": self.fixed_fee_entry.get(),
                    "prazo_dias_uteis": self.days_entry.get(),
                }
            )
            key = (condition["bandeira"].lower(), condition["modalidade"].lower(), int(condition["parcelas"]))
            for existing in self.conditions:
                existing_key = (str(existing.get("bandeira", "")).lower(), str(existing.get("modalidade", "")).lower(), int(existing.get("parcelas", 1)))
                if existing_key == key:
                    raise ValueError("Já existe uma condição para esta bandeira, modalidade e parcelas nesta máquina de cartão.")
        except Exception as exc:
            messagebox.showerror("Condição inválida", str(exc), parent=self.window)
            return
        self.conditions.append(condition)
        self.rate_entry.delete(0, "end")
        self.fixed_fee_entry.delete(0, "end")
        self.fixed_fee_entry.insert(0, "0")
        self.days_entry.delete(0, "end")
        self.days_entry.insert(0, "0")
        self.refresh_conditions()

    def remove_condition(self) -> None:
        selected = self.condition_tree.selection()
        if not selected:
            messagebox.showwarning("Selecione uma condição", "Selecione a condição que deseja remover.", parent=self.window)
            return
        indexes = sorted([int(item) for item in selected], reverse=True)
        for index in indexes:
            if 0 <= index < len(self.conditions):
                self.conditions.pop(index)
        self.refresh_conditions()

    def refresh_conditions(self) -> None:
        self.condition_tree.delete(*self.condition_tree.get_children())
        for index, row in enumerate(self.conditions):
            self.condition_tree.insert(
                "",
                "end",
                iid=str(index),
                values=[
                    row.get("bandeira", ""),
                    row.get("modalidade", ""),
                    f"{int(row.get('parcelas', 1))}x",
                    row.get("taxa_percentual", ""),
                    row.get("taxa_fixa", ""),
                    row.get("prazo_dias_uteis", ""),
                ],
            )

    def save(self) -> None:
        try:
            if self.machine:
                self.service.update_machine(
                    self.machine["maquina_cartao_id"],
                    nome=self.name_entry.get(),
                    observacoes=self.notes_entry.get(),
                    active=self.active_var.get(),
                    conditions=self.conditions,
                )
            else:
                self.service.create_machine(
                    nome=self.name_entry.get(),
                    observacoes=self.notes_entry.get(),
                    active=self.active_var.get(),
                    conditions=self.conditions,
                )
        except Exception as exc:
            messagebox.showerror("Não foi possível salvar", str(exc), parent=self.window)
            return
        if self.window is not None:
            self.window.destroy()
        self.on_saved()


class SaleRegisterTab(ttk.Frame):
    PAYMENT_CASH = "Dinheiro"
    PAYMENT_CARD = "Máquina de Cartão"

    def __init__(self, master, service: SalesService):
        super().__init__(master, padding=10)
        self.service = service
        self._build()
        self.refresh()

    def _build(self) -> None:
        help_label(
            self,
            "Registre vendas / entradas em dinheiro ou por máquina de cartão. O Fluxo de Caixa é alimentado automaticamente.",
            900,
        ).pack(anchor="w", fill="x", pady=(0, 10))
        form = ttk.Labelframe(self, text="Nova venda", padding=10)
        form.pack(fill="x", pady=(0, 10))
        for col in range(4):
            form.columnconfigure(col, weight=1)
        self.data_entry = self._field(form, "Data da venda", 0, 0, default=format_date())
        self.valor_entry = self._field(form, "Valor bruto", 0, 1)
        self.forma_pagamento_entry = ttk.Combobox(form, values=[self.PAYMENT_CASH, self.PAYMENT_CARD], state="readonly")
        self.forma_pagamento_entry.set(self.PAYMENT_CASH)
        self._place(form, "Forma de pagamento", self.forma_pagamento_entry, 0, 2)

        self.maquina_cartao_entry = ttk.Combobox(form, values=[], state="readonly")
        self.maquina_cartao_label = self._place(form, "Máquina de Cartão", self.maquina_cartao_entry, 0, 3)
        self.bandeira_entry = ttk.Combobox(form, values=[], state="readonly")
        self.bandeira_label = self._place(form, "Bandeira", self.bandeira_entry, 2, 0)
        self.modalidade_entry = ttk.Combobox(form, values=[], state="readonly")
        self.modalidade_label = self._place(form, "Modalidade", self.modalidade_entry, 2, 1)
        self.parcelas_label = ttk.Label(form, text="Parcelas", font=("Segoe UI", 9, "bold"))
        self.parcelas_entry = ttk.Combobox(form, values=["1x"], state="disabled")
        self.parcelas_entry.set("1x")
        self.parcelas_label.grid(row=2, column=2, sticky="w", padx=5, pady=(0, 2))
        self.parcelas_entry.grid(row=3, column=2, sticky="ew", padx=5, pady=(0, 8))
        self.descricao_entry = self._field(form, "Descrição", 4, 0)
        self.observacoes_entry = self._field(form, "Observações", 4, 1)

        self.result_label = ttk.Label(form, text="", bootstyle="primary", font=("Segoe UI", 10, "bold"))
        self.result_label.grid(row=6, column=0, columnspan=3, sticky="w", padx=5, pady=(10, 0))
        ttk.Button(form, text="Salvar venda / entrada", bootstyle="primary", command=self.save_sale).grid(row=6, column=3, sticky="e", padx=5, pady=(10, 0))

        for widget in (
            self.data_entry,
            self.valor_entry,
            self.forma_pagamento_entry,
            self.maquina_cartao_entry,
            self.bandeira_entry,
            self.modalidade_entry,
            self.parcelas_entry,
        ):
            widget.bind("<FocusOut>", lambda _event: self.update_preview())
        self.forma_pagamento_entry.bind("<<ComboboxSelected>>", lambda _event: self._on_payment_method_selected())
        self.maquina_cartao_entry.bind("<<ComboboxSelected>>", lambda _event: self._on_machine_selected())
        self.bandeira_entry.bind("<<ComboboxSelected>>", lambda _event: self._on_flag_selected())
        self.modalidade_entry.bind("<<ComboboxSelected>>", lambda _event: self._on_modality_selected())
        self.parcelas_entry.bind("<<ComboboxSelected>>", lambda _event: self.update_preview())

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(table_frame, height=11)
        configure_treeview(
            self.tree,
            [
                ("data_venda", "Data", 90),
                ("forma_pagamento", "Pagamento", 130),
                ("valor_bruto", "Bruto", 90),
                ("valor_taxa", "Taxa", 90),
                ("valor_liquido", "Líquido", 90),
                ("data_prevista_recebimento", "Previsto", 100),
                ("maquina_cartao", "Máquina de Cartão", 120),
                ("bandeira", "Bandeira", 100),
                ("modalidade", "Modalidade", 90),
                ("parcelas", "Parcelas", 80),
            ],
        )
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.refresh_options()
        self._on_payment_method_selected()

    def _field(self, parent, label, row, col, default=""):
        entry = ttk.Entry(parent)
        entry.insert(0, default)
        self._place(parent, label, entry, row, col)
        return entry

    def _place(self, parent, label, widget, row, col):
        label_widget = ttk.Label(parent, text=label, font=("Segoe UI", 9, "bold"))
        label_widget.grid(row=row, column=col, sticky="w", padx=5, pady=(0, 2))
        widget.grid(row=row + 1, column=col, sticky="ew", padx=5, pady=(0, 8))
        return label_widget

    def _show_widget_pair(self, label, widget) -> None:
        label.grid()
        widget.grid()

    def _hide_widget_pair(self, label, widget) -> None:
        label.grid_remove()
        widget.grid_remove()

    def refresh_options(self) -> None:
        self.maquina_cartao_entry.configure(values=self.service.machine_names())
        self._on_payment_method_selected()

    def _on_payment_method_selected(self) -> None:
        if self.forma_pagamento_entry.get() == self.PAYMENT_CASH:
            for label, widget in (
                (self.maquina_cartao_label, self.maquina_cartao_entry),
                (self.bandeira_label, self.bandeira_entry),
                (self.modalidade_label, self.modalidade_entry),
                (self.parcelas_label, self.parcelas_entry),
            ):
                self._hide_widget_pair(label, widget)
            self.maquina_cartao_entry.set("")
            self.bandeira_entry.set("")
            self.modalidade_entry.set("")
            self.parcelas_entry.configure(values=["1x"], state="disabled")
            self.parcelas_entry.set("1x")
        else:
            self._show_widget_pair(self.maquina_cartao_label, self.maquina_cartao_entry)
            self._show_widget_pair(self.bandeira_label, self.bandeira_entry)
            self._show_widget_pair(self.modalidade_label, self.modalidade_entry)
            if not self.maquina_cartao_entry.get():
                values = list(self.maquina_cartao_entry.cget("values"))
                if values:
                    self.maquina_cartao_entry.set(values[0])
            self._on_machine_selected()
            return
        self.update_preview()

    def _on_machine_selected(self) -> None:
        if self.forma_pagamento_entry.get() == self.PAYMENT_CASH:
            self.update_preview()
            return
        flags = self.service.flags_for_machine(self.maquina_cartao_entry.get())
        self.bandeira_entry.configure(values=flags)
        self.bandeira_entry.set(flags[0] if flags else "")
        self._on_flag_selected()

    def _on_flag_selected(self) -> None:
        if self.forma_pagamento_entry.get() == self.PAYMENT_CASH:
            self.update_preview()
            return
        modalities = self.service.modalities_for_machine_flag(self.maquina_cartao_entry.get(), self.bandeira_entry.get())
        self.modalidade_entry.configure(values=modalities)
        self.modalidade_entry.set(modalities[0] if modalities else "")
        self._on_modality_selected()

    def _on_modality_selected(self) -> None:
        if self.forma_pagamento_entry.get() == self.PAYMENT_CASH:
            self.update_preview()
            return
        modality = self.modalidade_entry.get()
        if modality == "Crédito":
            values = [f"{value}x" for value in self.service.installments_for_machine_flag_modality(
                self.maquina_cartao_entry.get(), self.bandeira_entry.get(), modality
            )]
            self._show_widget_pair(self.parcelas_label, self.parcelas_entry)
            self.parcelas_entry.configure(values=values, state="readonly")
            self.parcelas_entry.set(values[0] if values else "")
        else:
            self.parcelas_entry.configure(values=["1x"], state="disabled")
            self.parcelas_entry.set("1x")
            self._hide_widget_pair(self.parcelas_label, self.parcelas_entry)
        self.update_preview()

    def update_preview(self) -> None:
        try:
            calc = self.service.calculate_sale(
                data_venda=self.data_entry.get(),
                valor_bruto=self.valor_entry.get(),
                forma_pagamento=self.forma_pagamento_entry.get(),
                maquina_cartao=self.maquina_cartao_entry.get(),
                bandeira=self.bandeira_entry.get(),
                modalidade=self.modalidade_entry.get(),
                parcelas=self.parcelas_entry.get(),
            )
        except Exception:
            if self.forma_pagamento_entry.get() == self.PAYMENT_CASH:
                self.result_label.configure(text="Informe data e valor para calcular a venda em dinheiro.")
            else:
                self.result_label.configure(text="Selecione máquina de cartão, bandeira, modalidade e parcelas quando for crédito para calcular.")
            return
        self.result_label.configure(
            text=(
                f"Taxa: {format_money(calc['valor_taxa'])} | "
                f"Líquido: {format_money(calc['valor_liquido'])} | "
                f"Recebimento: {calc['data_prevista_recebimento']}"
            )
        )

    def save_sale(self) -> None:
        try:
            parse_date(self.data_entry.get())
            self.service.create_sale(
                data_venda=self.data_entry.get(),
                descricao=self.descricao_entry.get(),
                valor_bruto=self.valor_entry.get(),
                forma_pagamento=self.forma_pagamento_entry.get(),
                maquina_cartao=self.maquina_cartao_entry.get(),
                bandeira=self.bandeira_entry.get(),
                modalidade=self.modalidade_entry.get(),
                parcelas=self.parcelas_entry.get(),
                observacoes=self.observacoes_entry.get(),
            )
        except Exception as exc:
            messagebox.showerror("Não foi possível salvar", str(exc), parent=self)
            return
        for entry in (self.valor_entry, self.descricao_entry, self.observacoes_entry):
            entry.delete(0, "end")
        self.refresh()
        messagebox.showinfo("Venda / entrada salva", "Registro salvo e Fluxo de Caixa atualizado.", parent=self)

    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for row in self.service.list_sales():
            is_cash = str(row.get("forma_pagamento", "")) == self.PAYMENT_CASH
            self.tree.insert(
                "",
                "end",
                values=[
                    row.get("data_venda", ""),
                    row.get("forma_pagamento", ""),
                    row.get("valor_bruto", ""),
                    row.get("valor_taxa", ""),
                    row.get("valor_liquido", ""),
                    row.get("data_prevista_recebimento", ""),
                    row.get("maquina_cartao", ""),
                    row.get("bandeira", ""),
                    row.get("modalidade", ""),
                    "" if is_cash else f"{int(row.get('parcelas', 1) or 1)}x",
                ],
            )


class ReceivableConferenceTab(ttk.Frame):
    def __init__(self, master, service: SalesService):
        super().__init__(master, padding=10)
        self.service = service
        self._build()
        self.refresh()

    def _build(self) -> None:
        help_label(self, "Nem sempre o valor vendido é o valor recebido. Taxas e prazos precisam ser conferidos.", 900).pack(
            anchor="w", fill="x", pady=(0, 10)
        )
        form = ttk.Frame(self)
        form.pack(fill="x", pady=(0, 10))
        ttk.Label(form, text="Valor real depositado:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.received_entry = ttk.Entry(form, width=16)
        self.received_entry.pack(side="left", padx=(8, 0))
        ttk.Button(form, text="Confirmar conferência", bootstyle="primary", command=self.confirm).pack(side="left", padx=10)

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(table_frame, height=14)
        configure_treeview(
            self.tree,
            [
                ("venda_id", "Venda", 100),
                ("data_prevista", "Data prevista", 110),
                ("maquina_cartao", "Máquina de Cartão", 130),
                ("bandeira", "Bandeira", 110),
                ("modalidade", "Modalidade", 100),
                ("parcelas", "Parcelas", 80),
                ("valor_bruto", "Bruto", 100),
                ("valor_taxa", "Taxa", 100),
                ("valor_esperado", "Líquido esperado", 130),
                ("valor_recebido", "Recebido", 100),
                ("diferenca", "Diferença", 100),
                ("status", "Status", 100),
            ],
        )
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

    def confirm(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selecione uma venda", "Selecione um recebível para conferir.", parent=self)
            return
        venda_id = self.tree.item(selected[0], "values")[0]
        try:
            parse_decimal(self.received_entry.get())
            result = self.service.reconcile(venda_id, self.received_entry.get())
        except Exception as exc:
            messagebox.showerror("Não foi possível conferir", str(exc), parent=self)
            return
        self.received_entry.delete(0, "end")
        self.refresh()
        messagebox.showinfo("Conferência registrada", f"Status: {result['status']}", parent=self)

    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for row in self.service.reconciliation_rows():
            self.tree.insert(
                "",
                "end",
                values=[
                    row.get("venda_id", ""),
                    row.get("data_prevista", ""),
                    row.get("venda_maquina_cartao", ""),
                    row.get("venda_bandeira", ""),
                    row.get("venda_modalidade", ""),
                    f"{int(row.get('venda_parcelas', 1) or 1)}x",
                    row.get("venda_valor_bruto", ""),
                    row.get("venda_valor_taxa", ""),
                    row.get("valor_esperado", ""),
                    row.get("valor_recebido", ""),
                    row.get("diferenca", ""),
                    row.get("status", ""),
                ],
            )





