"""Inicialização do aplicativo."""

from __future__ import annotations

from dataclasses import dataclass

import ttkbootstrap as ttk

from app.config.paths import (
    get_audit_db_path,
    get_backups_dir,
    get_collaborators_db_path,
    get_data_dir,
    get_financial_db_path,
    get_icon_dir,
    get_pdfs_dir,
    get_sales_db_path,
)
from app.config.settings import APP_THEME, APP_TITLE
from app.repositories.excel_database import ExcelDatabase
from app.repositories.collaborator_repository import CollaboratorRepository
from app.repositories.excel_schema import AUDIT_SHEETS_CONFIG, COLLABORATORS_SHEETS_CONFIG, FINANCIAL_SHEETS_CONFIG, SALES_SHEETS_CONFIG
from app.repositories.financial_repository import CashFlowRepository, CostCategoryRepository, FixedCostRepository, VariableCostRepository
from app.repositories.sales_repository import SalesRepository
from app.services.accounting_report_service import AccountingReportService
from app.services.collaborator_service import CollaboratorService
from app.services.dashboard_service import DashboardService
from app.services.financial_service import FinancialService
from app.services.sales_service import SalesService
from app.ui.main_window import MainWindow
from app.ui.window_icon import apply_window_icon


@dataclass(slots=True)
class AppServices:
    financial: FinancialService
    sales: SalesService
    dashboard: DashboardService
    accounting_report: AccountingReportService
    collaborator: CollaboratorService


def ensure_runtime_dirs() -> None:
    get_data_dir()
    get_pdfs_dir()
    get_backups_dir()
    get_icon_dir()


def ensure_databases() -> None:
    ensure_runtime_dirs()
    databases = [
        ExcelDatabase(get_financial_db_path(), FINANCIAL_SHEETS_CONFIG),
        ExcelDatabase(get_sales_db_path(), SALES_SHEETS_CONFIG),
        ExcelDatabase(get_collaborators_db_path(), COLLABORATORS_SHEETS_CONFIG),
        ExcelDatabase(get_audit_db_path(), AUDIT_SHEETS_CONFIG),
    ]
    for database in databases:
        database.ensure_database()


def build_services() -> AppServices:
    ensure_databases()
    financial_db = ExcelDatabase(get_financial_db_path(), FINANCIAL_SHEETS_CONFIG)
    sales_db = ExcelDatabase(get_sales_db_path(), SALES_SHEETS_CONFIG)
    collaborators_db = ExcelDatabase(get_collaborators_db_path(), COLLABORATORS_SHEETS_CONFIG)

    collaborator = CollaboratorService(CollaboratorRepository(collaborators_db))
    financial = FinancialService(
        FixedCostRepository(financial_db),
        VariableCostRepository(financial_db),
        CashFlowRepository(financial_db),
        CostCategoryRepository(financial_db),
        collaborator,
    )
    sales = SalesService(SalesRepository(sales_db), financial)
    dashboard = DashboardService(financial, sales, collaborator)
    accounting_report = AccountingReportService(financial, sales)
    return AppServices(financial, sales, dashboard, accounting_report, collaborator)


def main() -> None:
    services = build_services()
    root = ttk.Window(themename=APP_THEME)
    root.title(APP_TITLE)
    root.geometry("1280x780")
    root.minsize(1100, 680)
    apply_window_icon(root)
    MainWindow(root, services.financial, services.sales, services.dashboard, services.accounting_report, services.collaborator)
    root.mainloop()


if __name__ == "__main__":
    main()
