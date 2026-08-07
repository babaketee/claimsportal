"""Claims Officer Intake Panel — Agent-assisted FNOL and claim staging workspace.
=========================================================================================
Role: claims_officer, head_of_claims
Spaces: New Claims Queue | Claim Details | My Queue | Reports

Agent-assisted FNOL: verify policy, confirm incident details, stage the claim.
Triage: assign fast-track or standard route based on claim characteristics.
Conditional document checklist shown per claim type (Appendix C, p1-gap-9).
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core_api
import core_engine
from core_engine import ClaimStatus, get_engine
import config_db

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Claims Intake — Definite Assurance", page_icon="🛡️", layout="wide")


def _doc_checklist(claim_class: str) -> tuple[list, list]:
    """Return (mandatory_docs, conditional_docs) for a claim class. Reads from config."""
    cfg = config_db.get_config()
    prefix = claim_class.replace("_", "").lower()
    # Try exact claim_class mapping
    mandatory = cfg.get(f"claim.{claim_class}.documents.mandatory", [])
    conditional = cfg.get(f"claim.{claim_class}.documents.conditional", [])
    return mandatory, conditional


def _is_fast_track_eligible(estimated_amount: float) -> bool:
    """Check fast-track eligibility from config. Returns (eligible, reason)."""
    cfg = config_db.get_config()
    max_amount = cfg.get("claim.motor.fast_track.max_claim_amount", 100_000)
    if estimated_amount > max_amount:
        return False
    return True


def render(user_email: str, user_role: str = "claims_officer") -> None:
    st.title("Claims Intake Panel")
    st.caption(f"Logged in as {user_email} [{user_role}]")

    tab_new, tab_queue, tab_reports = st.tabs(["📥 New Claims", "📋 My Queue", "📊 Reports"])

    with tab_new:
        _render_new_claim_form(user_email)
    with tab_queue:
        _render_my_queue(user_email)
    with tab_reports:
        _render_reports()


def _render_new_claim_form(user_email: str) -> None:
    st.subheader("Stage a New Claim")

    claim_ref = st.text_input("Claim Reference *", placeholder="e.g. CLM/MOT/NRB/2026/000123")
    policy_ref = st.text_input("Policy Reference *", placeholder="POL-MOT-2026-001")

    policy_data = None
    if policy_ref and len(policy_ref) >= 4:
        with st.spinner("Verifying policy..."):
            policy_data = core_api.verify_policy(policy_ref)
        if policy_data:
            st.success(f"Policy found: **{policy_data.get('policy_ref')}** — {policy_data.get('product')}")
        else:
            st.warning("Policy not found.")

    id_number = st.text_input("Policyholder ID *", placeholder="National ID")
    vehicle_reg = st.text_input("Vehicle Registration", placeholder="KBZ 000A")

    incident_type = st.selectbox("Incident Type *", [
        "Road Accident", "Theft/Break-in", "Fire", "Flood", "Vandalism", "Windscreen", "Other"])
    incident_date = st.date_input("Date of Incident")
    description = st.text_area("Incident Description", height=100)

    estimated_amount = st.number_input("Estimated Claim Amount (KES)", min_value=0, step=10_000, format="%d")

    claim_class = st.selectbox("Claim Class *", ["motor", "motor_tp", "motor_tp_bi", "medical", "property", "travel"])

    # ─── Document Checklist (Appendix C — conditional display) ─────────────────
    mandatory_docs, conditional_docs = _doc_checklist(claim_class)
    if mandatory_docs:
        st.markdown("#### Document Checklist")
        st.info(f"**Mandatory documents for {claim_class.replace('_', ' ').upper()} claims:**")
        for doc in mandatory_docs:
            st.write(f"  ✅ `{doc}`")
        if conditional_docs:
            st.info(f"**Conditional documents (if applicable):**")
            for doc in conditional_docs:
                st.write(f"  🔶 `{doc}`")
    # ─── Fast-Track Check (Section 3.1 — R7) ──────────────────────────────
    eligible = _is_fast_track_eligible(estimated_amount)
    fast_track = st.checkbox(
        "🚀 Fast Track",
        value=False,
        disabled=not eligible,
        help="Eligible if estimated amount ≤ KES 100,000 and incident is straightforward. TAT target: 4 hours."
    )
    if not eligible:
        st.caption("⚠️ Fast track not available: claim exceeds the KES 100,000 threshold.")

    st.markdown("---")
    if st.button("Stage Claim", type="primary", use_container_width=True):
        if not all([claim_ref, policy_ref, id_number, incident_type]):
            st.error("Please fill all mandatory fields.")
            return
        engine = get_engine()
        try:
            claim = engine.create_claim(
                claim_ref=claim_ref,
                policy_ref=policy_ref,
                id_number=id_number,
                vehicle_reg=vehicle_reg or "N/A",
                incident_type=incident_type,
                description=description,
                claim_class=claim_class,
                user_id=user_email,
                fast_track=1 if fast_track else 0,
            )
            engine.transition_to(claim_ref, ClaimStatus.REPORTED, user_email)
            if fast_track:
                engine.transition_to(claim_ref, ClaimStatus.TRIAGE, user_email, triage_decision="fast_track", fast_track=1)
            else:
                engine.transition_to(claim_ref, ClaimStatus.TRIAGE, user_email)
            st.success(f"Claim {claim_ref} staged and moved to Triage.")
        except Exception as e:
            st.error(f"Error: {e}")


def _render_my_queue(user_email: str) -> None:
    st.subheader("My Queue")
    engine = get_engine()
    triage_claims = engine.get_claims_by_status(ClaimStatus.TRIAGE)
    if not triage_claims:
        st.info("No claims in your queue.")
        return
    rows = [{
        "Claim Ref": c.get("claim_ref"),
        "Policy": c.get("policy_ref"),
        "Class": c.get("claim_class"),
        "Status": c.get("status"),
        "Fast Track": "🚀" if c.get("fast_track") else "",
    } for c in triage_claims]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_reports() -> None:
    st.subheader("Intake Reports")
    st.info("Reports coming soon.")
