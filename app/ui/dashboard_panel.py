"""Dashboard principal."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from app.services.accounting_report_service import AccountingReportService
from app.services.dashboard_service import DashboardService
from app.ui.components import ScrollableFrame, help_label, section_title
from app.utils.formatting import format_money
from app.utils.months import month_options, normalize_month
from app.utils.open_file_location import prompt_open_generated_file


CHART_COLORS = ("#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2")


class DashboardPanel(ttk.Frame):
    def __init__(self, master, dashboard_service: DashboardService, accounting_report_service: AccountingReportService):
        super().__init__(master, padding=12)
        self.dashboard_service = dashboard_service
        self.accounting_report_service = accounting_report_service
        self._build()

    def _build(self) -> None:
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        scroll = ScrollableFrame(self)
        scroll.grid(row=0, column=0, sticky="nsew")
        body = scroll.body

        section_title(
            body,
            "Dashboard",
            "Indicadores essenciais para acompanhar vendas / entradas, custos, produtividade e ponto de equil\u00edbrio.",
        ).pack(anchor="w", fill="x", pady=(0, 14))

        controls = ttk.Frame(body)
        controls.pack(fill="x", pady=(0, 12))
        ttk.Label(controls, text="M\u00eas do painel:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.month_var = tk.StringVar(value=normalize_month())
        self.month_entry = ttk.Combobox(controls, textvariable=self.month_var, values=month_options(36), width=12, state="normal")
        self.month_entry.pack(side="left", padx=(8, 12))
        self.month_entry.bind("<<ComboboxSelected>>", lambda _event: self.refresh(show_error=True))
        self.month_entry.bind("<Return>", lambda _event: self.refresh(show_error=True))
        ttk.Button(controls, text="Atualizar", bootstyle="secondary", command=lambda: self.refresh(show_error=True)).pack(side="left")
        ttk.Button(controls, text="Gerar PDF para contador", bootstyle="primary", command=self.generate_accounting_pdf).pack(side="right")

        self.indicators = ttk.Frame(body)
        self.indicators.pack(fill="x")
        for col in range(3):
            self.indicators.columnconfigure(col, weight=1)

        self.charts = ttk.Frame(body)
        self.charts.pack(fill="both", expand=True, pady=(16, 0))
        self.charts.columnconfigure(0, weight=1)
        self.charts.columnconfigure(1, weight=1)
        self.charts.rowconfigure(0, weight=1)

        self.pie_frame = ttk.Labelframe(self.charts, text="Distribui\u00e7\u00e3o de despesas do m\u00eas", padding=10)
        self.pie_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.line_frame = ttk.Labelframe(self.charts, text="Produtividade dos \u00faltimos 6 meses", padding=10)
        self.line_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.alerts = ttk.Labelframe(body, text="Alertas importantes", padding=12)
        self.alerts.pack(fill="x", pady=(16, 0))

        self.refresh()

    def _current_month(self, show_error: bool = False) -> str | None:
        try:
            month_text = normalize_month(self.month_var.get())
        except ValueError:
            if show_error:
                messagebox.showwarning("Mês inválido", "Informe o mês no formato MM/AAAA.", parent=self)
                self.month_entry.focus_set()
            return None
        self.month_var.set(month_text)
        return month_text

    def generate_accounting_pdf(self) -> None:
        month_text = self._current_month(show_error=True)
        if month_text is None:
            return
        try:
            path = self.accounting_report_service.generate_pdf(month_text)
        except Exception as exc:
            messagebox.showerror("N\u00e3o foi poss\u00edvel gerar", str(exc), parent=self)
            return
        prompt_open_generated_file(self, path, title="PDF gerado", message_prefix="Relatorio salvo em:")

    def _clear_frame(self, frame: ttk.Frame) -> None:
        for child in frame.winfo_children():
            child.destroy()

    def _indicator(self, title: str, value: str, text: str, index: int) -> None:
        frame = ttk.Frame(self.indicators, padding=10, bootstyle="light")
        frame.grid(row=index // 3, column=index % 3, sticky="ew", padx=5, pady=5)
        ttk.Label(frame, text=title, font=("Segoe UI", 9, "bold"), bootstyle="primary").pack(anchor="w")
        ttk.Label(frame, text=value, font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(5, 2))
        help_label(frame, text, 260).pack(anchor="w", fill="x")

    def _optional_money(self, value) -> str:
        if value is None:
            return "\u2014"
        return format_money(value)

    def _money_axis(self, value, _position) -> str:
        return f"R$ {value:,.0f}".replace(",", ".")

    def _embed_figure(self, frame: ttk.Frame, figure: Figure) -> None:
        canvas = FigureCanvasTkAgg(figure, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _draw_expense_pie(self, distribution: list[dict]) -> None:
        self._clear_frame(self.pie_frame)
        total = sum(float(row.get("valor", 0) or 0) for row in distribution)
        if total <= 0:
            help_label(self.pie_frame, "Nenhuma despesa encontrada para montar o gr\u00e1fico deste m\u00eas.", 420).pack(anchor="w", fill="x")
            return

        labels = [str(row["categoria"]) for row in distribution]
        values = [float(row["valor"]) for row in distribution]
        legend_labels = [
            f"{label}: {format_money(value)} ({(value / total) * 100:.0f}%)"
            for label, value in zip(labels, values, strict=False)
        ]

        figure = Figure(figsize=(5.4, 3.3), dpi=100, facecolor="white")
        axis = figure.add_subplot(111)
        axis.pie(
            values,
            startangle=90,
            colors=CHART_COLORS[: len(values)],
            autopct=lambda pct: f"{pct:.0f}%" if pct >= 4 else "",
            pctdistance=0.74,
            textprops={"fontsize": 8},
        )
        axis.axis("equal")
        axis.legend(legend_labels, loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8, frameon=False)
        figure.tight_layout()
        self._embed_figure(self.pie_frame, figure)

    def _draw_productivity_line(self, rows: list[dict]) -> None:
        self._clear_frame(self.line_frame)
        labels = [str(row.get("mes", ""))[:2] + "/" + str(row.get("mes", ""))[-2:] for row in rows]
        values = [float(row.get("produtividade", 0) or 0) for row in rows]
        positions = list(range(len(labels)))

        figure = Figure(figsize=(5.4, 3.3), dpi=100, facecolor="white")
        axis = figure.add_subplot(111)
        axis.plot(positions, values, color="#2563eb", marker="o", linewidth=2)
        axis.fill_between(positions, values, color="#93c5fd", alpha=0.25)
        axis.set_xticks(positions, labels)
        axis.grid(True, axis="y", alpha=0.25)
        axis.yaxis.set_major_formatter(FuncFormatter(self._money_axis))
        axis.tick_params(axis="x", labelsize=8)
        axis.tick_params(axis="y", labelsize=8)
        axis.set_ylabel("R$ por pessoa", fontsize=8)
        figure.tight_layout()
        self._embed_figure(self.line_frame, figure)

    def refresh(self, show_error: bool = False) -> None:
        month_text = self._current_month(show_error=show_error)
        if month_text is None:
            return

        self._clear_frame(self.indicators)
        self._clear_frame(self.alerts)
        data = self.dashboard_service.get_month_summary(month_text)

        break_even_value = self._optional_money(data["ponto_equilibrio"] if data["ponto_equilibrio_calculavel"] else None)
        indicators = [
            ("Lucro l\u00edquido", format_money(data["lucro_liquido"]), "Resultado depois de faturamento, custos vari\u00e1veis e custos fixos."),
            ("Custo vari\u00e1vel", format_money(data["custos_variaveis"]), "Custos que mudam conforme o volume de vendas."),
            ("Faturamento bruto", format_money(data["vendas_brutas"]), "Valor vendido antes de descontar taxas e custos."),
            ("Ponto de equil\u00edbrio", break_even_value, "Quanto precisa faturar para cobrir custos e n\u00e3o operar no preju\u00edzo."),
            ("Custo fixo", format_money(data["custos_fixos"]), "Gastos mensais que existem mesmo vendendo pouco."),
            ("Produtividade", self._optional_money(data["produtividade"]), "Mostra quanto a empresa gera ap\u00f3s custos vari\u00e1veis por pessoa ocupada."),
        ]
        for index, (title, value, text) in enumerate(indicators):
            self._indicator(title, value, text, index)

        self._draw_expense_pie(self.dashboard_service.get_expense_distribution(month_text))
        self._draw_productivity_line(self.dashboard_service.get_productivity_last_6_months(month_text))

        alerts = data["alertas"] or ["Nenhum alerta cr\u00edtico no momento."]
        for alert in alerts:
            help_label(self.alerts, f"\u2022 {alert}", 900).pack(anchor="w", fill="x", pady=3)
