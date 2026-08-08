"""API Status — pages/30_admin/05_api_status.py"""
"""Role: admin, super_admin. Show API queue depth and dead-letter status."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import streamlit as st

def render(user_email: str, user_role: str = "admin") -> None:
    st.title("📡 API Status")
    st.info("API queue and dead-letter view — Phase 2 integration.")
    st.markdown("Exchange endpoints (Phase 2 — configure in config_db):")
    import config_db
    cfg = config_db.get_config()
    exchanges = [
        (1, "Policy Lookup", cfg.get("exchange.1.policy_lookup.url","")),
        (2, "Claim Notification", cfg.get("exchange.2.claim_notification.url","")),
        (3, "Triage Push", cfg.get("exchange.3.triage_push.url","")),
        (4, "Reports Push", cfg.get("exchange.4.reports_push.url","")),
        (5, "Decision Push", cfg.get("exchange.5.decision_push.url","")),
        (6, "Settlement Push", cfg.get("exchange.6.settlement_push.url","")),
    ]
    for idx, name, url in exchanges:
        st.write(f"**Exchange {idx}: {name}**")
        st.code(url if url else "Not configured", language="")
