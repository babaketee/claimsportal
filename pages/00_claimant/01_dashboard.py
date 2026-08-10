"""
Claimant Dashboard - pages/00_claimant/01_dashboard.py
Role: client
Landing page: show all claims for logged-in user, status badges, TAT timers.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine
import streamlit as st
import pandas as pd
from datetime import datetime

def _tat_ms(elapsed_ms: int) -> str:
    d, r = divmod(int(elapsed_ms), 86400000)
    h, r2 = divmod(r, 3600000)
    m, s = divmod(r2, 60000)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    return " ".join(parts) if parts else "0m"

def render(user_email: str = None, user_role: str = "client") -> None:
    st.title("My Claims Dashboard")
    # Ensure we have the logged-in user's email even if the navigation system
    # didn't pass arguments — read from session_state as a fallback.
    import streamlit as _st
    if not user_email:
        user_email = _st.session_state.get("user_email", "")
    # If email still empty, try mapping the logged-in display name to a demo email
    if not user_email:
        try:
            import lib.auth as _auth
            display_name = _st.session_state.get("user_name", "")
            for e, info in _auth.DEMO_USERS.items():
                if info.get("name") == display_name:
                    user_email = e
                    break
        except Exception:
            pass
    engine = get_engine()
    all_claims = []
    for status in ["Draft","Reported","Triage","Investigation","Assessment","Approval",
                   "Approved","Pending Payment","Paid","Closed","Closed_Approved",
                   "Closed_Repudiated","Total_Loss_Settlement","Closed_Total_Loss"]:
        try:
            for c in engine.get_claims_by_status(status):
                if c.get("user_id") == user_email or c.get("claimant_email") == user_email:
                    all_claims.append(c)
        except: pass
    open_ = [c for c in all_claims if c.get("status") not in ["Closed","Closed_Approved","Closed_Repudiated","Closed_Total_Loss"]]
    m = {"motor":0,"medical":0}
    m["motor"] = len([c for c in open_ if c.get("claim_class")=="motor"])
    m["medical"] = len([c for c in open_ if c.get("claim_class")=="medical"])
    col1, col2, col3 = st.columns(3)
    col1.metric("Open Claims", len(open_))
    col2.metric("Motor", m["motor"])
    col3.metric("Medical", m["medical"])
    st.markdown("---")
    if not all_claims:
        st.info("No claims found.")
        return
    rows = []
    for c in sorted(all_claims, key=lambda x: x.get("created_at",""), reverse=True):
        rows.append({
            "Claim Ref": c.get("claim_ref",""),
            "Class": c.get("claim_class","").replace("_"," ").title(),
            "Status": c.get("status",""),
            "Created": str(c.get("created_at",""))[:10],
            "Amount": f"KES {c.get('estimated_amount',0):,.0f}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    render("test@insure.demo", "client")
