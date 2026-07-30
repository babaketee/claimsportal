"""Legal Officer Portal — disputed claims, litigation, repudiation appeals, and recovery."""
from __future__ import annotations
import datetime
import streamlit as st

# SQLite-backed — Delta warehouse removed
_DISPUTES_TABLE = None


def render() -> None:
    st.title("\u2696\ufe0f Legal Officer Portal")
    tabs = st.tabs([
        "\U0001f4c4 Dispute Register",
        "\U0001f514 Repudiation Appeals",
        "\U0001f3db\ufe0f Litigation Tracker",
        "\U0001f4ec Demand Letters & OTS",
        "\U0001f501 Recovery & Subrogation",
        "\U0001f4cb IRA Complaints",
    ])
    with tabs[0]: _dispute_register()
    with tabs[1]: _repudiation_appeals()
    with tabs[2]: _litigation_tracker()
    with tabs[3]: _demand_letters_ots()
    with tabs[4]: _recovery_subrogation()
    with tabs[5]: _ira_complaints()


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
        st.markdown("**\U0001f4ec Incoming Demand Letters**")
        st.caption("Log letters of demand received from claimants or their advocates.")
        letters = [
            {"Ref": "CLM-20250709012345", "From": "Mwangi & Associates (Advocates)", "Amount Demanded (KES)": "900,000", "Received": "2025-07-18", "Response Due": "2025-07-25", "Status": "Pending Response"},
            {"Ref": "CLM-20250620031122", "From": "Susan Waithaka (Self)",            "Amount Demanded (KES)": "150,000", "Received": "2025-07-10", "Response Due": "2025-07-24", "Status": "Response Drafted"},
        ]
        st.dataframe(letters, use_container_width=True)

    with col2:
        st.markdown("**\U0001f4ee Offers to Settle (OTS) Issued**")
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
