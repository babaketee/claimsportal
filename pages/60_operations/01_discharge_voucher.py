"""
Discharge Voucher - pages/60_operations/01_discharge_voucher.py
Role: head_of_claims
Process discharge vouchers for approved claims.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine
import streamlit as st
import pandas as pd

def render(user_email: str, user_role: str = "head_of_claims") -> None:
    st.title("Discharge Voucher")
    engine = get_engine()
    try:
        rows = []
        for c in engine.get_claims_by_status("Approved"):
            rows.append({
                "Claim Ref": c.get("claim_ref",""),
                "Class": c.get("claim_class","").replace("_"," ").title(),
                "Amount": f"KES {c.get('estimated_amount',0):,.0f}",
                "Status": c.get("status",""),
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No approved claims.")
    except Exception as e:
        st.error(f"Error: {e}")

if __name__ == "__main__":
    render("test@insure.demo", "head_of_claims")
