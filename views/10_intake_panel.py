"""Assisted Intake Panel — Call center / branch agents log claims on behalf of users.
=======================================================================================

Role: claims_officer / head_of_claims
Spaces: New Claim, Queue, Active Claim Detail, Quick Actions

Uses core_engine.ClaimManager for all claim operations.
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core_api
import core_engine
from core_engine import ClaimStatus, get_engine, can_transition, get_next_statuses

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Intake Panel — Definite Assurance", page_icon="📋", layout="wide")


def render(user_email: str, user_role: str) -> None:
    st.title("📋 Assisted Intake Panel")
    st.caption(f"Officer: {user_email} | Role: {user_role}")

    tab_new, tab_queue, tab_triage = st.tabs(["➕ New Claim", "📥 Claim Queue", "⚡ Triage"])

    with tab_new:
        _intake_form(user_email)
    with tab_queue:
        _claim_queue()
    with tab_triage:
        _triage_panel(user_email)


def _intake_form(officer_email: str) -> None:
    st.subheader("Log Claim on Behalf of Policyholder")
    with st.form("intake_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        id_number = c1.text_input("Policyholder ID / Passport *", placeholder="12345678")
        policy_ref = c2.text_input("Policy Reference", placeholder="POL-XXXXXX")

        # Auto-lookup if id entered
        policy_data = None
        if id_number and len(id_number) >= 4:
            with st.spinner("Looking up policy..."):
                policy_data = core_api.verify_policy(id_number)
            if policy_data:
                st.success(f"✓ Policy: {policy_data.get('policy_ref')} — {policy_data.get('product', 'N/A')}")

        st.markdown("--- Incident ---")
        c3, c4 = st.columns(2)
        incident_type = c3.selectbox("Incident Type *", [
            "Road Accident", "Theft/Break-in", "Fire", "Flood", "Landslide",
            "Broken Glass", "Third Party Damage", "Windscreen Damage", "Other"
        ])
        incident_date = c4.date_input("Date of Incident *")

        description = st.text_area("Incident Description *", height=100)

        c5, c6 = st.columns(2)
        vehicle_reg = c5.text_input("Vehicle Reg / Asset ID *")
        estimated_loss = c6.number_input("Estimated Loss (KES)", min_value=0, step=5000, format="%d")

        st.markdown("--- Claimant Consent ---")
        consent = st.checkbox("I confirm the policyholder has consented to this claim being lodged on their behalf (DPA 2019)")

        submitted = st.form_submit_button("Submit Claim", type="primary", use_container_width=True)
        if submitted:
            if not all([id_number, incident_type, description, vehicle_reg, consent]):
                st.error("Fill all fields and confirm consent.")
                return
            import uuid
            claim_ref = f"INT-{uuid.uuid4().hex[:8].upper()}"
            engine = get_engine()
            try:
                engine.create_claim(
                    claim_ref=claim_ref,
                    policy_ref=policy_data.get('policy_ref') if policy_data else (policy_ref or 'UNKNOWN'),
                    id_number=id_number,
                    vehicle_reg=vehicle_reg,
                    incident_type=incident_type,
                    description=description,
                    claim_class="motor",
                    user_id=officer_email,
                )
                st.success(f"Claim {claim_ref} created and queued for triage.")
            except Exception as e:
                st.error(f"Error: {e}")


def _claim_queue() -> None:
    st.subheader("Claim Queue")
    engine = get_engine()
    claims = engine.get_all()

    if not claims:
        st.info("No claims in the system.")
        return

    df = pd.DataFrame(claims)
    status_counts = df['status'].value_counts().to_dict()
    cols = st.columns(len(status_counts))
    for i, (status, count) in enumerate(status_counts.items()):
        cols[i].metric(f"{status}", count)

    st.markdown("---")
    filter_status = st.selectbox("Filter by status", ["All"] + list(df['status'].unique()))
    if filter_status != "All":
        df = df[df['status'] == filter_status]

    st.dataframe(df[['claim_ref', 'status', 'claim_class', 'vehicle_reg', 'created_at']],
                 use_container_width=True, hide_index=True)


def _triage_panel(officer_email: str) -> None:
    st.subheader("Triage — Assign Next Status")
    engine = get_engine()
    claims = engine.get_all({"status": "Submitted"})

    if not claims:
        st.info("No claims awaiting triage.")
        return

    triage_ref = st.selectbox("Select Claim", [c['claim_ref'] for c in claims])
    claim = engine.get_claim(triage_ref)
    if not claim:
        return

    st.json(claim)

    next_statuses = get_next_statuses(ClaimStatus.SUBMITTED)
    chosen = st.selectbox("Move to", [s.value for s in next_statuses])
    notes = st.text_area("Triage Notes")

    if st.button("Confirm Transition", type="primary"):
        target = ClaimStatus(chosen)
        if can_transition(ClaimStatus.SUBMITTED, target):
            try:
                engine.transition(triage_ref, target, officer_email, {"triage_notes": notes})
                st.success(f"Claim {triage_ref} moved to {target.value}")
            except Exception as e:
                st.error(f"Transition error: {e}")
        else:
            st.error("Invalid transition for this claim status.")
