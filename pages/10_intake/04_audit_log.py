"""Audit Log — pages/10_intake/04_audit_log.py"""
"""
Role: claims_officer, head_of_claims
Searchable audit trail for all claims.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine
import streamlit as st
import pandas as pd

def render(user_email: str, user_role: str = "claims_officer") -> None:
    st.title("📜 Audit Log")
    search = st.text_input("Search by Claim Reference", placeholder="CLM-XXXXXXXX")
    engine = get_engine()
    rows = []
    for status in ["Reported","Triage","Investigation","Assessment","Approval","Approved",
                   "Pending Payment","Paid","Closed","Closed_Approved","Closed_Repudiated"]:
        try:
            for c in engine.get_claims_by_status(status):
                try:
                    for h in engine.audit.get_history("claim", c.get("claim_ref")):
                        rows.append(h)
                except: pass
        except: pass
    if search:
        rows = [r for r in rows if search.upper() in str(r.get("claim_ref","")).upper()]
    if not rows:
        st.info("No audit entries found.")
        return
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(f"Total entries: {len(rows)}")
