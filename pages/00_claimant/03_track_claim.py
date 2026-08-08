"""Track My Claim — pages/00_claimant/03_track_claim.py"""
"""
Role: client
Search by claim reference and view status, TAT breakdown, audit trail.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine
import streamlit as st
import pandas as pd

def render(user_email: str, user_role: str = "client") -> None:
    st.title("🔍 Track My Claim")
    search_ref = st.text_input("Enter Claim Reference", placeholder="CLM-XXXXXXXX")
    if not search_ref:
        st.info("Enter your claim reference above.")
        return
    engine = get_engine()
    claim = engine.get_claim(search_ref)
    if not claim:
        st.warning("Claim not found.")
        return
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", claim.get("status","Unknown"))
    col2.metric("Class", claim.get("claim_class","N/A").replace("_"," ").title())
    col3.metric("Policy", claim.get("policy_ref","N/A"))
    st.markdown("---")
    st.subheader("Audit Trail")
    try:
        history = engine.audit.get_history("claim", search_ref)
    except:
        history = []
    if history:
        rows = [{"When": str(h.get("timestamp",""))[:19], "Action": h.get("action",""), "User": h.get("actor_id","")} for h in history]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No audit entries yet.")
