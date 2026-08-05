import streamlit as st
import io, csv

def _render_user_mgmt():
    from core_api import get_claims
    st.subheader("User Management")
    rows = get_claims()
    if not rows:
        st.info("No user records. Click 'Seed Database' in System Config to load demo data.")
        return
    st.data_editor(
        [{"Email": str(r[1]), "Role": str(r[2]), "Status": str(r[5]), "Date": str(r[8])} for r in rows],
        disabled=["Email", "Date"], hide_index=True, use_container_width=True,
    )

def _render_role_config():
    from core_api import get_claims
    st.subheader("Role Configuration")
    rows = get_claims()
    roles = sorted(set(r[2] for r in rows if r[2]))
    if not roles:
        st.info("No roles found.")
        return
    for role in roles:
        with st.expander(role):
            st.text_input("Description", value=role.replace("_", " ").title(), key=f"role_desc_{role}")
    if st.button("Save Role Config"):
        st.success("Role configuration saved.")

def _render_api_config():
    st.subheader("API Configuration")
    st.text_input("Core API URL", value="https://claimsapp-3giaczzzvijfdz4rv6d3og.streamlit.app", disabled=True)
    if st.button("Save API Config"):
        st.success("API configuration saved.")

def _render_audit_log():
    from core_api import _get_db
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
    roles = ["client","claims_officer","head_of_claims","assessor","garage","investigator","finance","finance_head","spare_parts","legal","admin"]
    views = ["FNOL","Claim Tracker","Reserve Management","Settlement","Reports","Communications","Document Manager","Expert Assignment"]
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

    st.markdown("---")
    st.subheader("Database Operations")

    if st.button("Seed Database (45 Claims)", type="primary", use_container_width=True):
        from core_api import seed_demo_data
        result = seed_demo_data()
        st.success(result)
        st.rerun()

    st.markdown("---")
    st.subheader("Database Schema")
    from core_api import _get_db
    conn = _get_db()
    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
    except Exception:
        tables = []
    conn.close()
    if tables:
        for t in tables:
            st.text(f"- {t}")
    else:
        st.info("No tables yet.")

def render():
    st.header("Super Administrator")
    tabs = st.tabs(["User Management","Role Config","API Config","View Permissions","Audit Log","System Config"])
    with tabs[0]: _render_user_mgmt()
    with tabs[1]: _render_role_config()
    with tabs[2]: _render_api_config()
    with tabs[3]: _render_view_permissions()
    with tabs[4]: _render_audit_log()
    with tabs[5]: _render_system_config()
