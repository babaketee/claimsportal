"""Administration Console â€” Hard segregation of duties.
=======================================================================
Role: admin | super_admin
Tabs: Config Manager (Maker-Checker) | Audit Log | User Management | System Health

admin: can propose config changes (Maker)
super_admin: can approve/reject changes AND has all admin powers (Checker)
"""

from __future__ import annotations

import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core_api
import core_engine
from core_engine import get_engine
import config_db
from config_db import get_config_db

import streamlit as st
import pandas as pd
from datetime import datetime, timezone

st.set_page_config(page_title="Admin Console â€” Definite Assurance", page_icon="âš™ï¸", layout="wide")


def render(user_email: str, user_role: str) -> None:
    st.title("âš™ï¸ Admin Console")
    st.caption(f"Admin: {user_email} | Role: {user_role}")

    is_super = (user_role == "super_admin")

    tabs = ["ðŸ”§ Config Manager", "ðŸ“‹ Audit Log"]
    if is_super:
        tabs += ["ðŸ‘¥ User Management", "ðŸ“Š System Health"]

    selected = st.sidebar.radio("Section", tabs)

    if selected == "ðŸ”§ Config Manager":
        _config_manager(user_email, is_super)
    elif selected == "ðŸ“‹ Audit Log":
        _audit_log()
    elif selected == "ðŸ‘¥ User Management" and is_super:
        _user_management()
    elif selected == "ðŸ“Š System Health" and is_super:
        _system_health()


def _config_manager(user_email: str, is_super: bool) -> None:
    st.subheader("ðŸ”§ Configuration Manager â€” Maker-Checker")

    cfg = get_config_db()

    tab_propose, tab_pending, tab_history = st.tabs(["ðŸ“ Propose Change", "â³ Pending Approval", "ðŸ“œ History"])

    with tab_propose:
        st.markdown("**Propose a Config Change** *(Maker)*")
        all_keys = cfg.get_all_keys()
        if not all_keys:
            st.info("No config keys found.")
        else:
            key = st.selectbox("Config Key", all_keys)
            current = cfg.get(key)
            st.write(f"**Current Value:** `{current}`")

            import json
            proposed_raw = st.text_area("Proposed Value (JSON)", value=json.dumps(current, indent=2), height=150)
            reason = st.text_input("Reason for change")
            effective = st.date_input("Effective From", value=datetime.today())

            if st.button("Submit Proposal", type="primary"):
                try:
                    proposed = json.loads(proposed_raw)
                    cr = cfg.propose_change(
                        key=key,
                        proposed_value=proposed,
                        reason=reason,
                        proposed_by=user_email,
                        effective_from=str(effective),
                    )
                    st.success(f"Change request **{cr.crid}** submitted. Awaiting Super-Admin approval.")
                except Exception as e:
                    st.error(f"Error: {e}")

    with tab_pending:
        st.markdown("**Pending Change Requests** *(Checker â€” Super-Admin only)*")
        pending = cfg.get_pending_changes()
        if not pending:
            st.info("No pending change requests.")
        else:
            for cr in pending:
                with st.expander(f"**{cr.crid}** â€” {cr.key}"):
                    st.write(f"**Proposed by:** {cr.proposed_by}")
                    st.write(f"**Proposed at:** {cr.proposed_at[:19]}")
                    st.write(f"**Reason:** {cr.reason}")
                    st.write(f"**Proposed Value:** `{cr.proposed_value}`")

                    if is_super:
                        c1, c2 = st.columns(2)
                        notes = st.text_input("Review notes")
                        if c1.button("âœ… Approve", key=f"apr-{cr.crid}"):
                            try:
                                cfg.approve_change(cr.crid, user_email, notes)
                                st.success(f"{cr.crid} approved.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                        if c2.button("âŒ Reject", key=f"rej-{cr.crid}"):
                            if not notes:
                                st.warning("Please add review notes before rejecting.")
                            else:
                                cfg.reject_change(cr.crid, user_email, notes)
                                st.info(f"{cr.crid} rejected.")
                                st.rerun()

    with tab_history:
        st.markdown("**Change Request History**")
        history = cfg.get_change_history()
        if not history:
            st.info("No change history.")
        else:
            rows = [{
                "CRID": h.crid,
                "Key": h.key,
                "Status": h.status,
                "Proposed By": h.proposed_by,
                "Proposed At": h.proposed_at[:19],
                "Reviewed By": h.reviewed_by or "â€”",
                "Reviewed At": h.reviewed_at[:19] if h.reviewed_at else "â€”",
            } for h in history]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _audit_log() -> None:
    st.subheader("ðŸ“‹ Immutable Audit Log")
    engine = get_engine()

    search_type = st.selectbox("Entity Type", ["claim", "config", "user"])
    search_ref = st.text_input("Entity Reference (optional)", placeholder="e.g. CLM-00000001")

    if st.button("Search"):
        if search_ref:
            entries = engine.audit.get_history(search_type, search_ref)
        else:
            