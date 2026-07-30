"""Claims Handler / Claims Officer Portal — core claims processing."""
from __future__ import annotations
import datetime
import streamlit as st

OFFICER_AUTHORITY_LIMIT = 500_000  # KES — above this needs Head of Claims sign-off


def render() -> None:
    st.title("📋 Claims Officer Portal")
    tabs = st.tabs(["📥 My Claims","👥 Assign Experts","💼 Reserve","✅ Settlement","💸 Authorise Payment","📨 Correspondence","🏷️ Bid Comparison"])
    with tabs[0]: _my_claims()
    with tabs[1]: _assign_experts()
    with tabs[2]: _set_reserve()
    with tabs[3]: _recommend_settlement()
    with tabs[4]: _authorise_service_payment()
    with tabs[5]: _correspondence()
    with tabs[6]: _bid_comparison()


def _my_claims() -> None:
    st.subheader("My Assigned Claims")
    c1, c2, c3 = st.columns(3)
    c1.selectbox("Status", ["All","New","Under Review","Awaiting Report","Under Assessment","Pending Settlement","Awaiting Payment","Settled","Repudiated"])
    c2.selectbox("Urgency", ["All","High","Medium","Low"])
    c3.text_input("Search Ref / Client")
    claims = [
        {"Ref":"CLM-20250715123456","Client":"John Mwangi",   "Type":"Motor Accident","Opened":"2025-07-15","Status":"Under Assessment", "Reserve (KES)":"320,000","Urgency":"High"},
        {"Ref":"CLM-20250714098765","Client":"Amina Wanjiru", "Type":"Theft",         "Opened":"2025-07-14","Status":"Awaiting Report",   "Reserve (KES)":"180,000","Urgency":"Medium"},
        {"Ref":"CLM-20250712055431","Client":"Peter Ochieng", "Type":"Fire",          "Opened":"2025-07-12","Status":"Pending Settlement","Reserve (KES)":"850,000","Urgency":"High"},
        {"Ref":"CLM-20250710033210","Client":"Grace Njoki",   "Type":"Windscreen",    "Opened":"2025-07-10","Status":"Awaiting Payment",  "Reserve (KES)":"22,000", "Urgency":"Low"},
    ]
    st.dataframe(claims, use_container_width=True)


def _assign_experts() -> None:
    st.subheader("Assign Expert to Claim")
    st.info("Assignment triggers an automatic SMS/email notification. SLA clock starts on assignment.")
    with st.form("assign_expert"):
        c1, c2 = st.columns(2)
        claim_ref   = c1.text_input("Claim Reference *")
        expert_type = c2.selectbox("Expert Type *", ["Assessor","Garage / Repairer","Investigator"])
        c1, c2 = st.columns(2)
        expert_name  = c1.text_input("Expert Name / Company *")
        expert_phone = c2.text_input("Phone / Email")
        c1, c2 = st.columns(2)
        priority  = c1.selectbox("Priority", ["Normal","Urgent","Critical"])
        sla_hours = c2.number_input("SLA (hours from now)", min_value=1, value=48)
        notes     = st.text_area("Assignment Notes")
        submitted = st.form_submit_button("Assign & Notify", type="primary", use_container_width=True)
    if submitted:
        if not claim_ref or not expert_name:
            st.error("Claim reference and expert name are required.")
        else:
            actor      = st.session_state.get("user", "claims_officer")
            new_status = _EXPERT_STATUS_MAP.get(expert_type, "Assessor Appointed")
            # Store as "Expert Name (Expert Type)" so the admin dashboard Handler column is readable
            handler_value = f"{expert_name} ({expert_type})"

            with st.spinner("Updating Delta table\u2026"):
                ok, result = _update_assignment(claim_ref, handler_value, new_status)

            if not ok:
                st.error(f"Delta UPDATE failed: {result}")
            elif result == "not_found":
                st.warning(
                    f"Claim **{claim_ref}** was not found in the system. "
                    "Please verify the reference number and try again."
                )
            else:
                # Sync status to core insurance system
                note = (
                    f"Assigned {expert_type}: {expert_name} — "
                    f"Phone/Email: {expert_phone or 'N/A'} — "
                    f"Priority: {priority} — SLA: {sla_hours}h"
                    + (f" — Notes: {notes}" if notes else "")
                )
                core_api.update_claim_status(
                    claim_ref, new_status, note=note, actor=actor
                )
                core_api.invalidate_claim_cache(claim_ref)

                st.success(
                    f"\u2705 **{expert_type}** *{expert_name}* assigned to claim **{claim_ref}**.  \n"
                    f"Status updated to **{new_status}** in Delta → core system synced.  \n"
                    f"SLA: **{sla_hours} hours** | Priority: **{priority}**"
                )
                # Surface the updated row for confirmation
                verify_rows, verify_cols = _run_sql(
                    f"SELECT claim_ref, status, assigned_handler, "
                    f"CAST(submitted_at AS STRING) AS submitted_at "
                    f"FROM {_FNOL} WHERE claim_ref = :ref",
                    params=[StatementParameterListItem(name="ref", value=claim_ref)],
                )
                if verify_rows:
                    import pandas as pd
                    st.dataframe(
                        pd.DataFrame(verify_rows, columns=verify_cols).rename(columns={
                            "claim_ref":        "Claim Ref",
                            "status":           "Status",
                            "assigned_handler": "Assigned Handler",
                            "submitted_at":     "Submitted At",
                        }),
                        use_container_width=True, hide_index=True,
                    )


def _set_reserve() -> None:
    st.subheader("Set / Update Claim Reserve")
    st.info("Update the reserve whenever new information changes the estimated liability.")
    with st.form("reserve_form"):
        c1, c2 = st.columns(2)
        claim_ref   = c1.text_input("Claim Reference *")
        new_reserve = c2.number_input("New Reserve (KES) *", min_value=0.0, format="%.2f")
        basis = st.selectbox("Basis", ["Initial FNOL Estimate","Assessment Report","Revised After Supplementary","Write-Off Valuation","Other"])
        justification = st.text_area("Justification *")
        submitted = st.form_submit_button("Update Reserve", type="primary", use_container_width=True)
    if submitted:
        if not claim_ref or not justification:
            st.error("Claim reference and justification are required.")
        else:
            st.success(f"Reserve for **{claim_ref}** updated to **KES {new_reserve:,.2f}** ({basis}).")


def _recommend_settlement() -> None:
    st.subheader("Issue Settlement Instruction")
    st.warning(f"Settlements above **KES {OFFICER_AUTHORITY_LIMIT:,}** are routed to the Head of Claims for approval before Finance processes payment.")
    with st.form("settlement_form"):
        c1, c2 = st.columns(2)
        claim_ref       = c1.text_input("Claim Reference *")
        settlement_type = c2.selectbox("Settlement Type *", ["Cash Settlement to Client","Repair Authorisation (Garage Payment)","Write-Off Payment","Third-Party Settlement"])
        c1, c2, c3 = st.columns(3)
        gross_amount = c1.number_input("Gross (KES) *",   min_value=0.0, format="%.2f")
        excess       = c2.number_input("Excess (KES)",    min_value=0.0, format="%.2f")
        net_payable  = c3.number_input("Net Payable (KES) *", min_value=0.0, format="%.2f", help="Gross minus excess/deductible")
        st.markdown("**Payee Details**")
        c1, c2 = st.columns(2)
        payee_name  = c1.text_input("Payee Name *")
        bank_name   = c2.text_input("Bank *")
        c1, c2, c3 = st.columns(3)
        account_no  = c1.text_input("Account Number *")
        c2.text_input("Branch Code")
        c3.text_input("KRA PIN / ID")
        settlement_notes = st.text_area("Settlement Basis / Notes *")
        st.file_uploader("Supporting Documents", accept_multiple_files=True)
        submitted = st.form_submit_button("Submit Settlement Instruction", type="primary", use_container_width=True)
    if submitted:
        if not all([claim_ref, payee_name, bank_name, account_no, settlement_notes]):
            st.error("All starred fields are required.")
        elif net_payable > OFFICER_AUTHORITY_LIMIT:
            st.warning(f"KES {net_payable:,.2f} exceeds your authority limit. Routed to **Head of Claims** for approval.")
        else:
            st.success(f"Settlement of **KES {net_payable:,.2f}** for **{claim_ref}** sent to Finance for processing.")


def _authorise_service_payment() -> None:
    st.subheader("Authorise Service Provider Payment")
    st.info("Verify the invoice against the approved estimate before authorising Finance to release payment.")
    pending = [
        {"Ref":"CLM-20250710033210","Provider":"Westlands Auto Garage","Service":"Repairs",   "Approved (KES)":"22,000","Invoice (KES)":"21,500","Variance":"-500"},
        {"Ref":"CLM-20250714098765","Provider":"J. Kamau & Associates","Service":"Assessment","Approved (KES)":"8,000", "Invoice (KES)":"8,000", "Variance":"0"},
    ]
    st.dataframe(pending, use_container_width=True)
    st.divider()
    with st.form("auth_payment"):
        c1, c2 = st.columns(2)
        claim_ref      = c1.text_input("Claim Reference *")
        provider_name  = c2.text_input("Service Provider *")
        c1, c2 = st.columns(2)
        invoice_number = c1.text_input("Invoice Number *")
        c2.date_input("Invoice Date")
        c1, c2, c3 = st.columns(3)
        c1.number_input("Approved Estimate (KES)", min_value=0.0, format="%.2f")
        invoice_amount = c2.number_input("Invoice Amount (KES) *", min_value=0.0, format="%.2f")
        decision       = c3.selectbox("Decision *", ["Approve for Payment","Reject — Return Invoice","Query — Request Clarification"])
        st.text_area("Authorisation Notes")
        invoice_file = st.file_uploader("Invoice PDF *", type=["pdf"])
        submitted    = st.form_submit_button("Submit Authorisation", type="primary", use_container_width=True)
    if submitted:
        if not all([claim_ref, provider_name, invoice_number, invoice_file]):
            st.error("Claim ref, provider name, invoice number, and invoice PDF are required.")
        elif decision == "Approve for Payment":
            st.success(f"Payment of **KES {invoice_amount:,.2f}** to **{provider_name}** authorised. Finance notified.")
        else:
            st.info(f"Invoice for **{claim_ref}** — **{decision}** recorded. Provider notified.")


def _correspondence() -> None:
    st.subheader("Correspondence & Notifications")
    st.caption("All correspondence is logged to the claims audit trail.")
    with st.form("correspondence"):
        c1, c2 = st.columns(2)
        claim_ref = c1.text_input("Claim Reference *")
        recipient = c2.selectbox("Send To", ["Client","Assessor","Garage","Investigator","Head of Claims","Finance","Legal"])
        channel   = st.radio("Channel", ["SMS","Email","Internal Note"], horizontal=True)
        subject   = st.text_input("Subject *")
        message   = st.text_area("Message *", height=150)
        st.file_uploader("Attachments", accept_multiple_files=True)
        submitted = st.form_submit_button("Send", type="primary", use_container_width=True)
    if submitted:
        if not all([claim_ref, subject, message]):
            st.error("Claim reference, subject, and message are required.")
        else:
            st.success(f"{channel} sent to **{recipient}** for **{claim_ref}**. Logged to audit trail.")


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
        b["recommended"] = "⭐ Recommended" if i == 0 else ""
    return bids


# ---------------------------------------------------------------------------
# Bid Comparison — evaluate and award spare parts RFQs
# ---------------------------------------------------------------------------

def _bid_comparison() -> None:
    import pandas as pd  # noqa: PLC0415

    st.subheader("Spare Parts Bid Comparison")
    st.info(
        "Review all bids for an open RFQ. "
        "Each bid is scored automatically: **price (60 %)** + **provider rating (40 %)**. "
        "Award the winning bid to trigger an order and notify all providers."
    )

    # Sample data — replace with live Delta query:
    #   rows, cols = _run_sql(
    #       "SELECT bid_ref, provider_name, brand, condition, unit_price, "
    #       "       lead_days, warranty, provider_rating AS rating, submitted_at "
    #       "FROM main.claims.rfq_bids WHERE rfq_ref = :rfq AND status = 'Pending Review'",
    #       params=[StatementParameterListItem(name='rfq', value=rfq_ref)],
    #   )
    _SAMPLE: dict = {
        "RFQ-20250715001": [
            {"bid_ref": "BID-2025A1", "provider": "AutoSpares Kenya Ltd",    "brand": "Toyota Genuine",  "condition": "New (Genuine OEM)",   "unit_price": 12_500.0, "lead_days": 3, "warranty": "6 months",  "rating": 4.5, "submitted": "2025-07-15 09:15"},
            {"bid_ref": "BID-2025A2", "provider": "Parts Unlimited Nairobi", "brand": "Aftermarket",      "condition": "New (Aftermarket)",    "unit_price":  9_800.0, "lead_days": 2, "warranty": "3 months",  "rating": 3.8, "submitted": "2025-07-15 10:45"},
            {"bid_ref": "BID-2025A3", "provider": "Motospares East Africa",  "brand": "TRD / OEM",       "condition": "New (OEM Equivalent)", "unit_price": 11_200.0, "lead_days": 4, "warranty": "12 months", "rating": 4.8, "submitted": "2025-07-15 12:00"},
        ],
        "RFQ-20250715002": [
            {"bid_ref": "BID-2025B1", "provider": "AutoSpares Kenya Ltd",    "brand": "Toyota Genuine",  "condition": "New (Genuine OEM)",   "unit_price": 18_000.0, "lead_days": 3, "warranty": "6 months",  "rating": 4.5, "submitted": "2025-07-15 09:20"},
            {"bid_ref": "BID-2025B2", "provider": "Tyre & Parts Hub",        "brand": "Aftermarket",      "condition": "New (Aftermarket)",    "unit_price": 14_500.0, "lead_days": 1, "warranty": "3 months",  "rating": 3.9, "submitted": "2025-07-15 11:05"},
        ],
        "RFQ-20250714001": [
            {"bid_ref": "BID-2025C1", "provider": "SpeedParts Mombasa",      "brand": "Toyota OEM",      "condition": "New (Genuine OEM)",   "unit_price":  4_200.0, "lead_days": 1, "warranty": "6 months",  "rating": 4.2, "submitted": "2025-07-14 08:30"},
            {"bid_ref": "BID-2025C2", "provider": "Coast Auto Parts",        "brand": "Aftermarket",      "condition": "New (Aftermarket)",    "unit_price":  3_500.0, "lead_days": 2, "warranty": "3 months",  "rating": 3.5, "submitted": "2025-07-14 11:20"},
            {"bid_ref": "BID-2025C3", "provider": "Mombasa Spares Direct",   "brand": "Toyota Genuine",  "condition": "New (Genuine OEM)",   "unit_price":  4_600.0, "lead_days": 2, "warranty": "12 months", "rating": 4.7, "submitted": "2025-07-14 14:00"},
        ],
    }

    # ── RFQ selector ──────────────────────────────────────────────────
    # TODO: replace with live open-RFQ list from Delta:
    #   rfq_rows, _ = _run_sql("SELECT rfq_ref, part_description FROM main.claims.rfq_broadcasts WHERE status = 'Open' ORDER BY broadcast_date DESC")
    open_rfqs = list(_SAMPLE.keys())

    c1, c2 = st.columns([3, 1])
    rfq_ref = c1.selectbox(
        "Select RFQ Reference",
        options=["— select an RFQ —"] + open_rfqs,
        key="bid_comp_rfq",
    )
    if c2.button("🔄 Refresh", key="bid_comp_refresh", use_container_width=True):
        st.rerun()

    if rfq_ref.startswith("—"):
        st.caption("Select an RFQ reference above to load submitted bids.")
        return

    bids = [dict(b) for b in _SAMPLE.get(rfq_ref, [])]
    if not bids:
        st.warning(f"No bids received yet for **{rfq_ref}**.")
        return

    bids = _score_bids(bids)

    # ── Summary metrics ──────────────────────────────────────────────────
    prices = [b["unit_price"] for b in bids]
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Bids Received",      len(bids))
    mc2.metric("Lowest Price (KES)",  f"{min(prices):,.2f}")
    mc3.metric("Highest Price (KES)", f"{max(prices):,.2f}")
    mc4.metric("Best Score",          bids[0]["composite"])

    # ── Comparison table ─────────────────────────────────────────────────
    st.markdown(f"**{len(bids)} bid(s) for {rfq_ref}** — sorted by composite score (highest first)")
    df = pd.DataFrame([{
        "Rank":              b["rank"],
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

    # ── Score breakdown chart ─────────────────────────────────────────────
    with st.expander("📊 Score Breakdown Chart"):
        st.caption("Price Score (60 %) and Rating Score (40 %) per provider.")
        chart_df = pd.DataFrame({
            "Provider":            [b["provider"]     for b in bids],
            "Price Score (60 %)": [b["price_score"]  for b in bids],
            "Rating Score (40 %)": [b["rating_score"] for b in bids],
        }).set_index("Provider")
        st.bar_chart(chart_df)

    st.divider()
    st.markdown("### Award Decision")
    st.caption(
        "The system pre-selects the highest-scoring bid. "
        "Any override is logged to the audit trail."
    )

    bid_labels = [
        f"{b['bid_ref']} — {b['provider']}  | KES {b['unit_price']:,.2f} | {b['lead_days']}d | Score {b['composite']}"
        for b in bids
    ]

    with st.form("award_bid_form"):
        selected_label = st.selectbox(
            "Select Winning Bid *",
            options=bid_labels,
            index=0,
        )
        selected_idx = bid_labels.index(selected_label)
        is_override  = bids[selected_idx]["rank"] != 1

        if is_override:
            st.warning(
                f"⚠️ Override: **{bids[0]['bid_ref']}** ({bids[0]['provider']}, Score {bids[0]['composite']}) "
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
            "🏆 Award Bid & Notify All Providers", type="primary", use_container_width=True
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

            # TODO: UPDATE main.claims.rfq_bids SET status='Won'  WHERE bid_ref = winner['bid_ref']
            # TODO: UPDATE main.claims.rfq_bids SET status='Lost' WHERE rfq_ref = rfq_ref AND bid_ref != winner['bid_ref']
            # TODO: INSERT INTO main.claims.spare_part_orders (order_ref, rfq_ref, provider, payer, delivery_address, ...)
            # TODO: INSERT INTO main.claims.notifications for winner (Bid Won) and each loser (Bid Lost)
            # TODO: UPDATE main.claims.rfq_broadcasts SET status='Closed — Awarded' WHERE rfq_ref = rfq_ref

            st.success(
                f"**Contract Awarded — {winner['provider']}** ({winner['bid_ref']})  \n"
                f"Unit Price: **KES {winner['unit_price']:,.2f}** · "
                f"Lead time: **{winner['lead_days']} days** · "
                f"Warranty: **{winner['warranty']}** · Score: **{winner['composite']}**  \n"
                f"Order: **{order_ref}** · Payer: **{payer.split(' (')[0]}**  \n"
                f"Delivery: {delivery_address}  \n"
                f"**{len(losers)}** losing provider(s) notified."
            )
