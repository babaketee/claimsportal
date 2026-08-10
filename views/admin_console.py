"""Administration Console — simplified for local testing.
Provides a minimal admin view so the Streamlit app can start.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
from core_engine import get_engine


def render(user_email: str, user_role: str) -> None:
    st.title("Admin Console (Minimal)")
    st.caption(f"Admin: {user_email} | Role: {user_role}")
    st.subheader("Audit Log (recent)")
    engine = get_engine()
    try:
        entries = engine.audit.get_history('claim') if hasattr(engine, 'audit') else []
    except Exception:
        entries = []
    if not entries:
        st.info("No audit entries available.")
        return
    rows = []
    for e in entries:
        rows.append({
            'When': getattr(e, 'created_at', '')[:19],
            'Entity': getattr(e, 'entity', ''),
            'Ref': getattr(e, 'ref', ''),
            'Action': getattr(e, 'action', ''),
            'Actor': getattr(e, 'actor_id', ''),
        })
    import pandas as pd
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
