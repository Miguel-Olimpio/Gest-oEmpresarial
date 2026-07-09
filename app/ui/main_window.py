"""Janela principal com sidebar."""

from __future__ import annotations

import ttkbootstrap as ttk

from app.config.settings import APP_TITLE
from app.services.accounting_report_service import AccountingReportService
from app.services.collaborator_service import CollaboratorService
from app.services.dashboard_service import DashboardService
from app.services.financial_service import FinancialService
from app.services.sales_service import SalesService
from app.ui.cash_flow_panel import CashFlowPanel
from app.ui.collaborators_panel import CollaboratorsPanel
from app.ui.cost_panels import FixedCostPanel, VariableCostPanel
from app.ui.dashboard_panel import DashboardPanel
from app.ui.sales_panel import SalesPanel


class MainWindow(ttk.Frame):
    def __init__(
        self,
        root,
        financial_service: FinancialService,
        sales_service: SalesService,
        dashboard_service: DashboardService,
        accounting_report_service: AccountingReportService,
        collaborator_service: CollaboratorService,
    ):
        super().__init__(root)
        self.root = root
        self.pack(fill="both", expand=True)
        self.panels: dict[str, ttk.Frame] = {}
        self._build_sidebar()
        self._build_content(financial_service, sales_service, dashboard_service, accounting_report_service, collaborator_service)
        self.show("Dashboard")

    def _build_sidebar(self) -> None:
        self.sidebar = ttk.Frame(self, width=240, padding=16, bootstyle="primary")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        ttk.Label(
            self.sidebar,
            text="Gest\u00e3o\nEmpresarial",
            font=("Segoe UI", 17, "bold"),
            bootstyle="inverse-primary",
            justify="center",
        ).pack(fill="x", pady=(2, 22))
        self.nav = ttk.Frame(self.sidebar, bootstyle="primary")
        self.nav.pack(fill="x")
        self.footer = ttk.Frame(self.sidebar, bootstyle="primary")
        self.footer.pack(side="bottom", fill="x")
        ttk.Separator(self.footer).pack(fill="x", pady=10)
        ttk.Label(self.footer, text="Desenvolvido por", bootstyle="inverse-primary", anchor="center").pack(fill="x")
        ttk.Label(self.footer, text="Miguel Olimpio", font=("Segoe UI", 10, "bold"), bootstyle="inverse-primary", anchor="center").pack(fill="x")
        ttk.Label(self.footer, text="Agente Local de Inova\u00e7\u00e3o", bootstyle="inverse-primary", anchor="center").pack(fill="x")

    def _build_content(
        self,
        financial_service: FinancialService,
        sales_service: SalesService,
        dashboard_service: DashboardService,
        accounting_report_service: AccountingReportService,
        collaborator_service: CollaboratorService,
    ) -> None:
        self.content = ttk.Frame(self)
        self.content.pack(side="left", fill="both", expand=True)
        self.content.rowconfigure(0, weight=1)
        self.content.columnconfigure(0, weight=1)
        definitions = [
            ("Dashboard", DashboardPanel(self.content, dashboard_service, accounting_report_service)),
            ("Vendas / Entradas", SalesPanel(self.content, sales_service)),
            ("Fluxo de Caixa", CashFlowPanel(self.content, financial_service, sales_service)),
            ("Custo Fixo", FixedCostPanel(self.content, financial_service)),
            ("Custo Vari\u00e1vel", VariableCostPanel(self.content, financial_service)),
            ("Colaboradores", CollaboratorsPanel(self.content, collaborator_service)),
        ]
        for name, panel in definitions:
            self.panels[name] = panel
            panel.grid(row=0, column=0, sticky="nsew")
            ttk.Button(self.nav, text=name, bootstyle="light", command=lambda item=name: self.show(item)).pack(fill="x", pady=4)

    def show(self, name: str) -> None:
        panel = self.panels[name]
        if hasattr(panel, "refresh"):
            panel.refresh()
        panel.tkraise()
        self.root.title(f"{APP_TITLE} - {name}")
