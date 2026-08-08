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
    
    user = auth.current_user()
    role = user["role"]
    
    all_pages = [
        ("Home", home_page, "🏠", "home"),
        ("Claimant Portal", "pages/00_claimant/01_dashboard.py", "👤", None),
        ("Intake Panel", "pages/10_intake/01_queue.py", "📋", None),
        ("Provider Panel", "pages/20_provider/01_assigned_claims.py", "🔧", None),
        ("Finance", "pages/40_finance/01_reserves.py", "💰", None),
        ("Legal", "pages/50_legal/01_legal_review.py", "⚖️", None),
        ("Operations", "pages/60_operations/01_discharge_voucher.py", "📄", None),
        ("Admin Console", "pages/30_admin/01_overview.py", "🖥️", None),
    ]
    
    role_access = {
        "client": [0, 1],
        "claims_officer": [0, 1, 2, 6],
        "head_of_claims": [0, 1, 2, 6],
        "assessor": [0, 1, 3],
        "investigator": [0, 1, 3],
        "garage": [0, 1, 3],
        "spare_parts": [0, 1, 3],
        "surveyor": [0, 1, 3],
        "finance": [0, 4],
        "cfo": [0, 4],
        "legal": [0, 5],
        "admin": list(range(8)),
        "super_admin": list(range(8)),
        "manager": list(range(8)),
    }
    
    allowed = role_access.get(role, [0])
    
    nav_pages = []
    for idx in allowed:
        title, page, icon, url_path = all_pages[idx]
        if url_path:
            nav_pages.append(st.Page(page, title=title, icon=icon, url_path=url_path))
        else:
            nav_pages.append(st.Page(page, title=title, icon=icon))
    
    pages = st.navigation(nav_pages)
    
    st.sidebar.title("Definite Assurance")
    st.sidebar.text(f"Logged in: {user['name']}")
    st.sidebar.text(f"Role: {role}")
    if st.sidebar.button("Sign Out"):
        auth.logout()
        st.rerun()
    pages.run()

if __name__ == "__main__":
    main()
