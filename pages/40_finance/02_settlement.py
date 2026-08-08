"""Settlement Processing — pages/40_finance/02_settlement.py"""
"""Role: finance, cfo. Process payment instructions. Phase 2 spec R3."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine, ClaimStatus
import streamlit as st

def _fmt(amount): return f"KES {amount:,.0f}"
def render(user_email: str, user_role: str = "finance") -> None:
    st.title("💸 Settlement Processing")
    ref = st.text_input("Claim Reference", placeholder="CLM-XXXXXXXX")
    if not ref:
        st.info("Enter claim reference."); return
    engine = get_engine()
    claim = engine.get_claim(ref)
    if not claim:
        st.warning("Claim not found."); return
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", claim.get("status","N/A"))
    col2.metric("Est. Amount", _fmt(claim.get("estimated_amount", 0)))
    col3.metric("Discharge Voucher", "Signed" if claim.get("discharge_voucher_signed") else "Pending")
    st.markdown("---—")
    if claim.get("status") == "Pending Payment":
        if st.button("Mark as Paid", type="primary"):
            try:
                engine.transition_to(ref, ClaimStatus.PAID, user_email)
                st.success(f"Claim {ref} marked as Paid.")
            except Exception as e:
                st.error(f"Error: {e}")
    elif claim.get("status") == "Paid":
        st.success(f"Claim {ref} has been settled.")
    else:
        st.info(f"Claim is at status '{claim.get('status')}'. Move to Pending Payment first.")
