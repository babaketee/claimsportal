"""Triage Action — pages/10_intake/03_triage_action.py"""
"""
Role: claims_officer, head_of_claims
Assign a claims officer and set route after triage.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine, ClaimStatus
import streamlit as st

def render(user_email: str, user_role: str = "claims_officer") -> None:
    st.title("⚡ Triage Action")
    ref = st.text_input("Claim Reference", placeholder="CLM-XXXXXXXX")
    if not ref:
        st.info("Enter claim reference.")
        return
    engine = get_engine()
    claim = engine.get_claim(ref)
    if not claim:
        st.warning("Claim not found."); return
    st.json(claim)
    st.markdown("---")
    triage_options = ["Investigator","Assessor","Legal Review","Decline"]
    triage_decision = st.selectbox("Triage Decision", triage_options)
    assigned_to = st.text_input("Assign To (email)", placeholder="assessor@insure.demo")
    if st.button("Confirm Triage", type="primary"):
        try:
            engine.transition_to(ref, ClaimStatus.INVESTIGATION, user_email, triage_decision=triage_decision, assigned_to=assigned_to)
            st.success(f"Claim {ref} triaged and assigned.")
        except Exception as e:
            st.error(f"Error: {e}")
