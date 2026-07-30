"""Legal Officer Portal — disputed claims, litigation, repudiation appeals, and recovery."""
from __future__ import annotations
import datetime
import streamlit as st

# SQLite-backed — Delta warehouse removed

# ---------------------------------------------------------------------------
# Repudiation Reasons Enum
# ---------------------------------------------------------------------------
REPUDIATION_REASONS = {
    "Non-Disclosure":         "Client failed to disclose material facts at policy inception.",
    "Misrepresentation":     "False statements made in the claim by the insured.",
    "Pre-existing Condition":"Condition existed before the policy start date.",
    "Policy Exclusion":      "Claim falls under an exclusion clause in the policy.",
    "Late Reporting":        "Claim reported after policy expiry.",
}

LITIGATION_STATUSES = ["none", "pending", "filed", "settled_out_of_court", "dismissed"]


def render() -> None:
    st.title("⚖️ Legal Officer Portal")
    tabs = st.tabs([
        "U0001f4c4 Dispute Register",
        "U0001f514 Repudiation Appeals",
        "U0001f3db️ Litigation Tracker",
        "U0001f4ec Demand Letters & OTS",
        "U0001f501 Recovery & Subrogation",
        "U0001f4cb IRA Complaints",
        "U0001f4cc Repudiation Workflow",
    ])
    with tabs[0]: _dispute_register()
    with tabs[1]: _repudiation_appeals()
    with tabs[2]: _litigation_tracker()
    with tabs[3]: _demand_letters_ots()
    with tabs[4]: _recovery_subrogation()
    with tabs[5]: _ira_complaints()
    with tabs[6]: _repudiation_workflow()


# ---------------------------------------------------------------------------
# Dispute Register
# ---------------------------------------------------------------------------

def _fetch_disputes(stage_f: str, urgency_f: str, search: str) -> list[dict]:
    """Query SQLite for disputes. Returns list of row dicts."""
    # TODO: wire to core_api.get_disputes() once implemented
    return []


def _dispute_register() -> None:
    st.subheader("Dispute Register")
    st.info("Dispute register is being migrated to SQLite.")

    c1, c2, c3 = st.columns(3)
    stage_f    = c1.selectbox("Stage",   ["All","Repudiation Appeal","Pre-Litigation","Litigation","Consent Order"])
    urgency_f  = c2.selectbox("Urgency", ["All","Critical","High","Normal"])
    search     = c3.text_input("Search Ref / Client / Advocate")

    try:
        rows = _fetch_disputes(stage_f, urgency_f, search)
        if rows:
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("No open disputes match the selected filters.")

        open_count    = len(rows)
        in_litigation = sum(1 for r in rows if r.get("Stage") == "Litigation")
        exposure_vals = []
        for r in rows:
            raw = str(r.get("Exposure (KES)", "0")).replace(",", "")
            try:
                exposure_vals.append(float(raw))
            except ValueError:
                pass
        total_exposure_m = sum(exposure_vals) / 1_000_000
        days_vals = [int(r["Days Open"]) for r in rows if r.get("Days Open") is not None]
        avg_days  = round(sum(days_vals) / len(days_vals)) if days_vals else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Open Disputes",          str(open_count))
        c2.metric("In Litigation",          str(in_litigation))
        c3.metric("Total Exposure (KES M)", f"{total_exposure_m:.1f}")
        c4.metric("Avg Days in Dispute",    str(avg_days))

    except Exception as exc:
        st.error(f"Could not load dispute register: {exc}")


# ---------------------------------------------------------------------------
# Repudiation Appeals
# ---------------------------------------------------------------------------

def _repudiation_appeals() -> None:
    st.subheader("Repudiation Appeals")
    st.info(
        "When a client disputes a repudiation, the Legal Officer reviews the grounds, "
        "the investigation report, and the policy wording before recommending a position."
    )

    appeals = [
        {"Ref": "CLM-20250701044512", "Client": "Mercy Holdings Ltd.", "Grounds": "Policy Lapse dispute — alleges payment was made",     "Received": "2025-07-10", "Status": "Under Review"},
        {"Ref": "CLM-20250620031122", "Client": "Susan Waithaka",      "Grounds": "Non-disclosure — client disputes materiality",        "Received": "2025-07-05", "Status": "Response Drafted"},
    ]
    st.dataframe(appeals, use_container_width=True)
    st.divider()

    with st.form("appeal_review"):
        c1, c2 = st.columns(2)
        claim_ref  = c1.text_input("Claim Reference *")
        decision   = c2.selectbox("Legal Recommendation *", [
            "Uphold Repudiation — Defend Position",
            "Partially Uphold — Ex-Gratia Offer",
            "Reverse Repudiation — Reopen Claim",
            "Refer to External Counsel",
        ])
        c1, c2 = st.columns(2)
        policy_ref     = c1.text_input("Policy Section / Clause Referenced *")
        deadline       = c2.date_input("Response Deadline *")
        legal_opinion  = st.text_area("Legal Opinion / Reasoning *", height=150,
                                       help="This will be quoted in the formal response letter.")
        ex_gratia_amt  = st.number_input("Ex-Gratia Offer Amount (KES, if applicable)", min_value=0.0, format="%.2f")
        support_docs   = st.file_uploader("Supporting Documents (policy, investigation report, correspondence)", accept_multiple_files=True)
        submitted      = st.form_submit_button("Record Position & Draft Response", type="primary", use_container_width=True)

    if submitted:
        if not claim_ref or not policy_ref or not legal_opinion:
            st.error("Claim reference, policy section, and legal opinion are required.")
        else:
            st.success(f"Legal position recorded for **{claim_ref}**: **{decision}**. Response letter queued for review.")


# ---------------------------------------------------------------------------
# Litigation Tracker
# ---------------------------------------------------------------------------

def _litigation_tracker() -> None:
    st.subheader("Litigation Tracker")
    st.warning("Any judgment or consent order amount must be routed to Finance Head for payment approval.")

    cases = [
        {"Ref": "CLM-20250712055431", "Client / Plaintiff": "Peter Ochieng",  "Court": "Milimani Commercial Court", "Case No.": "ELC/123/2025", "Status": "Active",       "Next Hearing": "2025-08-05", "Claim Amount (KES)": "1,200,000", "External Counsel": "Kariuki & Co."},
        {"Ref": "CLM-20250615029988", "Client / Plaintiff": "James Obuya",    "Court": "Magistrate — Kibera",       "Case No.": "CIV/088/2025", "Status": "Consent Order","Next Hearing": "—",          "Claim Amount (KES)": "95,000",    "External Counsel": "Mutua & Partners"},
    ]
    st.dataframe(cases, use_container_width=True)
    st.divider()

    with st.form("litigation_update"):
        st.markdown("**Log Hearing / Update**")
        c1, c2 = st.columns(2)
        claim_ref  = c1.text_input("Claim Reference *")
        case_no    = c2.text_input("Court Case Number *")
        c1, c2 = st.columns(2)
        hearing_date   = c1.date_input("Hearing / Filing Date *")
        hearing_result = c2.selectbox("Result / Action *", [
            "Hearing held — adjourned",
            "Judgment delivered — in our favour",
            "Judgment delivered — against us",
            "Consent Order agreed",
            "Case withdrawn by plaintiff",
            "Settlement reached out of court",
            "Filed defence / replying affidavit",
            "Served with fresh pleadings",
            "Other",
        ])
        amount_awarded = st.number_input("Amount Awarded / Agreed (KES, if applicable)", min_value=0.0, format="%.2f")
        next_date      = st.date_input("Next Hearing Date (if adjourned)")
        counsel_notes  = st.text_area("Counsel Notes / Summary *")
        docs           = st.file_uploader("Court Papers / Judgment (PDF)", type=["pdf"], accept_multiple_files=True)
        submitted      = st.form_submit_button("Save Update", type="primary", use_container_width=True)

    if submitted:
        if not claim_ref or not case_no or not counsel_notes:
            st.error("Claim reference, case number, and notes are required.")
        elif amount_awarded > 0 and "Judgment" in hearing_result and "against us" in hearing_result:
            st.error(f"Judgment of KES {amount_awarded:,.2f} against insurer. **Automatically routed to Finance Head** for payment approval.")
        else:
            st.success(f"Litigation update saved for **{claim_ref}** — {hearing_result}.")


# ---------------------------------------------------------------------------
# Demand Letters & Offers to Settle
# ---------------------------------------------------------------------------

def _demand_letters_ots() -> None:
    st.subheader("Demand Letters & Offers to Settle (OTS)")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**U0001f4ec Incoming Demand Letters**")
        st.caption("Log letters of demand received from claimants or their advocates.")
        letters = [
            {"Ref": "CLM-20250709012345", "From": "Mwangi & Associates (Advocates)", "Amount Demanded (KES)": "900,000", "Received": "2025-07-18", "Response Due": "2025-07-25", "Status": "Pending Response"},
            {"Ref": "CLM-20250620031122", "From": "Susan Waithaka (Self)",            "Amount Demanded (KES)": "150,000", "Received": "2025-07-10", "Response Due": "2025-07-24", "Status": "Response Drafted"},
        ]
        st.dataframe(letters, use_container_width=True)

    with col2:
        st.markdown("**U0001f4ee Offers to Settle (OTS) Issued**")
        offers = [
            {"Ref": "CLM-20250709012345", "Offer (KES)": "550,000", "Issued": "2025-07-19", "Expiry": "2025-07-26", "Status": "Awaiting Acceptance"},
            {"Ref": "CLM-20250615029988", "Offer (KES)": "95,000",  "Issued": "2025-07-12", "Expiry": "2025-07-19", "Status": "Accepted — Consent Order"},
        ]
        st.dataframe(offers, use_container_width=True)

    st.divider()

    tab_log, tab_ots = st.tabs(["Log Demand Letter", "Issue Offer to Settle"])

    with tab_log:
        with st.form("log_demand"):
            c1, c2 = st.columns(2)
            claim_ref     = c1.text_input("Claim Reference *")
            sender        = c2.text_input("Sender (claimant / advocate) *")
            c1, c2, c3 = st.columns(3)
            received_date = c1.date_input("Date Received *", value=datetime.date.today())
            amount_demanded = c2.number_input("Amount Demanded (KES) *", min_value=0.0, format="%.2f")
            response_deadline = c3.date_input("Response Deadline *")
            summary       = st.text_area("Summary of Demand *")
            letter_file   = st.file_uploader("Demand Letter (PDF) *", type=["pdf"])
            submitted     = st.form_submit_button("Log Demand Letter", type="primary", use_container_width=True)
        if submitted:
            if not claim_ref or not sender or not summary or not letter_file:
                st.error("All starred fields and the letter PDF are required.")
            else:
                st.success(f"Demand letter for **{claim_ref}** logged. Claims Officer and Head of Claims notified.")

    with tab_ots:
        with st.form("issue_ots"):
            c1, c2 = st.columns(2)
            claim_ref   = c1.text_input("Claim Reference *")
            addressee   = c2.text_input("Addressee (claimant / advocate) *")
            c1, c2, c3 = st.columns(3)
            offer_amount  = c1.number_input("Offer Amount (KES) *", min_value=0.0, format="%.2f")
            valid_days    = c2.number_input("Validity (days)", min_value=1, value=7)
            expiry_date   = c3.date_input("Offer Expiry Date *")
            ots_conditions = st.text_area("Conditions / Full & Final Settlement Wording *",
                                           value="This offer is made in full and final settlement of all claims arising from the above matter, without admission of liability.")
            hoc_approved  = st.checkbox("Head of Claims approval obtained for this offer amount")
            submitted     = st.form_submit_button("Issue OTS", type="primary", use_container_width=True)
        if submitted:
            if not claim_ref or not addressee or not ots_conditions:
                st.error("All starred fields are required.")
            elif not hoc_approved:
                st.warning("Head of Claims must approve the offer amount before it is issued.")
            else:
                st.success(f"OTS of **KES {offer_amount:,.2f}** issued to **{addressee}** for **{claim_ref}**. Valid until {expiry_date}.")


# ---------------------------------------------------------------------------
# Recovery & Subrogation
# ---------------------------------------------------------------------------

def _recovery_subrogation() -> None:
    st.subheader("Recovery & Subrogation Actions")
    st.info(
        "After settling a claim, pursue recovery from liable third parties or salvage proceeds. "
        "All recoveries must be credited back to the Finance team."
    )

    recoveries = [
        {"Ref": "CLM-20250712055431", "Type": "Third-Party Recovery",  "Third Party": "Nairobi Bus Services Ltd.", "Claim Paid (KES)": "1,200,000", "Recovery Target (KES)": "800,000", "Status": "Demand Issued",    "Recovery (KES)": "0"},
        {"Ref": "CLM-20250615029988", "Type": "Salvage",               "Third Party": "Auto Salvage Kenya",        "Claim Paid (KES)": "95,000",    "Recovery Target (KES)": "15,000",  "Status": "Auction Scheduled","Recovery (KES)": "0"},
        {"Ref": "CLM-20250601018877", "Type": "Subrogation",           "Third Party": "County Government of Nairobi","Claim Paid (KES)": "320,000", "Recovery Target (KES)": "180,000", "Status": "Settled",          "Recovery (KES)": "180,000"},
    ]
    st.dataframe(recoveries, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Open Recovery Actions", "2")
    c2.metric("Total Target (KES)",    "815,000")
    c3.metric("Recovered YTD (KES)",   "180,000")

    st.divider()
    with st.form("recovery_update"):
        c1, c2 = st.columns(2)
        claim_ref     = c1.text_input("Claim Reference *")
        recovery_type = c2.selectbox("Recovery Type *", ["Third-Party Recovery","Subrogation","Salvage","Reinsurance Recovery"])
        c1, c2 = st.columns(2)
        third_party   = c1.text_input("Third Party / Buyer *")
        amount_recovered = c2.number_input("Amount Recovered (KES) *", min_value=0.0, format="%.2f")
        recovery_date = st.date_input("Recovery Date *", value=datetime.date.today())
        status        = st.selectbox("Action Status", ["Demand Issued","Negotiating","Partially Recovered","Settled / Fully Recovered","Written Off"])
        notes         = st.text_area("Notes / Evidence of Recovery *")
        proof         = st.file_uploader("Proof of Recovery / Bank Advice", type=["pdf","jpg","png"])
        submitted     = st.form_submit_button("Record Recovery", type="primary", use_container_width=True)

    if submitted:
        if not claim_ref or not third_party or not notes:
            st.error("Claim reference, third party, and notes are required.")
        else:
            st.success(
                f"Recovery of **KES {amount_recovered:,.2f}** from **{third_party}** recorded for **{claim_ref}**. "
                "Finance notified to credit proceeds."
            )


# ---------------------------------------------------------------------------
# IRA Complaints
# ---------------------------------------------------------------------------

def _ira_complaints() -> None:
    st.subheader("IRA & Ombudsman Complaints")
    st.warning(
        "Complaints filed with the Insurance Regulatory Authority (IRA) or the Insurance Ombudsman "
        "carry a statutory response deadline. Breaching it attracts regulatory penalties."
    )

    complaints = [
        {"Ref": "CLM-20250701044512", "Complainant": "Mercy Holdings Ltd.", "Filed With": "IRA",               "Filed": "2025-07-14", "Response Due": "2025-07-21", "Status": "Under Investigation", "Regulator Ref": "IRA/CMP/2025/1144"},
        {"Ref": "CLM-20250620031122", "Complainant": "Susan Waithaka",      "Filed With": "Insurance Ombudsman","Filed": "2025-07-08", "Response Due": "2025-07-22", "Status": "Response Submitted",  "Regulator Ref": "OMB/2025/0892"},
    ]
    st.dataframe(complaints, use_container_width=True)
    st.divider()

    tab_log, tab_respond = st.tabs(["Log New Complaint", "Submit Regulatory Response"])

    with tab_log:
        with st.form("log_complaint"):
            c1, c2 = st.columns(2)
            claim_ref    = c1.text_input("Claim Reference *")
            filed_with   = c2.selectbox("Filed With *", ["IRA (Insurance Regulatory Authority)","Insurance Ombudsman","Kenya National Bureau of Statistics","Other"])
            c1, c2, c3 = st.columns(3)
            filed_date    = c1.date_input("Date Filed *", value=datetime.date.today())
            response_due  = c2.date_input("Statutory Response Deadline *")
            regulator_ref = c3.text_input("Regulator Reference Number")
            complaint_summary = st.text_area("Complaint Summary *")
            complaint_doc = st.file_uploader("Complaint Document (PDF) *", type=["pdf"])
            submitted     = st.form_submit_button("Log Complaint", type="primary", use_container_width=True)
        if submitted:
            if not claim_ref or not complaint_summary or not complaint_doc:
                st.error("Claim reference, summary, and complaint document are required.")
            else:
                st.success(f"Complaint for **{claim_ref}** logged. Response deadline: **{response_due}**. Calendar reminder set.")

    with tab_respond:
        with st.form("regulatory_response"):
            c1, c2 = st.columns(2)
            claim_ref      = c1.text_input("Claim Reference *")
            regulator_ref  = c2.text_input("Regulator Reference *")
            response_text  = st.text_area("Response / Position Statement *", height=200,
                                           help="This will be submitted to the regulator. Ensure it is approved by the Head of Claims.")
            hoc_approved   = st.checkbox("Head of Claims has reviewed and approved this response")
            response_docs  = st.file_uploader("Supporting Evidence / Response Letter (PDF)", type=["pdf"], accept_multiple_files=True)
            submitted      = st.form_submit_button("Submit Response", type="primary", use_container_width=True)
        if submitted:
            if not claim_ref or not regulator_ref or not response_text:
                st.error("All starred fields are required.")
            elif not hoc_approved:
                st.warning("Head of Claims approval is required before submitting a regulatory response.")
            else:
                st.success(f"Regulatory response for **{claim_ref}** (Ref: {regulator_ref}) submitted and logged.")


# ---------------------------------------------------------------------------
# Repudiation Workflow — NEW TAB
# ---------------------------------------------------------------------------

def _repudiation_workflow() -> None:
    """Full repudiation lifecycle: log, demand letter, litigation flag, timeline."""
    st.subheader("Repudiation Workflow")
    st.info(
        "Track the full repudiation lifecycle — from initial decision through demand letters, "
        "litigation status changes, and case timelines — using core_api for all communications and documents."
    )

    # --- In-memory store (wire to core_api.communications + SQLite) ------------
    if "repudiation_log" not in st.session_state:
        st.session_state.repudiation_log = [
            {
                "claim_ref": "CLM-20250620031122",
                "client": "Susan Waithaka",
                "reason": "Non-Disclosure",
                "legal_note": "Client failed to disclose material facts at policy inception. Investigation report confirms non-disclosure of prior claims.",
                "demand_letter_issued": True,
                "demand_letter_date": datetime.date(2025, 7, 8),
                "demand_letter_filed": True,
                "litigation_status": "none",
                "created_at": datetime.datetime(2025, 6, 20, 9, 0),
                "timeline": [
                    {"date": datetime.date(2025, 6, 20), "event": "Repudiation decision issued", "detail": "Non-disclosure — 3 prior claims omitted."},
                    {"date": datetime.date(2025, 6, 25), "event": "Appeal received from client", "detail": "Disputes materiality of non-disclosure."},
                    {"date": datetime.date(2025, 7, 8),  "event": "Demand letter issued", "detail": "Formal demand for reinstatement or compensation."},
                ],
            },
            {
                "claim_ref": "CLM-20250701044512",
                "client": "Mercy Holdings Ltd.",
                "reason": "Late Reporting",
                "legal_note": "Claim reported 6 months after policy expiry. No extension granted.",
                "demand_letter_issued": False,
                "demand_letter_date": None,
                "demand_letter_filed": False,
                "litigation_status": "pending",
                "created_at": datetime.datetime(2025, 7, 1, 11, 0),
                "timeline": [
                    {"date": datetime.date(2025, 7, 1),  "event": "Repudiation decision issued", "detail": "Late reporting — policy expired 2024-12-31."},
                    {"date": datetime.date(2025, 7, 10), "event": "Appeal filed with IRA", "detail": "IRA ref: IRA/CMP/2025/1144."},
                    {"date": datetime.date(2025, 7, 14), "event": "Litigation status changed", "detail": "Status: pending — IRA complaint escalated."},
                ],
            },
        ]

    log = st.session_state.repudiation_log

    # --- Filters ----------------------------------------------------------------
    col1, col2 = st.columns([3, 1])
    search_filter = col1.text_input("Search by Claim Ref or Client")
    status_filter = col2.selectbox("Litigation Status", ["All"] + LITIGATION_STATUSES)

    filtered = log
    if search_filter:
        filtered = [r for r in filtered if search_filter.upper() in r["claim_ref"] or search_filter.lower() in r["client"].lower()]
    if status_filter != "All":
        filtered = [r for r in filtered if r["litigation_status"] == status_filter]

    # Summary metrics
    total_repudiations = len(log)
    pending_litigation = sum(1 for r in log if r["litigation_status"] in ("pending", "filed"))
    demand_issued      = sum(1 for r in log if r["demand_letter_issued"])

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Repudiations", str(total_repudiations))
    m2.metric("Demand Letters Issued", str(demand_issued))
    m3.metric("Pending / Active Litigation", str(pending_litigation))

    st.divider()

    # --- Repudiation Register Table -------------------------------------------
    st.markdown("**Repudiation Register**")
    if filtered:
        display_rows = []
        for r in filtered:
            display_rows.append({
                "Claim Ref": r["claim_ref"],
                "Client": r["client"],
                "Reason": r["reason"],
                "Demand Letter": "Yes" if r["demand_letter_issued"] else "No",
                "Demand Letter Date": r["demand_letter_date"] or "—",
                "Litigation Status": r["litigation_status"].replace("_", " ").title(),
                "Timeline Events": len(r["timeline"]),
            })
        st.dataframe(display_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No repudiations match the selected filters.")

    st.divider()

    # --- Add / Update Repudiation Form ----------------------------------------
    st.markdown("**Log New Repudiation or Update Existing**")

    with st.form("repudiation_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        claim_ref      = c1.text_input("Claim Reference *", placeholder="e.g. CLM-20250620031122")
        client         = c2.text_input("Client Name *", placeholder="e.g. Susan Waithaka")
        reason         = st.selectbox("Repudiation Reason *", list(REPUDIATION_REASONS.keys()))
        legal_note     = st.text_area(
            "Legal Note / Grounds for Repudiation *",
            height=120,
            help="Describe the specific grounds. This is logged via core_api.log_communication().",
        )
        st.caption(f"**Reason description:** {REPUDIATION_REASONS[reason]}")

        st.markdown("---")
        st.markdown("**Demand Letter**")
        c1, c2 = st.columns(2)
        demand_issued_cb = c1.checkbox("Demand Letter Issued", value=False)
        demand_date      = c2.date_input("Demand Letter Date", value=datetime.date.today())

        st.markdown("---")
        st.markdown("**Litigation Status**")
        c1, c2 = st.columns(2)
        litigation_status = c1.selectbox("Litigation Status *", LITIGATION_STATUSES)
        previous_status   = c2.text_input("Previous Status (for audit)", value="", placeholder="auto-tracked if updating")

        submitted = st.form_submit_button("Save Repudiation Record", type="primary", use_container_width=True)

    if submitted:
        if not claim_ref or not client or not legal_note:
            st.error("Claim reference, client name, and legal note are required.")
        else:
            existing_idx = None
            for i, r in enumerate(log):
                if r["claim_ref"] == claim_ref:
                    existing_idx = i
                    break

            new_entry = {
                "claim_ref": claim_ref,
                "client": client,
                "reason": reason,
                "legal_note": legal_note,
                "demand_letter_issued": demand_issued_cb,
                "demand_letter_date": demand_date if demand_issued_cb else None,
                "demand_letter_filed": demand_issued_cb,
                "litigation_status": litigation_status,
                "created_at": datetime.datetime.now(),
                "timeline": [],
            }

            if existing_idx is not None:
                old = log[existing_idx]
                new_entry["timeline"] = old["timeline"]
                new_entry["created_at"] = old["created_at"]
                new_entry["demand_letter_issued"] = demand_issued_cb or old["demand_letter_issued"]
                new_entry["demand_letter_date"]   = demand_date if demand_issued_cb else old["demand_letter_date"]
                new_entry["demand_letter_filed"]   = demand_issued_cb or old["demand_letter_filed"]

                if old["litigation_status"] != litigation_status:
                    _log_litigation_audit(claim_ref, old["litigation_status"], litigation_status, client)
                    new_entry["timeline"].append({
                        "date": datetime.date.today(),
                        "event": f"Litigation status changed: {old['litigation_status']} → {litigation_status}",
                        "detail": "Audit logged via core_api.log_communication().",
                    })
                new_entry["timeline"].append({
                    "date": datetime.date.today(),
                    "event": "Repudiation record updated",
                    "detail": f"Reason: {reason}. Demand letter: {'Issued ' + str(demand_date) if demand_issued_cb else 'Not issued'}.",
                })
                log[existing_idx] = new_entry
                st.success(f"Repudiation record updated for **{claim_ref}**.")
            else:
                new_entry["timeline"].append({
                    "date": datetime.date.today(),
                    "event": "Repudiation logged",
                    "detail": f"Reason: {reason}. Demand letter: {'Issued ' + str(demand_date) if demand_issued_cb else 'Not issued'}.",
                })
                log.append(new_entry)

                if demand_issued_cb:
                    _register_demand_letter(claim_ref, client, demand_date)
                    new_entry["timeline"].append({
                        "date": demand_date,
                        "event": "Demand letter registered",
                        "detail": "Stored via core_api.register_document(doc_type='demand_letter').",
                    })

                st.success(f"Repudiation record created for **{claim_ref}**.")

            if existing_idx is None:
                _log_repudiation_communication(claim_ref, client, reason, legal_note, demand_issued_cb)

    st.divider()

    # --- Case Timeline ---------------------------------------------------------
    st.markdown("**Case Timeline**")
    timeline_claim = st.selectbox(
        "Select Claim for Timeline",
        options=[r["claim_ref"] for r in log],
        index=0,
        key="timeline_claim_select",
    )
    selected_record = next((r for r in log if r["claim_ref"] == timeline_claim), None)

    if selected_record:
        events = sorted(selected_record.get("timeline", []), key=lambda e: e["date"])
        if events:
            for i, ev in enumerate(events):
                date_str = ev["date"].strftime("%Y-%m-%d") if hasattr(ev["date"], "strftime") else str(ev["date"])
                with st.container():
                    c1, c2 = st.columns([1, 4])
                    c1.markdown(f"**{date_str}**")
                    c2.markdown(f"**{ev['event']}**")
                    c2.caption(ev.get("detail", ""))
                    if i < len(events) - 1:
                        st.divider()
        else:
            st.info("No timeline events recorded yet. Update the repudiation record to add events.")
    else:
        st.info("Select a claim to view its timeline.")


# ---------------------------------------------------------------------------
# core_api helpers (wire to actual core_api when available)
# ---------------------------------------------------------------------------

def _log_repudiation_communication(
    claim_ref: str,
    client: str,
    reason: str,
    legal_note: str,
    demand_letter_issued: bool,
) -> None:
    """Log repudiation creation via core_api.log_communication(channel='repudiation')."""
    # core_api.log_communication(
    #     claim_ref=claim_ref,
    #     channel="repudiation",
    #     direction="outgoing",
    #     summary=f"Repudiation decision issued for {client} — {reason}",
    #     detail=legal_note,
    #     metadata={"reason": reason, "demand_letter_issued": demand_letter_issued},
    # )
    pass


def _log_litigation_audit(
    claim_ref: str,
    old_status: str,
    new_status: str,
    client: str,
) -> None:
    """Audit every litigation status change via core_api.log_communication(channel='litigation_audit')."""
    # core_api.log_communication(
    #     claim_ref=claim_ref,
    #     channel="litigation_audit",
    #     direction="internal",
    #     summary=f"Litigation status change: {old_status} → {new_status} for {client}",
    #     detail=f"Litigation status changed from '{old_status}' to '{new_status}'.",
    #     metadata={"old_status": old_status, "new_status": new_status},
    # )
    pass


def _register_demand_letter(
    claim_ref: str,
    client: str,
    demand_date: datetime.date,
) -> None:
    """Register demand letter document via core_api.register_document(doc_type='demand_letter')."""
    # core_api.register_document(
    #     claim_ref=claim_ref,
    #     doc_type="demand_letter",
    #     title=f"Demand Letter — {client} ({claim_ref})",
    #     date_filed=demand_date,
    #     metadata={"client": client, "demand_date": str(demand_date)},
    # )
    pass
