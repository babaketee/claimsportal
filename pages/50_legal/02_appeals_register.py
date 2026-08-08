"""Appeals Register — pages/50_legal/02_appeals_register.py"""
"""Role: legal. Appeals register per Phase 2 spec R6."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine
import streamlit as st
import pandas as pd

def render(user_email: str, user_role: str = "legal") -> None:
    st.title("📋 Appeals Register")
    engine = get_engine()
    st.info("Track repudiated claims and appeal outcomes.")
    ref = st.text_input("Claim Reference", placeholder="CLM-XXXXXXXX")
    if ref:
        claim = engine.get_claim(ref)
        if not claim:
            st.warning("Claim not found."); return
        col1, col2 = st.columns(2)
        col1.metric("Status", claim.get("status","N/A"))
        col2.metric("Appeal Filed", "Yes" if claim.get("appeal_filed") else "No")
        if claim.get("appeal_ref"):
            st.write(f"Appeal Ref: **{claim.get('appeal_ref')}**")
        st.markdown("---—")
        if claim.get("status") == "Closed_Repudiated" and not claim.get("appeal_filed"):
            appeal_ref = st.text_input("Appeal Reference", placeholder="APP-XXXXXXXX")
            if st.button("File Appeal", type="primary"):
                try:
                    engine.file_appeal(ref, appeal_ref, user_email)
                    st.success(f"Appeal filed for {ref}.")
                except Exception as e:
                    st.error(f"Error: {e}")
        elif claim.get("appeal_filed"):
            st.success("Appeal already filed.")
        else:
            st.info("Only repudiated claims can be appealed.")
    st.subheader("Recent Appeals")
    rows = []
    try:
        for c in engine.get_claims_by_status("Closed_Repudiated"):
            if c.get("appeal_filed"):
                rows.append({"Ref": c.get("claim_ref"), "Appeal Ref": c.get("appeal_ref","N/A"), "Est.": c.get("estimated_amount", 0)})
    except: pass
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No appeals filed yet.")
