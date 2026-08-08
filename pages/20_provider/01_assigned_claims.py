"""Assigned Claims — pages/20_provider/01_assigned_claims.py"""
"""
Role: assessor, investigator, garage, spare_parts
View claims assigned to the logged-in provider.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine
import streamlit as st
import pandas as pd

def render(user_email: str, user_role: str = "assessor") -> None:
    st.title("🔧 Assigned Claims")
    engine = get_engine()
    statuses = ["Investigation","Assessment","Approval","Under Repair","Reinspection"]
    all_rows = []
    for s in statuses:
        try:
            for c in engine.get_claims_by_status(s):
                if c.get("assigned_to") == user_email:
                    all_rows.append(c)
        except: pass
    if not all_rows:
        st.info("No claims assigned to you.")
        return
    rows = [{"Ref": c.get("claim_ref"),"Status": c.get("status"),
             "Amount": f"KES {c.get('estimated_amount',0):,.0f}",
             "Class": c.get("claim_class","").replace("_"," ").title()} for c in all_rows]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
