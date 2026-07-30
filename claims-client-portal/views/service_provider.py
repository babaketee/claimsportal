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
    st.subheader("Assigned Claims")
    # TODO: Query Delta table filtered to this service provider's ID
    #   spark.sql("""
    #     SELECT claim_ref, client_name, incident_type, report_date, status, priority
    #     FROM claims.assignments
    #     WHERE provider_id = current_user_id AND status != 'Closed'
    #   """)
    sample = [
        {"Claim Ref": "CLM-20250715123456", "Client": "John Mwangi",   "Incident Type": "Motor Accident", "Date": "2025-07-15", "Status": "Under Assessment", "Priority": "High"},
        {"Claim Ref": "CLM-20250714098765", "Client": "Amina Wanjiru",  "Incident Type": "Theft",          "Date": "2025-07-14", "Status": "Awaiting Report",  "Priority": "Medium"},
    ]
    st.dataframe(sample, use_container_width=True)


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
            # TODO: Write to Delta + trigger notification to claims handler
            #   spark.sql(f"INSERT INTO claims.assessment_reports VALUES (...)")
            # TODO: Upload PDF to Unity Catalog Volume
            st.success(f"Assessment report submitted for claim **{claim_ref}**.")


# ---------------------------------------------------------------------------
# Assessor: Approve Estimate
# ---------------------------------------------------------------------------

def _approve_estimate() -> None:
    st.subheader("Approve / Reject Garage Estimate")
    st.info("Review the garage estimate and provide your decision before it is routed to accounts payable.")
    with st.form("approve_estimate"):
        c1, c2 = st.columns(2)
        claim_ref       = c1.text_input("Claim Reference Number *")
        garage_name     = c2.text_input("Garage Name *")
        estimate_amount = st.number_input("Estimate Amount (KES) *", min_value=0.0, format="%.2f")
        decision        = st.radio("Decision *", ["Approve", "Reject", "Request Revision"])
        comments        = st.text_area("Comments / Conditions for Approval")
        submitted       = st.form_submit_button("Submit Decision", type="primary", use_container_width=True)

    if submitted:
        if not claim_ref or not garage_name:
            st.error("Claim reference and garage name are required.")
        else:
            # TODO: Write decision to Delta + notify garage + route to AP if Approved
            st.success(f"Decision **{decision}** recorded for claim {claim_ref}. Garage notified.")


# ---------------------------------------------------------------------------
# Garage: Submit Estimate
# ---------------------------------------------------------------------------

def _submit_estimate() -> None:
    st.subheader("Submit Repair Estimate")
    st.info("Your estimate will be reviewed and approved by an assessor before repair work begins.")
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
            # TODO: Write to Delta + notify assigned assessor for sign-off
            # SLA: if no assessor decision within 48 h, escalate to claims manager
            st.success(
                f"Estimate submitted for **{claim_ref}**. Awaiting assessor approval (SLA: 48 hours)."
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
        additional_amount = st.number_input("Additional Amount Requested (KES) *", min_value=0.0, format="%.2f")
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
            # TODO: Write to Delta + notify claims handler for internal approval
            st.success(f"Supplementary request submitted for **{claim_ref}**. Under review.")


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
            if invoice_file is not None:
                core_api.post_document(
                    claim_ref,
                    invoice_file.name,
                    "application/pdf",
                    invoice_file.getvalue(),
                    "invoice",
                )
            # Update payment record in core system
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
            # Also update overall claim status
            core_api.update_claim_status(
                claim_ref, "Invoice Submitted",
                note=f"Invoice {invoice_number} KES {invoice_amount:,.2f}",
                actor=actor,
            )
            core_api.invalidate_claim_cache(claim_ref)
            msg = f"Invoice **{invoice_number}** for claim **{claim_ref}** submitted. Routed to accounts payable."
            if not payment_synced and core_api.is_configured():
                msg += " (Core system sync pending.)"
            st.success(msg)


# ---------------------------------------------------------------------------
# Shared: Payment Status
# ---------------------------------------------------------------------------

def _payment_status(role: str) -> None:
    st.subheader("Payment Status")
    st.info("Track the payment status for your submitted invoices and service fees.")

    # TODO: Query Delta table filtered to this provider's ID
    #   spark.sql("""
    #     SELECT claim_ref, invoice_number, service_date, amount, status,
    #            payment_date, payment_reference, notes
    #     FROM claims.payments
    #     WHERE provider_id = current_user_id
    #     ORDER BY service_date DESC
    #   """)

    if role == "garage":
        sample = [
            {
                "Claim Ref":       "CLM-20250715123456",
                "Invoice No":      "INV-2025-001",
                "Invoice Date":    "2025-07-15",
                "Amount (KES)":    "45,000.00",
                "Status":          "🟢 Payment Initiated",
                "Payment Date":    "2025-07-18",
                "Payment Ref":     "PAY-20250718001",
                "Notes":           "EFT to Equity Bank",
            },
            {
                "Claim Ref":       "CLM-20250714098765",
                "Invoice No":      "INV-2025-002",
                "Invoice Date":    "2025-07-14",
                "Amount (KES)":    "12,500.00",
                "Status":          "🔵 Under Review",
                "Payment Date":    "—",
                "Payment Ref":     "—",
                "Notes":           "Awaiting assessor sign-off",
            },
            {
                "Claim Ref":       "CLM-20250710054321",
                "Invoice No":      "INV-2025-003",
                "Invoice Date":    "2025-07-10",
                "Amount (KES)":    "78,200.00",
                "Status":          "✅ Paid",
                "Payment Date":    "2025-07-12",
                "Payment Ref":     "PAY-20250712004",
                "Notes":           "Full settlement — KCB Bank",
            },
            {
                "Claim Ref":       "CLM-20250705011111",
                "Invoice No":      "INV-2025-004",
                "Invoice Date":    "2025-07-05",
                "Amount (KES)":    "23,800.00",
                "Status":          "🟠 On Hold",
                "Payment Date":    "—",
                "Payment Ref":     "—",
                "Notes":           "Dispute raised by client",
            },
        ]
        amount_key = "Amount (KES)"

    elif role == "assessor":
        sample = [
            {
                "Claim Ref":       "CLM-20250715123456",
                "Service":         "Assessment Fee",
                "Service Date":    "2025-07-15",
                "Fee (KES)":       "8,000.00",
                "Status":          "✅ Paid",
                "Payment Date":    "2025-07-17",
                "Payment Ref":     "PAY-20250717002",
                "Notes":           "Standard assessment fee",
            },
            {
                "Claim Ref":       "CLM-20250714098765",
                "Service":         "Re-assessment Fee",
                "Service Date":    "2025-07-14",
                "Fee (KES)":       "5,000.00",
                "Status":          "🟡 Invoice Received",
                "Payment Date":    "—",
                "Payment Ref":     "—",
                "Notes":           "Awaiting finance approval",
            },
            {
                "Claim Ref":       "CLM-20250709077432",
                "Service":         "Assessment Fee",
                "Service Date":    "2025-07-09",
                "Fee (KES)":       "8,000.00",
                "Status":          "🔵 Under Review",
                "Payment Date":    "—",
                "Payment Ref":     "—",
                "Notes":           "Finance team processing",
            },
        ]
        amount_key = "Fee (KES)"

    else:  # investigator
        sample = [
            {
                "Claim Ref":       "CLM-20250715123456",
                "Service":         "Investigation Fee",
                "Service Date":    "2025-07-15",
                "Fee (KES)":       "15,000.00",
                "Status":          "🔵 Under Review",
                "Payment Date":    "—",
                "Payment Ref":     "—",
                "Notes":           "Report under review by claims manager",
            },
            {
                "Claim Ref":       "CLM-20250708012345",
                "Service":         "Investigation Fee",
                "Service Date":    "2025-07-08",
                "Fee (KES)":       "15,000.00",
                "Status":          "✅ Paid",
                "Payment Date":    "2025-07-11",
                "Payment Ref":     "PAY-20250711005",
                "Notes":           "Settled in full",
            },
            {
                "Claim Ref":       "CLM-20250630099001",
                "Service":         "Supplementary Investigation",
                "Service Date":    "2025-06-30",
                "Fee (KES)":       "8,500.00",
                "Status":          "✅ Paid",
                "Payment Date":    "2025-07-03",
                "Payment Ref":     "PAY-20250703007",
                "Notes":           "Supplementary fee approved",
            },
        ]
        amount_key = "Fee (KES)"

    st.dataframe(sample, use_container_width=True)

    # Summary metrics
    st.divider()
    total_txns = len(sample)
    paid_count = sum(1 for r in sample if "Paid" in r.get("Status", ""))
    pending_count = total_txns - paid_count
    try:
        paid_amount = sum(
            float(r[amount_key].replace(",", ""))
            for r in sample
            if "Paid" in r.get("Status", "")
        )
    except Exception:
        paid_amount = 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Transactions", total_txns)
    c2.metric("Paid", paid_count)
    c3.metric("Pending / In Progress", pending_count)
    c4.metric("Total Paid (KES)", f"{paid_amount:,.2f}")


# ---------------------------------------------------------------------------
# Investigator: Investigation Report
# ---------------------------------------------------------------------------

def _submit_investigation_report() -> None:
    st.subheader("Submit Investigation Report")
    st.info(
        "This portal contains private claim details. "
        "Handle all information in accordance with DPA 2019 and your engagement mandate."
    )
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
            # TODO: Write to Delta + notify claims handler
            # TODO: Log action to audit table (timestamp, user, IP, claim_ref)
            st.success(f"Investigation report submitted for **{claim_ref}**. Claims handler notified.")
