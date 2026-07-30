import os
import sys

import streamlit as st

# Ensure views/ is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="Definite Assurance | Claims Portal",
    page_icon="â",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Brand identity â must run right after set_page_config
from views.brand import (  # noqa: E402
    inject_brand_css,
    brand_strip,
    brand_login_header,
    brand_sidebar_header,
)
inject_brand_css()

# ---------------------------------------------------------------------------
# Role registry
# ---------------------------------------------------------------------------
ROLES: dict[str, str] = {
    "client":         "Policyholder / Client",
    "claims_officer": "Claims Officer",
    "head_of_claims": "Head of Claims",
    "assessor":       "Assessor",
    "garage":         "Garage / Repairer",
    "investigator":   "Investigator",
    "finance":        "Finance / Accounts Payable",
    "finance_head":   "Finance Head",
    "spare_parts":    "Spare Parts Provider",
    "legal":          "Legal Officer",
    "admin":          "Internal Staff / Admin",
}

# ---------------------------------------------------------------------------
# Demo accounts  (swap for real auth in production)
# ---------------------------------------------------------------------------
DEMO_ACCOUNTS: dict[str, dict] = {
    "client@insure.demo":       {"password": "Assured#99",   "role": "client"},
    "officer@insure.demo":      {"password": "Handler#99",   "role": "claims_officer"},
    "hoc@insure.demo":          {"password": "Oversee#99",   "role": "head_of_claims"},
    "assessor@insure.demo":     {"password": "Survey#99",    "role": "assessor"},
    "garage@insure.demo":       {"password": "Wrench#99",    "role": "garage"},
    "investigator@insure.demo": {"password": "Sleuth#99",    "role": "investigator"},
    "finance@insure.demo":      {"password": "Invoice#99",   "role": "finance"},
    "cfo@insure.demo":          {"password": "Reserves#99",  "role": "finance_head"},
    "spares@insure.demo":       {"password": "Catalog#99",   "role": "spare_parts"},
    "legal@insure.demo":        {"password": "Counsel#99",   "role": "legal"},
    "admin@insure.demo":        {"password": "SysCtrl#99",   "role": "admin"},
}


def show_login() -> None:
    """Render the login page."""
    _, col, _ = st.columns([1, 2, 1])
    with col:
        brand_login_header()
        st.markdown("---")
        with st.form("login"):
            identifier  = st.text_input("Email Address / Policy Number")
            password    = st.text_input("Password", type="password")
            submitted   = st.form_submit_button(
                "Sign In", use_container_width=True, type="primary"
            )

        if submitted:
            identifier = identifier.strip()
            password   = password.strip()
            if not identifier or not password:
                st.error("Please fill in all fields.")
            elif identifier not in DEMO_ACCOUNTS or DEMO_ACCOUNTS[identifier]["password"] != password:
                st.error("Invalid email or password.")
            else:
                # TODO: Replace this stub with your real auth flow:
                #   - IMS REST API  â  POST /api/auth/login
                #   - Okta / Azure AD SSO  â  OIDC redirect
                #   - OTP via Africa's Talking / Twilio
                acct = DEMO_ACCOUNTS[identifier]
                st.session_state.update(
                    authenticated=True,
                    role=acct["role"],
                    user=identifier,
                )
                st.rerun()


def show_sidebar(role: str) -> None:
    """Render the persistent sidebar."""
    with st.sidebar:
        brand_sidebar_header()
        st.divider()
        st.markdown(f"**Role:** {ROLES[role]}")
        st.caption(f"{st.session_state['user']}")
        st.divider()
        if st.button("Sign Out", use_container_width=True):
            st.session_state.clear()
            st.rerun()


def main() -> None:
    if not st.session_state.get("authenticated"):
        show_login()
        return

    role = st.session_state["role"]
    show_sidebar(role)
    brand_strip()

    if role == "client":
        from views.client_portal import render
        render()
    elif role == "claims_officer":
        from views.claims_officer import render
        render()
    elif role == "head_of_claims":
        from views.head_of_claims import render
        render()
    elif role in ("assessor", "garage", "investigator"):
        from views.service_provider import render
        render(role)
    elif role in ("finance", "finance_head"):
        from views.finance import render
        render(role)
    elif role == "spare_parts":
        from views.spare_parts_provider import render
        render()
    elif role == "legal":
        from views.legal import render
        render()
    elif role == "admin":
        from views.admin_dashboard import render
        render()
    else:
        st.error("Unknown role. Contact your administrator.")


main()
