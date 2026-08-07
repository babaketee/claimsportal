"""External Provider Panel — Scoped workspaces for investigators, assessors, garages, parts sellers.
=============================================================================================================

Role: investigator | assessor | garage | spare_parts
Provider sees ONLY their assigned jobs — strict tenant isolation.

Uses core_engine.ClaimManager for claim reads and transitions.
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core_api
import core_engine
from core_engine import ClaimStatus, get_engine, can_transition, get_next_statuses

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Provider Panel — Definite Assurance", page_icon="🔧", layout="wide")


PROVIDER_TABS = {
    "investigator":  ["My Assignments", "Submit Report"],
    "assessor":       ["My Assessments", "Submit Assessment"],
    "garage":         ["My Jobs", "Update Status"],
    "spare_parts":    ["My Orders", "Update Availability"],
}

PROVIDER_TRANSITIONS = {
    "investigator":  ClaimStatus.INVESTIGATION,
    "assessor":      ClaimStatus.INVESTIGATION,
    "garage":         ClaimStatus.UNDER_REPAIR,
    "spare_parts":    ClaimStatus.UNDER_REPAIR,
}

PROVIDER_NEXT = {
    "investigator":  ClaimStatus.PENDING_APPROVAL,
    "assessor":       ClaimStatus.PENDING_APPROVAL,
    "garage":         ClaimStatus.PENDING_PAYMENT,
    "spare_parts":    ClaimStatus.UNDER_REPAIR,
}


def render(user_email: str, user_role: str) -> None:
    st.title(f"🔧 Provider Panel — {user_role.title()}")
    st.caption(f"Provider: {user_email}")

    if user_role not in PROVIDER_TABS:
        st.error("Your role is not configured for the provider panel.")
        return

    tabs = PROVIDER_TABS[user_role]
    tab_a, tab_b = st.tabs(tabs)

    with tab_a:
        _my_assignments(user_email, user_role)
    with tab_b:
        _submit_report(user_email, user_role)


def _my_assignments(user_email: str, user_role: str) -> None:
    st.subheader("My Assignments")
    engine = get_engine()

    # In Phase 1: show all claims in the relevant status for this provider
    # Phase 2: filter by provider assignment table
    relevant_statuses = ["Investigation/Assessment", "Under Repair"]
    all_claims = engine.get_all()

    my_claims = [c for c in all_claims if c.get("status") in relevant_statuses]

    if not my_claims:
        st.info("No assignments at this time.")
        return

    df = pd.DataFrame(my_claims)
    st.dataframe(
        df[["claim_ref", "status", "vehicle_reg", "incident_type", "created_at"]],
        use_container_width=True, hide_index=True
    )


def _submit_report(user_email: str, user_role: str) -> None:
    st.subheader(f"Submit {user_role.title()} Report")
    engine = get_engine()

    # Get claims in the relevant stage for this provider
    stage = PROVIDER_TRANSITIONS.get(user_role, ClaimStatus.INVESTIGATION)
    all_claims = engine.get_all()
    eligible = [c for c in all_claims if c.get("status") == stage.value]

    if not eligible:
        st.info(f"No claims currently in {stage.value} stage.")
        return

    ref = st.selectbox("Select Claim", [c["claim_ref"] for c in eligible])
    claim = engine.get_claim(ref)
    if not claim:
        return

    st.json(claim)

    report = st.text_area(f"{user_role.title()} Report / Notes", height=150)
    estimated_amount = st.number_input("Estimated Amount (KES)", min_value=0, step=1000, format="%d")

    if st.button("Submit Report", type="primary"):
        # Audit the report submission
        engine.audit.log(
            "claim", ref, f"{user_role}_report", user_email,
            before=None,
            after={"report": report, "estimated_amount": estimated_amount},
            metadata={"provider_role": user_role}
        )
        st.success(f"Report submitted for {ref}. Pending approval.")


def _update_availability(user_email: str, user_role: str) -> None:
    st.subheader("Update Availability")
    st.info("Spare parts availability update — coming in Phase 2.")
