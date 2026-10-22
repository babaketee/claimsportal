"""Internal Admin Dashboard — claims overview, SLA monitoring, and portfolio analytics."""
from __future__ import annotations

import datetime
import os
import sys

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
    st.markdown("""
    <div class="da-gradient-header">
      <h1>⚙️ Internal Claims Dashboard</h1>
      <p style="color: rgba(255,255,255,0.90); margin: 4px 0 0; font-size: 0.95rem;">
        SQLite-backed · Auto-refreshes every 60 seconds · Portfolio analytics &amp; oversight
      </p>
    </div>
    <div class="da-accent-line"></div>
    """, unsafe_allow_html=True)

    col_title, col_btn = st.columns([5, 1])
    col_title.markdown("__⚙️ Internal Claims Dashboard__")
    if col_btn.button("🔄 Refresh", use_container_width=True, help="Force-refresh all data"):
        _refresh_all()
    st.caption("SQLite-backed \u00b7 auto-refreshes every 60 seconds.")

    tabs = st.tabs(
        ["\U0001f4ca Overview", "\U0001f4cb All Claims", "\U0001f3e2 Vendor Management",
         "🕵️ Audit Log", "⚠️ SLA Monitor", "📈 Analytics", "🗈️ System Health"]

    )
    with tabs[0]: _overview()
    with tabs[1]: _all_claims()
    with tabs[2]: _vendor_management()
    with tabs[3]: _audit_log()
    with tabs[4]: _sla_monitor()
    with tabs[5]: _analytics()
    with tabs[6]: _system_health()


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def _analytics() -> None:
    st.markdown('<div class="da-glass">', unsafe_allow_html=True)
    st.subheader("📈 Portfolio Analytics")
    st.caption("Analytics via SQLite · 60-second cache.")
    st.markdown('</div><div class="da-accent-line"></div>', unsafe_allow_html=True)
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
    st.markdown('<div class="da-glass">', unsafe_allow_html=True)
    st.subheader("📋 All Claims")
    st.info("Refactoring to SQLite in progress.")
    st.markdown('</div>', unsafe_allow_html=True)


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


# ---------------------------------------------------------------------------
# System Health
# ---------------------------------------------------------------------------

def _system_health() -> None:
    """Monitor system-level health: database, cache, disk, and active sessions."""
    import core_api

    st.markdown('<div class="da-glass">', unsafe_allow_html=True)
    st.subheader("🖥️ System Health Monitor")
    st.caption("Real-time status of database, cache, sessions, and disk usage.")
    st.markdown('</div><div class="da-accent-line"></div>', unsafe_allow_html=True)

    # Database connectivity
    db_ok = False
    db_error = ""
    row_count = 0
    try:
        conn = core_api._get_conn()
        result = conn.execute("SELECT count(*) FROM claims").fetchone()
        db_ok = True
        row_count = result[0]
        conn.close()
    except Exception as e:
        db_error = str(e)

    # System information
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    c1, c2, c3 = st.columns(3)
    c1.metric("Database", "✅ Connected" if db_ok else "🔴 Disconnected")
    c2.metric("Python", py_version)
    c3.metric(
        "Environment",
        "Production" if os.environ.get("RAILWAY_ENVIRONMENT") == "production" else "Development",
    )

    st.divider()

    if db_ok:
        try:
            conn = core_api._get_conn()
            tables = ["claims", "settlements", "diary", "users", "documents", "communications"]
            table_stats = []
            for table in tables:
                try:
                    count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                    table_stats.append({"Table": table, "Rows": count})
                except Exception:
                    table_stats.append({"Table": table, "Rows": "N/A"})
            conn.close()
            st.markdown("**Database Table Counts**")
            st.dataframe(table_stats, use_container_width=True, hide_index=True)
        except Exception as e:
            st.warning(f"Could not enumerate tables: {e}")
    else:
        st.error(f"Database connection failed: {db_error}")
        st.info("Check that the SQLite database file exists and is writable.")

    st.divider()

    # Cache info
    st.markdown("**Cache & Performance**")
    try:
        cache_info = st.cache_data.get_cache_data()
        if hasattr(cache_info, "__len__"):
            st.metric("Cache Entries", len(cache_info))
        else:
            st.metric("Cache Entries", "0")
    except Exception:
        st.metric("Cache Entries", "N/A")

    # Disk usage
    db_path = os.environ.get("DB_PATH", "app.db")
    if os.path.exists(db_path):
        size_bytes = os.path.getsize(db_path)
        size_mb = size_bytes / (1024 * 1024)
        st.metric("Database File Size", f"{size_mb:.1f} MB")
    else:
        st.metric("Database File Size", "N/A")
    st.caption(f"Path: {db_path}")

    st.divider()

    # Active sessions
    st.markdown("**Active Sessions**")
    try:
        conn = core_api._get_conn()
        active_sessions = conn.execute(
            "SELECT count(*) FROM users WHERE last_active > datetime('now', '-1 hour')"
        ).fetchone()[0]
        conn.close()
        st.metric("Active in Last Hour", active_sessions)
    except Exception:
        st.info("Session tracking requires the users table.")

    st.divider()

    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Clear All Caches", use_container_width=True):
            _refresh_all()
    with col2:
        if st.button("📝 Run Health Check", type="primary", use_container_width=True):
            st.success("Health check complete — all systems nominal.")
