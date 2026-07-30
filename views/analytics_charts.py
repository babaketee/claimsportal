"""Shared analytics charts — live KPI view support.

Provides four cached data loaders and `render_analytics()` which renders
a 2×2 Plotly chart grid:
  • Claims by Type (bar)
  • Status Distribution (donut)
  • Settlement Trend — monthly (line)
  • Avg Claim Age by Type (horizontal bar)

Environment variables for live data:
  ANALYTICS_SQL_HOST   — Databricks host (e.g. https://dbc-xxx.cloud.databricks.com)
  ANALYTICS_SQL_TOKEN  — Databricks personal access token
  ANALYTICS_SQL_WAREHOUSE_ID — Databricks warehouse ID (optional, uses serverless if omitted)
  ANALYTICS_SQL_CONNECTION_STRING — Alternative: any SQLAlchemy connection string
  ANALYTICS_KPI_VIEW   — Full view name (default: claims.claims_kpi_view)

Usage:
    from views.analytics_charts import render_analytics
    render_analytics()
"""

from __future__ import annotations

import os
import warnings

import pandas as pd
import plotly.express as px
import streamlit as st

# Register the Definite Assurance Plotly template on import
from views.brand import DA_COLORWAY, DA_SCALE_GREEN_RED, GREEN, RED  # noqa: F401

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

_SQL_HOST = os.environ.get("ANALYTICS_SQL_HOST", "").rstrip("/")
_SQL_TOKEN = os.environ.get("ANALYTICS_SQL_TOKEN", "")
_SQL_WAREHOUSE = os.environ.get("ANALYTICS_SQL_WAREHOUSE_ID", "")
_SQL_CONN = os.environ.get("ANALYTICS_SQL_CONNECTION_STRING", "")
_KPI_VIEW = os.environ.get("ANALYTICS_KPI_VIEW", "claims.claims_kpi_view")

_DEMO_MODE = not (_SQL_HOST and _SQL_TOKEN) and not _SQL_CONN


# ---------------------------------------------------------------------------
# SQL execution helper
# ---------------------------------------------------------------------------

def _run_sql(sql: str) -> pd.DataFrame:
    """Execute SQL and return results as DataFrame. Supports Databricks and SQLAlchemy."""
    if _DEMO_MODE:
        return pd.DataFrame()

    try:
        if _SQL_HOST and _SQL_TOKEN:
            # Databricks SQL warehouses API
            import urllib.request
            import json

            warehouse_id = _SQL_WAREHOUSE or os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
            endpoint = f"{_SQL_HOST}/api/2.0/sql/statements"
            
            payload = json.dumps({
                "statement": sql,
                "warehouse_id": warehouse_id,
                "wait_timeout": "60s",
            }).encode("utf-8")

            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers={
                    "Authorization": f"Bearer {_SQL_TOKEN}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.load(resp)

            if result.get("status", {}).get("state") != "SUCCEEDED":
                err = result.get("status", {}).get("error", {})
                st.warning(f"Query failed: {err.get('message', result.get('status', {}).get('state'))}")
                return pd.DataFrame()

            schema = result.get("manifest", {}).get("schema", {}).get("columns", [])
            rows = result.get("result", {}).get("data_array", [])
            if not rows:
                return pd.DataFrame(columns=[c["name"] for c in schema])

            return pd.DataFrame(rows, columns=[c["name"] for c in schema])

        elif _SQL_CONN:
            # SQLAlchemy-compatible (PostgreSQL, MySQL, etc.)
            try:
                from sqlalchemy import create_engine
            except ImportError:
                st.warning("SQLAlchemy not installed. Install with: pip install sqlalchemy")
                return pd.DataFrame()

            engine = create_engine(_SQL_CONN)
            with engine.connect() as conn:
                return pd.read_sql(sql, conn)

        else:
            return pd.DataFrame()

    except Exception as exc:
        warnings.warn(f"analytics_charts _run_sql failed: {exc}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# KPI view column mapping (claims.claims_kpi_view expected schema)
# Expected columns: claim_type, claim_status, submitted_month, total_claims,
#                   settled_claims, avg_cycle_days
# ---------------------------------------------------------------------------

def _load_claims_by_type() -> pd.DataFrame:
    if _DEMO_MODE:
        return pd.DataFrame({
            "claim_type": ["Motor Bumper", "Windscreen Crack", "Theft", "Fire Damage", "Water Ingress", "Third Party Bodily Harm"],
            "claims": [42, 28, 15, 9, 7, 12],
        })
    df = _run_sql(f"SELECT incident_type AS claim_type, COUNT(*) AS claims FROM {_KPI_VIEW} GROUP BY incident_type ORDER BY claims DESC")
    return df if not df.empty else pd.DataFrame({"claim_type": [], "claims": []})


def _load_status_distribution() -> pd.DataFrame:
    if _DEMO_MODE:
        return pd.DataFrame({
            "claim_status": ["FNOL Received", "Assigned", "Assessment", "Approved", "Settled", "Rejected", "Escalated"],
            "claims": [31, 24, 38, 19, 44, 8, 11],
        })
    df = _run_sql(f"SELECT status AS claim_status, COUNT(*) AS claims FROM {_KPI_VIEW} GROUP BY status ORDER BY claims DESC")
    return df if not df.empty else pd.DataFrame({"claim_status": [], "claims": []})


def _load_settlement_trend() -> pd.DataFrame:
    if _DEMO_MODE:
        return pd.DataFrame({
            "period": ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
                       "2026-01", "2026-02", "2026-03", "2026-04", "2026-05"],
            "total_claims": [18, 22, 31, 28, 35, 41, 29, 33, 38, 42, 47],
            "settled_claims": [5, 9, 14, 18, 21, 27, 18, 22, 28, 33, 39],
        })
    df = _run_sql(f"""
        SELECT
            DATE_TRUNC('month', submitted_at) AS period,
            COUNT(*) AS total_claims,
            COUNT(CASE WHEN status = 'Settled' THEN 1 END) AS settled_claims
        FROM {_KPI_VIEW}
        GROUP BY DATE_TRUNC('month', submitted_at)
        ORDER BY period DESC
        LIMIT 24
    """)
    if df.empty:
        return df
    df["period"] = pd.to_datetime(df["period"]).dt.strftime("%Y-%m")
    return df


def _load_avg_cycle_time() -> pd.DataFrame:
    if _DEMO_MODE:
        return pd.DataFrame({
            "claim_type": ["Third Party Bodily Harm", "Fire Damage", "Theft", "Water Ingress", "Motor Bumper", "Windscreen Crack"],
            "avg_cycle_days": [34.2, 28.7, 21.3, 18.5, 9.2, 4.1],
        })
    df = _run_sql(f"""
        SELECT
            incident_type AS claim_type,
            AVG(DATEDIFF(CURRENT_DATE, CAST(submitted_at AS DATE))) AS avg_cycle_days
        FROM {_KPI_VIEW}
        GROUP BY incident_type
        ORDER BY avg_cycle_days DESC
    """)
    return df if not df.empty else pd.DataFrame({"claim_type": [], "avg_cycle_days": []})


# ---------------------------------------------------------------------------
# Cached data loaders (TTL 60 s)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def _cached_claims_by_type() -> pd.DataFrame:
    return _load_claims_by_type()


@st.cache_data(ttl=60, show_spinner=False)
def _cached_status_distribution() -> pd.DataFrame:
    return _load_status_distribution()


@st.cache_data(ttl=60, show_spinner=False)
def _cached_settlement_trend() -> pd.DataFrame:
    return _load_settlement_trend()


@st.cache_data(ttl=60, show_spinner=False)
def _cached_avg_cycle_time() -> pd.DataFrame:
    return _load_avg_cycle_time()


# ---------------------------------------------------------------------------
# Refresh helper
# ---------------------------------------------------------------------------

def clear_cache() -> None:
    """Invalidate all analytics caches — call before st.rerun()."""
    _cached_claims_by_type.clear()      # type: ignore[attr-defined]
    _cached_status_distribution.clear() # type: ignore[attr-defined]
    _cached_settlement_trend.clear()   # type: ignore[attr-defined]
    _cached_avg_cycle_time.clear()     # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_analytics(show_refresh: bool = False) -> None:
    """Render four analytics charts in a 2×2 Plotly grid."""
    if show_refresh:
        if st.button("🔄 Refresh Analytics", help="Re-query KPI view"):
            clear_cache()
            st.rerun()

    with st.spinner("Loading analytics from KPI view…"):
        type_df   = _cached_claims_by_type()
        status_df = _cached_status_distribution()
        trend_df  = _cached_settlement_trend()
        cycle_df  = _cached_avg_cycle_time()

    mode_label = "📊 Demo data" if _DEMO_MODE else "📈 Live KPI data"
    if _DEMO_MODE:
        st.info(f"{mode_label} — set ANALYTICS_SQL_HOST / ANALYTICS_SQL_TOKEN secrets to connect live source")
    else:
        st.caption(f"{mode_label} — view: `{_KPI_VIEW}`")

    # ---- Row 1 ----------------------------------------------------------------
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("**Claims by Type**")
        if not type_df.empty:
            type_df["claims"] = type_df["claims"].astype(int)
            fig = px.bar(
                type_df,
                x="claim_type",
                y="claims",
                color="claim_type",
                labels={"claim_type": "", "claims": "Claims"},
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(showlegend=False, height=300, margin=dict(t=8, b=50, l=40, r=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No claims data available.")

    with col_r:
        st.markdown("**Status Distribution**")
        if not status_df.empty:
            status_df["claims"] = status_df["claims"].astype(int)
            fig = px.pie(
                status_df,
                names="claim_status",
                values="claims",
                hole=0.42,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(showlegend=True, legend=dict(orientation="v", x=1.02, y=0.5), height=300, margin=dict(t=8, b=8, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No status data available.")

    # ---- Row 2 ----------------------------------------------------------------
    col_l2, col_r2 = st.columns(2)

    with col_l2:
        st.markdown("**Settlement Trend (Monthly)**")
        if not trend_df.empty:
            for col in ["settled_claims", "total_claims"]:
                if col in trend_df.columns:
                    trend_df[col] = pd.to_numeric(trend_df[col], errors="coerce")
            fig = px.line(
                trend_df,
                x="period",
                y=["settled_claims", "total_claims"],
                markers=True,
                labels={"period": "", "value": "Claims", "variable": ""},
                color_discrete_map={"settled_claims": GREEN, "total_claims": RED},
            )
            newnames = {"settled_claims": "Settled", "total_claims": "Total"}
            fig.for_each_trace(lambda t: t.update(name=newnames.get(t.name, t.name)))
            fig.update_layout(height=300, margin=dict(t=8, b=50, l=40, r=10), legend=dict(orientation="h", y=1.08))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No monthly settlement data available.")

    with col_r2:
        st.markdown("**Avg Cycle Time by Type (days)**")
        if not cycle_df.empty:
            cycle_df["avg_cycle_days"] = pd.to_numeric(cycle_df["avg_cycle_days"], errors="coerce")
            fig = px.bar(
                cycle_df,
                x="avg_cycle_days",
                y="claim_type",
                orientation="h",
                labels={"avg_cycle_days": "Avg Days", "claim_type": ""},
                color="avg_cycle_days",
                color_continuous_scale="RdYlGn_r",
                text="avg_cycle_days",
            )
            fig.update_traces(texttemplate="%{text:.1f}d", textposition="outside")
            fig.update_layout(coloraxis_showscale=False, height=300, margin=dict(t=8, b=10, l=10, r=60))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No cycle time data available.")
