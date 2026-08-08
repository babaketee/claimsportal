"""Intake Queue — pages/10_intake/01_queue.py"""
"""
Role: claims_officer, head_of_claims
Shows submitted claims awaiting triage and review.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine
import streamlit as st
import pandas as pd

def render(user_email: str, user_role: str = "claims_officer") -> None:
    st.title("📥 Intake Queue")
    engine = get_engine()
    statuses = ["Reported","Triage"]
    all_rows = []
    for s in statuses:
        try:
            for c in engine.get_claims_by_status(s):
                all_rows.append(c)
        except: pass
    if not all_rows:
        st.info("No claims in intake queue.")
        return
    rows = [{"Ref": c.get("claim_ref"),"Class": c.get("claim_class","").replace("_"," ").title(),
             "Status": c.get("status"),"Amount": f"KES {c.get('estimated_amount',0):,.0f}",
             "Created": str(c.get("created_at",""))[:10]} for c in all_rows]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown(f"**Total: {len(rows)} claims**")
