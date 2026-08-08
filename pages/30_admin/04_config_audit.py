"""Config Audit — pages/30_admin/04_config_audit.py"""
"""Role: admin, super_admin. Full config history."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config_db
import streamlit as st

def render(user_email: str, user_role: str = "admin") -> None:
    st.title("📜 Config Audit Log")
    cfg = config_db.get_config()
    key = st.text_input("Config Key", placeholder="claim.motor.fast_track.max_claim_amount")
    if not key:
        st.info("Enter a config key to view its history."); return
    history = cfg.history(key)
    if not history:
        st.warning(f"No history for {key}."); return
    import pandas as pd
    rows = [{"Version": h.get("version"),"When": h.get("changed_at","")[:19],"By": h.get("changed_by",""),"Type": h.get("change_type",""),"Value": str(h.get("value",""))[:60]} for h in history]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
