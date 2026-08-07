"""Claimant Portal — Self-service workspace for policyholders.
=======================================================================
Spaces: File a Claim (FNOL), Track My Claim, My Documents, My Profile

Claims portal SoR: uses core_engine.ClaimManager and core_api.
"""

from __future__ import annotations

import sys
import os
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core_api
import core_engine
from core_engine import ClaimStatus, get_engine

import streamlit as st
import pandas as pd

st.set_page_config(page_title="My Claims — Definite Assurance", page_icon="🛡️", layout="wide")


def _tat_display(tat_ms: int) -> str:
    """Format milliseconds into human-readable TAT string."""
    if tat_ms < 1000:
        return f"{tat_ms}ms"
    total_secs = tat_ms // 1000
    days, rem = divmod(total_secs, 86400)
    hrs, rem2 = divmod(rem, 3600)
    mins, secs = divmod(rem2, 60)
    parts = []
    if days: parts.append(f"{days}d")
    if hrs: parts.append(f"{hrs}h")
    if mins: parts.append(f"{mins}m")
    if secs and not days: parts.append(f"{secs}s")
    return " ".join(parts) if parts else "0s"


def render(user_email: str) -> None:
    st.title("🛡️ My Claims Portal")
    st.caption(f"Welcome, {user_email} — Definite Assurance Insurance")

    tab_fnol, tab_track, tab_docs, tab_profile = st.tabs([
        "📝 File a Claim", "🔍 Track My Claim", "📎 My Documents", "👤 My Profile"
    ])

    with tab_fnol:
        _fnol_form(user_email)
    with tab_track:
        _claim_tracker(user_email)
    with tab_docs:
        _my_documents(user_email)
    with tab_profile:
        _my_profile(user_email)


def _fnol_form(user_email: str) -> None:
    st.subheader("First Notification of Loss (FNOL)")
    st.info("Complete all sections. Fields marked * are mandatory.")

    # --- Policy Lookup ---
    st.markdown("#### 1. Policy Verification")
    c1, c2 = st.columns(2)
    id_type = c1.selectbox("ID Type *", ["National ID", "Passport", "Foreign Id"])
    id_number = c2.text_input("ID / Passport Number *", placeholder="e.g. 12345678")

    if id_number and len(id_number) >= 4:
        with st.spinner("Verifying policy..."):
            policy_data = core_api.verify_policy(id_number)
        if policy_data:
            st.success(f"Policy found: **{policy_data.get('policy_ref', 'N/A')}** — {policy_data.get('product', 'Motor')}")
        else:
            st.warning("No active policy found for this ID. Contact your agent or branch.")

    st.markdown("#### 2. Incident Details")
    c3, c4 = st.columns(2)
    incident_type = c3.selectbox("Incident Type *", [
        "Road Accident", "Theft/Break-in", "Fire", "Flood", "Landslide",
        "Broken Glass", "Third Party Damage", "Windscreen Damage", "Other"
    ])
    incident_date = c4.date_input("Date of Incident *")
    description = st.text_area("Description of Incident *", placeholder="Describe what happened...", height=100)

    st.markdown("#### 3. Vehicle / Item Details")
    c5, c6 = st.columns(2)
    vehicle_reg = c5.text_input("Vehicle Registration *", placeholder="e.g. KBZ 000A")
    estimated_loss = c6.number_input("Estimated Loss (KES) *", min_value=0, step=1000, format="%d")

    st.markdown("#### 4. Documents")
    uploaded = st.file_uploader(
        "Upload supporting documents (images, PDF)",
        type=["jpg", "jpeg", "png", "pdf", "webp"],
        accept_multiple_files=True
    )
    if uploaded:
        st.write(f"**{len(uploaded)} file(s) uploaded** — processing...")

    st.markdown("---")
    submitted = st.form_submit_button("Submit Claim", type="primary", use_container_width=True)
    if submitted:
        if not all([id_number, incident_type, str(incident_date), description, vehicle_reg]):
            st.error("Please fill all mandatory fields.")
            return
        claim_ref = f"CLM-{uuid.uuid4().hex[:8].upper()}"
        engine = get_engine()
        try:
            engine.create_claim(
                claim_ref=claim_ref,
                policy_ref=policy_data.get('policy_ref', 'UNKNOWN') if policy_data else 'UNKNOWN',
                id_number=id_number,
                vehicle_reg=vehicle_reg,
                incident_type=incident_type,
                description=description,
                claim_class="motor" if incident_type != "Business Interruption" else "business",
                user_id=user_email,
            )
            st.success(f"Claim submitted successfully! Your claim reference is **{claim_ref}**")
            st.balloons()
        except Exception as e:
            st.error(f"Failed to submit: {e}")


def _claim_tracker(user_email: str) -> None:
    st.subheader("Track My Claims")
    search_ref = st.text_input("Enter Claim Reference", placeholder="e.g. CLM-00000001")

    if search_ref:
        engine = get_engine()
        claim = engine.get_claim(search_ref)
        if not claim:
            st.warning("Claim not found. Check the reference and try again.")
            return

        col1, col2, col3 = st.columns(3)
        col1.metric("Status", claim.get("status", "Unknown"))
        col2.metric("Claim Class", claim.get("claim_class", "N/A").title())
        col3.metric("Policy", claim.get("policy_ref", "N/A"))

        st.markdown("---")
        st.markdown("#### Turnaround Time")
        breakdown = engine.clock.get_tat_breakdown(search_ref)
        if breakdown:
            rows = []
            for stage in breakdown:
                elapsed = stage.get("elapsed_ms")
                rows.append({
                    "Stage": stage["stage"],
                    "Entered": stage.get("entered_at", ""),
                    "Exited": stage.get("exited_at", "Running..."),
                    "Elapsed": _tat_display(elapsed) if elapsed else "In progress",
                    "Parallel": "✓" if stage.get("parallel") else "",
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No TAT data available yet.")

        st.markdown("#### Audit Trail")
        history = engine.audit.get_history("claim", search_ref)
        if history:
            audit_rows = []
            for h in history:
                import json
                before = json.loads(h.before) if h.before else None
                after = json.loads(h.after) if h.after else None
                audit_rows.append({
                    "When": h.timestamp[:19],
                    "Action": h.action,
                    "User": h.user_id,
                    "Before": str(before) if before else "—",
                    "After": str(after) if after else "—",
                })
            st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No audit entries yet.")
    else:
        st.info("Enter your claim reference above to track progress.")


def _my_documents(user_email: str) -> None:
    st.subheader("My Documents")
    st.info("Documents uploaded during FNOL will appear here once processed.")
    st.markdown("*Document management coming soon — uploads from FNOL form are queued for processing.*")


def _my_profile(user_email: str) -> None:
    st.subheader("My Profile")
    user = core_api.get_user(user_email) if hasattr(core_api, 'get_user') else None
    if user:
        st.json(user)
    else:
        st.write(f"**Email:** {user_email}")
        st.write("Profile management coming soon.")
