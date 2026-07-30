"""Shared analytics charts — demo data version.

Provides four cached data loaders and `render_analytics()` which renders
a 2×2 Plotly chart grid:
  • Claims by Type (bar)
  • Status Distribution (donut)
  • Settlement Trend — monthly (line)
  • Avg Claim Age by Type (horizontal bar)

Usage in any view module:
    from views.analytics_charts import render_analytics
    render_analytics()
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

# Register the Definite Assurance Plotly template on import
from views.brand import DA_COLORWAY, DA_SCALE_GREEN_RED, GREEN, RED  # noqa: F401

_DEMO_MODE = True


# ---------------------------------------------------------------------------
# Demo data generators
# ---------------------------------------------------------------------------

def _demo_claims_by_type() -> pd.DataFrame:
    return pd.DataFrame({
        "claim_type": ["Motor Bumper", "Windscreen Crack", "Theft", "Fire Damage", "Water Ingress", "Third Party Bodily Harm"],
        "claims": [42, 28, 15, 9, 7, 12],
    })


def _demo_status_distribution() -> pd.DataFrame:
    return pd.DataFrame({
        "claim_status": ["FNOL Received", "Assigned", "Assessment", "Approved", "Settled", "Rejected", "Escalated"],
        "claims": [31, 24, 38, 19, 44, 8, 11],
    })


def _demo_settlement_trend() -> pd.DataFrame:
    return pd.DataFrame({
        "claim_year":  [2025, 2025, 2025, 2025, 2025, 2025, 2026, 2026, 2026, 2026, 2026],
        "claim_month": [1,     2,     3,     4,     5,     6,     1,     2,     3,     4,     5],
        "total_claims":   [18, 22, 31, 28, 35, 41, 29, 33, 38, 42, 47],
        "settled_claims": [5,  9,  14, 18, 21, 27, 18, 22, 28, 33, 39],
        "period": ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
                   "2026-01", "2026-02", "2026-03", "2026-04", "2026-05"],
    })


def _demo_avg_cycle_time() -> pd.DataFrame:
    return pd.DataFrame({
        "claim_type": ["Third Party Bodily Harm", "Fire Damage", "Theft", "Water Ingress", "Motor Bumper", "Windscreen Crack"],
        "avg_cycle_days": [34.2, 28.7, 21.3, 18.5, 9.2, 4.1],
    })


# ---------------------------------------------------------------------------
# Cached data loaders (TTL 60 s) — demo mode returns static sample data
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def _load_claims_by_type() -> pd.DataFrame:
    return _demo_claims_by_type()


@st.cache_data(ttl=60, show_spinner=False)
def _load_status_distribution() -> pd.DataFrame:
    return _demo_status_distribution()


@st.cache_data(ttl=60, show_spinner=False)
def _load_settlement_trend() -> pd.DataFrame:
    return _demo_settlement_trend()


@st.cache_data(ttl=60, show_spinner=False)
def _load_avg_cycle_time() -> pd.DataFrame:
    return _demo_avg_cycle_time()


# ---------------------------------------------------------------------------
# Refresh helper
# ---------------------------------------------------------------------------

def clear_cache() -> None:
    """Invalidate all analytics caches — call before st.rerun()."""
    _load_claims_by_type.clear()      # type: ignore[attr-defined]
    _load_status_distribution.clear() # type: ignore[attr-defined]
    _load_settlement_trend.clear()    # type: ignore[attr-defined]
    _load_avg_cycle_time.clear()      # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_analytics(show_refresh: bool = False) -> None:
    """Render four analytics charts in a 2×2 Plotly grid (demo data)."""
    if show_refresh:
        if st.button("🔄 Refresh Analytics", help="Refresh demo data"):
            clear_cache()
            st.rerun()

    with st.spinner("Loading analytics…"):
        type_df   = _load_claims_by_type()
        status_df = _load_status_distribution()
        trend_df  = _load_settlement_trend()
        cycle_df  = _load_avg_cycle_time()

    # Demo mode notice
    st.info("📊 Demo data — connect core_api for live claims analytics")

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
            trend_df["claim_year"]     = trend_df["claim_year"].astype(int)
            trend_df["claim_month"]   = trend_df["claim_month"].astype(int)
            trend_df["settled_claims"] = trend_df["settled_claims"].astype(float)
            trend_df["total_claims"]  = trend_df["total_claims"].astype(float)
            fig = px.line(
                trend_df,
                x="period",
                y=["settled_claims", "total_claims"],
                markers=True,
                labels={"period": "", "value": "Claims", "variable": ""},
                color_discrete_map={"settled_claims": "#00CC96", "total_claims": "#636EFA"},
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
            fig.update_layout(coloraxis_showscale=False, height=300, margin=dict(t=8, b=10, l=10, r=60))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No cycle time data available.")
