"""Service Provider Portal — Assessors, Garages, and Investigators."""
from __future__ import annotations

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core_api  # noqa: E402

import streamlit as st

ROLE_LABELS = {
    "assessor":     "Assessor",
    "garage":       "Garage / Repairer",
    "investigator": "Investigator",
}


def render(role: str) -> None:
    st.title(f"🔧 Service Provider Portal — {ROLE_LABELS.get(role, role)}")

    if role == "assessor":
        tabs = st.tabs(["📂 Assigned Claims", "📝 Assessment Report", "✅ Approve Estimate", "💳 Payment Status"])
        with tabs[0]: _assigned_claims(role)
        with tabs[1]: _submit_assessment_report()
        with tabs[2]: _approve_estimate()
        with tabs[3]: _payment_status(role)

    elif role == "garage":
        tabs = st.tabs(["📂 My Jobs", "💰 Submit Estimate", "🔄 Supplementary Request", "🧾 Submit Invoice", "💳 Payment Status"])
        with tabs[0]: _assigned_claims(role)
        with tabs[1]: _submit_estimate()
        with tabs[2]: _request_supplementary()
        with tabs[3]: _submit_invoice()
        with tabs[4]: _payment_status(role)

    elif role == "investigator":
        tabs = st.tabs(["📂 Assigned Claims", "🔍 Investigation Report", "💳 Payment Status"])
        with tabs[0]: _assigned_claims(role)
        with tabs[1]: _submit_investigation_report()
        with tabs[2]: _payment_status(role)


# ---------------------------------------------------------------------------
# Shared: Assigned Claims
# ---------------------------------------------------------------------------

def _assigned_claims(role: str) -> None:
    """Show claims assigned to this provider, filtered by expert type."""
    expert_type = role
    st.subheader("My Assigned Jobs")

    if core_api.is_configured():
        try:
            assignments = core_api.get_assignments(expert_type=expert_type)
            my_jobs = assignments if assignments else []
        except Exception:
            my_jobs = []
    else:
        my_jobs = []

    if not my_jobs:
        st.info(f"No {expert_type} jobs assigned to you.")
        return

    for job in my_jobs:
        with st.expander(f"**{job['claim_ref']}** — {job.get('claim_type', 'N/A')} — {job['status']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Vehicle:** {job.get('vehicle', 'N/A')}")
                st.markdown(f"**Assigned:** {job.get('assigned_at', 'N/A')}")
            with col2:
                est = job.get('estimated_cost', 0)
                st.markdown(f"**Est. Cost:** KES {est:,}" if est else "**Est. Cost:** —")
                st.markdown(f"**Status:** {job['status']}")

            # Status update workflow
            next_statuses = {
                "pending": ["accepted", "rejected"],
                "accepted": ["in_progress"],
                "in_progress": ["completed"],
            }
            available = next_statuses.get(job["status"], [])
            if available:
                sel = st.selectbox("Update status", available, key=f"upd_{job['claim_ref']}")
                if st.button("Submit Update", key=f"btn_{job['claim_ref']}"):
                    if core_api.is_configured():
                        try:
                            core_api.update_job_status(
                                claim_ref=job["claim_ref"],
                                new_status=sel,
                                actor=st.session_state.get("user", expert_type),
                            )
                            st.success(f"✅ Status updated to '{sel}' for {job['claim_ref']}")
                            core_api.invalidate_claim_cache(job["claim_ref"])
                        except Exception as e:
                            st.error(f"Failed to update status: {e}")
                    else:
                        st.success(f"✅ Status updated to '{sel}' for {job['claim_ref']} (demo mode)")


# ---------------------------------------------------------------------------
# Garage: Submit Quote
# ---------------------------------------------------------------------------

def _submit_quote(claim_ref: str, provider_email: str) -> None:
    """Submit a quote for a job (used by assessor/garage/investigator)."""
    st.subheader("Submit Quote")

    with st.form(key=f"quote_form_{claim_ref}"):
        labour = st.number_input("Labour Cost (KES)", min_value=0, value=0, step=500, key=f"lab_{claim_ref}")
        parts = st.number_input("Parts Cost (KES)", min_value=0, value=0, step=500, key=f"parts_{claim_ref}")
        total = labour + parts

        # WHT auto-calc (5% for assessors/garages/investigators)
        wht = total * 0.05
        net = total - wht

        col1, col2, col3 = st.columns(3)
        with col1: st.text_input("Total", value=f"KES {total:,}", disabled=True)
        with col2: st.text_input("WHT (5%)", value=f"KES {wht:,.0f}", disabled=True)
        with col3: st.text_input("Net Quoted", value=f"KES {net:,.0f}", disabled=True)

        note = st.text_area("Quote Note", key=f"qnote_{claim_ref}")
        submitted = st.form_submit_button("Submit Quote")
        if submitted:
            if core_api.is_configured():
                try:
                    # Log communication event
                    core_api.log_communication(
                        claim_ref=claim_ref,
                        channel="quote",
                        direction="outbound",
                        summary=f"Quote submitted — KES {net:,.0f} net (labour={labour}, parts={parts}, wht={wht:,.0f})",
                        actor=provider_email,
                    )
                    # Register quote document
                    core_api.register_document(
                        claim_ref=claim_ref,
                        doc_type="quote",
                        description=f"Quote — KES {net:,.0f} net | labour={labour} parts={parts} wht={wht:,.0f} | {note}",
                        actor=provider_email,
                    )
                    st.success(f"✅ Quote submitted — KES {net:,.0f} net for {claim_ref}")
                except Exception as e:
                    st.error(f"Failed to submit quote: {e}")
            else:
                st.success(f"✅ Quote submitted — KES {net:,.0f} net for {claim_ref} (demo mode)")


# ---------------------------------------------------------------------------
# Assessor: Assessment Report
# ---------------------------------------------------------------------------

def _submit_assessment_report() -> None:
    st.subheader("Submit Assessment Report")
    with st.form("assessment_report"):
        c1, c2 = st.columns(2)
        claim_ref        = c1.text_input("Claim Reference Number *")
        assessment_date  = c2.date_input("Assessment Date *", value=datetime.date.today())
        vehicle_condition = st.selectbox(
            "Vehicle Condition *",
            ["Repairable", "Write-Off / Total Loss"],
        )
        c1, c2 = st.columns(2)
        repair_estimate  = c1.number_input("Estimated Repair Cost (KES) *", min_value=0.0, format="%.2f")
        salvage_value    = c2.number_input("Salvage Value (KES — if write-off)", min_value=0.0, format="%.2f")
        assessment_notes = st.text_area("Assessment Notes *", height=120)
        report_file      = st.file_uploader("Assessment Report (PDF) *", type=["pdf"])
        photos           = st.file_uploader("Damage Photographs", type=["jpg", "png"], accept_multiple_files=True)
        submitted        = st.form_submit_button("Submit Report", type="primary", use_container_width=True)

    if submitted:
        if not claim_ref or not assessment_notes or not report_file:
            st.error("Claim reference, notes, and the PDF report are required.")
        else:
            actor = st.session_state.get("user", "assessor")
            if core_api.is_configured():
                try:
                    core_api.post_document(
                        claim_ref,
                        report_file.name,
                        "application/pdf",
                        report_file.getvalue(),
                        "assessment_report",
                    )
                    core_api.log_communication(
                        claim_ref=claim_ref,
                        channel="assessment",
                        direction="outbound",
                        summary=f"Assessment report submitted — condition: {vehicle_condition}, repair estimate: KES {repair_estimate:,.2f}",
                        actor=actor,
                    )
                    st.success(f"Assessment report submitted for claim **{claim_ref}**.")
                except Exception as e:
                    st.error(f"Failed to submit report: {e}")
            else:
                st.success(f"Assessment report submitted for claim **{claim_ref}** (demo mode).")


# ---------------------------------------------------------------------------
# Assessor: Approve Estimate
# ---------------------------------------------------------------------------

def _approve_estimate() -> None:
    st.subheader("Approve / Reject Garage Estimate")
    with st.form("approve_estimate"):
        c1, c2 = st.columns(2)
        claim_ref       = c1.text_input("Claim Reference Number *")
        garage_name     = c2.text_input("Garage Name *")
        estimate_amount = c2.number_input("Estimate Amount (KES) *", min_value=0.0, format="%.2f")
        decision        = st.radio("Decision *", ["Approve", "Reject", "Request Revision"])
        comments        = st.text_area("Comments / Conditions for Approval")
        submitted       = st.form_submit_button("Submit Decision", type="primary", use_container_width=True)

    if submitted:
        if not claim_ref or not garage_name:
            st.error("Claim reference and garage name are required.")
        else:
            actor = st.session_state.get("user", "assessor")
            if core_api.is_configured():
                try:
                    core_api.log_communication(
                        claim_ref=claim_ref,
                        channel="decision",
                        direction="outbound",
                        summary=f"Estimate decision: {decision} — garage: {garage_name}, amount: KES {estimate_amount:,.2f}, comments: {comments}",
                        actor=actor,
                    )
                    core_api.update_claim_status(
                        claim_ref,
                        f"Estimate {decision}",
                        note=f"Garage {garage_name}: {decision} — KES {estimate_amount:,.2f}",
                        actor=actor,
                    )
                    core_api.invalidate_claim_cache(claim_ref)
                    st.success(f"Decision **{decision}** recorded for claim {claim_ref}. Garage notified.")
                except Exception as e:
                    st.error(f"Failed to record decision: {e}")
            else:
                st.success(f"Decision **{decision}** recorded for claim {claim_ref}. Garage notified (demo mode).")


# ---------------------------------------------------------------------------
# Garage: Submit Estimate
# ---------------------------------------------------------------------------

def _submit_estimate() -> None:
    st.subheader("Submit Repair Estimate")
    with st.form("garage_estimate"):
        claim_ref     = st.text_input("Claim Reference Number *")
        c1, c2, c3   = st.columns(3)
        labour_cost   = c1.number_input("Labour Cost (KES)",    min_value=0.0, format="%.2f")
        parts_cost    = c2.number_input("Parts Cost (KES)",      min_value=0.0, format="%.2f")
        total_estimate = c3.number_input("Total Estimate (KES) *", min_value=0.0, format="%.2f")
        estimate_file = st.file_uploader("Detailed Estimate (PDF) *", type=["pdf"])
        notes         = st.text_area("Additional Notes")
        submitted     = st.form_submit_button("Submit Estimate", type="primary", use_container_width=True)

    if submitted:
        if not claim_ref or not estimate_file:
            st.error("Claim reference and the estimate PDF are required.")
        else:
            actor = st.session_state.get("user", "garage")
            if core_api.is_configured():
                try:
                    core_api.post_document(
                        claim_ref,
                        estimate_file.name,
                        "application/pdf",
                        estimate_file.getvalue(),
                        "repair_estimate",
                    )
                    core_api.log_communication(
                        claim_ref=claim_ref,
                        channel="estimate",
                        direction="outbound",
                        summary=f"Repair estimate submitted — labour: KES {labour_cost:,.2f}, parts: KES {parts_cost:,.2f}, total: KES {total_estimate:,.2f}",
                        actor=actor,
                    )
                    st.success(
                        f"Estimate submitted for **{claim_ref}**. Awaiting assessor approval (SLA: 48 hours)."
                    )
                except Exception as e:
                    st.error(f"Failed to submit estimate: {e}")
            else:
                st.success(
                    f"Estimate submitted for **{claim_ref}**. Awaiting assessor approval (SLA: 48 hours) (demo mode)."
                )


# ---------------------------------------------------------------------------
# Garage: Supplementary Request
# ---------------------------------------------------------------------------

def _request_supplementary() -> None:
    st.subheader("Supplementary Approval Request")
    with st.form("supplementary"):
        c1, c2 = st.columns(2)
        claim_ref         = c1.text_input("Claim Reference Number *")
        approved_estimate = c2.number_input("Original Approved Estimate (KES)", min_value=0.0, format="%.2f")
        additional_amount = c1.number_input("Additional Amount Requested (KES) *", min_value=0.0, format="%.2f")
        reason            = st.text_area("Reason for Supplementary Request *", height=100)
        support_docs      = st.file_uploader(
            "Supporting Documents (photos, parts invoices)",
            accept_multiple_files=True,
        )
        submitted = st.form_submit_button("Submit Request", type="primary", use_container_width=True)

    if submitted:
        if not claim_ref or not reason:
            st.error("Claim reference and reason are required.")
        else:
            actor = st.session_state.get("user", "garage")
            if core_api.is_configured():
                try:
                    core_api.log_communication(
                        claim_ref=claim_ref,
                        channel="supplementary",
                        direction="outbound",
                        summary=f"Supplementary request — original: KES {approved_estimate:,.2f}, additional: KES {additional_amount:,.2f}, reason: {reason}",
                        actor=actor,
                    )
                    core_api.update_claim_status(
                        claim_ref,
                        "Supplementary Requested",
                        note=f"Additional amount: KES {additional_amount:,.2f} — {reason}",
                        actor=actor,
                    )
                    core_api.invalidate_claim_cache(claim_ref)
                    st.success(f"Supplementary request submitted for **{claim_ref}**. Under review.")
                except Exception as e:
                    st.error(f"Failed to submit request: {e}")
            else:
                st.success(f"Supplementary request submitted for **{claim_ref}**. Under review (demo mode).")


# ---------------------------------------------------------------------------
# Garage: Submit Invoice
# ---------------------------------------------------------------------------

def _submit_invoice() -> None:
    st.subheader("Submit Final Invoice")
    st.warning(
        "⚠️ Invoices require prior assessor sign-off. "
        "Submission without an approved estimate will be rejected."
    )
    with st.form("invoice"):
        c1, c2 = st.columns(2)
        claim_ref      = c1.text_input("Claim Reference Number *")
        invoice_number = c2.text_input("Invoice Number *")
        invoice_date   = c1.date_input("Invoice Date *", value=datetime.date.today())
        invoice_amount = c2.number_input("Invoice Amount (KES) *", min_value=0.0, format="%.2f")
        invoice_file   = st.file_uploader("Invoice (PDF) *", type=["pdf"])
        st.markdown("**Payment Details (for accounts payable)**")
        c1, c2 = st.columns(2)
        kra_pin      = c1.text_input("KRA PIN *")
        bank_name    = c2.text_input("Bank Name *")
        bank_account = c1.text_input("Account Number *")
        bank_branch  = c2.text_input("Branch Name")
        submitted    = st.form_submit_button("Submit Invoice", type="primary", use_container_width=True)

    if submitted:
        if not all([claim_ref, invoice_number, invoice_file, kra_pin, bank_name, bank_account]):
            st.error("All required fields must be completed.")
        else:
            actor = st.session_state.get("user", "garage")
            # Upload invoice PDF to core system
            if invoice_file is not None and core_api.is_configured():
                try:
                    core_api.post_document(
                        claim_ref,
                        invoice_file.name,
                        "application/pdf",
                        invoice_file.getvalue(),
                        "invoice",
                    )
                except Exception as e:
                    st.error(f"Failed to upload invoice: {e}")
                    return
            # Update payment record in core system
            if core_api.is_configured():
                try:
                    payment_synced = core_api.update_payment_status(claim_ref, {
                        "status":         "Invoice Received",
                        "invoice_number": invoice_number,
                        "invoice_date":   str(invoice_date),
                        "amount":         invoice_amount,
                        "kra_pin":        kra_pin,
                        "bank_name":      bank_name,
                        "bank_account":   bank_account,
                        "bank_branch":    bank_branch,
                        "submitted_by":   actor,
                        "submitted_at":   datetime.datetime.utcnow().isoformat() + "Z",
                    })
                except Exception as e:
                    st.error(f"Failed to update payment status: {e}")
                    return
                # Also update overall claim status
                core_api.update_claim_status(
                    claim_ref, "Invoice Submitted",
                    note=f"Invoice {invoice_number} KES {invoice_amount:,.2f}",
                    actor=actor,
                )
                core_api.invalidate_claim_cache(claim_ref)
                msg = f"Invoice **{invoice_number}** for claim **{claim_ref}** submitted. Routed to accounts payable."
                if not payment_synced:
                    msg += " (Core system sync pending.)"
                st.success(msg)
            else:
                st.success(
                    f"Invoice **{invoice_number}** for claim **{claim_ref}** submitted. "
                    "Routed to accounts payable (demo mode)."
                )


# ---------------------------------------------------------------------------
# Shared: Payment Status
# ---------------------------------------------------------------------------

def _payment_status(role: str) -> None:
    st.subheader("Payment Status")

    # Fetch real payment data via core_api
    if core_api.is_configured():
        try:
            payment_data = core_api.get_assignments(expert_type=role)
            if payment_data:
                st.dataframe(payment_data, use_container_width=True)
                total_txns = len(payment_data)
                paid_count = sum(1 for r in payment_data if r.get("status", "").lower() == "paid")
                pending_count = total_txns - paid_count
                try:
                    paid_amount = sum(float(r.get("amount") or r.get("estimated_cost") or 0) for r in payment_data if r.get("status", "").lower() == "paid")
                except Exception:
                    paid_amount = 0.0
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Transactions", total_txns)
                c2.metric("Paid", paid_count)
                c3.metric("Pending / In Progress", pending_count)
                c4.metric("Total Paid (KES)", f"{paid_amount:,.2f}")
            else:
                st.info(f"No payment records found for your account.")
        except Exception as e:
            st.error(f"Failed to load payment status: {e}")
    else:
        st.info("Payment tracking is not available in demo mode.")


# ---------------------------------------------------------------------------
# Investigator: Investigation Report
# ---------------------------------------------------------------------------

def _submit_investigation_report() -> None:
    st.subheader("Submit Investigation Report")
    with st.form("investigation"):
        c1, c2 = st.columns(2)
        claim_ref   = c1.text_input("Claim Reference Number *")
        _           = c2.empty()  # spacer
        c1, c2      = st.columns(2)
        period_start = c1.date_input("Investigation Start Date")
        period_end   = c2.date_input("Investigation End Date")
        findings     = st.text_area("Key Findings *", height=150)
        recommendation = st.selectbox(
            "Recommendation *",
            [
                "Claim Valid — Proceed to Settlement",
                "Claim Repudiated — Refer to Legal",
                "Further Investigation Required",
            ],
        )
        report_file = st.file_uploader("Full Investigation Report (PDF) *", type=["pdf"])
        submitted   = st.form_submit_button("Submit Report", type="primary", use_container_width=True)

    if submitted:
        if not claim_ref or not findings or not report_file:
            st.error("Claim reference, findings, and the PDF report are required.")
        else:
            actor = st.session_state.get("user", "investigator")
            if core_api.is_configured():
                try:
                    core_api.post_document(
                        claim_ref,
                        report_file.name,
                        "application/pdf",
                        report_file.getvalue(),
                        "investigation_report",
                    )
                    core_api.log_communication(
                        claim_ref=claim_ref,
                        channel="investigation",
                        direction="outbound",
                        summary=f"Investigation report submitted — recommendation: {recommendation}",
                        actor=actor,
                    )
                    core_api.update_claim_status(
                        claim_ref,
                        "Investigation Submitted",
                        note=f"Recommendation: {recommendation} — findings: {findings[:200]}",
                        actor=actor,
                    )
                    core_api.invalidate_claim_cache(claim_ref)
                    st.success(f"Investigation report submitted for **{claim_ref}**. Claims handler notified.")
                except Exception as e:
                    st.error(f"Failed to submit report: {e}")
            else:
                st.success(f"Investigation report submitted for **{claim_ref}**. Claims handler notified (demo mode).")
