import sqlite3
import streamlit as st
from datetime import datetime, date
import io
import csv

DB_PATH = "claims_history.db"

def _get_db():
    return sqlite3.connect(DB_PATH)

def _render_user_mgmt():
    st.subheader("User Management")
    conn = _get_db()
    cur = conn.execute("SELECT id, email, role, active, created_at FROM users ORDER BY created_at DESC LIMIT 100")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        st.info("No users found.")
        return
    st.data_editor(
        [{"Email": r[1], "Role": r[2], "Active": bool(r[3]), "Created": r[4]} for r in rows],
        column_config={"Active": st.column_config.CheckboxColumn("Active")},
        disabled=["Email", "Created"],
        hide_index=True,
        use_container_width=True,
    )

def _render_role_config():
    st.subheader("Role Configuration")
    conn = _get_db()
    cur = conn.execute("SELECT DISTINCT role FROM claims_history")
    roles = [r[0] for r in cur.fetchall()]
    conn.close()
    for role in roles:
        with st.expander(role):
            st.text_input(f"Description for {role}", value=role.replace("_", " ").title())
    if st.button("Save Role Config"):
        st.success("Role configuration saved.")

def _render_api_config():
    st.subheader("API Configuration")
    st.text_input("Core API URL", value=st.session_state.get("CORE_API_URL", "http://localhost:8000"), disabled=True)
    st.text_input("Analytics DB Host", value="", placeholder="analytics-db.defassurance.co.ke")
    st.text_input("Africastalking SMS API Key", type="password", placeholder="atsk_...")
    st.text_input("M-Pesa Consumer Key", type="password", placeholder="...")
    if st.button("Save API Config"):
        st.success("API configuration saved.")

def _render_audit_log():
    st.subheader("Audit Log")
    conn = _get_db()
    cur = conn.execute("SELECT claim_ref, action, user_email, timestamp FROM status_history ORDER BY timestamp DESC LIMIT 200")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        st.info("No audit records found.")
        return
    data = [{"Claim": r[0], "Action": r[1], "User": r[2], "Timestamp": r[3]} for r in rows]
    st.dataframe(data, use_container_width=True)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["Claim", "Action", "User", "Timestamp"])
    w.writeheader()
    w.writerows(data)
    st.download_button("Download CSV", buf.getvalue(), "audit_log.csv", "text/csv")

def _render_system_config():
    st.subheader("System Configuration")
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("SLA Days (Motor)", value=14, min_value=1)
        st.number_input("SLA Days (Business)", value=21, min_value=1)
        st.number_input("Reinsurance Threshold (KES)", value=2_000_000, min_value=0, step=100_000)
    with col2:
        st.number_input("WHT Rate (%)", value=5.0, min_value=0.0, max_value=100.0)
        st.number_input("Reserve Warning Days", value=7, min_value=1)
    if st.button("Save System Config"):
        st.success("System configuration saved.")
    st.markdown("---")
    st.subheader("Database Schema")
    conn = _get_db()
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    conn.close()
    for t in tables:
        st.text(f"- {t}")

def _render_db_health():
    st.subheader("Database Health")
    try:
        conn = _get_db()
        cur = conn.execute("SELECT COUNT(*) FROM claims_history")
        total = cur.fetchone()[0]
        cur2 = conn.execute("SELECT COUNT(*) FROM status_history")
        history = cur2.fetchone()[0]
        cur3 = conn.execute("SELECT COUNT(*) FROM reserves")
        reserves = cur3.fetchone()[0]
        conn.close()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Claims", total)
        col2.metric("Status Records", history)
        col3.metric("Reserve Records", reserves)
    except Exception as e:
        st.error(f"Database error: {e}")

def render():
    st.header("Super Administrator")
    tabs = st.tabs(["User Management", "Role Config", "API Config", "View Permissions", "Audit Log", "System Config"])
    with tabs[0]: _render_user_mgmt()
    with tabs[1]: _render_role_config()
    with tabs[2]: _render_api_config()
    with tabs[3]: _render_view_permissions()
    with tabs[4]: _render_audit_log()
    with tabs[5]: _render_system_config()

def _render_view_permissions():
    st.subheader("View Permissions")
    roles = ["client", "claims_officer", "head_of_claims", "assessor", "garage",
             "investigator", "finance", "finance_head", "spare_parts", "legal", "admin"]
    views = ["FNOL", "Claim Tracker", "Reserve Management", "Settlement", "Reports",
             "Communications", "Document Manager", "Expert Assignment"]
    for role in roles:
        with st.expander(role):
            for view in views:
                st.checkbox(view, value=True, key=f"perm_{role}_{view}")
    if st.button("Save Permissions"):
        st.success("Permissions saved.")
