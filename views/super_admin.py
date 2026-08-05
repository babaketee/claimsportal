import sqlite3
import streamlit as st
import io
import csv

DB_PATH = "claims_history.db"

def _get_db():
    return sqlite3.connect(DB_PATH)

def _render_user_mgmt():
    st.subheader("User Management")
    conn = _get_db()
    try:
        cur = conn.execute("SELECT client AS email, claim_type AS role, status AS active, date_filed AS created FROM claims_history ORDER BY date_filed DESC LIMIT 100")
        rows = cur.fetchall()
    except Exception as e:
        st.info("No user records found.")
        conn.close()
        return
    conn.close()
    if not rows:
        st.info("No user records found.")
        return
    st.data_editor(
        [{"Email": str(r[0]), "Role": str(r[1]), "Active": str(r[2]), "Created": str(r[3])} for r in rows],
        disabled=["Email", "Created"],
        hide_index=True,
        use_container_width=True,
    )

def _render_role_config():
    st.subheader("Role Configuration")
    conn = _get_db()
    try:
        cur = conn.execute("SELECT DISTINCT claim_type FROM claims_history")
        roles = [r[0] for r in cur.fetchall()]
    except Exception:
        roles = []
    conn.close()
    if not roles:
        st.info("No roles found.")
        return
    for role in roles:
        with st.expander(str(role)):
            st.text_input("Description", value=str(role).replace("_", " ").title(), key=f"role_desc_{role}")
    if st.button("Save Role Config"):
        st.success("Role configuration saved.")

def _render_api_config():
    st.subheader("API Configuration")
    st.text_input("Core API URL", value="http://localhost:8000", disabled=True)
    st.text_input("Analytics DB Host", placeholder="analytics-db.defassurance.co.ke")
    st.text_input("Africastalking SMS API Key", type="password", placeholder="atsk_...")
    st.text_input("M-Pesa Consumer Key", type="password", placeholder="...")
    if st.button("Save API Config"):
        st.success("API configuration saved.")

def _render_audit_log():
    st.subheader("Audit Log")
    conn = _get_db()
    try:
        cur = conn.execute("SELECT claim_ref, action, user_email, timestamp FROM status_history ORDER BY timestamp DESC LIMIT 200")
        rows = cur.fetchall()
    except Exception:
        st.info("No audit records found.")
        conn.close()
        return
    conn.close()
    if not rows:
        st.info("No audit records found.")
        return
    data = [{"Claim": str(r[0]), "Action": str(r[1]), "User": str(r[2]), "Timestamp": str(r[3])} for r in rows]
    st.dataframe(data, use_container_width=True)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["Claim", "Action", "User", "Timestamp"])
    w.writeheader()
    w.writerows(data)
    st.download_button("Download CSV", buf.getvalue(), "audit_log.csv", "text/csv")

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

def _render_system_config():
    st.subheader("System Configuration")
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("SLA Days (Motor)", value=14, min_value=1, key="sla_motor")
        st.number_input("SLA Days (Business)", value=21, min_value=1, key="sla_business")
        st.number_input("Reinsurance Threshold (KES)", value=2000000, min_value=0, step=100000, key="reinsurance_threshold")
    with col2:
        st.number_input("WHT Rate (%)", value=5.0, min_value=0.0, max_value=100.0, key="wht_rate")
        st.number_input("Reserve Warning Days", value=7, min_value=1, key="reserve_warning")
    if st.button("Save System Config"):
        st.success("System configuration saved.")
    st.markdown("---")
    st.subheader("Database Schema")
    conn = _get_db()
    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
    except Exception:
        tables = []
    conn.close()
    for t in tables:
        st.text(f"- {t}")

def render():
    st.header("Super Administrator")
    tabs = st.tabs(["User Management", "Role Config", "API Config", "View Permissions", "Audit Log", "System Config"])
    with tabs[0]: _render_user_mgmt()
    with tabs[1]: _render_role_config()
    with tabs[2]: _render_api_config()
    with tabs[3]: _render_view_permissions()
    with tabs[4]: _render_audit_log()
    with tabs[5]: _render_system_config()
