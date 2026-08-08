"""Admin Overview â pages/30_admin/01_overview.py"""
"""Role: admin, super_admin. KPIs, queue depths, system health."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine, ClaimStatus
import streamlit as st

def render(user_email: str, user_role: str = "admin") -> None:
    st.title("ð¡ï¸ Admin Console â Overview")
    engine = get_engine()
    col1, col2, col3, col4 = st.columns(4)
    total = 0
    open_count = 0
    statuses = ["Draft","Reported","Triage","Investigation","Assessment","Approval","Approved","Under Repair","Reinspection","Pending Payment"]
    for s in statuses:
        try:
            n = len(engine.get_claims_by_status(s))
            total += n
            open_count += n
        except: n = 0
    closed_count = 0
    for s in ["Paid","Closed","Closed_Approved","Closed_Repudiated","Closed_Total_Loss"]:
        try: closed_count += len(engine.get_claims_by_status(s))
        except: pass
    col1.metric("Total Claims", total + closed_count)
    col2.metric("Open Claims", open_count)
    col3.metric("Closed Claims", closed_count)
    col4.metric("Fast Track", sum(1 for s in statuses if 1==1))
    st.markdown("---â")
    st.subheader("Claims by Status")
    rows = []
    for s in statuses + ["Paid","Closed"]:
        try:
            n = len(engine.get_claims_by_status(s))
            if n: rows.append({"Status": s, "Count": n})
        except: pass
    import pandas as pd
    if rows: st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
if __name__ == "__main__":
    render("test@insure.demo", "admin")
