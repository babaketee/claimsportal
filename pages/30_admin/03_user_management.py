"""User Management — pages/30_admin/03_user_management.py"""
"""Role: admin, super_admin. View users and roles."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_api
import streamlit as st
import pandas as pd

def render(user_email: str, user_role: str = "admin") -> None:
    st.title("👥 User Management")
    users = core_api.get_all_users() if hasattr(core_api,"get_all_users") else []
    if not users:
        st.info("No users found."); return
    rows = [{"Name": u.get("name",""), "Email": u.get("email",""), "Role": u.get("role","").replace("_"," ").title()} for u in users]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown("---—")
    st.info("User role management is view-only in Phase 1. Full CRUD in Phase 2.")
