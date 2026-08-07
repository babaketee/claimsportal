"""Claimant Portal — Self-service workspace for policyholders and third-party claimants.
==================================================================================================
Spaces: Own Damage (FNOL) | Third-Party Claim | Track My Claim | My Documents | My Profile

Third-party claimants have no policy with Definite Assurance — they enter via the 
insured vehicle's registration number (guest lookup). TP claims route through the 
same workflow but are flagged as third-party and do not include garage/repair stages 
for bodily injury claims.

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
    if tat_ms < 1000:
        return f"{tat_ms}ms"
    total_secs = tat_ms // 1000
    days, rem = divmod(total_secs, 86400)
    hrs, rem2 = divmod(rem, 3600)
    mins, secs = divmod(rem2, 60)
    parts = []
    if days: parts.append(f"{days}d")
    if hrs:  parts.append(f"{hrs}h")
    if mins: parts.append(f"{mins}m")
    if secs and not days: parts.append(f"{secs}s")
    return " ".join(parts) if parts else "0s"


def render(user_email: str) -> None:
    st.title("🛡️ My Claims Portal")
    st.caption(f"Welcome — Definite Assurance Insurance")

    tab_fnol, tab_tp, tab_track, tab_docs, tab_profile = st.tabs([
        "📝 Own Damage Claim",
        "🚗 Third-Party Claim",
        "🔍 Track My Claim",
        "📎 My Documents",
        "👤 My Profile",
    ])

    with tab_fnol:
        _fnol_form(user_email)
    with tab_tp:
        _tp_claim_form(user_email)
    with tab_track:
        _claim_tracker(user_email)
    with tab_docs:
        _my_documents(user_email)
    with tab_profile:
        _my_profile(user_email)


# ─── Own Damage FNOL ──────────────────────────────────────────────────────────

def _fnol_form(user_email: str) -> None:
    st.subheader("First Notification of Loss (FNOL)")
    st.info("Complete all sections. Fields marked * are mandatory.")

    st.markdown("#### 1. Policy Verification")
    c1, c2 = st.columns(2)
    id_type   = c1.selectbox("ID Type *", ["National Id", "Passport", "Foreign Id"])
    id_number = c2.text_input("ID / Passport Number *", placeholder="e.g. 12345678")

    policy_data = None
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
    description   = st.text_area("Description of Incident *", placeholder="Describe what happened...", height=100)

    st.markdown("#### 3. Vehicle / Item Details")
    c5, c6 = st.columns(2)
    vehicle_reg     = c5.text_input("Vehicle Registration *", placeholder="KBZ 000A")
    estimated_loss = c6.number_input("Estimated Loss (KES) *", min_value=0, step=1000, format="%d")

    st.markdown("#### 4. Documents")
    uploaded = st.file_uploader(
        "Upload supporting documents",
        type=["jpg", "jpeg", "png", "pdf", "webp"],
        accept_multiple_files=True
    )
    if uploaded:
        st.write(f"**{len(uploaded)} file(s) uploaded**")

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
                policy_ref=policy_data.get('policy_ref') if policy_data else 'UNKNOWN',
                id_number=id_number,
                vehicle_reg=vehicle_reg,
                incident_type=incident_type,
                description=description,
                claim_class="motor",
                user_id=user_email,
            )
            st.success(f"Claim submitted! Reference: **{claim_ref}**")
            st.balloons()
        except Exception as e:
            st.error(f"Failed: {e}")


# ─── Third-Party Claim Form (R1) ───────────────────────────────────────────────

def _tp_claim_form(user_email: str) -> None:
    st.subheader("Third-Party Claim — Guest Intake")
    st.markdown("""
    **You are a third party** if you were involved in an accident caused by a vehicle 
    insured with Definite Assurance. Enter the **at-fault vehicle's registration number** 
    below to verify coverage and lodge your claim.
    """)

    # Step 1: Guest lookup by vehicle registration
    st.markdown("#### Step 1 — Verify the At-Fault Vehicle")
    tp_vehicle_reg = st.text_input(
        "At-Fault Vehicle Registration *",
        placeholder="e.g. KBZ 000A",
        key="tp_vehicle_reg"
    )

    insured_info = None
    if tp_vehicle_reg and len(tp_vehicle_reg) >= 3:
        with st.spinner("Checking vehicle coverage..."):
            insured_info = core_api.verify_vehicle_reg(tp_vehicle_reg) if hasattr(core_api, 'verify_vehicle_reg') else None
        if not insured_info:
            # Fallback: try policy lookup by reg as identity
            insured_info = core_api.verify_policy(tp_vehicle_reg) if hasattr(core_api, 'verify_policy') else None

        if insured_info:
            st.success(
                f"✓ Vehicle **{tp_vehicle_reg}** is insured with Definite Assurance "
                f"(Policy: **{insured_info.get('policy_ref', 'N/A')}** — {insured_info.get('product', 'Motor')})"
            )
        else:
            st.error(
                f"✗ Vehicle **{tp_vehicle_reg}** is not insured with Definite Assurance. "
                f"You may only claim against a policy held at this company."
            )
            st.stop()

    # Step 2: Third-party claimant details
    st.markdown("#### Step 2 — Your Details")
    c1, c2 = st.columns(2)
    tp_id_type   = c1.selectbox("Your ID Type *", ["National Id", "Passport", "Foreign Id"])
    tp_id_number = c2.text_input("Your ID / Passport Number *", placeholder="12345678")

    tp_name = st.text_input("Your Full Name *", placeholder="Your name as on ID")
    tp_phone = st.text_input("Phone Number *", placeholder="+254...")
    tp_email = st.text_input("Email Address", placeholder="optional@email.com")

    # Step 3: Claim type
    st.markdown("#### Step 3 — Nature of Claim")
    tp_claim_type = st.selectbox("Claim Type *", [
        "Third-Party Property Damage",   # vehicle damage only
        "Third-Party Bodily Injury",       # injury included
    ])

    is_bodily_injury = (tp_claim_type == "Third-Party Bodily Injury")

    if is_bodily_injury:
        st.info("Bodily injury claims follow a separate review process. You will be contacted by our legal team.")

    # Step 4: Incident details
    st.markdown("#### Step 4 — Incident Details")
    c3, c4 = st.columns(2)
    tp_incident_type = c3.selectbox("Incident Type *", [
        "Road Accident", "Hit and Run", "Vandalism", "Other"
    ])
    tp_incident_date  = c4.date_input("Date of Incident *")

    tp_description = st.text_area("Description of Incident *", height=100,
        placeholder="Describe what happened, including location, vehicles involved, and parties...")

    # Step 5: At-fault driver details (if known)
    st.markdown("#### Step 5 — At-Fault Driver (if known)")
    c5, c6 = st.columns(2)
    tp_driver_name  = c5.text_input("Driver Name", placeholder="Name of the at-fault driver")
    tp_driver_phone = c6.text_input("Driver Phone", placeholder="+254...")
    tp_driver_lic   = c6.text_input("Driving Licence Number", placeholder="DL-XXXXXX")

    # Step 6: Police report
    st.markdown("#### Step 6 — Police Abstract")
    tp_police_station = st.text_input("Police Station", placeholder="e.g. Kilimani Police Station")
    tp_ob_number      = st.text_input("OB Number", placeholder="OB-XXXXXX")
    tp_ob_date        = st.date_input("OB Date")

    # Step 7: Documents
    st.markdown("#### Step 7 — Supporting Documents")
    tp_uploaded = st.file_uploader(
        "Upload documents",
        type=["jpg", "jpeg", "png", "pdf", "webp"],
        accept_multiple_files=True
    )
    if tp_uploaded:
        st.write(f"**{len(tp_uploaded)} file(s) uploaded**")

    st.markdown("---")
    tp_submitted = st.form_submit_button("Submit Third-Party Claim", type="primary", use_container_width=True)
    if tp_submitted:
        if not all([tp_vehicle_reg, tp_id_number, tp_name, tp_phone, tp_incident_type, str(tp_incident_date), tp_description]):
            st.error("Please fill all mandatory fields.")
            return
        claim_ref = f"TP-{uuid.uuid4().hex[:8].upper()}"
        engine = get_engine()
        try:
            # Create TP claim — policy_ref is the insured vehicle's policy
            engine.create_claim(
                claim_ref=claim_ref,
                policy_ref=insured_info.get('policy_ref') if insured_info else 'UNKNOWN',
                id_number=tp_id_number,
                vehicle_reg=tp_vehicle_reg,
                incident_type=tp_incident_type,
                description=tp_description,
                claim_class="motor_tp" if not is_bodily_injury else "motor_tp_bi",
                user_id=user_email,
            )
            # Log TP metadata
            engine.audit.log(
                "claim", claim_ref, "tp_intake", user_email,
                before=None,
                after={
                    "claim_type": tp_claim_type,
                    "tp_name": tp_name,
                    "tp_phone": tp_phone,
                    "at_fault_vehicle": tp_vehicle_reg,
                    "driver_name": tp_driver_name,
                    "driver_phone": tp_driver_phone,
                    "police_station": tp_police_station,
                    "ob_number": tp_ob_number,
                }
            )
            st.success(
                f"Third-party claim submitted! Reference: **{claim_ref}**"
                f"\nYou will be contacted by our claims team."
            )
            st.balloons()
        except Exception as e:
            st.error(f"Failed: {e}")


# ─── Claim Tracker ─────────────────────────────────────────────────────────────

def _claim_tracker(user_email: str) -> None:
    st.subheader("Track My Claims")
    search_ref = st.text_input("Enter Claim Reference", placeholder="e.g. CLM-00000001 or TP-00000001")

    if not search_ref:
        st.info("Enter your claim reference above.")
        return

    engine = get_engine()
    claim = engine.get_claim(search_ref)
    if not claim:
        st.warning("Claim not found.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Status", claim.get("status", "Unknown"))
    col2.metric("Claim Class", claim.get("claim_class", "N/A").replace("_", " ").title())
    col3.metric("Policy", claim.get("policy_ref", "N/A"))

    st.markdown("#### Turnaround Time")
    breakdown = engine.clock.get_tat_breakdown(search_ref)
    if breakdown:
        rows = []
        for stage in breakdown:
            elapsed = stage.get("elapsed_ms")
            rows.append({
                "Stage":   stage["stage"],
                "Entered": stage.get("entered_at", ""),
                "Exited":  stage.get("exited_at", "Running..."),
                "Elapsed": _tat_display(elapsed) if elapsed else "In progress",
                "Parallel": "✓" if stage.get("parallel") else "",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No TAT data yet.")

    st.markdown("#### Audit Trail")
    history = engine.audit.get_history("claim", search_ref)
    if history:
        import json
        rows = []
        for h in history:
            before = json.loads(h.before) if h.before else None
            after  = json.loads(h.after)  if h.after  else None
            rows.append({
                "When":    h.timestamp[:19],
                "Action":  h.action,
                "User":    h.user_id,
                "Before":  str(before) if before else "—",
                "After":   str(after)  if after  else "—",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No audit entries yet.")


# ─── My Documents ─────────────────────────────────────────────────────────────

def _my_documents(user_email: str) -> None:
    st.subheader("My Documents")
    st.info("Documents uploaded during FNOL will appear here once processed.")
    st.markdown("*Document management coming soon — uploads from FNOL form are queued for processing.*")


# ─── My Profile ────────────────────────────────────────────────────────────────

def _my_profile(user_email: str) -> None:
    st.subheader("My Profile")
    user = getattr(core_api, 'get_user', lambda e: None)(user_email) if hasattr(core_api, 'get_user') else None
    if user:
        st.json(user)
    else:
        st.write(f"**Email:** {user_email}")
        st.write("Profile management coming soon.")
