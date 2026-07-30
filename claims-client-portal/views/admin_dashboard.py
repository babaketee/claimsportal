"""Internal Admin Dashboard — live Delta data from main.claims.fnol_submissions."""
from __future__ import annotations

import datetime
import os

import pandas as pd
import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState
from views.analytics_charts import render_analytics, clear_cache as _clear_analytics_cache

_WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID", "4489dbff81694cd8")
_FNOL = "main.claims.fnol_submissions"


# ---------------------------------------------------------------------------
# SQL execution helper
# ---------------------------------------------------------------------------

def _run_sql(sql: str) -> pd.DataFrame:
    """Run SQL on the configured warehouse and return a DataFrame.

    Returns an empty DataFrame on error; surfaces warnings in the UI so the
    dashboard degrades gracefully when tables are unavailable.
    """
    try:
        w = WorkspaceClient()
        resp = w.statement_execution.execute_statement(
            warehouse_id=_WAREHOUSE_ID,
            statement=sql,
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
def _load_status_counts() -> pd.DataFrame:
    return _run_sql(f"""
        SELECT status, COUNT(*) AS cnt
        FROM {_FNOL}
        GROUP BY status
        ORDER BY cnt DESC
    """)


@st.cache_data(ttl=60, show_spinner=False)
def _load_type_distribution() -> pd.DataFrame:
    return _run_sql(f"""
        SELECT incident_type, COUNT(*) AS claims
        FROM {_FNOL}
        GROUP BY incident_type
        ORDER BY claims DESC
    """)


@st.cache_data(ttl=60, show_spinner=False)
def _load_daily_trend() -> pd.DataFrame:
    return _run_sql(f"""
        SELECT CAST(submitted_at AS DATE) AS submission_date, COUNT(*) AS new_claims
        FROM {_FNOL}
        WHERE submitted_at >= CURRENT_DATE - INTERVAL 30 DAYS
        GROUP BY CAST(submitted_at AS DATE)
        ORDER BY submission_date
    """)


@st.cache_data(ttl=60, show_spinner=False)
def _load_all_claims(
    status_filter: str, type_filter: str,
    date_from: str, date_to: str,
) -> pd.DataFrame:
    status_clause = "1=1" if status_filter == "All" else f"status = '{status_filter}'"
    type_clause   = "1=1" if type_filter  == "All" else f"incident_type = '{type_filter}'"
    return _run_sql(f"""
        SELECT
            claim_ref,
            policy_number,
            submitted_by                       AS client_email,
            incident_type,
            CAST(incident_date AS STRING)      AS incident_date,
            status,
            COALESCE(assigned_handler,'Unassigned') AS handler,
            DATEDIFF(CURRENT_DATE, CAST(submitted_at AS DATE)) AS age_days
        FROM {_FNOL}
        WHERE {status_clause}
          AND {type_clause}
          AND CAST(submitted_at AS DATE) BETWEEN '{date_from}' AND '{date_to}'
        ORDER BY submitted_at DESC
        LIMIT 500
    """)


@st.cache_data(ttl=60, show_spinner=False)
def _load_sla() -> pd.DataFrame:
    """Derive SLA status directly from submission timestamps and claim lifecycle stage."""
    return _run_sql(f"""
        SELECT
            claim_ref,
            status                                               AS current_stage,
            COALESCE(assigned_handler, 'Unassigned')           AS handler,
            CAST(submitted_at AS STRING)                        AS submitted_at,
            DATEDIFF(CURRENT_DATE, CAST(submitted_at AS DATE))  AS age_days,
            CASE
              WHEN status = 'Submitted'
               AND TIMESTAMPDIFF(HOUR, submitted_at, CURRENT_TIMESTAMP()) > 4
                    THEN '\U0001f534 Breached'
              WHEN status = 'Submitted'
               AND TIMESTAMPDIFF(HOUR, submitted_at, CURRENT_TIMESTAMP()) > 2
                    THEN '\U0001f7e1 At Risk'
              WHEN status IN ('Assessor Appointed','Under Assessment')
               AND DATEDIFF(CURRENT_DATE, CAST(submitted_at AS DATE)) > 2
                    THEN '\U0001f534 Breached'
              WHEN status IN ('Assessor Appointed','Under Assessment')
               AND DATEDIFF(CURRENT_DATE, CAST(submitted_at AS DATE)) > 1
                    THEN '\U0001f7e1 At Risk'
              WHEN DATEDIFF(CURRENT_DATE, CAST(submitted_at AS DATE)) > 30
                    THEN '\U0001f534 Breached'
              WHEN DATEDIFF(CURRENT_DATE, CAST(submitted_at AS DATE)) > 25
                    THEN '\U0001f7e1 At Risk'
              ELSE '\U0001f7e2 On Track'
            END AS sla_status
        FROM {_FNOL}
        WHERE status NOT IN ('Settled','Repudiated')
        ORDER BY submitted_at ASC
        LIMIT 300
    """)


@st.cache_data(ttl=120, show_spinner=False)
def _load_vendors() -> pd.DataFrame:
    return _run_sql(
        "SELECT name, vendor_type AS type, kra_pin, aki_certified, status "
        "FROM main.claims.vendors ORDER BY name"
    )


@st.cache_data(ttl=30, show_spinner=False)
def _load_audit_log() -> pd.DataFrame:
    return _run_sql(
        "SELECT event_ts AS timestamp, user_email AS user, ip_address AS ip, "
        "action_description AS action FROM main.claims.audit_log "
        "ORDER BY event_ts DESC LIMIT 500"
    )


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
    if col_btn.button("\U0001f504 Refresh", use_container_width=True, help="Force-refresh all Delta data"):
        _refresh_all()
    st.caption("Live data from Delta \u00b7 auto-refreshes every 60 seconds.")

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
    st.caption("Live from workspace.default.claims_silver & claims_gold_monthly \u00b7 60-second cache.")
    render_analytics(show_refresh=False)


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

def _overview() -> None:
    st.subheader("Claims Overview")

    with st.spinner("Loading metrics\u2026"):
        status_df = _load_status_counts()
        type_df   = _load_type_distribution()
        trend_df  = _load_daily_trend()

    def _cnt(statuses: list) -> int:
        if status_df.empty:
            return 0
        return int(status_df[status_df["status"].isin(statuses)]["cnt"].sum())

    open_statuses = [
        "Submitted", "Under Review", "Assessor Appointed", "Under Assessment",
        "Approved for Repair", "Repair in Progress", "Estimate Submitted",
        "Invoice Submitted", "Pending Settlement",
    ]
    total_open     = _cnt(open_statuses)
    pending_assess = _cnt(["Submitted", "Under Review"])
    under_assess   = _cnt(["Under Assessment", "Assessor Appointed"])

    settled_month_df = _run_sql(f"""
        SELECT COUNT(*) AS cnt FROM {_FNOL}
        WHERE status = 'Settled'
          AND MONTH(submitted_at) = MONTH(CURRENT_DATE)
          AND YEAR(submitted_at)  = YEAR(CURRENT_DATE)
    """)
    settled_month = int(settled_month_df.iloc[0, 0]) if not settled_month_df.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Open Claims",  total_open)
    c2.metric("Pending Assessment", pending_assess)
    c3.metric("Under Assessment",   under_assess)
    c4.metric("Settled This Month", settled_month)

    st.divider()

    left, right = st.columns(2)
    with left:
        st.markdown("**Claims by Incident Type**")
        if not type_df.empty:
            type_df["claims"] = type_df["claims"].astype(int)
            st.bar_chart(type_df.set_index("incident_type")["claims"])
        else:
            st.info("No submissions yet.")

    with right:
        st.markdown("**Daily New Claims (last 30 days)**")
        if not trend_df.empty:
            trend_df["new_claims"] = trend_df["new_claims"].astype(int)
            st.line_chart(trend_df.set_index("submission_date")["new_claims"])
        else:
            st.info("No submissions in the last 30 days.")

    if not status_df.empty:
        st.divider()
        st.markdown("**Status Distribution**")
        status_df["cnt"] = status_df["cnt"].astype(int)
        st.dataframe(
            status_df.rename(columns={"status": "Status", "cnt": "Count"}),
            use_container_width=True, hide_index=True,
        )


# ---------------------------------------------------------------------------
# All Claims
# ---------------------------------------------------------------------------

def _all_claims() -> None:
    st.subheader("All Claims")
    c1, c2, c3, c4 = st.columns(4)
    status_filter = c1.selectbox(
        "Status",
        ["All", "Submitted", "Under Review", "Assessor Appointed", "Under Assessment",
         "Approved for Repair", "Repair in Progress", "Estimate Submitted",
         "Invoice Submitted", "Pending Settlement", "Settled", "Repudiated"],
    )
    type_filter = c2.selectbox(
        "Type",
        ["All", "Motor Vehicle Accident", "Theft / Burglary", "Fire Damage",
         "Natural Disaster", "Windscreen / Glass", "Other"],
    )
    date_from = c3.date_input("From", value=datetime.date.today() - datetime.timedelta(days=90))
    date_to   = c4.date_input("To",   value=datetime.date.today())

    with st.spinner("Querying Delta\u2026"):
        df = _load_all_claims(status_filter, type_filter, str(date_from), str(date_to))

    if df.empty:
        st.info("No claims match the selected filters.")
    else:
        df["age_days"] = df["age_days"].astype(int)
        st.caption(f"{len(df)} claim(s) returned (capped at 500).")
        st.dataframe(
            df.rename(columns={
                "claim_ref":     "Claim Ref",
                "policy_number": "Policy",
                "client_email":  "Client Email",
                "incident_type": "Type",
                "incident_date": "Incident Date",
                "status":        "Status",
                "handler":       "Handler",
                "age_days":      "Age (days)",
            }),
            use_container_width=True, hide_index=True,
        )


# ---------------------------------------------------------------------------
# Vendor Management
# ---------------------------------------------------------------------------

def _vendor_management() -> None:
    st.subheader("Vendor / Service Provider Management")
    tab_active, tab_pending = st.tabs(["Active Vendors", "Pending Onboarding"])

    with st.spinner("Loading vendor data\u2026"):
        vendors_df = _load_vendors()

    with tab_active:
        if vendors_df.empty:
            st.info(
                "No vendor records found. "
                "Create `main.claims.vendors` with columns "
                "`name`, `vendor_type`, `kra_pin`, `aki_certified`, `status` "
                "to enable live vendor management."
            )
        else:
            active = vendors_df[vendors_df["status"] == "Active"]
            st.dataframe(
                active.rename(columns={
                    "name": "Name", "type": "Type", "kra_pin": "KRA PIN",
                    "aki_certified": "AKI Certified", "status": "Status",
                }),
                use_container_width=True, hide_index=True,
            )

    with tab_pending:
        if not vendors_df.empty:
            pending = vendors_df[vendors_df["status"] == "Pending"]
            if pending.empty:
                st.info("No pending onboarding requests.")
            else:
                st.dataframe(pending, use_container_width=True, hide_index=True)
        else:
            st.info("No pending onboarding requests.")


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

def _audit_log() -> None:
    st.subheader("Audit Log")
    st.caption("User actions: timestamp, user, IP, and action description.")

    with st.spinner("Loading audit log\u2026"):
        logs_df = _load_audit_log()

    if logs_df.empty:
        st.info(
            "Live audit log requires `main.claims.audit_log` "
            "(`event_ts TIMESTAMP`, `user_email STRING`, `ip_address STRING`, "
            "`action_description STRING`). "
            "Showing FNOL submission history as a proxy trail."
        )
        fnol_audit = _run_sql(f"""
            SELECT
                CAST(submitted_at AS STRING)                AS timestamp,
                submitted_by                                AS user,
                'Portal'                                   AS ip,
                CONCAT('FNOL submitted \u2014 ', claim_ref)    AS action
            FROM {_FNOL}
            ORDER BY submitted_at DESC
            LIMIT 200
        """)
        if fnol_audit.empty:
            st.info("No submissions yet.")
        else:
            st.dataframe(
                fnol_audit.rename(columns={
                    "timestamp": "Timestamp", "user": "User",
                    "ip": "Source", "action": "Action",
                }),
                use_container_width=True, hide_index=True,
            )
    else:
        st.dataframe(
            logs_df.rename(columns={
                "timestamp": "Timestamp", "user": "User",
                "ip": "IP", "action": "Action",
            }),
            use_container_width=True, hide_index=True,
        )


# ---------------------------------------------------------------------------
# SLA Monitor
# ---------------------------------------------------------------------------

def _sla_monitor() -> None:
    st.subheader("SLA Monitor")
    st.caption(
        "Computed live from Delta \u00b7 based on submission timestamp and current claim status."
    )

    with st.spinner("Computing SLA status from Delta\u2026"):
        sla_df = _load_sla()

    if sla_df.empty:
        st.success("No open claims \u2014 nothing to monitor.")
    else:
        sla_df["age_days"] = sla_df["age_days"].astype(int)

        breached = int((sla_df["sla_status"] == "\U0001f534 Breached").sum())
        at_risk  = int((sla_df["sla_status"] == "\U0001f7e1 At Risk").sum())
        on_track = int((sla_df["sla_status"] == "\U0001f7e2 On Track").sum())

        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("\U0001f534 Breached", breached)
        tc2.metric("\U0001f7e1 At Risk",  at_risk)
        tc3.metric("\U0001f7e2 On Track", on_track)

        st.divider()

        show_all   = st.checkbox("Show all open claims", value=False)
        display_df = sla_df if show_all else sla_df[sla_df["sla_status"] != "\U0001f7e2 On Track"]

        if display_df.empty:
            st.success("All open claims are on track.")
        else:
            st.dataframe(
                display_df.rename(columns={
                    "claim_ref":     "Claim Ref",
                    "current_stage": "Stage",
                    "handler":       "Handler",
                    "submitted_at":  "Submitted At",
                    "age_days":      "Age (days)",
                    "sla_status":    "SLA Status",
                }),
                use_container_width=True, hide_index=True,
            )

    st.divider()
    st.markdown("**SLA Thresholds (reference)**")
    thresholds = [
        {"Stage": "Assessor Assignment",        "SLA": "4 business hours after FNOL"},
        {"Stage": "Assessment Completion",       "SLA": "48 hours after appointment"},
        {"Stage": "Garage Estimate Submission",  "SLA": "48 hours after repair authorisation"},
        {"Stage": "Invoice Payment",             "SLA": "7 business days after invoice receipt"},
        {"Stage": "Final Settlement",            "SLA": "30 days from date of loss"},
    ]
    st.dataframe(thresholds, use_container_width=True, hide_index=True)
