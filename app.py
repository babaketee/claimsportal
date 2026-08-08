"""
# v2026-08-08-redeploy - force fresh container
app.py Ã¢ÂÂ Definite Assurance Claims Portal
Stackwire / Definite Assurance Ã¢ÂÂ Phase 2 (Railway Migration)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from datetime import datetime

import config_db
import core_engine
from core_engine import get_engine, ClaimStatus
import lib.auth as auth
import lib.helpers as helpers

PAGE_STRUCTURE = {
    "Ã°ÂÂÂ  Home": [],
    "Ã°ÂÂÂ Claimant Portal": [
        "pages/00_claimant/01_dashboard.py",
        "pages/00_claimant/02_new_claim.py",
        "pages/00_claimant/03_track_claim.py",
        "pages/00_claimant/04_upload_documents.py",
        "pages/00_claimant/05_claim_detail.py",
    ],
    "Ã°ÂÂÂ¥ Intake Panel": [
        "pages/10_intake/01_queue.py",
        "pages/10_intake/02_claim_review.py",
        "pages/10_intake/03_triage_action.py",
        "pages/10_intake/04_audit_log.py",
    ],
    "Ã°ÂÂÂ§ Provider Panel": [
        "pages/20_provider/01_assigned_claims.py",
        "pages/20_provider/02_submit_report.py",
        "pages/20_provider/03_settlement_view.py",
    ],
    "Ã°ÂÂÂ¦ Finance": [
        "pages/40_finance/01_reserves.py",
        "pages/40_finance/02_settlement.py",
    ],
    "Ã¢ÂÂÃ¯Â¸Â Legal": [
        "pages/50_legal/01_legal_review.py",
        "pages/50_legal/02_appeals_register.py",
    ],
    "Ã¢ÂÂÃ¯Â¸Â Operations": [
        "pages/60_operations/01_discharge_voucher.py",
        "pages/60_operations/02_fast_track.py",
    ],
    "Ã°ÂÂÂ¡Ã¯Â¸Â Admin Console": [
        "pages/30_admin/01_overview.py",
        "pages/30_admin/02_config_editor.py",
        "pages/30_admin/03_user_management.py",
        "pages/30_admin/04_config_audit.py",
        "pages/30_admin/05_api_status.py",
    ],
}

ROLE_ACCESS = {
    "client":           ["Ã°ÂÂÂ  Home", "Ã°ÂÂÂ Claimant Portal"],
    "claims_officer":   ["Ã°ÂÂÂ¥ Intake Panel", "Ã°ÂÂÂ Claimant Portal"],
    "head_of_claims":   ["Ã°ÂÂÂ¥ Intake Panel", "Ã¢ÂÂÃ¯Â¸Â Operations"],
    "assessor":         ["Ã°ÂÂÂ§ Provider Panel"],
    "investigator":     ["Ã°ÂÂÂ§ Provider Panel"],
    "garage":           ["Ã°ÂÂÂ§ Provider Panel"],
    "spare_parts":      ["Ã°ÂÂÂ§ Provider Panel"],
    "finance":          ["Ã°ÂÂÂ¦ Finance"],
    "legal":            ["Ã¢ÂÂÃ¯Â¸Â Legal"],
    "admin":            ["Ã°ÂÂÂ¡Ã¯Â¸Â Admin Console", "Ã°ÂÂÂ¦ Finance", "Ã¢ÂÂÃ¯Â¸Â Legal", "Ã¢ÂÂÃ¯Â¸Â Operations"],
    "super_admin":      ["Ã°ÂÂÂ¡Ã¯Â¸Â Admin Console", "Ã°ÂÂÂ¦ Finance", "Ã¢ÂÂÃ¯Â¸Â Legal", "Ã¢ÂÂÃ¯Â¸Â Operations", "Ã°ÂÂÂ¥ Intake Panel", "Ã°ÂÂÂ§ Provider Panel", "Ã°ÂÂÂ Claimant Portal"],
    "cfo":              ["Ã°ÂÂÂ¦ Finance", "Ã°ÂÂÂ¡Ã¯Â¸Â Admin Console"],
    "manager":          ["Ã°ÂÂÂ¡Ã¯Â¸Â Admin Console"],
    "surveyor":         ["Ã°ÂÂÂ§ Provider Panel"],
    "motor_fleet":      ["Ã°ÂÂÂ Claimant Portal"],
}

def init() -> None:
    auth.init_session()
    if "engine" not in st.session_state:
        st.session_state["engine"] = get_engine()
    if "cfg" not in st.session_state:
        st.session_state["cfg"] = config_db.get_config()

def login_page() -> None:
    st.html("<div style='text-align:center;margin-bottom:1rem'><h1>Ã°ÂÂÂ¢ Definite Assurance</h1><p style='color:#666'>Claims Management Portal</p></div>")
    email = st.text_input("Email", placeholder="claims_officer@insure.demo", label_visibility="collapsed")
    password = st.text_input("Password", type="password", placeholder="Officer#99", label_visibility="collapsed")
    if st.button("Sign In", type="primary", use_container_width=True):
        if auth.login(email, password):
            st.rerun()
        else:
            st.error("Invalid credentials. Try a demo account.")
    with st.expander("Ã°ÂÂÂ Demo Accounts"):
        for email_addr, info in auth.DEMO_USERS.items():
            st.caption(f"**{info["name"]}** ({info["role"]}): `{email_addr}` / `{info["password"]}`")

def sidebar_nav() -> str:
    st.sidebar.title("Ã°ÂÂÂ¢ Definite Assurance")
    st.sidebar.caption("Claims Portal v2.0")
    st.sidebar.divider()
    user = auth.current_user()
    st.sidebar.success(f"Ã¢ÂÂ {user["name"]}")
    st.sidebar.caption(f"Role: {user["role"].replace("_", " ").title()}")
    st.sidebar.divider()
    allowed = ROLE_ACCESS.get(user["role"], [])
    selected = st.sidebar.radio("Navigation", allowed, index=None, placeholder="Choose a section...")
    st.sidebar.divider()
    if st.sidebar.button("Ã°ÂÂÂª Sign Out"):
        auth.logout()
        st.rerun()
    return selected

def render_page(page_path: str) -> None:
    user = auth.current_user()
    with st.spinner(f"Loading {page_path}..."):
        import importlib.util
        spec = importlib.util.spec_from_file_location("page_module", page_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules["page_module"] = mod
            spec.loader.exec_module(mod)
            if hasattr(mod, "render"):
                mod.render(user_email=user["email"], user_role=user["role"])
            else:
                st.info(f"Page loaded but has no render() function.")
        else:
            st.error(f"Could not load page: {page_path}")

def main() -> None:
    st.set_page_config(page_title="Definite Assurance Ã¢ÂÂ Claims Portal", page_icon="Ã°ÂÂÂ¢", layout="wide")
    init()
    if not st.session_state.get("authenticated"):
        login_page()
        return
    selected = sidebar_nav()
    if not selected:
        st.title("🏢 Definite Assurance — Claims Portal")
        st.success("Welcome! Claims Portal v2.0 is running.")
        st.info("Select a section from the sidebar to begin.")
        returnpage_path = None
    for section, pages in PAGE_STRUCTURE.items():
        if section == selected and pages:
            page_path = pages[0]
            break
    if not page_path:
        st.error("No page configured.")
        return
    render_page(page_path)

if __name__ == "__main__":
    main()
