import streamlit as st
from core_api import get_claims, seed_demo_data

def _render_user_mgmt():
    from core_api import get_claims
    st.subheader("User Management")
    rows = get_claims()
    if not rows:
        st.info("No user records. Click 'Seed Database' in System Config.")
        return
    import pandas as pd
    df = pd.DataFrame(rows, columns=["Claim Ref","Client","Type","Insurer","Cause","Status","Location","Vehicle","Date Filed","Last Updated"])
    st.dataframe(df, use_container_width=True, hide_index=True)

def _render_role_config():
    st.subheader("Role Configuration")
    roles = {
        "client": "Client Portal",
        "claims_officer": "Claims Officer",
        "head_of_claims": "Head of Claims",
        "assessor": "Assessor",
        "garage": "Garage / Workshop",
        "investigator": "Investigator",
        "finance": "Finance Officer",
        "finance_head": "Finance Head / CFO",
        "spare_parts": "Spare Parts Provider",
        "legal": "Legal Counsel",
        "admin": "System Administrator",
        "super_admin": "Super Administrator",
    }
    for role, label in roles.items():
        st.markdown(f"**{label}** — `{role}@insure.demo`")

def _render_api_config():
    st.subheader("API Configuration")
    st.info("API keys managed centrally. Contact the system administrator.")
    st.text_input("API Endpoint", value="https://api.definiteassurance.co.ke", disabled=True)
    st.text_input("API Version", value="v1", disabled=True)

def _render_view_permissions():
    st.subheader("View Permissions")
    st.info("Role-based access control is enforced at authentication.")

def _render_audit_log():
    st.subheader("Audit Log")
    from core_api import get_timeline
    rows = get_timeline("MTR-2026-0001")
    if not rows:
        st.info("No audit records.")
        return
    import pandas as pd
    df = pd.DataFrame(rows, columns=["ID","Action","User","Timestamp","Notes"])
    st.dataframe(df, use_container_width=True, hide_index=True)

def _render_system_config():
    st.subheader("System Configuration")
    if st.button("Seed Database (45 Claims)"):
        from core_api import seed_demo_data
        result = seed_demo_data()
        st.success(result)
    if st.button("Rebuild Tables"):
        from core_api import _ensure_tables
        _ensure_tables()
        st.success("Tables rebuilt.")
    from core_api import _get_db
    conn = _get_db()
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cur.fetchall()
    conn.close()
    if tables:
        st.write("Tables:", ", ".join([r[0] for r in tables]))
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
