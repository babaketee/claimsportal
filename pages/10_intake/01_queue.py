"""
Intake Queue - pages/10_intake/01_queue.py
Role: claims_officer, head_of_claims
Queue of all reported claims awaiting triage/assignment.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine
import streamlit as st
import pandas as pd

def render(user_email: str, user_role: str = "claims_officer") -> None:
    st.title("Intake Queue")
    engine = get_engine()
    try:
        rows = []
        for c in engine.get_claims_by_status("Reported"):
            rows.append({
                "Claim Ref": c.get("claim_ref",""),
                "Class": c.get("claim_class","").replace("_"," ").title(),
                " claimant_email": c.get("claimant_email",""),
                "Amount": f"KES {c.get('estimated_amount',0):,.0f}",
                "Status": c.get("status",""),
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No reported claims in queue.")
    except Exception as e:
        st.error(f"Error: {e}")
    st.markdown(f"**Total: {len(rows) if 'rows' in dir() else 0} claims**")

if __name__ == "__main__":
    render("test@insure.demo", "claims_officer")
