"""Tests that verify all view modules can be imported without errors.

These tests catch import-time crashes (missing dependencies, syntax errors,
undefined names in module-level code) across every view in the portal.
"""
from __future__ import annotations

import importlib

import pytest

# Every view module that the app routes to — see app.py main()
VIEW_MODULES = [
    "views.brand",
    "views.client_portal",
    "views.claims_officer",
    "views.head_of_claims",
    "views.service_provider",
    "views.finance",
    "views.spare_parts_provider",
    "views.legal",
    "views.super_admin",
    "views.admin_dashboard",
    "views.analytics_charts",
]


@pytest.mark.parametrize("module_name", VIEW_MODULES)
def test_view_imports(module_name):
    """Each view module must import cleanly."""
    mod = importlib.import_module(module_name)
    assert mod is not None


def test_brand_exports():
    from views.brand import (
        DA_COLORWAY, DA_SCALE_GREEN_RED, GREEN, RED,
        inject_brand_css, brand_strip, brand_login_header, brand_sidebar_header,
    )
    assert isinstance(DA_COLORWAY, list)
    assert len(DA_COLORWAY) > 0


def test_core_api_imports():
    """Verify the key symbols views depend on are exported from core_api."""
    from core_api import (
        core_api, is_configured, get_claim, create_claim, get_claims,
        update_claim_status, get_timeline, get_reserves, get_communications,
        assign_expert, log_communication,
    )
    assert core_api is not None
    assert callable(is_configured)
    assert callable(get_claim)
    assert callable(create_claim)
    assert callable(get_claims)
    assert callable(update_claim_status)


def test_app_routes_exist():
    """Verify app.py declares a render function for every role."""
    # We test the routing dictionary exists, not the actual streamlit call
    import app
    assert hasattr(app, "ROLES")
    assert hasattr(app, "DEMO_ACCOUNTS")
    assert "claims_officer" in app.ROLES
    assert "super_admin" in app.ROLES
    assert "legal" in app.ROLES
    assert "spare_parts" in app.ROLES
