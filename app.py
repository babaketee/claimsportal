"""
app.py - Definite Assurance Claims Portal
Phase 2 Railway Migration
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

import config_db
import core_engine
from core_engine import get_engine, ClaimStatus
import lib.auth as auth
import lib.helpers as helpers

PAGE_STRUCTURE = {
    "Home": [],
    "Claimant Portal": ["pages/00_claimant/01_dashboard.py"],
    "Intake Panel": ["pages/10_intake/01_queue.py"],
    "Provider Panel": ["pages/20_provider/01_assigned_claims.py"],
    "Finance": ["pages/40_finance/01_reserves.py"],
    "Legal": ["pages/50_legal/01_legal_review.py"],
    "Operations": ["pages/60_operations/01_discharge_voucher.py"],
    "Admin Console": ["pages/30_admin/01_overview.py"],
}

ROLE_ACCESS = {
    "client": ["Home", "Claimant Portal"],
    "claims_officer": ["Intake Panel", "Claimant Portal"],
    "head_of_claims": ["Intake Panel", "Operations"],
    "assessor": ["Provider Panel"],
    "investigator": ["Provider Panel"],
    "garage": ["Provider Panel"],
    "spare_parts": ["Provider Panel"],
    "finance": ["Finance"],
    "legal": ["Legal"],
    "admin": ["Admin Console", "Finance", "Legal", "Operations"],
    "super_admin": ["Admin Console", "Finance", "Legal", "Operations", "Intake Panel", "Provider Panel", "Claimant Portal"],
    "cfo": ["Finance", "Admin Console"],
    "manager": ["Admin Console"],
    "surveyor": ["Provider Panel"],
    "motor_fleet": ["Claimant Portal"],
}

def init():
    auth.init_session()
    if "engine" not in st.session_state:
        st.session_state["engine"] = get_engine()
    if "cfg" not in st.session_state:
        st.session_state["cfg"] = config_db.get_config()

def login_page():
    st.title("Definite Assurance")
    st.caption("Claims Management Portal")
    email = st.text_input("Email", placeholder="claims_officer@insure.demo")
    password = st.text_input("Password", type="password", placeholder="Officer#99")
    if st.button("Sign In", type="primary"):
        if auth.login(email, password):
            st.rerun()
        else:
            st.error("Invalid credentials.")
    with st.expander("Demo Accounts"):
        for email_addr, info in auth.DEMO_USERS.items():
            st.caption(f"{info['name']} ({info['role']})")

def sidebar_nav():
    st.sidebar.title("Definite Assurance")
    st.sidebar.caption("Claims Portal v2.0")
    user = auth.current_user()
    st.sidebar.text(f"Logged in as: {user['name']}")
    allowed = ROLE_ACCESS.get(user["role"], [])
    selected = st.sidebar.radio("Go to", allowed)
    if st.sidebar.button("Sign Out"):
        auth.logout()
        st.rerun()
    return selected

def render_page(page_path):
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
            st.error(f"Could not load: {page_path}")

def main():
    st.set_page_config(page_title="Claims Portal", page_icon="🏢", layout="wide")
    init()
    if not st.session_state.get("authenticated"):
        login_page()
        return
    selected = sidebar_nav()
    if not selected or selected == "Home":
        st.title("Claims Portal v2.0")
        st.success("Welcome! Select a section from the sidebar.")
        return
    page_path = None
    for section, pages in PAGE_STRUCTURE.items():
        if section == selected and pages:
            page_path = pages[0]
            break
    if page_path:
        render_page(page_path)
    else:
        st.error("No page configured.")

if __name__ == "__main__":
    main()
