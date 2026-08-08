"""Legal Review â pages/50_legal/01_legal_review.py"""
"""Role: legal. Legal review of claims with legal holds."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine
import streamlit as st
import pandas as pd
import json

def render(user_email: str, user_role: str = "legal") -> None:
    st.title("âï¸ Legal Review")
    engine = get_engine()
    st.subheader("Claims with Legal Holds")
    rows = []
    try:
        for s in ["Investigation","Assessment","Approval","Pending Payment"]:
            for c in engine.get_claims_by_status(s):
                extra = {}
                try: extra = json.loads(c.get("extra_data","{}"))
                except: pass
                if extra.get("legal_hold"):
                    rows.append({"Ref": c.get("claim_ref"), "Status": c.get("status"), "Legal Hold": extra.get("legal_hold_reason","Yes"), "Est.": c.get("estimated_amount", 0)})
    except: pass
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No legal holds active.")
    st.markdown("---â")
    ref = st.text_input("Search Claim", placeholder="CLM-XXXXXXXX")
    if ref:
        claim = engine.get_claim(ref)
        if claim:
            st.json(claim)
        else:
            st.warning("Not found.")
if __name__ == "__main__":
    render("test@insure.demo", "legal")
