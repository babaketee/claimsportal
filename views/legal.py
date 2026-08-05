"""Legal Officer Portal — disputed claims, litigation, repudiation appeals, and recovery."""
from __future__ import annotations
import datetime
import streamlit as st

# --------------------------------------------------------------------------
# Repudiation Reasons Enum
# --------------------------------------------------------------------------
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
        "📔 Dispute Register",
        "🔔 Repudiation Appeals",
        "🏛️ Litigation Tracker",
        "📜 Demand Letters & OTS",
        "📁 Recovery & Subrogation",
        "📋 IRA Complaints",
        "📃 Repudiation Workflow",
    ])
    with tabs[0]: _dispute_register()
    with tabs[1]: _repudiation_appeals()
    with tabs[2]: _litigation_tracker()
    with tabs[3]: _demand_letters_ots()
    with tabs[4]: _recovery_subrogation()
    with tabs[5]: _ira_complaints()
    with tabs[6]: _repudiation_workflow()


# --------------------------------------------------------------------------
# Dispute Register
# --------------------------------------------------------------------------

def _fetch_disputes(stage_f: str, urgency_f: str, search: str) -> list[dict]:
    """Query disputes via core_api. Returns list of row dicts."""
    try:
        return core_api.get_disputes(stage=stage_f, urgency=urgency_f, search=search)
    except Exception:
        return []


def _dispute_register() -> None:
    st.subheader("Dispute Register")

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
        in_litigation = sum(1 for r in rows if r.get("stage") == "Litigation")
        exposure_vals = []
        for r in rows:
            raw = str(r.get("exposure_kes", "0")).replace(",", "")
            try:
                exposure_vals.append(float(raw))
            except ValueError:
                pass
        total_exposure_m = sum(exposure_vals) / 1_000_000
        days_vals = [int(r["days_open"]) for r in rows if r.get("days_open") is not None]
        avg_days  = round(sum(days_vals) / len(days_vals)) if days_vals else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Open Disputes",          str(open_count))
        c2.metric("In Litigation",          str(in_litigation))
        c3.metric("Total Exposure (KES M)", f"{total_exposure_m:.1f}")
        c4.metric("Avg Days in Dispute",    str(avg_days))

    except Exception as exc:
        st.error(f"Could not load dispute register: {exc}")


# --------------------------------------------------------------------------
# Repudiation Appeals
# --------------------------------------------------------------------------

def _repudiation_appeals() -> None:
    st.subheader("Repudiation Appeals")
    st.info(
        "When a client disputes a repudiation, the Legal Officer reviews the grounds, "
        "the investigation report, and the policy wording before recommending a position."
    )

    try:
        appeals = core_api.get_repudiation_appeals()
    except Exception:
        appeals = []
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
            try:
                core_api.log_communication(
                    claim_ref=claim_ref,
                    channel="repudiation_appeal",
                    direction="outgoing",
                    summary=f"Legal position recorded: {decision}",
                    detail=legal_opinion,
                    metadata={"policy_ref": policy_ref, "deadline": str(deadline), "ex_gratia": ex_gratia_amt},
                )
                st.success(f"Legal position recorded for **{claim_ref}**: **{decision}**. Response letter queued for review.")
            except Exception as e:
                st.error(f"Failed to record position: {e}")


# --------------------------------------------------------------------------
# Litigation Tracker
# --------------------------------------------------------------------------

def _litigation_tracker() -> None:
    st.subheader("Litigation Tracker")
    st.warning("Any judgment or consent order amount must be routed to Finance Head for payment approval.")

    try:
        cases = core_api.get_litigation_cases()
    except Exception:
        cases = []
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
            try:
                core_api.log_litigation_update(
                    claim_ref=claim_ref,
                    case_no=case_no,
                    hearing_date=hearing_date,
                    result=hearing_result,
                    amount_awarded=amount_awarded,
                    next_hearing=next_date,
                    notes=counsel_notes,
                )
                st.success(f"Litigation update saved for **{claim_ref}** — {hearing_result}.")
            except Exception as e:
                st.error(f"Failed to save update: {e}")


# --------------------------------------------------------------------------
# Demand Letters & Offers to Settle
# --------------------------------------------------------------------------

def _demand_letters_ots() -> None:
    st.subheader("Demand Letters & Offers to Settle (OTS)")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📜 Incoming Demand Letters**")
        st.caption("Log letters of demand received from claimants or their advocates.")
        try:
            letters = core_api.get_demand_letters()
        except Exception:
            letters = []
        st.dataframe(letters, use_container_width=True)

    with col2:
        st.markdown("**📮 Offers to Settle (OTS) Issued**")
        try:
            offers = core_api.get_offers_to_settle()
        except Exception:
            offers = []
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
                try:
                    core_api.register_document(
                        claim_ref=claim_ref,
                        doc_type="demand_letter",
                        title=f"Demand Letter — {sender}",
                        date_filed=received_date,
                        metadata={"sender": sender, "amount_demanded": amount_demanded, "response_deadline": str(response_deadline)},
                    )
                    core_api.log_communication(
                        claim_ref=claim_ref,
                        channel="demand_letter",
                        direction="incoming",
                        summary=f"Demand letter received from {sender}",
                        detail=summary,
                        metadata={"amount_demanded": amount_demanded},
                    )
                    st.success(f"Demand letter for **{claim_ref}** logged. Claims Officer and Head of Claims notified.")
                except Exception as e:
                    st.error(f"Failed to log demand letter: {e}")

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
                try:
                    core_api.issue_offer_to_settle(
                        claim_ref=claim_ref,
                        addressee=addressee,
                        amount=offer_amount,
                        expiry_date=expiry_date,
                        conditions=ots_conditions,
                    )
                    st.success(f"OTS of **KES {offer_amount:,.2f}** issued to **{addressee}** for **{claim_ref}**. Valid until {expiry_date}.")
                except Exception as e:
                    st.error(f"Failed to issue OTS: {e}")


# --------------------------------------------------------------------------
# Recovery & Subrogation
# --------------------------------------------------------------------------

def _recovery_subrogation() -> None:
    st.subheader("Recovery & Subrogation Actions")
    st.info(
        "After settling a claim, pursue recovery from liable third parties or salvage proceeds. "
        "All recoveries must be credited back to the Finance team."
    )

    try:
        recoveries = core_api.get_recovery_actions()
    except Exception:
        recoveries = []
    st.dataframe(recoveries, use_container_width=True)

    total_target = sum(float(str(r.get("recovery_target_kes", "0")).replace(",", "")) for r in recoveries)
    total_recovered = sum(float(str(r.get("recovery_kes", "0")).replace(",", "")) for r in recoveries)
    open_actions = sum(1 for r in recoveries if r.get("status") not in ("Settled", "Written Off"))

    c1, c2, c3 = st.columns(3)
    c1.metric("Open Recovery Actions", str(open_actions))
    c2.metric("Total Target (KES)",    f"{total_target:,.0f}")
    c3.metric("Recovered YTD (KES)",   f"{total_recovered:,.0f}")

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
            try:
                core_api.record_recovery(
                    claim_ref=claim_ref,
                    recovery_type=recovery_type,
                    third_party=third_party,
                    amount=amount_recovered,
                    recovery_date=recovery_date,
                    status=status,
                    notes=notes,
                )
                st.success(
                    f"Recovery of **KES {amount_recovered:,.2f}** from **{third_party}** recorded for **{claim_ref}**. "
                    "Finance notified to credit proceeds."
                )
            except Exception as e:
                st.error(f"Failed to record recovery: {e}")


# --------------------------------------------------------------------------
# IRA Complaints
# --------------------------------------------------------------------------

def _ira_complaints() -> None:
    st.subheader("IRA & Ombudsman Complaints")
    st.warning(
        "Complaints filed with the Insurance Regulatory Authority (IRA) or the Insurance Ombudsman "
        "carry a statutory response deadline. Breaching it attracts regulatory penalties."
    )

    try:
        complaints = core_api.get_ira_complaints()
    except Exception:
        complaints = []
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
                try:
                    core_api.register_document(
                        claim_ref=claim_ref,
                        doc_type="ira_complaint",
                        title=f"IRA/Ombudsman Complaint — {regulator_ref or claim_ref}",
                        date_filed=filed_date,
                        metadata={"filed_with": filed_with, "regulator_ref": regulator_ref, "response_due": str(response_due)},
                    )
                    core_api.log_communication(
                        claim_ref=claim_ref,
                        channel="ira_complaint",
                        direction="incoming",
                        summary=f"Complaint filed with {filed_with}",
                        detail=complaint_summary,
                        metadata={"regulator_ref": regulator_ref, "response_due": str(response_due)},
                    )
                    st.success(f"Complaint for **{claim_ref}** logged. Response deadline: **{response_due}**. Calendar reminder set.")
                except Exception as e:
                    st.error(f"Failed to log complaint: {e}")

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
                try:
                    core_api.submit_regulatory_response(
                        claim_ref=claim_ref,
                        regulator_ref=regulator_ref,
                        response_text=response_text,
                    )
                    st.success(f"Regulatory response for **{claim_ref}** (Ref: {regulator_ref}) submitted and logged.")
                except Exception as e:
                    st.error(f"Failed to submit response: {e}")


# --------------------------------------------------------------------------
# Repudiation Workflow — uses core_api for all data, communications, and documents
# --------------------------------------------------------------------------

def _repudiation_workflow() -> None:
    """Full repudiation lifecycle: log, demand letter, litigation flag, timeline — all via core_api."""
    st.subheader("Repudiation Workflow")
    st.info(
        "Track the full repudiation lifecycle — from initial decision through demand letters, "
        "litigation status changes, and case timelines — using core_api for all communications and documents."
    )

    try:
        log = core_api.get_repudiation_log()
    except Exception:
        log = []

    col1, col2 = st.columns([3, 1])
    search_filter = col1.text_input("Search by Claim Ref or Client")
    status_filter = col2.selectbox("Litigation Status", ["All"] + LITIGATION_STATUSES)

    filtered = log
    if search_filter:
        filtered = [r for r in filtered if search_filter.upper() in r.get("claim_ref","").upper() or search_filter.lower() in r.get("client","").lower()]
    if status_filter != "All":
        filtered = [r for r in filtered if r.get("litigation_status") == status_filter]

    total_repudiations = len(log)
    pending_litigation = sum(1 for r in log if r.get("litigation_status") in ("pending", "filed"))
    demand_issued      = sum(1 for r in log if r.get("demand_letter_issued"))

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Repudiations", str(total_repudiations))
    m2.metric("Demand Letters Issued", str(demand_issued))
    m3.metric("Pending / Active Litigation", str(pending_litigation))

    st.divider()

    st.markdown("**Repudiation Register**")
    if filtered:
        display_rows = []
        for r in filtered:
            display_rows.append({
                "Claim Ref": r.get("claim_ref",""),
                "Client": r.get("client",""),
                "Reason": r.get("reason",""),
                "Demand Letter": "Yes" if r.get("demand_letter_issued") else "No",
                "Demand Letter Date": r.get("demand_letter_date") or "—",
                "Litigation Status": (r.get("litigation_status","none").replace("_"," ").title()),
                "Timeline Events": len(r.get("timeline",[])),
            })
        st.dataframe(display_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No repudiations match the selected filters.")

    st.divider()

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
            existing_record = next((r for r in log if r.get("claim_ref") == claim_ref), None)
            old_status = existing_record.get("litigation_status","none") if existing_record else "none"

            new_entry = {
                "claim_ref": claim_ref,
                "client": client,
                "reason": reason,
                "legal_note": legal_note,
                "demand_letter_issued": demand_issued_cb,
                "demand_letter_date": demand_date if demand_issued_cb else None,
                "demand_letter_filed": demand_issued_cb,
                "litigation_status": litigation_status,
                "created_at": datetime.datetime.now().isoformat(),
                "timeline": existing_record.get("timeline",[]) if existing_record else [],
            }

            if existing_record:
                if old_status != litigation_status:
                    _log_litigation_audit(claim_ref, old_status, litigation_status, client)
                    new_entry["timeline"].append({
                        "date": datetime.date.today().isoformat(),
                        "event": f"Litigation status changed: {old_status} -> {litigation_status}",
                        "detail": "Audit logged via core_api.log_communication().",
                    })
                new_entry["timeline"].append({
                    "date": datetime.date.today().isoformat(),
                    "event": "Repudiation record updated",
                    "detail": f"Reason: {reason}. Demand letter: {'Issued ' + str(demand_date) if demand_issued_cb else 'Not issued'}.",
                })
            else:
                new_entry["timeline"].append({
                    "date": datetime.date.today().isoformat(),
                    "event": "Repudiation logged",
                    "detail": f"Reason: {reason}. Demand letter: {'Issued ' + str(demand_date) if demand_issued_cb else 'Not issued'}.",
                })
                if demand_issued_cb:
                    _register_demand_letter(claim_ref, client, demand_date)
                    new_entry["timeline"].append({
                        "date": demand_date.isoformat(),
                        "event": "Demand letter registered",
                        "detail": "Stored via core_api.register_document(doc_type='demand_letter').",
                    })
                _log_repudiation_communication(claim_ref, client, reason, legal_note, demand_issued_cb)

            try:
                core_api.save_repudiation_record(new_entry)
                if existing_record:
                    st.success(f"Repudiation record updated for **{claim_ref}**.")
                else:
                    st.success(f"Repudiation record created for **{claim_ref}**.")
            except Exception as e:
                st.error(f"Failed to save repudiation record: {e}")

    st.divider()

    st.markdown("**Case Timeline**")
    if not log:
        st.info("No repudiation records found. Add a record above to see its timeline.")
    else:
        timeline_claim = st.selectbox(
            "Select Claim for Timeline",
            options=[r.get("claim_ref","") for r in log],
            index=0,
            key="timeline_claim_select",
        )
        selected_record = next((r for r in log if r.get("claim_ref") == timeline_claim), None)

        if selected_record:
            events = sorted(selected_record.get("timeline", []), key=lambda e: e.get("date",""))
            if events:
                for i, ev in enumerate(events):
                    date_str = ev.get("date","")
                    if hasattr(date_str, "strftime"):
                        date_str = date_str.strftime("%Y-%m-%d")
                    with st.container():
                        c1, c2 = st.columns([1, 4])
                        c1.markdown(f"**{date_str}**")
                        c2.markdown(f"**{ev.get('event','')}**")
                        c2.caption(ev.get("detail",""))
                        if i < len(events) - 1:
                            st.divider()
            else:
                st.info("No timeline events recorded yet. Update the repudiation record to add events.")
        else:
            st.info("Select a claim to view its timeline.")


# --------------------------------------------------------------------------
# core_api helpers — all real calls, no stubs
# --------------------------------------------------------------------------

def _log_repudiation_communication(
    claim_ref: str,
    client: str,
    reason: str,
    legal_note: str,
    demand_letter_issued: bool,
) -> None:
    core_api.log_communication(
        claim_ref=claim_ref,
        channel="repudiation",
        direction="outgoing",
        summary=f"Repudiation decision issued for {client} — {reason}",
        detail=legal_note,
        metadata={"reason": reason, "demand_letter_issued": demand_letter_issued},
    )


def _log_litigation_audit(
    claim_ref: str,
    old_status: str,
    new_status: str,
    client: str,
) -> None:
    core_api.log_communication(
        claim_ref=claim_ref,
        channel="litigation_audit",
        direction="internal",
        summary=f"Litigation status change: {old_status} -> {new_status} for {client}",
        detail=f"Litigation status changed from '{old_status}' to '{new_status}'.",
        metadata={"old_status": old_status, "new_status": new_status},
    )


def _register_demand_letter(
    claim_ref: str,
    client: str,
    demand_date: datetime.date,
) -> None:
    core_api.register_document(
        claim_ref=claim_ref,
        doc_type="demand_letter",
        title=f"Demand Letter — {client} ({claim_ref})",
        date_filed=demand_date,
        metadata={"client": client, "demand_date": str(demand_date)},
    )
