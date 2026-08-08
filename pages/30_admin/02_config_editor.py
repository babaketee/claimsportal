"""Config Editor — pages/30_admin/02_config_editor.py"""
"""Role: admin, super_admin, head_of_claims. Maker-Checker config management."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config_db
import streamlit as st

def render(user_email: str, user_role: str = "admin") -> None:
    st.title("⚙️ Config Editor")
    cfg = config_db.get_config()
    tab1, tab2 = st.tabs(["Current Config", "Pending Changes"])
    with tab1:
        keys = cfg.all_keys()
        st.write(f"**{len(keys)} config keys**")
        import pandas as pd
        rows = [{"Key": k, "Value": str(cfg.get(k,""))[:80]} for k in sorted(keys)]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with tab2:
        pending = cfg.get_pending_approvals()
        if not pending:
            st.info("No pending config changes.")
        else:
            for p in pending:
                st.write(f"**{p["key"]}** — proposed by {p["proposed_by"]}")
                st.write(f"Value: {str(p["proposed_value"])}[:100]")
                col1, col2 = st.columns(2)
                if col1.button(f"Approve", key=f"approve_{p["approval_id"]}"):
                    result = cfg.approve(p["approval_id"], user_email)
                    st.success(result)
                if col2.button(f"Reject", key=f"reject_{p["approval_id"]}"):
                    result = cfg.reject(p["approval_id"], user_email)
                    st.info(result)
                st.markdown("---—")
