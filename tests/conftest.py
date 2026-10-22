"""Pytest configuration and fixtures for the claims portal test suite."""
from __future__ import annotations

import os
import sys

# Ensure the project root is on sys.path so `import core_api` works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Redirect the SQLite database to a temporary file for test isolation.

    Each test gets a fresh database so tests never interfere with each other
    or with the developer's local claims_operations.db.
    """
    db_path = str(tmp_path / "test_claims_operations.db")
    monkeypatch.setenv("CLAIMS_DB_PATH", db_path)
    monkeypatch.setenv("CORE_API_BASE_URL", "")
    monkeypatch.setenv("CORE_API_TOKEN", "")

    import core_api
    # Monkey-patch the DB path and re-init schema
    monkeypatch.setattr(core_api, "_DB_PATH", db_path)
    monkeypatch.setattr(core_api, "_CORE_API_BASE_URL", "")
    monkeypatch.setattr(core_api, "_CORE_API_KEY", "")
    core_api._init_db()
    yield


@pytest.fixture
def capi():
    """Return a fresh CoreAPI instance."""
    import core_api
    return core_api.CoreAPI()
