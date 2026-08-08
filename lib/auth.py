"""auth.py — RBAC session helpers for Definite Assurance Claims Portal"""
"""Phase 1: session_state-based demo auth. Phase 2: swap for real SSO/OIDC."""

import streamlit as st

DEMO_USERS = {
    "client@insure.demo":        {"name":"Jane Policyholder","role":"client","password":"Client#99"},
    "claims_officer@insure.demo":{"name":"Caleb Officer","role":"claims_officer","password":"Officer#99"},
    "head_of_claims@insure.demo":{"name":"Diana HOC","role":"head_of_claims","password":"HOC#99"},
    "assessor@insure.demo":      {"name":"Felix Assessor","role":"assessor","password":"Survey#99"},
    "investigator@insure.demo":  {"name":"Ivan Investigator","role":"investigator","password":"Sleuth#99"},
    "garage@insure.demo":        {"name":"George Garage","role":"garage","password":"Wrench#99"},
    "spare_parts@insure.demo":   {"name":"Sara Spares","role":"spare_parts","password":"Catalog#99"},
    "finance@insure.demo":        {"name":"Fatima Finance","role":"finance","password":"Invoice#99"},
    "admin@insure.demo":         {"name":"Ada Admin","role":"admin","password":"SysCtrl#99"},
    "super@insure.demo":          {"name":"Sam Super","role":"super_admin","password":"Super#99"},
    "legal@insure.demo":         {"name":"Lara Legal","role":"legal","password":"Counsel#99"},
    "manager@insure.demo":       {"name":"Mary Manager","role":"manager","password":"Manager#99"},
    "surveyor@insure.demo":      {"name":"Steve Surveyor","role":"surveyor","password":"Survey#99"},
    "motor_fleet@insure.demo":   {"name":"Molly Fleet","role":"motor_fleet","password":"Fleet#99"},
}

ROLE_LABELS = {
    "client":"Client / Policyholder","claims_officer":"Claims Officer","head_of_claims":"Head of Claims","assessor":"Assessor","investigator":"Investigator","garage":"Garage","spare_parts":"Spare Parts","finance":"Finance","admin":"Administrator","super_admin":"Super Administrator","legal":"Legal","manager":"Manager","surveyor":"Surveyor","motor_fleet":"Motor Fleet Manager","cfo":"CFO","spare_parts":"Spare Parts Supplier","hod":"Head of Department","driver":"Driver","motor_technical":"Motor Technical","branches":"Branches","ict":"ICT",
}

def init_session() -> None:
    for k, v in {"authenticated":False,"user_email":"","user_name":"","user_role":""}.items():
        st.session_state.setdefault(k, v)

def login(email: str, password: str) -> bool:
    entry = DEMO_USERS.get(email)
    if entry and entry["password"] == password:
        st.session_state["authenticated"] = True
        st.session_state["user_email"] = email
        st.session_state["user_name"] = entry["name"]
        st.session_state["user_role"] = entry["role"]
        return True
    return False

def logout() -> None:
    for k in list(st.session_state.keys()):
        del st.session_state[k]

def require_role(allowed_roles: list[str]) -> None:
    if not st.session_state.get("authenticated"):
        st.error("Not authenticated. Please sign in."); st.stop()
    role = st.session_state.get("user_role","")
    if role not in allowed_roles:
        st.error(f"Access denied. Your role ({ROLE_LABELS.get(role,role)}) cannot access this page."); st.stop()

def current_user() -> dict:
    return {"email": st.session_state.get("user_email",""),"name": st.session_state.get("user_name",""),"role": st.session_state.get("user_role","")}

def can_approve(role: str) -> bool:
    return role in ["head_of_claims","admin","super_admin","cfo"]

def can_view_financials(role: str) -> bool:
    return role in ["finance","cfo","admin","super_admin","head_of_claims"]
