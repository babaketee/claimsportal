import streamlit as st
import pandas as pd

def _render_open_rfqs():
    from core_api import _get_db
    st.subheader("Open RFQs")
    conn = _get_db()
    try:
        cur = conn.execute("SELECT id, claim_ref, entry_text, due_date, priority, status FROM diary_entries WHERE status='Open' ORDER BY due_date ASC LIMIT 50")
        rows = cur.fetchall()
    except Exception:
        rows = []
    conn.close()
    if not rows:
        st.info("No open RFQs.")
        return
    df = pd.DataFrame(rows, columns=["ID","Claim Ref","Description","Due Date","Priority","Status"])
    st.dataframe(df, use_container_width=True, hide_index=True)

def _render_my_bids():
    from core_api import get_assignments
    st.subheader("My Bids")
    rows = get_assignments(expert_type="spare_parts")
    if not rows:
        st.info("No bids submitted.")
        return
    df = pd.DataFrame(rows, columns=["ID","Claim Ref","Expert Name","Type","Assigned Date","Status","Notes"])
    st.dataframe(df, use_container_width=True, hide_index=True)

def _render_active_orders():
    from core_api import _get_db
    st.subheader("Active Orders")
    conn = _get_db()
    try:
        cur = conn.execute("SELECT id, claim_ref, entry_text, due_date, priority, status FROM diary_entries WHERE status='Open' ORDER BY due_date ASC LIMIT 50")
        rows = cur.fetchall()
    except Exception:
        rows = []
    conn.close()
    if not rows:
        st.info("No active orders.")
        return
    df = pd.DataFrame(rows, columns=["ID","Claim Ref","Description","Due Date","Priority","Status"])
    st.dataframe(df, use_container_width=True, hide_index=True)

def _render_payments():
    from core_api import get_settlements_by_status
    st.subheader("Payments")
    try:
        df = get_settlements_by_status(["Recommended", "Approved", "Paid"])
        if df.empty:
            st.info("No payment records.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception:
        st.info("No payment records.")

def render():
    st.header("Spare Parts Provider")
    tab1, tab2, tab3, tab4 = st.tabs(["Open RFQs", "My Bids", "Active Orders", "Payments"])
    with tab1: _render_open_rfqs()
    with tab2: _render_my_bids()
    with tab3: _render_active_orders()
    with tab4: _render_payments()
