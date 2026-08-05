import streamlit as st
import pandas as pd
from datetime import datetime, date

from core_api import _get_db

def _metric_card(label, value, delta=None):
    st.metric(label, value, delta=delta)

def _render_kpis():
    col1, col2, col3, col4 = st.columns(4)
    conn = _get_db()
    try:
        cur = conn.execute("SELECT COUNT(*) FROM claims_history")
        total = cur.fetchone()[0] or 0
    except Exception:
        total = 0
    try:
        cur2 = conn.execute("SELECT COUNT(*) FROM claims_history WHERE status LIKE '%Closed%'")
        closed = cur2.fetchone()[0] or 0
    except Exception:
        closed = 0
    try:
        cur3 = conn.execute("SELECT COUNT(*) FROM claims_history WHERE status LIKE '%Reported%'")
        open_ = cur3.fetchone()[0] or 0
    except Exception:
        open_ = 0
    try:
        cur4 = conn.execute("SELECT SUM(reserve_amount) FROM reserves WHERE status='Active'")
        reserves = cur4.fetchone()[0] or 0
    except Exception:
        reserves = 0
    conn.close()
    col1.metric("Total Claims", total)
    col2.metric("Closed", closed)
    col3.metric("Open", open_)
    col4.metric("Active Reserves (KES)", f"{reserves:,.0f}")

def _render_claims_table():
    st.subheader("All Claims")
    conn = _get_db()
    try:
        cur = conn.execute("SELECT claim_ref, client, claim_type, status, location, date_filed FROM claims_history ORDER BY date_filed DESC LIMIT 100")
        rows = cur.fetchall()
    except Exception:
        st.info("No claims found.")
        conn.close()
        return
    conn.close()
    if not rows:
        st.info("No claims found.")
        return
    df = pd.DataFrame(rows, columns=["Claim Ref", "Client", "Type", "Status", "Location", "Date Filed"])
    st.dataframe(df, use_container_width=True, hide_index=True)

def _render_status_breakdown():
    st.subheader("Claims by Status")
    conn = _get_db()
    try:
        cur = conn.execute("SELECT status, COUNT(*) FROM claims_history GROUP BY status ORDER BY COUNT(*) DESC")
        rows = cur.fetchall()
    except Exception:
        rows = []
    conn.close()
    if not rows:
        st.info("No status data available.")
        return
    df = pd.DataFrame(rows, columns=["Status", "Count"])
    st.dataframe(df, use_container_width=True, hide_index=True)

def _render_type_breakdown():
    st.subheader("Claims by Type")
    conn = _get_db()
    try:
        cur = conn.execute("SELECT claim_type, COUNT(*) FROM claims_history GROUP BY claim_type ORDER BY COUNT(*) DESC")
        rows = cur.fetchall()
    except Exception:
        rows = []
    conn.close()
    if not rows:
        st.info("No type data available.")
        return
    df = pd.DataFrame(rows, columns=["Claim Type", "Count"])
    st.dataframe(df, use_container_width=True, hide_index=True)

def _render_recent_activity():
    st.subheader("Recent Activity")
    conn = _get_db()
    try:
        cur = conn.execute("SELECT claim_ref, action, user_email, timestamp FROM status_history ORDER BY timestamp DESC LIMIT 20")
        rows = cur.fetchall()
    except Exception:
        rows = []
    conn.close()
    if not rows:
        st.info("No recent activity found.")
        return
    df = pd.DataFrame(rows, columns=["Claim Ref", "Action", "User", "Timestamp"])
    st.dataframe(df, use_container_width=True, hide_index=True)

def render():
    st.header("Admin Dashboard")
    _render_kpis()
    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs(["All Claims", "By Status", "By Type", "Recent Activity"])
    with tab1:
        _render_claims_table()
    with tab2:
        _render_status_breakdown()
    with tab3:
        _render_type_breakdown()
    with tab4:
        _render_recent_activity()
