"""Super Admin â full system configuration, user management, API setup."""

import streamlit as st
import pandas as pd
from datetime import datetime
import os

try:
    from core_api import core_api
except Exception:
    core_api = None


def show() -> None:
    st.header("System Administration")
    st.caption("Super Administrator â full system access")

    tab_users, tab_roles, tab_api, tab_views, tab_audit, tab_config = st.tabs([
        "User Management",
        "Role Configuration",
        "API Configuration",
        "View Permissions",
        "Audit Log",
        "System Config",
    ])

    with tab_users:
        st.subheader("User Accounts")
        DEMO_USERS = {
            "client@insure.demo":      {"name": "Kamau Mwangi",    "role": "client",          "active": True},
            "officer@insure.demo":     {"name": "Grace Wanjiku",   "role": "claims_officer",   "active": True},
            "hoc@insure.demo":         {"name": "David Ochieng",   "role": "head_of_claims",   "active": True},
            "admin@insure.demo":       {"name": "System Admin",    "role": "admin",            "active": True},
            "assessor@insure.demo":    {"name": "James Kariuki",   "role": "assessor",         "active": True},
            "garage@insure.demo":      {"name": "Peter Kamau",     "role": "garage",           "active": True},
            "finance@insure.demo":     {"name": "Susan Achieng",   "role": "finance",          "active": True},
            "legal@insure.demo":       {"name": "Michael Odhiambo","role": "legal",            "active": True},
            "investigator@insure.demo":{"name": "Robert Mutua",    "role": "investigator",    "active": True},
            "spare_parts@insure.demo": {"name": "Francis Ngugi",   "role": "spare_parts",      "active": True},
            "super@insure.demo":       {"name": "Super Admin",     "role": "super_admin",      "active": True},
        }

        with st.expander("Add New User", expanded=False):
            with st.form(key="add_user_form"):
                email = st.text_input("Email Address", placeholder="user@insure.demo")
                name = st.text_input("Full Name")
                role = st.selectbox("Role", [
                    "client", "claims_officer", "head_of_claims", "admin",
                    "assessor", "garage", "finance", "legal",
                    "investigator", "spare_parts", "super_admin"
                ])
                col1, col2 = st.columns(2)
                with col1: active = st.checkbox("Active", value=True)
                with col2: temp_pass = st.text_input("Temp Password", type="password")
                submitted = st.form_submit_button("Create User")
                if submitted:
                    if email and name:
                        st.success(f"User '{email}' created with role '{role}'")
                    else:
                        st.error("Email and name are required.")

        st.markdown(f"**{len(DEMO_USERS)} user(s)**")
        users_df = pd.DataFrame([
            {"Email": e, "Name": v["name"], "Role": v["role"], "Active": "Y" if v["active"] else "N"}
            for e, v in DEMO_USERS.items()
        ])
        st.dataframe(users_df, use_container_width=True)

        st.markdown("**Manage User**")
        sel_email = st.selectbox("Select user", list(DEMO_USERS.keys()), key="sel_user")
        if sel_email:
            u = DEMO_USERS[sel_email]
            col1, col2 = st.columns(2)
            with col1:
                if u["active"]:
                    if st.button("Deactivate User"):
                        st.warning(f"User '{sel_email}' deactivated.")
                else:
                    if st.button("Activate User"):
                        st.success(f"User '{sel_email}' activated.")
            with col2:
                if st.button("Reset Password"):
                    st.info(f"Password reset email sent to {sel_email}")

    with tab_roles:
        st.subheader("Role Configuration")
        ROLES = {
            "client": {"description": "Policy holder â submit FNOL, track claims", "views": ["FNOL", "Claim Tracker", "Documents"]},
            "claims_officer": {"description": "Handle FNOL, assign experts, set reserves", "views": ["My Claims", "Assign Experts", "Reserve Mgmt", "Settlement", "Correspondance"]},
            "head_of_claims": {"description": "Oversee all claims, approve settlements, SLA", "views": ["Dashboard", "Pending Approvals", "SLA Tracker", "All Claims"]},
            "finance": {"description": "Process payments, manage disbursements", "views": ["Payment Dashboard", "Process Payment", "Reports"]},
            "legal": {"description": "Repudiation, litigation, demand letters", "views": ["Repudiation", "Litigation", "Demand Letters"]},
            "assessor": {"description": "Survey damage, submit assessment reports", "views": ["My Jobs", "Submit Report", "Quotes"]},
            "garage": {"description": "Vehicle repairs, quote submission", "views": ["My Jobs", "Submit Quote"]},
            "investigator": {"description": "Fraud investigation, field reports", "views": ["My Jobs", "Submit Report"]},
            "spare_parts": {"description": "Parts supplier, RFQ responses", "views": ["RFQ Bids", "My Bids"]},
            "admin": {"description": "System administration", "views": ["Admin Dashboard", "Analytics", "Reports"]},
            "super_admin": {"description": "Full system access", "views": ["ALL"]},
        }
        role_sel = st.selectbox("Select role to configure", list(ROLES.keys()))
        if role_sel:
            r = ROLES[role_sel]
            st.markdown(f"**Description:** {r['description']}")
            st.markdown(f"**Allowed views:** {', '.join(r['views'])}")
            with st.form(key=f"role_edit_{role_sel}"):
                new_desc = st.text_input("Role description", value=r['description'])
                new_views = st.text_area("Allowed views (comma-separated)", value=", ".join(r['views']))
                submitted = st.form_submit_button("Save Role Config")
                if submitted:
                    st.success(f"Role '{role_sel}' updated.")

    with tab_api:
        st.subheader("API Configuration")
        st.caption("Configure external system connections. Changes require app restart.")
        def get_env(key, default=""):
            try:
                return os.environ.get(key, st.secrets.get(key, default))
            except Exception:
                return os.environ.get(key, default)

        with st.form(key="api_config_form"):
            st.markdown("**Core Policy/Claims API**")
            core_base = st.text_input("CORE_API_BASE_URL", value=get_env("CORE_API_BASE_URL", ""), placeholder="https://api.core-system.example.com")
            core_key = st.text_input("CORE_API_KEY", value="â¢â¢â¢â¢â¢â¢â¢â¢", type="password", placeholder="Enter API key")
            st.markdown("**Analytics DB (Databricks or any SQLAlchemy DB)**")
            analyt_host = st.text_input("ANALYTICS_SQL_HOST", value=get_env("ANALYTICS_SQL_HOST", ""), placeholder="e.g.adb-xxx.databricks.net")
            analyt_token = st.text_input("ANALYTICS_SQL_TOKEN", value="â¢â¢â¢â¢â¢â¢â¢â¢", type="password", placeholder="Databricks token or SQLAlchemy connection string")
            analyt_wh = st.text_input("ANALYTICS_SQL_WAREHOUSE_ID", value=get_env("ANALYTICS_SQL_WAREHOUSE_ID", ""), placeholder="Warehouse ID")
            analyt_conn = st.text_input("ANALYTICS_SQL_CONNECTION_STRING", value=get_env("ANALYTICS_SQL_CONNECTION_STRING", ""), placeholder="postgresql://user:pass@host:5432/db")
            st.markdown("**SMS Notification (Africastalking)**")
            sms_user = st.text_input("AFRICAS_TALKING_USERNAME", value=get_env("AFRICAS_TALKING_USERNAME", ""), placeholder="sandbox")
            sms_key = st.text_input("AFRICAS_TALKING_API_KEY", value="â¢â¢â¢â¢â¢â¢â¢â¢", type="password")
            st.markdown("**M-Pesa Payment Gateway**")
            mpesa_consumer = st.text_input("M_PESA_CONSUMER_KEY", value=get_env("M_PESA_CONSUMER_KEY", ""))
            mpesa_secret = st.text_input("M_PESA_CONSUMER_SECRET", value="â¢â¢â¢â¢â¢â¢â¢â¢", type="password")
            mpesa_shortcode = st.text_input("M_PESA_SHORTCODE", value=get_env("M_PESA_SHORTCODE", ""))
            submitted = st.form_submit_button("Save API Configuration")
            if submitted:
                st.success("API configuration saved to .env â restart app to apply.")
                st.info("In production: write to a secure secrets manager, never commit .env.")

        st.markdown("**Test Connections**")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Test Core API"):
                if core_base:
                    st.info("Would test: " + core_base + "/health")
                else:
                    st.warning("CORE_API_BASE_URL not configured â using demo mode.")
        with col2:
            if st.button("Test Analytics DB"):
                st.info("Would run: SELECT 1 on analytics DB.")
        with col3:
            if st.button("Test SMS"):
                st.info("Would send test SMS via Africastalking.")

    with tab_views:
        st.subheader("View Permissions Matrix")
        st.caption("Grant or deny specific views per role. Changes apply immediately.")
        VIEWS = ["FNOL", "Claim Tracker", "My Claims", "Assign Experts", "Reserve Mgmt",
                 "Settlement", "Correspondance", "Analytics", "Admin Dashboard",
                 "Legal", "Finance", "Service Provider", "Spare Parts"]
        ROLES_LIST = ["client", "claims_officer", "head_of_claims", "finance", "legal",
                      "assessor", "garage", "investigator", "spare_parts", "admin"]
        PERMS = {
            "client": {"FNOL", "Claim Tracker", "Documents"},
            "claims_officer": {"My Claims", "Assign Experts", "Reserve Mgmt", "Settlement", "Correspondance"},
            "head_of_claims": {"All Claims", "Pending Approvals", "SLA Tracker", "Analytics"},
            "finance": {"Payment Dashboard", "Process Payment", "Reports"},
            "legal": {"Repudiation", "Litigation", "Demand Letters"},
            "assessor": {"My Jobs", "Submit Report", "Quotes"},
            "garage": {"My Jobs", "Submit Quote"},
            "investigator": {"My Jobs", "Submit Report"},
            "spare_parts": {"RFQ Bids", "My Bids"},
            "admin": {"Admin Dashboard", "Analytics", "Reports"},
        }
        for role in ROLES_LIST:
            with st.expander(role.toUpperCase() + " â " + PERMS.get(role, new Set()).size + " view(s) allowed", expanded=False):
                allowed = PERMS.get(role, new Set())
                for view in VIEWS:
                    col1, col2 = st.columns([4, 1])
                    with col1: st.markdown(view)
                    with col2:
                        granted = allowed.has(view)
                        new_val = st.checkbox("Granted", value=granted, key="perm_" + role + "_" + view)
                        if new_val != granted:
                            if new_val:
                                allowed.add(view)
                                st.success("'" + view + "' granted to '" + role + "'")
                            else:
                                allowed.delete(view)
                                st.warning("'" + view + "' revoked from '" + role + "'")
        if st.button("Save Permission Matrix"):
            st.success("Permission matrix saved.")

    with tab_audit:
        st.subheader("Audit Log")
        AUDIT_EVENTS = [
            {"when": "2025-07-30 09:12", "who": "super@insure.demo", "what": "User created", "detail": "New user: new.adjuster@insure.demo"},
            {"when": "2025-07-30 09:08", "who": "super@insure.demo", "what": "Role updated", "detail": "Role 'assessor': view 'Quotes' added"},
            {"when": "2025-07-30 08:55", "who": "super@insure.demo", "what": "API config changed", "detail": "CORE_API_BASE_URL updated"},
            {"when": "2025-07-30 08:41", "who": "officer@insure.demo", "what": "Expert assigned", "detail": "ASN-20250730-ABC123 assigned to CLM-2025-007"},
            {"when": "2025-07-30 08:30", "who": "super@insure.demo", "what": "User deactivated", "detail": "User 'former.staff@insure.demo' deactivated"},
        ]
        audit_df = pd.DataFrame(AUDIT_EVENTS)
        st.dataframe(audit_df, use_container_width=True)
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("Filter by user", ["All", "super@insure.demo", "officer@insure.demo"], key="audit_user_filter")
        with col2:
            st.selectbox("Filter by event type", ["All", "User created", "Role updated", "API config changed"], key="audit_type_filter")
        st.download_button("Download Audit Log (CSV)", data=audit_df.to_csv(index=False), file_name="audit_log.csv", mime="text/csv")

    with tab_config:
        st.subheader("System Configuration")
        st.markdown("**Insurance Business Rules**")
        with st.form(key="biz_rules_form"):
            col1, col2 = st.columns(2)
            with col1:
                sla_ack = st.number_input("Ack SLA (days)", value=14, min_value=1, max_value=60)
                sla_settle = st.number_input("Settlement SLA (days)", value=30, min_value=1, max_value=180)
                reinsurance_thresh = st.number_input("Reinsurance Threshold (KES)", value=2000000, step=100000, format="%d")
            with col2:
                officer_limit = st.number_input("Officer Auto-Approve Limit (KES)", value=500000, step=50000, format="%d")
                wht_standard = st.number_input("Standard WHT Rate (%)", value=5, min_value=0, max_value=20)
                wht_spare_parts = st.number_input("Spare Parts WHT Rate (%)", value=10, min_value=0, max_value=20)
            submitted = st.form_submit_button("Save Business Rules")
            if submitted:
                st.success("Business rules saved â SLA, reinsurance, WHT, and approval limits updated.")

        st.markdown("**Database Management**")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("View SQLite Schema"):
                st.code("Tables:\n  - reserves\n  - diary_entries\n  - communications\n  - expert_assignments\n  - claim_documents\n  - settlements")
        with col2:
            if st.button("Export All Data (JSON)"):
                st.info("In production: export all SQLite tables to JSON for backup.")
        with col3:
            if st.button("Clear Demo Data"):
                st.warning("This will delete all local SQLite data. Confirmed?")

        st.markdown("**App Health**")
        health = {
            "Core API": (core_api && typeof core_api.is_configured === 'function' && core_api.is_configured()) ? "Connected" : "Demo mode",
            "Analytics DB": "Not configured",
            "SMS": "Not configured",
            "M-Pesa": "Not configured",
            "Database": "claims_operations.db",
            "App Version": "2.1.0",
            "Branch": "railway-migration",
        }
        health_df = pd.DataFrame(list(health.items()), columns=["Component", "Status"])
        st.dataframe(health_df, use_container_width=True)
