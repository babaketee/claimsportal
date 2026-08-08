"""
Legal Review - pages/50_legal/01_legal_review.py
Role: legal
Review claims pending legal sign-off.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine
import streamlit as st
import pandas as pd

def render(user_email: str, user_role: str = "legal") -> None:
    st.title("Legal Review")
    engine = get_engine()
    try:
        rows = []
        for c in engine.get_claims_by_status("Approval"):
            if "legal" in c.get("status","").lower():
                rows.append({
                    "Claim Ref": c.get("claim_ref",""),
                    "Class": c.get("claim_class","").replace("_"," ").title(),
                    "Status": c.get("status",""),
                    "Amount": f"KES {c.get('estimated_amount',0):,.0f}",
                })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.warning("Not found.")
    except Exception as e:
        st.error(f"Error: {e}")

if __name__ == "__main__":
    render("test@insure.demo", "legal")
