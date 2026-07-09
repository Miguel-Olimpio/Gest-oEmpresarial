"""Telas de custo fixo e custo variavel."""

from __future__ import annotations

from tkinter import messagebox, simpledialog

import ttkbootstrap as ttk

from app.services.financial_service import DEFAULT_FIXED_CATEGORIES, DEFAULT_VARIABLE_CATEGORIES, FinancialService
from app.ui.components import ScrollableFrame, configure_treeview, help_label, section_title
from app.utils.formatting import format_money
from app.utils.months import month_options, normalize_month
from app.utils.numbers import parse_decimal


class FixedCostPanel(ttk.Frame):
    def __init__(self, master, service: FinancialService):
        super().__init__(master, padding=18)
        self.service = service
        self.rows: list[dict] = []
        self.custom_categories: set[str] = set()
        self.automatic_categories = {"salários", "salarios", "pró-labore", "pro-labore", "pro labore"}
        section_title(
            self,
            "Custo Fixo",
            "Custos fixos são gastos que acontecem mesmo que a empresa venda pouco ou não venda nada.",
        ).pack(fill="x", pady=(0, 12))
        self._build_form()
        self._build_table()
        self.refresh()

    def _build_form(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 10))
        ttk.Button(toolbar, text="Salvar custos fixos", bootstyle="primary", command=self.save_costs).pack(side="right")
        ttk.Button(toolbar, text="Adicionar custo", bootstyle="secondary", command=self.add_custom_row).pack(side="right", padx=(0, 8))

        month_frame = ttk.Frame(self)
        month_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(month_frame, text="Mês dos custos:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.month_entry = ttk.Combobox(month_frame, values=month_options(), width=12)
        self.month_entry.set(normalize_month())
        self.month_entry.pack(side="left", padx=(8, 0))
        self.month_entry.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        self.month_entry.bind("<FocusOut>", lambda _event: self.refresh())
        help_label(month_frame, "Use MM/AAAA. O mês vale para todos os custos preenchidos.", 520).pack(side="left", padx=(12, 0))
        help_label(
            self,
            "Salários e pró-labore são calculados automaticamente a partir da aba Colaboradores.",
            900,
        ).pack(anchor="w", fill="x", pady=(0, 10))

        form_box = ttk.Labelframe(self, text="Custos fixos do mês", padding=10)
        form_box.pack(fill="x", pady=(0, 12))
        self.scroll = ScrollableFrame(form_box)
        self.scroll.pack(fill="x", expand=True)
        self.scroll.canvas.configure(height=280)
        self.rows_frame = self.scroll.body
        self.rows_frame.columnconfigure(0, weight=1)
        self.rows_frame.columnconfigure(1, weight=0)

        ttk.Label(self.rows_frame, text="Custo", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(self.rows_frame, text="Valor", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="e", pady=(0, 6))

        for name in DEFAULT_FIXED_CATEGORIES:
            self.add_cost_row(name, custom=False)

    def _build_table(self) -> None:
        self.total_label = ttk.Label(self, text="", font=("Segoe UI", 10, "bold"), bootstyle="primary")
        self.total_label.pack(anchor="w", pady=(0, 8))

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(table_frame, height=9)
        configure_treeview(
            self.tree,
            [
                ("data", "Mês", 100),
                ("categoria", "Categoria", 240),
                ("valor", "Valor", 110),
                ("observacoes", "Observações", 260),
            ],
        )
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

    def add_cost_row(self, name: str = "", *, custom: bool = True) -> None:
        row_index = len(self.rows) + 1
        if custom:
            name_widget = ttk.Entry(self.rows_frame)
            name_widget.insert(0, name)
            name_widget.grid(row=row_index, column=0, sticky="ew", padx=(0, 12), pady=4)
        else:
            name_widget = ttk.Label(self.rows_frame, text=name, anchor="w", justify="left")
            name_widget.grid(row=row_index, column=0, sticky="ew", padx=(0, 12), pady=4)

        value_entry = ttk.Entry(self.rows_frame, width=18)
        value_entry.grid(row=row_index, column=1, sticky="e", pady=4)
        auto = name.strip().lower() in self.automatic_categories
        if auto:
            value_entry.configure(state="readonly")
        self.rows.append({"name": name_widget, "value": value_entry, "custom": custom, "auto": auto})

    def add_custom_row(self) -> None:
        self.add_cost_row("", custom=True)
        self.scroll.canvas.yview_moveto(1)

    def _row_name(self, row: dict) -> str:
        return row["name"].get().strip() if row["custom"] else row["name"].cget("text").strip()

    def _find_row(self, name: str) -> dict | None:
        wanted = name.strip().lower()
        for row in self.rows:
            if self._row_name(row).lower() == wanted:
                return row
        return None

    def _ensure_custom_row(self, name: str) -> dict:
        existing = self._find_row(name)
        if existing:
            return existing
        self.add_cost_row(name, custom=True)
        self.custom_categories.add(name.lower())
        return self.rows[-1]

    def _clear_values(self) -> None:
        for row in self.rows:
            row["value"].configure(state="normal")
            row["value"].delete(0, "end")
            if row.get("auto"):
                row["value"].configure(state="readonly")

    def _set_row_value(self, row: dict, value) -> None:
        row["value"].configure(state="normal")
        row["value"].delete(0, "end")
        parsed = parse_decimal(value)
        if parsed:
            row["value"].insert(0, str(parsed).replace(".", ","))
        if row.get("auto"):
            row["value"].configure(state="readonly")

    def _load_month_values(self, month_text: str) -> None:
        self._clear_values()
        for item in self.service.list_fixed_costs_for_month(month_text):
            category = str(item.get("categoria", "")).strip()
            if not category:
                continue
            row = self._find_row(category) or self._ensure_custom_row(category)
            if row.get("auto"):
                continue
            self._set_row_value(row, item.get("valor"))
        for category, value in self.service.automatic_fixed_cost_values().items():
            row = self._find_row(category) or self._ensure_custom_row(category)
            row["auto"] = True
            self._set_row_value(row, value)

    def save_costs(self) -> None:
        try:
            month_text = normalize_month(self.month_entry.get())
        except ValueError:
            messagebox.showerror("Mês inválido", "Mês obrigatório e válido. Use MM/AAAA.", parent=self)
            return

        payloads: list[dict] = []
        seen: set[str] = set()
        for row in self.rows:
            if row.get("auto"):
                continue
            name = self._row_name(row)
            value_text = row["value"].get().strip()
            if not name and not value_text:
                continue
            if not name:
                messagebox.showerror("Nome obrigatório", "Informe o nome do custo personalizado.", parent=self)
                return
            try:
                value = parse_decimal(value_text or "0")
            except ValueError:
                messagebox.showerror("Valor inválido", f"Valor inválido em {name}.", parent=self)
                return
            if value < 0:
                messagebox.showerror("Valor inválido", f"O valor de {name} não pode ser negativo.", parent=self)
                return
            key = name.lower()
            if key in seen:
                messagebox.showerror("Custo duplicado", f"O custo {name} aparece mais de uma vez na tela.", parent=self)
                return
            seen.add(key)
            payloads.append({"categoria": name, "descricao": name, "valor": value, "observacoes": ""})

        try:
            self.service.sync_fixed_costs_for_month(month_text, payloads)
        except Exception as exc:
            messagebox.showerror("Não foi possível salvar", str(exc), parent=self)
            return

        self.refresh()
        messagebox.showinfo("Custos salvos", "Custos fixos do mês sincronizados com sucesso.", parent=self)

    def refresh(self) -> None:
        try:
            month_text = normalize_month(self.month_entry.get())
        except ValueError:
            month_text = normalize_month()
            self.month_entry.set(month_text)
        self._load_month_values(month_text)
        self.tree.delete(*self.tree.get_children())
        for row in self.service.list_effective_fixed_costs_for_month(month_text):
            self.tree.insert(
                "",
                "end",
                values=[
                    row.get("data", ""),
                    row.get("categoria", ""),
                    row.get("valor", ""),
                    row.get("observacoes", ""),
                ],
            )
        self.total_label.configure(text=f"Total de custos fixos do mês: {format_money(self.service.total_fixed_costs(month_text))}")


class VariableCostPanel(ttk.Frame):
    def __init__(self, master, service: FinancialService):
        super().__init__(master, padding=18)
        self.service = service
        section_title(
            self,
            "Custo Variável",
            "Custos variáveis aumentam ou diminuem conforme o volume de vendas.",
        ).pack(fill="x", pady=(0, 12))
        self._build()
        self.refresh()

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text="Mês de acompanhamento:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.month_entry = ttk.Combobox(top, values=month_options(), width=12)
        self.month_entry.set(normalize_month())
        self.month_entry.pack(side="left", padx=(8, 0))
        self.month_entry.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        self.month_entry.bind("<FocusOut>", lambda _event: self.refresh())
        ttk.Button(top, text="Atualizar", bootstyle="primary", command=self.refresh).pack(side="right")
        ttk.Button(top, text="Adicionar custo variável", bootstyle="secondary", command=self.add_variable_category).pack(side="right", padx=(0, 8))

        help_label(
            self,
            "Lance custos variáveis no Fluxo de Caixa. Taxas de máquina de cartão geradas nas vendas entram automaticamente nesta tela.",
            920,
        ).pack(anchor="w", fill="x", pady=(0, 12))

        self.total_label = ttk.Label(self, text="", font=("Segoe UI", 11, "bold"), bootstyle="primary")
        self.total_label.pack(anchor="w", pady=(0, 8))

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(table_frame, height=16)
        configure_treeview(self.tree, [("categoria", "Categoria", 320), ("valor", "Total do mês", 140)])
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")

    def refresh(self) -> None:
        try:
            month_text = normalize_month(self.month_entry.get())
        except ValueError:
            messagebox.showerror("Mês inválido", "Mês obrigatório e válido. Use MM/AAAA.", parent=self)
            return
        self.tree.delete(*self.tree.get_children())
        for row in self.service.variable_costs_by_category(month_text):
            self.tree.insert("", "end", values=[row["categoria"], format_money(row["valor"])])
        self.total_label.configure(text=f"Total variável do mês: {format_money(self.service.total_variable_costs(month_text))}")

    def add_variable_category(self) -> None:
        name = simpledialog.askstring("Adicionar custo variável", "Nome da nova categoria:", parent=self)
        if name is None:
            return
        name = name.strip()
        if not name:
            messagebox.showwarning("Categoria obrigatória", "Informe o nome da categoria.", parent=self)
            return
        try:
            self.service.create_category("variavel", name)
        except Exception as exc:
            messagebox.showerror("Não foi possível salvar", str(exc), parent=self)
            return
        self.refresh()
        messagebox.showinfo("Categoria salva", "Categoria variável adicionada ao app e ao Fluxo de Caixa.", parent=self)


