"""New Claim (FNOL) — pages/00_claimant/02_new_claim.py"""
"""
Role: client
First Notification of Loss form — verify policy, enter incident details, submit.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core_engine
from core_engine import get_engine, ClaimStatus
import core_api
import uuid
import streamlit as st

def render(user_email: str, user_role: str = "client") -> None:
    st.title("📋 New Claim (FNOL)")
    st.info("Complete all sections. Fields marked * are mandatory.")
    col1, col2 = st.columns(2)
    id_type = col1.selectbox("ID Type *", ["National Id","Passport","Foreign Id"])
    id_number = col2.text_input("ID / Passport Number *", placeholder="12345678")
    policy_data = None
    if id_number and len(id_number) >= 4:
        with st.spinner("Verifying policy..."):
            policy_data = core_api.verify_policy(id_number)
        if policy_data:
            st.success(f"Policy found: **{policy_data.get('policy_ref','N/A')}** - {policy_data.get('product','Motor')}")
        else:
            st.warning("No active policy found. Contact your agent or branch.")
    st.markdown("#### Incident Details")
    col3, col4 = st.columns(2)
    incident_type = col3.selectbox("Incident Type *", ["Road Accident","Theft/Break-in","Fire","Flood","Landslide","Broken Glass","Windscreen Damage","Other"])
    incident_date = col4.date_input("Date of Incident *")
    description = st.text_area("Description of Incident *", height=100)
    st.markdown("#### Vehicle / Item Details")
    col5, col6 = st.columns(2)
    vehicle_reg = col5.text_input("Vehicle Registration *", placeholder="KBZ 000A")
    estimated_amount = col6.number_input("Estimated Loss (KES) *", min_value=0, step=10000, format="%d")
    st.markdown("---")
    if st.button("Submit Claim", type="primary", use_container_width=True):
        if not all([id_number, incident_type, str(incident_date), description, vehicle_reg]):
            st.error("Please fill all mandatory fields.")
            return
        claim_ref = f"CLM-{uuid.uuid4().hex[:8].upper()}"
        engine = get_engine()
        try:
            engine.create_claim(
                claim_ref=claim_ref,
                policy_ref=policy_data.get("policy_ref") if policy_data else "UNKNOWN",
                id_number=id_number,
                vehicle_reg=vehicle_reg,
                incident_type=incident_type,
                description=description,
                claim_class="motor",
                user_id=user_email,
            )
            engine.transition_to(claim_ref, ClaimStatus.REPORTED, user_email)
            st.success(f"Claim {claim_ref} submitted successfully!")
            st.balloons()
        except Exception as e:
            st.error(f"Failed: {e}")
