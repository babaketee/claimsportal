"""Settlement View — pages/20_provider/03_settlement_view.py
Role: assessor, investigator, garage, finance. Read-only settlement status.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core_engine import get_engine
import streamlit as st


def render(user_email: str, user_role: str = "assessor") -> None:
    st.title("💰 Settlement View")
    ref = st.text_input("Claim Reference", placeholder="CLM-XXXXXXXX")
    if not ref:
        st.info("Enter claim reference.")
        return
    engine = get_engine()
    claim = engine.get_claim(ref)
    if not claim:
        st.warning("Claim not found.")
        return
    st.json(claim)
    st.subheader("Settlement Status")
    status = claim.get("status", "")
    if status in ["Paid", "Closed", "Closed_Approved"]:
        st.success(f"Claim {ref} has been settled.")
    elif status in ["Pending Payment"]:
        st.info(f"Claim {ref} is pending payment.")
    else:
        st.info(f"Claim {ref} is at status: {status}. Settlement pending.")
