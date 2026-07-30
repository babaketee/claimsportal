"""Internal Admin Dashboard — claims overview, SLA monitoring, and portfolio analytics."""
from __future__ import annotations

import datetime

import pandas as pd
import streamlit as st
from views.analytics_charts import render_analytics, clear_cache as _clear_analytics_cache

# SQLite-backed — Delta warehouse removed


# ---------------------------------------------------------------------------
# SQL execution helper — deprecated, returns empty DataFrame
# ---------------------------------------------------------------------------

def _run_sql(sql: str) -> pd.DataFrame:
    """Deprecated — Delta warehouse removed. Dashboard degrades gracefully."""
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Cached data loaders  (TTL 60 s) — return empty, will be refactored to SQLite
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def _load_status_counts() -> pd.DataFrame:
    return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def _load_type_distribution() -> pd.DataFrame:
    return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def _load_daily_trend() -> pd.DataFrame:
    return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def _load_all_claims(
    status_filter: str, type_filter: str,
    date_from: str, date_to: str,
) -> pd.DataFrame:
    return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def _load_sla() -> pd.DataFrame:
    return pd.DataFrame()


@st.cache_data(ttl=120, show_spinner=False)
def _load_vendors() -> pd.DataFrame:
    return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def _load_audit_log() -> pd.DataFrame:
    return pd.DataFrame()


def _refresh_all() -> None:
    """Clear all cached loaders and rerun the page."""
    _load_status_counts.clear()      # type: ignore[attr-defined]
    _load_type_distribution.clear()  # type: ignore[attr-defined]
    _load_daily_trend.clear()        # type: ignore[attr-defined]
    _load_all_claims.clear()         # type: ignore[attr-defined]
    _load_sla.clear()                # type: ignore[attr-defined]
    _load_vendors.clear()            # type: ignore[attr-defined]
    _load_audit_log.clear()          # type: ignore[attr-defined]
    _clear_analytics_cache()
    st.rerun()


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------

def render() -> None:
    col_title, col_btn = st.columns([5, 1])
    col_title.title("\u2699\ufe0f Internal Claims Dashboard")
    if col_btn.button("\U0001f504 Refresh", use_container_width=True, help="Force-refresh all data"):
        _refresh_all()
    st.caption("SQLite-backed \u00b7 auto-refreshes every 60 seconds.")

    tabs = st.tabs(
        ["\U0001f4ca Overview", "\U0001f4cb All Claims", "\U0001f3e2 Vendor Management",
         "\U0001f575\ufe0f Audit Log", "\u26a0\ufe0f SLA Monitor", "\U0001f4c8 Analytics"]
    )
    with tabs[0]: _overview()
    with tabs[1]: _all_claims()
    with tabs[2]: _vendor_management()
    with tabs[3]: _audit_log()
    with tabs[4]: _sla_monitor()
    with tabs[5]: _analytics()


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def _analytics() -> None:
    st.subheader("Portfolio Analytics")
    st.caption("Analytics via SQLite \u00b7 60-second cache.")
    render_analytics(show_refresh=False)


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

def _overview() -> None:
    st.subheader("Claims Overview")
    st.info("Dashboard is being migrated to SQLite. Data loaders will return empty until refactored.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Open Claims",  0)
    c2.metric("Pending Assessment", 0)
    c3.metric("Under Assessment",   0)
    c4.metric("Settled This Month", 0)


# ---------------------------------------------------------------------------
# All Claims
# ---------------------------------------------------------------------------

def _all_claims() -> None:
    st.subheader("All Claims")
    st.info("Refactoring to SQLite in progress.")


# ---------------------------------------------------------------------------
# Vendor Management
# ---------------------------------------------------------------------------

def _vendor_management() -> None:
    st.subheader("Vendor / Service Provider Management")
    st.info("Refactoring to SQLite in progress.")


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

def _audit_log() -> None:
    st.subheader("Audit Log")
    st.info("Refactoring to SQLite in progress.")


# ---------------------------------------------------------------------------
# SLA Monitor
# ---------------------------------------------------------------------------

def _sla_monitor() -> None:
    st.subheader("SLA Monitor")
    st.info("Refactoring to SQLite in progress.")


# ---------------------------------------------------------------------------
# SLA Thresholds (reference)
# ---------------------------------------------------------------------------

def _sla_thresholds() -> None:
    st.markdown("**SLA Thresholds (reference)**")
    thresholds = [
        {"Stage": "Assessor Assignment",        "SLA": "4 business hours after FNOL"},
        {"Stage": "Assessment Completion",       "SLA": "48 hours after appointment"},
        {"Stage": "Garage Estimate Submission",  "SLA": "48 hours after repair authorisation"},
        {"Stage": "Invoice Payment",             "SLA": "7 business days after invoice receipt"},
        {"Stage": "Final Settlement",            "SLA": "30 days from date of loss"},
    ]
    st.dataframe(thresholds, use_container_width=True, hide_index=True)
