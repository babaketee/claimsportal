"""Submit Report — pages/20_provider/02_submit_report.py"""
"""
Role: assessor, investigator
Submit assessment or investigation report for an assigned claim.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine
import streamlit as st

def render(user_email: str, user_role: str = "assessor") -> None:
    st.title("📝 Submit Report")
    ref = st.text_input("Claim Reference", placeholder="CLM-XXXXXXXX")
    if not ref:
        st.info("Enter claim reference.")
        return
    engine = get_engine()
    claim = engine.get_claim(ref)
    if not claim:
        st.warning("Claim not found."); return
    if claim.get("assigned_to") != user_email:
        st.warning("This claim is not assigned to you.")
        return
    st.json(claim)
    st.markdown("---")
    findings = st.text_area("Findings / Assessment Report", height=150)
    recommended = st.number_input("Recommended Amount (KES)", min_value=0, step=10000, format="%d")
    if st.button("Submit Report", type="primary"):
        try:
            engine.transition_to(ref, "Assessment", user_email, findings=findings, recommended_amount=float(recommended))
            st.success(f"Report submitted for {ref}.")
        except Exception as e:
            st.error(f"Error: {e}")
