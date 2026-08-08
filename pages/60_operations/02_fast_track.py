"""Fast Track Sampling — pages/60_operations/02_fast_track.py"""
"""Role: head_of_claims, admin. Fast-track sampling display per Phase 2 spec R7."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine
import config_db
import streamlit as st
import pandas as pd
import random

def _fmt(amount): return f"KES {amount:,.0f}"
def render(user_email: str, user_role: str = "head_of_claims") -> None:
    st.title("🚀 Fast Track — Sampling Dashboard")
    cfg = config_db.get_config()
    sampling_rate = cfg.get("claim.motor.fast_track.sampling_rate", 0.05)
    max_amount = cfg.get("claim.motor.fast_track.max_claim_amount", 100000)
    sla_hours = cfg.get("claim.motor.fast_track.sla_hours", 4)
    col1, col2, col3 = st.columns(3)
    col1.metric("Sampling Rate", f"{sampling_rate*100:.1f}%")
    col2.metric("Max Claim Amount", f"KES {max_amount:,.0f}")
    col3.metric("SLA", f"{sla_hours}h")
    st.markdown("---—")
    engine = get_engine()
    fast_track_claims = []
    try:
        for s in ["Investigation","Assessment","Approval","Approved"]:
            for c in engine.get_claims_by_status(s):
                if c.get("fast_track"):
                    fast_track_claims.append(c)
    except: pass
    st.subheader(f"Fast Track Claims ({len(fast_track_claims)} active)" )
    if fast_track_claims:
        rows = [{"Ref": c.get("claim_ref"), "Status": c.get("status"), "Est.": c.get("estimated_amount", 0), "Class": c.get("claim_class")} for c in fast_track_claims]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        sampled = [c for c in fast_track_claims if random.random() < sampling_rate]
        if sampled:
            st.success(f"{len(sampled)} claim(s) selected for mandatory quality review.")
            for c in sampled:
                st.write(f"  • {c.get('claim_ref')} — {_fmt(c.get('estimated_amount', 0))}")
    else:
        st.info("No active fast-track claims.")
