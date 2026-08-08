"""Claim Detail — pages/00_claimant/05_claim_detail.py"""
"""
Role: client
Read-only view of a single claim's full details and timeline.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine
import streamlit as st

def render(user_email: str, user_role: str = "client") -> None:
    st.title("📄 Claim Detail")
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
    st.subheader("Status Timeline")
    try:
        hist = engine.audit.get_history("claim", ref)
    except: hist = []
    for h in hist:
        st.write(f"**{str(h.get('timestamp',''))[:19]}** - {h.get('action','')} by {h.get('actor_id','')}")
