"""Shared analytics charts Ã¢ÂÂ live from main.claims.fnol_submissions.

Provides four cached data loaders and `render_analytics()` which renders
a 2ÃÂ2 Plotly chart grid:
  Ã¢ÂÂ¢ Claims by Type (bar)
  Ã¢ÂÂ¢ Status Distribution (donut)
  Ã¢ÂÂ¢ Settlement Trend Ã¢ÂÂ monthly (line)
  Ã¢ÂÂ¢ Avg Claim Age by Type (horizontal bar)

Usage in any view module:
    from views.analytics_charts import render_analytics
    render_analytics()
"""
from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st

# Register the Definite Assurance Plotly template on import
from views.brand import DA_COLORWAY, DA_SCALE_GREEN_RED, GREEN, RED  # noqa: F401

_FNOL         = "main.claims.fnol_submissions"


# ---------------------------------------------------------------------------
# SQL execution helper
# ---------------------------------------------------------------------------

def _run_sql(sql: str) -> pd.DataFrame:
    """Execute SQL against the configured warehouse; returns empty DataFrame on error."""
    try:
                resp = w.statement_execution.execute_statement(
            warehouse_id=            statement=sql,
            wait_timeout="30s",
        )
        if resp.status.state != StatementState.SUCCEEDED:
            err = resp.status.error.message if resp.status.error else str(resp.status.state)
            st.warning(f"Query returned non-success state: {err}")
            return pd.DataFrame()
        if not resp.result or not resp.result.data_array:
            return pd.DataFrame()
        cols = [c.name for c in resp.manifest.schema.columns]
        return pd.DataFrame(resp.result.data_array, columns=cols)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Delta query failed: {exc}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Cached data loaders  (TTL 60 s)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def _load_claims_by_type() -> pd.DataFrame:
    """Row count grouped by incident_type from fnol_submissions."""
    return _run_sql(f"""
        SELECT incident_type AS claim_type, COUNT(*) AS claims
        FROM {_FNOL}
        GROUP BY incident_type
        ORDER BY claims DESC
    """)


@st.cache_data(ttl=60, show_spinner=False)
def _load_status_distribution() -> pd.DataFrame:
    """Row count grouped by status from fnol_submissions."""
    return _run_sql(f"""
        SELECT status AS claim_status, COUNT(*) AS claims
        FROM {_FNOL}
        GROUP BY status
        ORDER BY claims DESC
    """)


@st.cache_data(ttl=60, show_spinner=False)
def _load_settlement_trend() -> pd.DataFrame:
    """Monthly total vs settled claims derived from fnol_submissions."""
    return _run_sql(f"""
        SELECT
            YEAR(submitted_at)  AS claim_year,
            MONTH(submitted_at) AS claim_month,
            COUNT(*) AS total_claims,
            COUNT(CASE WHEN status = 'Settled' THEN 1 END) AS settled_claims
        FROM {_FNOL}
        GROUP BY YEAR(submitted_at), MONTH(submitted_at)
        ORDER BY claim_year, claim_month
    """)


@st.cache_data(ttl=60, show_spinner=False)
def _load_avg_cycle_time() -> pd.DataFrame:
    """Average age-in-days per incident type (submission date to today)."""
    return _run_sql(f"""
        SELECT
            incident_type AS claim_type,
            ROUND(AVG(DATEDIFF(CURRENT_DATE, CAST(submitted_at AS DATE))), 1) AS avg_cycle_days
        FROM {_FNOL}
        GROUP BY incident_type
        ORDER BY avg_cycle_days DESC
    """)


# ---------------------------------------------------------------------------
# Refresh helper
# ---------------------------------------------------------------------------

def clear_cache() -> None:
    """Invalidate all analytics caches Ã¢ÂÂ call before st.rerun()."""
    _load_claims_by_type.clear()      # type: ignore[attr-defined]
    _load_status_distribution.clear() # type: ignore[attr-defined]
    _load_settlement_trend.clear()    # type: ignore[attr-defined]
    _load_avg_cycle_time.clear()      # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_analytics(show_refresh: bool = False) -> None:
    """Render four live analytics charts in a 2ÃÂ2 Plotly grid.

    Args:
        show_refresh: When True, displays a Refresh button that clears
                      all caches and reruns the page.
    """
    if show_refresh:
        if st.button("Ã°ÂÂÂ Refresh Analytics", help="Re-query Delta tables"):
            clear_cache()
            st.rerun()

    with st.spinner("Loading analytics from DeltaÃ¢ÂÂ¦"):
        type_df   = _load_claims_by_type()
        status_df = _load_status_distribution()
        trend_df  = _load_settlement_trend()
        cycle_df  = _load_avg_cycle_time()

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
            fig.update_layout(
                showlegend=False,
                height=300,
                margin=dict(t=8, b=50, l=40, r=10),
            )
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
            fig.update_layout(
                showlegend=True,
                legend=dict(orientation="v", x=1.02, y=0.5),
                height=300,
                margin=dict(t=8, b=8, l=10, r=10),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No status data available.")

    # ---- Row 2 ----------------------------------------------------------------
    col_l2, col_r2 = st.columns(2)

    with col_l2:
        st.markdown("**Settlement Trend (Monthly)**")
        if not trend_df.empty:
            trend_df["claim_year"]     = trend_df["claim_year"].astype(int)
            trend_df["claim_month"]    = trend_df["claim_month"].astype(int)
            trend_df["settled_claims"] = trend_df["settled_claims"].astype(float)
            trend_df["total_claims"]   = trend_df["total_claims"].astype(float)
            trend_df["period"] = trend_df.apply(
                lambda r: f"{int(r['claim_year'])}-{int(r['claim_month']):02d}", axis=1
            )
            fig = px.line(
                trend_df,
                x="period",
                y=["settled_claims", "total_claims"],
                markers=True,
                labels={"period": "", "value": "Claims", "variable": ""},
                color_discrete_map={
                    "settled_claims": "#00CC96",
                    "total_claims":   "#636EFA",
                },
            )
            newnames = {"settled_claims": "Settled", "total_claims": "Total"}
            fig.for_each_trace(lambda t: t.update(name=newnames.get(t.name, t.name)))
            fig.update_layout(
                height=300,
                margin=dict(t=8, b=50, l=40, r=10),
                legend=dict(orientation="h", y=1.08),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No monthly settlement data available.")

    with col_r2:
        st.markdown("**Avg Cycle Time by Type (days)**")
        if not cycle_df.empty:
            cycle_df["avg_cycle_days"] = cycle_df["avg_cycle_days"].astype(float)
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
            fig.update_layout(
                coloraxis_showscale=False,
                height=300,
                margin=dict(t=8, b=10, l=10, r=60),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No cycle time data available.")
