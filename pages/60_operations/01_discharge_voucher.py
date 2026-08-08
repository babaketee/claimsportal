"""Discharge Voucher â pages/60_operations/01_discharge_voucher.py"""
"""Role: finance, claims_officer. Sign and manage discharge vouchers. Phase 2 spec R5."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine
import streamlit as st

def _fmt(amount): return f"KES {amount:,.0f}"
def render(user_email: str, user_role: str = "finance") -> None:
    st.title("ð Discharge Voucher")
    ref = st.text_input("Claim Reference", placeholder="CLM-XXXXXXXX")
    if not ref:
        st.info("Enter claim reference."); return
    engine = get_engine()
    claim = engine.get_claim(ref)
    if not claim:
        st.warning("Claim not found."); return
    status = claim.get("status","")
    dv_signed = bool(claim.get("discharge_voucher_signed"))
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", status)
    col2.metric("Est. Amount", _fmt(claim.get("estimated_amount", 0)))
    col3.metric("DV Signed", "Yes" if dv_signed else "No")
    st.markdown("---â")
    st.subheader("Discharge Voucher Details")
    st.write(f"**Claimant:** {claim.get('claimant_email','N/A')}")
    st.write(f"**Claim Ref:** {ref}")
    st.write(f"**Settlement Amount:** {_fmt(claim.get('estimated_amount', 0))}")
    st.write(f"**DV Status:** {"SIGNED" if dv_signed else "PENDING"}")
    if dv_signed:
        st.success("Discharge voucher has been signed.")
        st.write(f"**Signed Date:** {str(claim.get('discharge_voucher_date',''))[:19]}")
    else:
        if status in ["Approved","Pending Payment"]:
            st.warning("This claim is awaiting discharge voucher signature.")
            if st.button("Sign Discharge Voucher", type="primary"):
                try:
                    engine.sign_discharge_voucher(ref, user_email)
                    st.success(f"Discharge voucher signed for {ref}.")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.info(f"Claim must be at Approved or Pending Payment status. Currently: {status}.")
if __name__ == "__main__":
    render("test@insure.demo", "finance")
