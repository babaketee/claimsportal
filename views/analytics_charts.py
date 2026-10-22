"""Shared analytics charts — live KPI view support.

Provides four cached data loaders and render_analytics() which renders
a 2x2 Plotly chart grid:
  - Claims by Type (bar)
  - Status Distribution (donut)
  - Settlement Trend - monthly (line)
  - Avg Claim Age by Type (horizontal bar)

Also provides render_advanced_analytics() rendering a 3-row grid:
  - Reserve vs Actual (stacked bar)
  - SLA Compliance (gauge)
  - Claims Aging (histogram / bar)
  - Expert Performance (horizontal bar)
  - WHT Summary (stacked bar)

Environment variables for live data:
  ANALYTICS_SQL_HOST   - Databricks host (e.g. https://dbc-xxx.cloud.databricks.com)
  ANALYTICS_SQL_TOKEN  - Databricks personal access token
  ANALYTICS_SQL_WAREHOUSE_ID - Databricks warehouse ID (optional)
  ANALYTICS_SQL_CONNECTION_STRING - Alternative: any SQLAlchemy connection string
  ANALYTICS_KPI_VIEW   - Full view name (default: claims.claims_kpi_view)

Usage:
    from views.analytics_charts import render_analytics
    render_analytics()
"""

from __future__ import annotations

import os
import warnings

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from views.brand import (  # noqa: F401
    BLUE,
    BLUE_10,
    BLUE_30,
    GREEN,
    GREEN_10,
    GREEN_30,
    RED,
    RED_10,
    DA_COLORWAY,
    DA_SCALE_GREEN_RED,
)

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
# Advanced analytics loaders (new)
# ---------------------------------------------------------------------------

def _load_reserve_vs_actual() -> pd.DataFrame:
    """Compare reserved amounts vs actual incurred amounts by claim type."""
    if _DEMO_MODE:
        return pd.DataFrame({
            "claim_type": ["Motor Bumper", "Windscreen Crack", "Theft", "Fire Damage",
                           "Water Ingress", "Third Party Bodily Harm"],
            "reserved":   [2_800_000, 420_000, 1_500_000, 2_200_000, 950_000, 3_500_000],
            "actual":     [3_150_000, 380_000, 1_750_000, 2_100_000, 1_120_000, 3_800_000],
        })
    df = _run_sql(f"""
        SELECT
            incident_type AS claim_type,
            SUM(reserve_amount) AS reserved,
            SUM(actual_incurred) AS actual
        FROM {_KPI_VIEW}
        GROUP BY incident_type
        ORDER BY reserved DESC
    """)
    return df if not df.empty else pd.DataFrame({"claim_type": [], "reserved": [], "actual": []})


def _load_sla_compliance() -> pd.DataFrame:
    """Overall SLA compliance percentage (claims settled within 30 days)."""
    if _DEMO_MODE:
        return pd.DataFrame({"sla_pct": [78.5]})
    df = _run_sql(f"""
        SELECT ROUND(
            100.0 * SUM(CASE WHEN settle_days <= 30 THEN 1 ELSE 0 END) / COUNT(*), 2
        ) AS sla_pct
        FROM {_KPI_VIEW}
    """)
    return df if not df.empty else pd.DataFrame({"sla_pct": []})


def _load_claims_aging() -> pd.DataFrame:
    """Distribution of open claims across age buckets (days since submission)."""
    if _DEMO_MODE:
        return pd.DataFrame({
            "age_bucket": ["0-7 days", "8-14 days", "15-30 days", "31-60 days", "61-120 days", "120+ days"],
            "claims":      [22, 18, 15, 9, 7, 5],
        })
    df = _run_sql(f"""
        SELECT
            CASE
                WHEN age_days <= 7   THEN '0-7 days'
                WHEN age_days <= 14  THEN '8-14 days'
                WHEN age_days <= 30  THEN '15-30 days'
                WHEN age_days <= 60  THEN '31-60 days'
                WHEN age_days <= 120 THEN '61-120 days'
                ELSE '120+ days'
            END AS age_bucket,
            COUNT(*) AS claims
        FROM (
            SELECT DATEDIFF(CURRENT_DATE, CAST(submitted_at AS DATE)) AS age_days
            FROM {_KPI_VIEW}
            WHERE status NOT IN ('Settled', 'Rejected')
        ) t
        GROUP BY age_bucket
        ORDER BY MIN(age_days)
    """)
    return df if not df.empty else pd.DataFrame({"age_bucket": [], "claims": []})


def _load_expert_performance() -> pd.DataFrame:
    """Average resolution days by assigned expert / adjuster."""
    if _DEMO_MODE:
        return pd.DataFrame({
            "expert":    ["S. Karimi", "T. Mutua", "J. Njeru", "A. Ochieng", "M. Wanjiru"],
            "avg_days":  [18.5, 22.1, 14.3, 26.7, 19.8],
        })
    df = _run_sql(f"""
        SELECT
            assigned_to AS expert,
            AVG(DATEDIFF(CURRENT_DATE, CAST(submitted_at AS DATE))) AS avg_days
        FROM {_KPI_VIEW}
        WHERE assigned_to IS NOT NULL
        GROUP BY assigned_to
        ORDER BY avg_days ASC
    """)
    return df if not df.empty else pd.DataFrame({"expert": [], "avg_days": []})


def _load_wht_summary() -> pd.DataFrame:
    """Withholding Tax breakdown by claim type.

    Returns gross settlement, WHT withheld, and net payable so the two
    segments (net + wht) can be stacked to reconstruct gross.
    """
    if _DEMO_MODE:
        return pd.DataFrame({
            "claim_type": ["Motor Bumper", "Windscreen Crack", "Theft", "Fire Damage",
                           "Water Ingress", "Third Party Bodily Harm"],
            "gross":       [3_150_000, 380_000, 1_750_000, 2_100_000, 1_120_000, 3_800_000],
            "wht":         [315_000, 38_000, 175_000, 210_000, 112_000, 380_000],
            "net":         [2_835_000, 342_000, 1_575_000, 1_890_000, 1_008_000, 3_420_000],
        })
    df = _run_sql(f"""
        SELECT
            incident_type AS claim_type,
            SUM(settlement_amount) AS gross,
            SUM(settlement_amount * 0.10) AS wht,
            SUM(settlement_amount * 0.90) AS net
        FROM {_KPI_VIEW}
        GROUP BY incident_type
        ORDER BY gross DESC
    """)
    return df if not df.empty else pd.DataFrame({"claim_type": [], "gross": [], "wht": [], "net": []})


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
# Cached advanced analytics loaders (TTL 60 s)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def _cached_reserve_vs_actual() -> pd.DataFrame:
    return _load_reserve_vs_actual()


@st.cache_data(ttl=60, show_spinner=False)
def _cached_sla_compliance() -> pd.DataFrame:
    return _load_sla_compliance()


@st.cache_data(ttl=60, show_spinner=False)
def _cached_claims_aging() -> pd.DataFrame:
    return _load_claims_aging()


@st.cache_data(ttl=60, show_spinner=False)
def _cached_expert_performance() -> pd.DataFrame:
    return _load_expert_performance()


@st.cache_data(ttl=60, show_spinner=False)
def _cached_wht_summary() -> pd.DataFrame:
    return _load_wht_summary()


# ---------------------------------------------------------------------------
# Refresh helper
# ---------------------------------------------------------------------------

def clear_cache() -> None:
    """Invalidate all analytics caches - call before st.rerun()."""
    _cached_claims_by_type.clear()      # type: ignore[attr-defined]
    _cached_status_distribution.clear() # type: ignore[attr-defined]
    _cached_settlement_trend.clear()   # type: ignore[attr-defined]
    _cached_avg_cycle_time.clear()     # type: ignore[attr-defined]
    _cached_reserve_vs_actual.clear()  # type: ignore[attr-defined]
    _cached_sla_compliance.clear()     # type: ignore[attr-defined]
    _cached_claims_aging.clear()       # type: ignore[attr-defined]
    _cached_expert_performance.clear() # type: ignore[attr-defined]
    _cached_wht_summary.clear()        # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_analytics(show_refresh: bool = False) -> None:
    """Render four analytics charts in a 2x2 Plotly grid."""
    if show_refresh:
        if st.button("Refresh Analytics", help="Re-query KPI view"):
            clear_cache()
            st.rerun()

    with st.spinner("Loading analytics from KPI view..."):
        type_df   = _cached_claims_by_type()
        status_df = _cached_status_distribution()
        trend_df  = _cached_settlement_trend()
        cycle_df  = _cached_avg_cycle_time()

    mode_label = "Demo data" if _DEMO_MODE else "Live KPI data"
    if _DEMO_MODE:
        st.info(f"{mode_label} - set ANALYTICS_SQL_HOST / ANALYTICS_SQL_TOKEN secrets to connect live source")
    else:
        st.caption(f"{mode_label} - view: {_KPI_VIEW}")

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


# ---------------------------------------------------------------------------
# Advanced analytics — 5 chart types
# ---------------------------------------------------------------------------
#   1. Reserve vs Actual          — stacked bar
#   2. SLA Compliance             — gauge
#   3. Claims Aging               — histogram
#   4. Expert Performance         — horizontal bar
#   5. WHT Summary                — stacked bar
# ---------------------------------------------------------------------------

def render_advanced_analytics(show_refresh: bool = False) -> None:
    """Render five advanced analytics charts for senior KPI review.

    Charts:
        - Reserve vs Actual  (stacked bar)     — reserved vs actual incurred
        - SLA Compliance      (gauge)           — % claims settled within 30d
        - Claims Aging        (histogram)       — open claims age-bucketed
        - Expert Performance  (horizontal bar)  — avg resolution days per expert
        - WHT Summary         (stacked bar)     — gross vs withholding tax vs net
    """
    if show_refresh:
        if st.button("Refresh Advanced Analytics", help="Re-query KPI view"):
            clear_cache()
            st.rerun()

    if _DEMO_MODE:
        st.info("Demo data — set ANALYTICS_SQL_HOST / ANALYTICS_SQL_TOKEN secrets to connect live source")
    else:
        st.caption(f"Live KPI data — view: {_KPI_VIEW}")

    with st.spinner("Loading advanced analytics..."):
        reserve_df   = _cached_reserve_vs_actual()
        sla_df       = _cached_sla_compliance()
        aging_df     = _cached_claims_aging()
        expert_df    = _cached_expert_performance()
        wht_df       = _cached_wht_summary()

    # ---- Row 1 ----------------------------------------------------------------
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("**Reserve vs Actual by Claim Type**")
        if not reserve_df.empty:
            for col in ("reserved", "actual"):
                if col in reserve_df.columns:
                    reserve_df[col] = pd.to_numeric(reserve_df[col], errors="coerce")
            diff_df = reserve_df.copy()
            diff_df["variance"] = diff_df["actual"] - diff_df["reserved"]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Reserved",
                x=reserve_df["claim_type"],
                y=reserve_df["reserved"],
                marker_color=GREEN_30,
            ))
            fig.add_trace(go.Bar(
                name="Actual",
                x=reserve_df["claim_type"],
                y=reserve_df["actual"],
                marker_color=RED,
            ))
            fig.update_layout(
                barmode="stack",
                height=320,
                margin=dict(t=8, b=50, l=10, r=10),
                legend=dict(orientation="h", y=1.05, x=0),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No reserve vs actual data available.")

    with col_r:
        st.markdown("**SLA Compliance (Claims Settled ≤ 30 Days)**")
        if not sla_df.empty:
            sla_pct = float(pd.to_numeric(sla_df["sla_pct"].iloc[0], errors="coerce"))
            color = GREEN if sla_pct >= 75 else (RED if sla_pct < 50 else "#d97706")
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=sla_pct,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "SLA Compliance %", "font": {"size": 14, "color": BLUE}},
                number={"font": {"size": 26}, "suffix": "%"},
                delta={"reference": 100, "increasing": False, "position": "top"},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 2, "tickcolor": "#ccc"},
                    "bar": {"color": color, "thickness": 0.6},
                    "bgcolor": "white",
                    "borderwidth": 1,
                    "bordercolor": "#ccc",
                    "steps": [
                        {"range": [0, 50], "color": "#fce8e9"},
                        {"range": [50, 75], "color": "#fff4e5"},
                        {"range": [75, 100], "color": "#e6f4f1"},
                    ],
                },
            ))
            fig.update_layout(height=320, margin=dict(t=8, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No SLA data available.")

    # ---- Row 2 ----------------------------------------------------------------
    col_l2, col_r2 = st.columns(2)

    with col_l2:
        st.markdown("**Claims Aging (Open Claims)**")
        if not aging_df.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=aging_df["age_bucket"],
                y=aging_df["claims"],
                marker_color=BLUE,
                text=aging_df["claims"],
                textposition="auto",
            ))
            fig.update_traces(marker_color=DA_COLORWAY)
            fig.update_layout(
                height=320,
                margin=dict(t=8, b=50, l=10, r=10),
                xaxis_title="Age Bucket (days)",
                yaxis_title="Open Claims",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No claims aging data available.")

    with col_r2:
        st.markdown("**Expert Performance (Avg Resolution Days)**")
        if not expert_df.empty:
            expert_df["avg_days"] = pd.to_numeric(expert_df["avg_days"], errors="coerce")
            fig = px.bar(
                expert_df,
                x="avg_days",
                y="expert",
                orientation="h",
                labels={"avg_days": "Avg Days", "expert": ""},
                color="avg_days",
                color_continuous_scale=DA_SCALE_GREEN_RED,
                text="avg_days",
            )
            fig.update_traces(texttemplate="%{text:.1f}d", textposition="outside")
            fig.update_layout(
                coloraxis_showscale=False,
                height=320,
                margin=dict(t=8, b=10, l=10, r=70),
                yaxis={"categoryorder": "total ascending"},
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No expert performance data available.")

    # ---- Row 3: WHT Summary (spanning full width) -----------------------------
    st.markdown("**Withholding Tax Summary by Claim Type**")
    if not wht_df.empty:
        for col in ("gross", "wht", "net"):
            if col in wht_df.columns:
                wht_df[col] = pd.to_numeric(wht_df[col], errors="coerce")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Net Payable",
            x=wht_df["claim_type"],
            y=wht_df["net"],
            marker_color=GREEN,
        ))
        fig.add_trace(go.Bar(
            name="WHT Withheld",
            x=wht_df["claim_type"],
            y=wht_df["wht"],
            marker_color=RED,
        ))
        fig.update_layout(
            barmode="stack",
            height=360,
            margin=dict(t=8, b=50, l=10, r=10),
            legend=dict(orientation="h", y=1.05, x=0),
            xaxis_title="Claim Type",
            yaxis_title="Amount (KES)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No WHT data available.")
