"""Claim Review — pages/10_intake/02_claim_review.py"""
"""
Role: claims_officer, head_of_claims
Review a claim and move it through triage/investigation/assessment stages.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine, ClaimStatus
import streamlit as st

def render(user_email: str, user_role: str = "claims_officer") -> None:
    st.title("🔎 Claim Review")
    ref = st.text_input("Claim Reference", placeholder="CLM-XXXXXXXX")
    if not ref:
        st.info("Enter claim reference to review.")
        return
    engine = get_engine()
    claim = engine.get_claim(ref)
    if not claim:
        st.warning("Claim not found."); return
    st.json(claim)
    st.markdown("---")
    st.subheader("Take Action")
    current = claim.get("status","")
    col1, col2 = st.columns(2)
    notes = col1.text_area("Notes", placeholder="Decision notes...")
    findings = col2.text_area("Findings", placeholder="Key findings...")
    next_status = st.selectbox("Move to", [s for s in ClaimStatus.STATUSES if s != current])
    if st.button("Transition Claim", type="primary"):
        try:
            result = engine.transition_to(ref, next_status, user_email, notes=notes, findings=findings)
            st.success(f"Moved {ref} -> {next_status}")
        except Exception as e:
            st.error(f"Error: {e}")
