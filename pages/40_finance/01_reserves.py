"""Reserves Management â pages/40_finance/01_reserves.py"""
"""Role: finance, cfo. View and manage claim reserves. Phase 2 spec R3."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine, ClaimStatus
import config_db
import streamlit as st
import pandas as pd

def _fmt(amount): return f"KES {amount:,.0f}"
def render(user_email: str, user_role: str = "finance") -> None:
    st.title("ð¦ Reserve Management")
    ref = st.text_input("Claim Reference", placeholder="CLM-XXXXXXXX")
    if not ref:
        st.info("Enter claim reference."); return
    engine = get_engine()
    claim = engine.get_claim(ref)
    if not claim:
        st.warning("Claim not found."); return
    est = claim.get("estimated_amount", 0)
    reserve = config_db.get_config().get("claim.reserve.default_amount", est * 0.8)
    st.metric("Estimated Loss", _fmt(est))
    st.metric("Reserve Held", _fmt(reserve))
    st.metric("Reserve Remaining", _fmt(max(0, reserve - est)))
    st.markdown("---â")
    st.subheader("Reserve Movements")
    rows = []
    try:
        db = engine.db
        cur = db.cursor()
        cur.execute("SELECT id, movement_type, amount, created_at FROM reserve_movements WHERE claim_ref=? ORDER BY created_at DESC", (ref,))
        for r in cur.fetchall():
            rows.append({"ID": r[0], "Type": r[1], "Amount": _fmt(r[2]), "Date": str(r[3])[:19]})
    except: pass
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No reserve movements recorded.")
    col1, col2 = st.columns(2)
    mov_type = col1.selectbox("Movement Type", ["initial_reserve","top_up","reduction","release"])
    amount = col2.number_input("Amount (KES)", min_value=0, step=10000, format="%d")
    if st.button("Record Movement", type="primary"):
        try:
            engine.record_reserve_movement(ref, mov_type, amount, user_email)
            st.success("Reserve movement recorded.")
        except Exception as e:
            st.error(f"Error: {e}")
if __name__ == "__main__":
    render("test@insure.demo", "finance")
