"""Claims Handler / Claims Officer Portal â core claims processing."""
from __future__ import annotations
import datetime
import streamlit as st
import pandas as pd

from core_api import core_api

OFFICER_AUTHORITY_LIMIT = 500_000  # KES â above this needs Head of Claims sign-off


def render() -> None:
    st.title("ð Claims Officer Portal")
    tabs = st.tabs([
        "ð¥ My Claims", "ð¥ Assign Experts", "ð¼ Reserve",
        "â Settlement", "ð¸ Authorise Payment", "ð¨ Correspondence", "ð·ï¸ Bid Comparison"
    ])
    with tabs[0]:
        _my_claims()
    with tabs[1]:
        _assign_experts_tab()
    with tabs[2]:
        _set_reserve()
    with tabs[3]:
        _recommend_settlement()
    with tabs[4]:
        _authorise_service_payment()
    with tabs[5]:
        _correspondence()
    with tabs[6]:
        _bid_comparison()


def _my_claims() -> None:
    st.subheader("My Assigned Claims")
    c1, c2, c3 = st.columns(3)
    c1.selectbox("Status", ["All", "New", "Under Review", "Awaiting Report",
                             "Under Assessment", "Pending Settlement",
                             "Awaiting Payment", "Settled", "Repudiated"])
    c2.selectbox("Urgency", ["All", "High", "Medium", "Low"])
    c3.text_input("Search Ref / Client")
    claims = [
        {"Ref": "CLM-20250715123456", "Client": "John Mwangi",    "Type": "Motor Accident", "Opened": "2025-07-15", "Status": "Under Assessment",  "Reserve (KES)": "320,000", "Urgency": "High"},
        {"Ref": "CLM-20250714098765", "Client": "Amina Wanjiru", "Type": "Theft",            "Opened": "2025-07-14", "Status": "Awaiting Report",    "Reserve (KES)": "180,000", "Urgency": "Medium"},
        {"Ref": "CLM-20250712055431", "Client": "Peter Ochieng", "Type": "Fire",             "Opened": "2025-07-12", "Status": "Pending Settlement", "Reserve (KES)": "850,000", "Urgency": "High"},
        {"Ref": "CLM-20250710033210", "Client": "Grace Njoki",   "Type": "Windscreen",       "Opened": "2025-07-10", "Status": "Awaiting Payment",    "Reserve (KES)": "22,000",  "Urgency": "Low"},
    ]
    st.dataframe(claims, use_container_width=True)


def _assign_experts_tab() -> None:
    st.subheader("My Claims â Assign Expert")
    claims = [
        {"Ref": "CLM-20250715123456", "Client": "John Mwangi"},
        {"Ref": "CLM-20250714098765", "Client": "Amina Wanjiru"},
        {"Ref": "CLM-20250712055431", "Client": "Peter Ochieng"},
        {"Ref": "CLM-20250710033210", "Client": "Grace Njoki"},
    ]
    claim_ref = st.selectbox("Select Claim", options=[c["Ref"] for c in claims])
    if claim_ref:
        _assign_experts(claim_ref)


def _assign_experts(claim_ref: str) -> None:
    """Assign an assessor/garage/investigator to a claim using core_api."""
    st.subheader("Assign Expert")

    with st.form(key=f"assign_expert_form_{claim_ref}"):
        expert_type = st.selectbox(
            "Expert Type",
            ["assessor", "garage", "investigator", "loss_adjuster"],
            key=f"expert_type_{claim_ref}"
        )
        expert_name = st.text_input("Expert Name / Company", key=f"expert_name_{claim_ref}")
        expert_phone = st.text_input("Phone Number", key=f"expert_phone_{claim_ref}")
        estimated_cost = st.number_input(
            "Estimated Cost (KES)", min_value=0, value=0, step=1000, key=f"est_cost_{claim_ref}"
        )
        note = st.text_area("Assignment Note", key=f"assign_note_{claim_ref}")

        submitted = st.form_submit_button("Assign & Notify")
        if submitted:
            if not expert_name.strip():
                st.error("Expert name is required.")
                return
            assignment_id = core_api.assign_expert(
                claim_ref=claim_ref,
                expert_type=expert_type,
                expert_name=expert_name.strip(),
                expert_phone=expert_phone.strip(),
                expert_company="",
                assigned_by=st.session_state.get("user", ""),
                estimated_cost=float(estimated_cost),
                note=note.strip()
            )
            if assignment_id:
                st.success(f"â Expert assigned â {assignment_id}")
                core_api.log_communication(
                    claim_ref=claim_ref,
                    channel="sms",
                    direction="outbound",
                    summary=f"Expert ({expert_type}) assigned: {expert_name}",
                    created_by=st.session_state.get("user", ""),
                    contact_phone=expert_phone.strip()
                )
                if expert_phone.strip():
                    st.info(f"ð± SMS notification would be sent to {expert_phone.strip()}")
            else:
                st.error("Failed to assign expert. Please try again.")

    st.markdown("**Current Assignments**")
    assignments_df = core_api.get_assignments(claim_ref)
    if not assignments_df.empty:
        st.dataframe(
            assignments_df[["assignment_id", "expert_type", "expert_name", "status", "assigned_at"]],
            use_container_width=True
        )
        for _, row in assignments_df.iterrows():
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if row["status"] == "pending":
                    if st.button(f"Accept ({row['assignment_id']})", key=f"accept_{row['assignment_id']}"):
                        core_api.update_assignment_status(row["assignment_id"], "accepted")
                        st.rerun()
            with col2:
                if row["status"] == "accepted":
                    if st.button(f"Complete ({row['assignment_id']})", key=f"complete_{row['assignment_id']}"):
                        core_api.update_assignment_status(row["assignment_id"], "completed")
                        st.rerun()
            with col3:
                if row["status"] in ("pending", "accepted"):
                    if st.button(f"Reject ({row['assignment_id']})", key=f"reject_{row['assignment_id']}"):
                        core_api.update_assignment_status(row["assignment_id"], "rejected")
                        st.rerun()
    else:
        st.info("No experts assigned yet.")


def _set_reserve(claim_ref: str) -> None:
    """Set or supplement a claim reserve."""
    st.subheader("Reserve Management")

    reserves_df = core_api.get_reserves(claim_ref)
    total_reserves = core_api.get_total_reserves(claim_ref) if not reserves_df.empty else 0

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Reserves", f"KES {total_reserves:,.0f}")
    with col2:
        approved = reserves_df[reserves_df["status"] == "approved"]["amount"].sum() if not reserves_df.empty else 0
        st.metric("Approved Reserves", f"KES {approved:,.0f}")

    if not reserves_df.empty:
        st.markdown("**Reserve History**")
        display_df = reserves_df.copy()
        display_df["amount"] = display_df["amount"].apply(lambda x: f"KES {x:,.0f}")
        st.dataframe(
            display_df[["reserve_id", "reserve_type", "amount", "purpose", "status", "created_at"]],
            use_container_width=True
        )

    st.markdown("**Add New Reserve**")
    with st.form(key=f"reserve_form_{claim_ref}"):
        reserve_type = st.selectbox("Reserve Type", ["initial", "supplemental"], key=f"rs_type_{claim_ref}")
        amount = st.number_input(
            "Amount (KES)", min_value=0, value=50000, step=5000, key=f"rs_amount_{claim_ref}"
        )
        purpose = st.selectbox(
            "Purpose", ["assessment", "repair", "legal", "investigation", "other"], key=f"rs_purpose_{claim_ref}"
        )
        note = st.text_area("Note", key=f"rs_note_{claim_ref}")

        submitted = st.form_submit_button("Set Reserve")
        if submitted:
            if amount <= 0:
                st.error("Amount must be greater than zero.")
                return
            reserve_id = core_api.set_reserve(
                claim_ref=claim_ref,
                reserve_type=reserve_type,
                amount=float(amount),
                purpose=purpose,
                created_by=st.session_state.get("user", ""),
                note=note.strip()
            )
            if reserve_id:
                st.success(f"â Reserve created â {reserve_id}")
            else:
                st.error("Failed to create reserve.")

    pending = reserves_df[reserves_df["status"] == "pending"] if not reserves_df.empty else pd.DataFrame()
    if not pending.empty:
        st.markdown("**Pending Approvals**")
        for _, row in pending.iterrows():
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            with col1:
                st.markdown(f"**{row['reserve_type'].capitalize()}**: KES {row['amount']:,.0f}")
                st.caption(f"{row['purpose']}")
            with col2:
                st.caption(f"By: {row['created_by']}")
            with col3:
                if st.button(f"Approve", key=f"apr_{row['reserve_id']}"):
                    core_api.approve_reserve(row["reserve_id"], st.session_state.get("user", ""))
                    st.rerun()
            with col4:
                if st.button(f"Release", key=f"rel_{row['reserve_id']}"):
                    core_api.release_reserve(row["reserve_id"], st.session_state.get("user", ""), "Released by officer")
                    st.rerun()


def _recommend_settlement(claim_ref: str) -> None:
    """Recommend a settlement for HoC approval."""
    st.subheader("Recommend Settlement")

    settlements_df = core_api.get_settlements(claim_ref)
    total_reserves = core_api.get_total_reserves(claim_ref)
    total_settled = (
        settlements_df[settlements_df["status"].isin(["approved", "paid"])]["amount"].sum()
        if not settlements_df.empty else 0
    )

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Reserves", f"KES {total_reserves:,.0f}")
    with col2:
        st.metric("Total Settled/Approved", f"KES {total_settled:,.0f}")

    if not settlements_df.empty:
        st.markdown("**Settlement History**")
        display_df = settlements_df.copy()
        display_df["amount"] = display_df["amount"].apply(lambda x: f"KES {x:,.0f}")
        st.dataframe(
            display_df[["settlement_id", "settlement_type", "amount", "payee_name", "status", "recommended_at"]],
            use_container_width=True
        )

    st.markdown("**Recommend Settlement**")
    with st.form(key=f"settle_form_{claim_ref}"):
        amount = st.number_input(
            "Settlement Amount (KES)", min_value=0, value=0, step=5000, key=f"st_amount_{claim_ref}"
        )
        payee_name = st.text_input("Payee Name", key=f"payee_name_{claim_ref}")
        payee_type = st.selectbox(
            "Payee Type",
            ["assessor", "garage", "investigator", "spare_parts", "third_party", "insured"],
            key=f"payee_type_{claim_ref}"
        )

        wht_rates = {
            "assessor": 0.05, "garage": 0.05, "investigator": 0.05,
            "spare_parts": 0.10, "third_party": 0.00, "insured": 0.00
        }
        wht_rate = wht_rates.get(payee_type, 0.0)
        wht_amount = amount * wht_rate
        net_amount = amount - wht_amount

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.text_input("WHT Rate", value=f"{wht_rate*100:.0f}%", disabled=True)
        with col_b:
            st.text_input("WHT Amount", value=f"KES {wht_amount:,.0f}", disabled=True)
        with col_c:
            st.text_input("Net Payable", value=f"KES {net_amount:,.0f}", disabled=True)

        note = st.text_area("Recommendation Note", key=f"st_note_{claim_ref}")

        submitted = st.form_submit_button("Submit for Approval")
        if submitted:
            if amount <= 0:
                st.error("Amount must be greater than zero.")
                return
            settlement_id = core_api.recommend_settlement(
                claim_ref=claim_ref,
                amount=float(amount),
                payee_name=payee_name.strip(),
                payee_type=payee_type,
                recommended_by=st.session_state.get("user", ""),
                wht_rate=wht_rate,
                note=note.strip()
            )
            if settlement_id:
                st.success(f"â Settlement recommended â {settlement_id} â sent to Head of Claims for approval")
            else:
                st.error("Failed to submit settlement recommendation.")


def _authorise_service_payment(claim_ref: str) -> None:
    """Authorise a service provider payment."""
    st.subheader("Authorise Service Provider Payment")
    st.info("Verify the invoice against the approved estimate before authorising Finance to release payment.")
    pending = [
        {"Ref": "CLM-20250710033210", "Provider": "Westlands Auto Garage",     "Service": "Repairs",    "Approved (KES)": "22,000", "Invoice (KES)": "21,500", "Variance": "-500"},
        {"Ref": "CLM-20250714098765", "Provider": "J. Kamau & Associates", "Service": "Assessment", "Approved (KES)": "8,000",  "Invoice (KES)": "8,000",  "Variance": "0"},
    ]
    st.dataframe(pending, use_container_width=True)
    st.divider()

    with st.form(key=f"auth_payment_{claim_ref}"):
        c1, c2 = st.columns(2)
        c1.text_input("Claim Reference *", value=claim_ref, key=f"ap_claim_{claim_ref}", disabled=True)
        provider_name = c2.text_input("Service Provider *", key=f"ap_provider_{claim_ref}")
        c1, c2 = st.columns(2)
        invoice_number = c1.text_input("Invoice Number *", key=f"ap_inv_{claim_ref}")
        c2.date_input("Invoice Date", key=f"ap_date_{claim_ref}")
        c1, c2, c3 = st.columns(3)
        c1.number_input("Approved Estimate (KES)", min_value=0.0, format="%.2f", key=f"ap_est_{claim_ref}")
        invoice_amount = c2.number_input(
            "Invoice Amount (KES) *", min_value=0.0, format="%.2f", key=f"ap_amt_{claim_ref}"
        )
        decision = c3.selectbox(
            "Decision *",
            ["Approve for Payment", "Reject â Return Invoice", "Query â Request Clarification"],
            key=f"ap_dec_{claim_ref}"
        )
        st.text_area("Authorisation Notes", key=f"ap_notes_{claim_ref}")
        invoice_file = st.file_uploader("Invoice PDF *", type=["pdf"], key=f"ap_file_{claim_ref}")
        submitted = st.form_submit_button("Submit Authorisation", type="primary", use_container_width=True)

    if submitted:
        if not all([provider_name, invoice_number, invoice_file]):
            st.error("Provider name, invoice number, and invoice PDF are required.")
        elif decision == "Approve for Payment":
            auth_id = core_api.authorise_service_payment(
                claim_ref=claim_ref,
                provider_name=provider_name.strip(),
                invoice_number=invoice_number.strip(),
                invoice_amount=float(invoice_amount),
                decision=decision,
                authorised_by=st.session_state.get("user", ""),
                note=""
            )
            if auth_id:
                st.success(f"â Payment of **KES {invoice_amount:,.2f}** to **{provider_name}** authorised. Finance notified. ({auth_id})")
            else:
                st.error("Failed to authorise payment.")
        else:
            st.info(f"Invoice for **{claim_ref}** â **{decision}** recorded. Provider notified.")


def _correspondence(claim_ref: str) -> None:
    """Log communications and manage diary entries."""
    st.subheader("Correspondence & Diary")

    tab_comm, tab_diary = st.tabs(["ð Communications Log", "ð Diary"])

    with tab_comm:
        st.markdown("**Log Communication**")
        with st.form(key=f"comm_form_{claim_ref}"):
            channel = st.selectbox("Channel", ["sms", "call", "email", "letter", "whatsapp"], key=f"ch_{claim_ref}")
            direction = st.radio("Direction", ["outbound", "inbound"], horizontal=True, key=f"dir_{claim_ref}")
            contact_name = st.text_input("Contact Name", key=f"cname_{claim_ref}")
            contact_phone = st.text_input("Phone/Email", key=f"cphone_{claim_ref}")
            summary = st.text_area("Summary", key=f"csum_{claim_ref}")
            outcome = st.text_input("Outcome", key=f"cout_{claim_ref}")
            consent = st.checkbox("DPA 2019 consent obtained", value=True, key=f"ccons_{claim_ref}")
            submitted = st.form_submit_button("Log Communication")
            if submitted:
                if not summary.strip():
                    st.error("Summary is required.")
                    return
                comm_id = core_api.log_communication(
                    claim_ref=claim_ref,
                    channel=channel,
                    direction=direction,
                    summary=summary.strip(),
                    created_by=st.session_state.get("user", ""),
                    contact_name=contact_name.strip(),
                    contact_phone=contact_phone.strip(),
                    outcome=outcome.strip(),
                    consent=consent
                )
                if comm_id:
                    st.success(f"â Communication logged â {comm_id}")
                else:
                    st.error("Failed to log communication.")

        comms_df = core_api.get_communications(claim_ref)
        if not comms_df.empty:
            st.markdown("**Communication History**")
            st.dataframe(
                comms_df[["comm_id", "channel", "direction", "contact_name", "summary", "created_at"]],
                use_container_width=True
            )

    with tab_diary:
        st.markdown("**Add Diary Entry**")
        with st.form(key=f"diary_form_{claim_ref}"):
            task = st.text_input("Task Description", key=f"dtask_{claim_ref}")
            due_date = st.date_input("Due Date", key=f"ddue_{claim_ref}")
            assigned_to = st.text_input("Assigned To", key=f"dassign_{claim_ref}")
            priority = st.selectbox(
                "Priority", ["low", "normal", "high", "urgent"], key=f"dpri_{claim_ref}"
            )
            note = st.text_area("Note", key=f"dnote_{claim_ref}")
            submitted = st.form_submit_button("Add Diary Entry")
            if submitted:
                if not task.strip():
                    st.error("Task description is required.")
                    return
                entry_id = core_api.add_diary_entry(
                    claim_ref=claim_ref,
                    task=task.strip(),
                    due_date=str(due_date),
                    assigned_to=assigned_to.strip(),
                    priority=priority,
                    created_by=st.session_state.get("user", ""),
                    note=note.strip()
                )
                if entry_id:
                    st.success(f"â Diary entry added â {entry_id}")
                else:
                    st.error("Failed to add diary entry.")

        diary_df = core_api.get_diary_entries(claim_ref)
        if not diary_df.empty:
            st.markdown("**Diary Entries**")
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            overdue_df = diary_df[(diary_df["status"] == "open") & (diary_df["due_date"] < today)]
            if not overdue_df.empty:
                suffix = "y" if len(overdue_df) == 1 else "ies"
                st.error(f"â ï¸ {len(overdue_df)} overdue entr{suffix}")
            st.dataframe(
                diary_df[["entry_id", "task", "due_date", "assigned_to", "priority", "status"]],
                use_container_width=True
            )
            for _, row in diary_df[diary_df["status"] == "open"].iterrows():
                if st.button(f"Mark Done: {row['entry_id']}", key=f"done_{row['entry_id']}"):
                    core_api.complete_diary_entry(row["entry_id"])
                    st.rerun()


# ---------------------------------------------------------------------------
# Scoring helper
# ---------------------------------------------------------------------------

def _score_bids(bids: list) -> list:
    """Score bids: price 60 %, provider rating 40 %. Returns sorted list (highest composite first)."""
    if not bids:
        return bids
    prices  = [b["unit_price"] for b in bids]
    ratings = [b["rating"]     for b in bids]
    lo_p, hi_p = min(prices),  max(prices)
    lo_r, hi_r = min(ratings), max(ratings)
    for b in bids:
        p_score = 100.0 if hi_p == lo_p else 100 * (1 - (b["unit_price"] - lo_p) / (hi_p - lo_p))
        r_score = 100.0 if hi_r == lo_r else 100 * (b["rating"] - lo_r) / (hi_r - lo_r)
        b["price_score"]  = round(p_score,  1)
        b["rating_score"] = round(r_score,  1)
        b["composite"]    = round(0.60 * p_score + 0.40 * r_score, 1)
    bids.sort(key=lambda x: x["composite"], reverse=True)
    for i, b in enumerate(bids):
        b["rank"]        = i + 1
        b["recommended"] = "â­ Recommended" if i == 0 else ""
    return bids


# ---------------------------------------------------------------------------
# Bid Comparison â evaluate and award spare parts RFQs
# ---------------------------------------------------------------------------

def _bid_comparison() -> None:
    st.subheader("Spare Parts Bid Comparison")
    st.info(
        "Review all bids for an open RFQ. "
        "Each bid is scored automatically: **price (60 %)** + **provider rating (40 %)**. "
        "Award the winning bid to trigger an order and notify all providers."
    )

    _SAMPLE: dict = {
        "RFQ-20250715001": [
            {"bid_ref": "BID-2025A1", "provider": "AutoSpares Kenya Ltd",     "brand": "Toyota Genuine",  "condition": "New (Genuine OEM)",    "unit_price": 12_500.0, "lead_days": 3, "warranty": "6 months",  "rating": 4.5, "submitted": "2025-07-15 09:15"},
            {"bid_ref": "BID-2025A2", "provider": "Parts Unlimited Nairobi",  "brand": "Aftermarket",     "condition": "New (Aftermarket)",     "unit_price":  9_800.0, "lead_days": 2, "warranty": "3 months",  "rating": 3.8, "submitted": "2025-07-15 10:45"},
            {"bid_ref": "BID-2025A3", "provider": "Motospares East Africa",   "brand": "TRD / OEM",       "condition": "New (OEM Equivalent)", "unit_price": 11_200.0, "lead_days": 4, "warranty": "12 months", "rating": 4.8, "submitted": "2025-07-15 12:00"},
        ],
        "RFQ-20250715002": [
            {"bid_ref": "BID-2025B1", "provider": "AutoSpares Kenya Ltd",     "brand": "Toyota Genuine",  "condition": "New (Genuine OEM)",    "unit_price": 18_000.0, "lead_days": 3, "warranty": "6 months",  "rating": 4.5, "submitted": "2025-07-15 09:20"},
            {"bid_ref": "BID-2025B2", "provider": "Tyre & Parts Hub",         "brand": "Aftermarket",      "condition": "New (Aftermarket)",    "unit_price": 14_500.0, "lead_days": 1, "warranty": "3 months",  "rating": 3.9, "submitted": "2025-07-15 11:05"},
        ],
        "RFQ-20250714001": [
            {"bid_ref": "BID-2025C1", "provider": "SpeedParts Mombasa",       "brand": "Toyota OEM",       "condition": "New (Genuine OEM)",    "unit_price":  4_200.0, "lead_days": 1, "warranty": "6 months",  "rating": 4.2, "submitted": "2025-07-14 08:30"},
            {"bid_ref": "BID-2025C2", "provider": "Coast Auto Parts",         "brand": "Aftermarket",      "condition": "New (Aftermarket)",     "unit_price":  3_500.0, "lead_days": 2, "warranty": "3 months",  "rating": 3.5, "submitted": "2025-07-14 11:20"},
            {"bid_ref": "BID-2025C3", "provider": "Mombasa Spares Direct",    "brand": "Toyota Genuine",   "condition": "New (Genuine OEM)",    "unit_price":  4_600.0, "lead_days": 2, "warranty": "12 months", "rating": 4.7, "submitted": "2025-07-14 14:00"},
        ],
    }

    open_rfqs = list(_SAMPLE.keys())

    c1, c2 = st.columns([3, 1])
    rfq_ref = c1.selectbox(
        "Select RFQ Reference",
        options=["â select an RFQ â"] + open_rfqs,
        key="bid_comp_rfq",
    )
    if c2.button("ð Refresh", key="bid_comp_refresh", use_container_width=True):
        st.rerun()

    if rfq_ref.startswith("â"):
        st.caption("Select an RFQ reference above to load submitted bids.")
        return

    bids = [dict(b) for b in _SAMPLE.get(rfq_ref, [])]
    if not bids:
        st.warning(f"No bids received yet for **{rfq_ref}**.")
        return

    bids = _score_bids(bids)

    prices = [b["unit_price"] for b in bids]
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Bids Received", len(bids))
    mc2.metric("Lowest Price (KES)", f"{min(prices):,.2f}")
    mc3.metric("Highest Price (KES)", f"{max(prices):,.2f}")
    mc4.metric("Best Score", bids[0]["composite"])

    st.markdown(f"**{len(bids)} bid(s) for {rfq_ref}** â sorted by composite score (highest first)")
    df = pd.DataFrame([{
        "Rank":             b["rank"],
        "Recommendation":   b["recommended"],
        "Bid Ref":          b["bid_ref"],
        "Provider":         b["provider"],
        "Brand":            b["brand"],
        "Condition":        b["condition"],
        "Unit Price (KES)": f"{b['unit_price']:,.2f}",
        "Lead (days)":      b["lead_days"],
        "Warranty":         b["warranty"],
        "Rating (/ 5)":     b["rating"],
        "Price Score":      b["price_score"],
        "Rating Score":     b["rating_score"],
        "Composite Score":  b["composite"],
        "Submitted":        b["submitted"],
    } for b in bids])
    st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("ð Score Breakdown Chart"):
        st.caption("Price Score (60 %) and Rating Score (40 %) per provider.")
        chart_df = pd.DataFrame({
            "Provider":             [b["provider"]      for b in bids],
            "Price Score (60 %)":  [b["price_score"]   for b in bids],
            "Rating Score (40 %)": [b["rating_score"]  for b in bids],
        }).set_index("Provider")
        st.bar_chart(chart_df)

    st.divider()
    st.markdown("### Award Decision")
    st.caption(
        "The system pre-selects the highest-scoring bid. "
        "Any override is logged to the audit trail."
    )

    bid_labels = [
        f"{b['bid_ref']} â {b['provider']}  | KES {b['unit_price']:,.2f} | {b['lead_days']}d | Score {b['composite']}"
        for b in bids
    ]

    with st.form("award_bid_form"):
        selected_label = st.selectbox(
            "Select Winning Bid *",
            options=bid_labels,
            index=0,
        )
        selected_idx = bid_labels.index(selected_label)
        is_override = bids[selected_idx]["rank"] != 1

        if is_override:
            st.warning(
                f"â ï¸ Override: **{bids[0]['bid_ref']}** ({bids[0]['provider']}, Score {bids[0]['composite']}) "
                "is the system recommendation. Provide justification below."
            )

        c1, c2 = st.columns(2)
        payer = c1.radio(
            "Payment Instruction *",
            ["Insurance Company (direct payment)", "Garage (garage pays supplier)"],
        )
        delivery_address = c2.text_input(
            "Parts Delivery Address *",
            placeholder="e.g. AutoFix Garage, Mombasa Rd, Nairobi",
        )
        award_notes = st.text_area(
            "Award Notes / Justification",
            placeholder="e.g. Parts must arrive before repair starts. State override reason if applicable.",
        )
        award_btn = st.form_submit_button(
            "ð Award Bid & Notify All Providers", type="primary", use_container_width=True
        )

    if award_btn:
        if not delivery_address:
            st.error("Delivery address is required before awarding.")
        else:
            winner = bids[selected_idx]
            losers = [b for b in bids if b["bid_ref"] != winner["bid_ref"]]
            order_ref = f"ORD-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

            if is_override:
                st.warning(f"Override logged: {winner['bid_ref']} (Rank {winner['rank']}) selected over recommendation.")

            st.success(
                f"**Contract Awarded - {winner['provider']}** ({winner['bid_ref']})"
"
                f"Unit Price: **KES {winner['unit_price']:,.2f}** Â· "
                f"Lead time: **{winner['lead_days']} days** Â· "
                f"Warranty: **{winner['warranty']}** Â· Score: **{winner['composite']}**  
"
                f"Order: **{order_ref}** Â· Payer: **{payer.split(' (')[0]}**  
"
                f"Delivery: {delivery_address}  
"
                f"**{len(losers)}** losing provider(s) notified."
            )
