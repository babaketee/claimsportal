"""app.py — Phase 1 Claims Portal Router
=========================================
Definite Assurance Insurance | Claims Portal

Auth: session_state-based demo auth (swap for real auth in Phase 2).
Role -> view mapping:
  client           -> views/claimant_portal
  claims_officer   -> views/intake_panel
  head_of_claims   -> views/intake_panel  (superset)
  assessor         -> views/provider_panel
  investigator     -> views/provider_panel
  garage           -> views/provider_panel
  spare_parts      -> views/provider_panel
  admin            -> views/admin_console
  super_admin      -> views/admin_console  (superset)
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import core_api
import core_engine
import config_db

# Import legacy views
import views.client_portal     as client_portal
import views.claims_officer  as claims_officer
import views.head_of_claims  as hoc
import views.surveyor        as surveyor
import views.investigator    as investigator
import views.garage          as garage_mod
import views.legal           as legal
import views.manager         as manager
import views.motor_fleet     as motor_fleet
import views.admin_dashboard as admin_dashboard
import views.analytics_charts as analytics_charts
import views.brand           as brand
import views.super_admin     as super_admin

# Phase 1 new views — valid Python identifiers (no leading digits)
try:
    import views.claimant_portal as claimant_portal
except ImportError:
    claimant_portal = None

try:
    import views.intake_panel as intake_panel
except ImportError:
    intake_panel = None

try:
    import views.provider_panel as provider_panel
except ImportError:
    provider_panel = None

try:
    import views.admin_console as admin_console
except ImportError:
    admin_console = None


# ─── Role definitions ────────────────────────────────────────────────────────

CLAIMANT_ROLES = {"client"}
INTAKE_ROLES    = {"claims_officer", "head_of_claims"}
PROVIDER_ROLES  = {"assessor", "investigator", "garage", "spare_parts"}
ADMIN_ROLES     = {"admin", "super_admin"}

ROLE_LABELS = {
    "client":          "Client / Policyholder",
    "claims_officer":  "Claims Officer",
    "head_of_claims":   "Head of Claims",
    "assessor":         "Assessor",
    "investigator":      "Investigator",
    "garage":           "Garage",
    "spare_parts":      "Spare Parts",
    "admin":            "Administrator",
    "super_admin":      "Super Administrator",
    "legal":            "Legal",
    "manager":          "Manager",
    "surveyor":         "Surveyor",
    "motor_fleet":      "Motor Fleet Manager",
}

# ─── Demo users ───────────────────────────────────────────────────────────────

DEMO_USERS = {
    "client@insure.demo":               ("Jane Policyholder",  "client",           "Client#99"),
    "claims_officer@insure.demo":       ("Caleb Officer",      "claims_officer",  "Officer#99"),
    "head_of_claims@insure.demo":       ("Diana HOC",          "head_of_claims",  "HOC#99"),
    "assessor@insure.demo":             ("Felix Assessor",     "assessor",        "Survey#99"),
    "investigator@insure.demo":         ("Ivan Investigator",  "investigator",    "Sleuth#99"),
    "garage@insure.demo":               ("George Garage",      "garage",          "Wrench#99"),
    "spare_parts@insure.demo":          ("Sara Spares",        "spare_parts",     "Catalog#99"),
    "admin@insure.demo":                ("Ada Admin",          "admin",           "SysCtrl#99"),
    "super@insure.demo":                 ("Sam Super",           "super_admin",      "Super#99"),
    "legal@insure.demo":                ("Lara Legal",         "legal",           "Counsel#99"),
    "manager@insure.demo":             ("Mary Manager",        "manager",         "Manager#99"),
    "surveyor@insure.demo":             ("Steve Surveyor",      "surveyor",        "Survey#99"),
    "motor_fleet@insure.demo":          ("Molly Fleet",         "motor_fleet",     "Fleet#99"),
}

def _get_user(email: str, password: str) -> tuple | None:
    entry = DEMO_USERS.get(email)
    if entry and entry[2] == password:
        return entry[0], entry[1]
    return None

# ─── Page dispatch ───────────────────────────────────────────────────────────

def _render_page(user_email: str, user_name: str, user_role: str) -> None:
    # Phase 1 new views (digit-free names)
    if claimant_portal and user_role in CLAIMANT_ROLES:
        claimant_portal.render(user_email)
        return

    if intake_panel and user_role in INTAKE_ROLES:
        intake_panel.render(user_email, user_role)
        return

    if provider_panel and user_role in PROVIDER_ROLES:
        provider_panel.render(user_email, user_role)
        return

    if admin_console and user_role in ADMIN_ROLES:
        admin_console.render(user_email, user_role)
        return

    # Legacy views (prototype-era)
    legacy_map = {
        "claims_officer": claims_officer.render,
        "head_of_claims": hoc.render,
        "surveyor":       surveyor.render,
        "investigator":   investigator.render,
        "garage":         garage_mod.render,
        "legal":          legal.render,
        "manager":        manager.render,
        "motor_fleet":    motor_fleet.render,
        "admin":          admin_dashboard.render,
        "super_admin":    super_admin.render,
    }

    fn = legacy_map.get(user_role)
    if fn:
        try:
            fn(user_email)
        except TypeError:
            fn()
        return

    st.error(f"No view configured for role: {user_role}")

# ─── Login page ───────────────────────────────────────────────────────────────

def _render_login() -> None:
    st.set_page_config(
        page_title="Definite Assurance — Claims Portal",
        page_icon="🛡️",
        layout="centered",
    )

    st.html("""<div style="text-align:center; margin-bottom:2rem;">
        <h1 style="color:#1a5276;">🛡️ Definite Assurance</h1>
        <p style="color:gray;">Insurance Company Limited — Kenya</p>
    </div>""")

    st.info("**Demo Accounts** (email / password)")
    demo_rows = ""
    for email, (name, role, pwd) in sorted(DEMO_USERS.items()):
        label = ROLE_LABELS.get(role, role)
        demo_rows += f"<tr><td>{name}</td><td><code>{email}</code></td><td><code>{pwd}</code></td><td>{label}</td></tr>"
    st.html(f"""
    <table style="width:100%; border-collapse:collapse; font-size:0.85rem;">
        <tr style="background:#1a5276; color:white;">
            <th style="padding:6px;text-align:left;">Name</th>
            <th style="padding:6px;text-align:left;">Email</th>
            <th style="padding:6px;text-align:left;">Password</th>
            <th style="padding:6px;text-align:left;">Role</th>
        </tr>
        {demo_rows}
    </table>""")

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Sign In")
        email    = st.text_input("Email",    placeholder="client@insure.demo",   disabled=False)
        password = st.text_input("Password", placeholder="Client#99", type="password", disabled=False)
        submitted = st.button("Sign In", type="primary", use_container_width=True)

    if submitted:
        user = _get_user(email, password)
        if user:
            st.session_state["authenticated"] = True
            st.session_state["user_email"]     = email
            st.session_state["user_name"]      = user[0]
            st.session_state["user_role"]      = user[1]
            st.rerun()
        else:
            st.error("Invalid email or password.")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Definite Assurance — Claims Portal",
        page_icon="🛡️",
        layout="wide",
    )

    for k, v in {
        "authenticated": False,
        "user_email":    "",
        "user_name":     "",
        "user_role":     "",
    }.items():
        st.session_state.setdefault(k, v)

    if not st.session_state["authenticated"]:
        _render_login()
        return

    user_email = st.session_state["user_email"]
    user_name  = st.session_state["user_name"]
    user_role  = st.session_state["user_role"]

    with st.sidebar:
        st.write(f"**{user_name}**")
        st.caption(ROLE_LABELS.get(user_role, user_role))
        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    _render_page(user_email, user_name, user_role)


if __name__ == "__main__":
    main()
