"""
# v2026-08-08-redeploy - force fresh container
app.py ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Definite Assurance Claims Portal
Stackwire / Definite Assurance ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Phase 2 (Railway Migration)
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
    "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ  Home": [],
    "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Claimant Portal": [
        "pages/00_claimant/01_dashboard.py",
        "pages/00_claimant/02_new_claim.py",
        "pages/00_claimant/03_track_claim.py",
        "pages/00_claimant/04_upload_documents.py",
        "pages/00_claimant/05_claim_detail.py",
    ],
    "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¥ Intake Panel": [
        "pages/10_intake/01_queue.py",
        "pages/10_intake/02_claim_review.py",
        "pages/10_intake/03_triage_action.py",
        "pages/10_intake/04_audit_log.py",
    ],
    "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ§ Provider Panel": [
        "pages/20_provider/01_assigned_claims.py",
        "pages/20_provider/02_submit_report.py",
        "pages/20_provider/03_settlement_view.py",
    ],
    "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¦ Finance": [
        "pages/40_finance/01_reserves.py",
        "pages/40_finance/02_settlement.py",
    ],
    "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Legal": [
        "pages/50_legal/01_legal_review.py",
        "pages/50_legal/02_appeals_register.py",
    ],
    "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Operations": [
        "pages/60_operations/01_discharge_voucher.py",
        "pages/60_operations/02_fast_track.py",
    ],
    "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Admin Console": [
        "pages/30_admin/01_overview.py",
        "pages/30_admin/02_config_editor.py",
        "pages/30_admin/03_user_management.py",
        "pages/30_admin/04_config_audit.py",
        "pages/30_admin/05_api_status.py",
    ],
}

ROLE_ACCESS = {
    "client":           ["ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ  Home", "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Claimant Portal"],
    "claims_officer":   ["ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¥ Intake Panel", "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Claimant Portal"],
    "head_of_claims":   ["ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¥ Intake Panel", "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Operations"],
    "assessor":         ["ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ§ Provider Panel"],
    "investigator":     ["ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ§ Provider Panel"],
    "garage":           ["ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ§ Provider Panel"],
    "spare_parts":      ["ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ§ Provider Panel"],
    "finance":          ["ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¦ Finance"],
    "legal":            ["ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Legal"],
    "admin":            ["ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Admin Console", "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¦ Finance", "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Legal", "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Operations"],
    "super_admin":      ["ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Admin Console", "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¦ Finance", "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Legal", "ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Operations", "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¥ Intake Panel", "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ§ Provider Panel", "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Claimant Portal"],
    "cfo":              ["ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¦ Finance", "ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Admin Console"],
    "manager":          ["ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂ¯ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ Admin Console"],
    "surveyor":         ["ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ§ Provider Panel"],
    "motor_fleet":      ["ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Claimant Portal"],
}

def init() -> None:
    auth.init_session()
    if "engine" not in st.session_state:
        st.session_state["engine"] = get_engine()
    if "cfg" not in st.session_state:
        st.session_state["cfg"] = config_db.get_config()

def login_page() -> None:
    st.title("ð¢ Definite Assurance")
    st.caption("Claims Management Portal")
    email = st.text_input("Email", placeholder="claims_officer@insure.demo")
    password = st.text_input("Password", type="password", placeholder="Officer#99")
    if st.button("Sign In", type="primary"):
        if auth.login(email, password):
            st.rerun()
        else:
            st.error("Invalid credentials. Try a demo account.")
    with st.expander("Demo Accounts"):
        for email_addr, info in auth.DEMO_USERS.items():
            st.caption(f"{info['name']} ({info['role']}): {email_addr}")

def sidebar_nav() -> str:
    st.sidebar.title("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢ Definite Assurance")
    st.sidebar.caption("Claims Portal v2.0")
    st.sidebar.divider()
    user = auth.current_user()
    st.sidebar.success(f"ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ {user["name"]}")
    st.sidebar.caption(f"Role: {user["role"].replace("_", " ").title()}")
    st.sidebar.divider()
    allowed = ROLE_ACCESS.get(user["role"], [])
    selected = st.sidebar.radio("Navigation", allowed, index=None, placeholder="Choose a section...")
    st.sidebar.divider()
    if st.sidebar.button("ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂª Sign Out"):
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
    st.set_page_config(page_title="Definite Assurance ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ Claims Portal", page_icon="ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¢", layout="wide")
    init()
    if not st.session_state.get("authenticated"):
        login_page()
        return
    selected = sidebar_nav()
    if not selected:
        st.title("Claims Portal v2.0")
        st.success("Running.")
        return
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
