"""Caminhos relativos seguros para desenvolvimento e PyInstaller."""

from __future__ import annotations

import os
import sys

from app.config.settings import AUDIT_DB_FILENAME, COLLABORATORS_DB_FILENAME, FINANCIAL_DB_FILENAME, SALES_DB_FILENAME

_ROOT_OVERRIDE: str | None = None


def set_root_override(path: str | None) -> None:
    global _ROOT_OVERRIDE
    _ROOT_OVERRIDE = os.path.abspath(path) if path else None


def is_packaged() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_project_root() -> str:
    if _ROOT_OVERRIDE:
        return _ROOT_OVERRIDE
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", ".."))


def get_app_base_path() -> str:
    if _ROOT_OVERRIDE:
        path = _ROOT_OVERRIDE
    elif is_packaged():
        path = os.path.dirname(os.path.abspath(sys.executable))
    else:
        path = get_project_root()
    os.makedirs(path, exist_ok=True)
    return path


def _ensure_child(name: str) -> str:
    path = os.path.join(get_app_base_path(), name)
    os.makedirs(path, exist_ok=True)
    return path


def get_data_dir() -> str:
    return _ensure_child("data")


def get_pdfs_dir() -> str:
    return _ensure_child("pdfs")


def get_backups_dir() -> str:
    return _ensure_child("backups")


def get_icon_dir() -> str:
    return _ensure_child("icon")


def get_financial_db_path() -> str:
    return os.path.join(get_data_dir(), FINANCIAL_DB_FILENAME)


def get_sales_db_path() -> str:
    return os.path.join(get_data_dir(), SALES_DB_FILENAME)


def get_collaborators_db_path() -> str:
    return os.path.join(get_data_dir(), COLLABORATORS_DB_FILENAME)


def get_audit_db_path() -> str:
    return os.path.join(get_data_dir(), AUDIT_DB_FILENAME)


def get_icon_path() -> str:
    roots: list[str] = []
    if is_packaged():
        roots.append(os.path.dirname(os.path.abspath(sys.executable)))
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            roots.append(str(bundle_dir))
    roots.append(get_project_root())

    candidates = [os.path.join(root, "icon", "icon.ico") for root in roots]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return candidates[0]
