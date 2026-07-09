from __future__ import annotations

import pytest

from app.config.paths import set_root_override
from app.main import build_services, ensure_databases


@pytest.fixture()
def services(tmp_path):
    set_root_override(str(tmp_path))
    ensure_databases()
    app_services = build_services()
    yield app_services
    set_root_override(None)

