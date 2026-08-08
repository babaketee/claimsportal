"""
Admin Overview - pages/30_admin/01_overview.py
Role: admin, super_admin, manager, cfo
Overview of all claims across the system.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine
import streamlit as st
import pandas as pd

def render(user_email: str, user_role: str = "admin") -> None:
    st.title("Admin Overview")
    engine = get_engine()
    try:
        rows = []
        for status in ["Draft","Reported","Triage","Investigation","Assessment","Approval","Approved","Pending Payment","Paid","Closed"]:
            for c in engine.get_claims_by_status(status):
                rows.append({
                    "Claim Ref": c.get("claim_ref",""),
                    "Class": c.get("claim_class","").replace("_"," ").title(),
                    "Status": c.get("status",""),
                    "Amount": f"KES {c.get('estimated_amount',0):,.0f}",
                })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No claims found.")
    except Exception as e:
        st.error(f"Error: {e}")

if __name__ == "__main__":
    render("test@insure.demo", "admin")
