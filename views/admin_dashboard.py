import streamlit as st
import pandas as pd

def _render_kpis():
    from core_api import get_claims, _get_db
    col1, col2, col3, col4 = st.columns(4)
    conn = _get_db()
    try:
        cur = conn.execute("SELECT COUNT(*) FROM claims_history")
        total = cur.fetchone()[0] or 0
    except Exception:
        total = 0
    try:
        cur2 = conn.execute("SELECT COUNT(*) FROM claims_history WHERE status LIKE 'Closed%'")
        closed = cur2.fetchone()[0] or 0
    except Exception:
        closed = 0
    try:
        cur3 = conn.execute("SELECT COUNT(*) FROM claims_history WHERE status LIKE 'Reported%' OR status LIKE 'Reserve%'")
        open_ = cur3.fetchone()[0] or 0
    except Exception:
        open_ = 0
    try:
        cur4 = conn.execute("SELECT COALESCE(SUM(reserve_amount),0) FROM reserves WHERE status='Active'")
        reserves = cur4.fetchone()[0] or 0
    except Exception:
        reserves = 0
    conn.close()
    col1.metric("Total Claims", total)
    col2.metric("Closed", closed)
    col3.metric("Open", open_)
    col4.metric("Active Reserves (KES)", f"{float(reserves):,.0f}")

def _render_claims_table():
    from core_api import get_claims
    st.subheader("All Claims")
    rows = get_claims()
    if not rows:
        st.info("No claims. Click 'Seed Database' in Super Admin to load demo data.")
        return
    df = pd.DataFrame(rows, columns=["Claim Ref","Client","Type","Insurer","Cause","Status","Location","Vehicle","Date Filed","Last Updated"])
    st.dataframe(df, use_container_width=True, hide_index=True)

def _render_status_breakdown():
    from core_api import _get_db
    st.subheader("Claims by Status")
    conn = _get_db()
    try:
        cur = conn.execute("SELECT status, COUNT(*) FROM claims_history GROUP BY status ORDER BY COUNT(*) DESC")
        rows = cur.fetchall()
    except Exception:
        rows = []
    conn.close()
    if not rows:
        st.info("No data.")
        return
    df = pd.DataFrame(rows, columns=["Status","Count"])
    st.dataframe(df, use_container_width=True, hide_index=True)

def _render_type_breakdown():
    from core_api import _get_db
    st.subheader("Claims by Type")
    conn = _get_db()
    try:
        cur = conn.execute("SELECT claim_type, COUNT(*) FROM claims_history GROUP BY claim_type ORDER BY COUNT(*) DESC")
        rows = cur.fetchall()
    except Exception:
        rows = []
    conn.close()
    if not rows:
        st.info("No data.")
        return
    df = pd.DataFrame(rows, columns=["Claim Type","Count"])
    st.dataframe(df, use_container_width=True, hide_index=True)

def _render_recent_activity():
    from core_api import _get_db
    st.subheader("Recent Activity")
    conn = _get_db()
    try:
        cur = conn.execute("SELECT claim_ref, action, user_email, timestamp FROM status_history ORDER BY timestamp DESC LIMIT 20")
        rows = cur.fetchall()
    except Exception:
        rows = []
    conn.close()
    if not rows:
        st.info("No recent activity.")
        return
    df = pd.DataFrame(rows, columns=["Claim Ref","Action","User","Timestamp"])
    st.dataframe(df, use_container_width=True, hide_index=True)

def render():
    st.header("Admin Dashboard")
    _render_kpis()
    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs(["All Claims","By Status","By Type","Recent Activity"])
    with tab1: _render_claims_table()
    with tab2: _render_status_breakdown()
    with tab3: _render_type_breakdown()
    with tab4: _render_recent_activity()
