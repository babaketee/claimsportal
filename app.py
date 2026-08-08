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

def home_page():
    st.title("Claims Portal v2.0")
    st.success("Welcome! Select a section from the navigation above.")
    st.markdown("---")
    user = auth.current_user()
    col1, col2, col3 = st.columns(3)
    col1.metric("User", user["name"])
    col2.metric("Role", user["role"])
    col3.metric("Email", user["email"])

def main():
    st.set_page_config(page_title="Claims Portal", page_icon="🏢", layout="wide")
    init()
    if not st.session_state.get("authenticated"):
        login_page()
        return
    pages = st.navigation([
        st.Page(home_page, title="Home", icon="🏠", url_path="home"),
        st.Page("pages/00_claimant/01_dashboard.py", title="Claimant Portal", icon="👤"),
        st.Page("pages/10_intake/01_queue.py", title="Intake Panel", icon="📋"),
        st.Page("pages/20_provider/01_assigned_claims.py", title="Provider Panel", icon="🔧"),
        st.Page("pages/40_finance/01_reserves.py", title="Finance", icon="💰"),
        st.Page("pages/50_legal/01_legal_review.py", title="Legal", icon="⚖️"),
        st.Page("pages/60_operations/01_discharge_voucher.py", title="Operations", icon="📄"),
        st.Page("pages/30_admin/01_overview.py", title="Admin Console", icon="🖥️"),
    ])
    user = auth.current_user()
    st.sidebar.title("Definite Assurance")
    st.sidebar.text(f"Logged in: {user['name']}")
    st.sidebar.text(f"Role: {user['role']}")
    if st.sidebar.button("Sign Out"):
        auth.logout()
        st.rerun()
    pages.run()

if __name__ == "__main__":
    main()
