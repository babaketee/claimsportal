"""Tests for core_api module-level functions and CoreAPI class.

Covers: claim CRUD, status history, reserves, diary, communications,
expert assignments, documents, settlements, payments, audit, SLA,
and the module-level wrapper functions used by views and the seed script.
"""
from __future__ import annotations

import pytest

import core_api
from core_api import (
    CoreAPI,
    core_api as core_api_instance,
    create_claim, get_claim, get_claims, update_claim_status,
    record_status_change, get_timeline,
    set_reserve, approve_reserve, get_reserves, get_total_reserves,
    add_diary_entry, complete_diary_entry, get_diary_entries, get_overdue_entries,
    log_communication, get_communications,
    assign_expert, update_assignment_status, get_assignments,
    register_document, get_documents,
    recommend_settlement, approve_settlement, mark_settlement_paid, get_settlements,
    update_payment_status,
    is_configured, invalidate_claim_cache, post_claim, post_document,
    send_message, get_disputes, add_dispute, log_audit, get_audit_log,
    get_sla_status, update_job_status,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def test_is_configured_default_false(capi):
    """When CORE_API_BASE_URL is empty, is_configured returns False."""
    assert capi.is_configured() is False


def test_is_configured_true(monkeypatch):
    """When CORE_API_BASE_URL is set, is_configured returns True."""
    monkeypatch.setattr(core_api, "_CORE_API_BASE_URL", "https://core.example.com")
    assert core_api.is_configured() is True


def test_module_level_is_configured():
    assert isinstance(is_configured(), bool)


# ---------------------------------------------------------------------------
# Claim CRUD
# ---------------------------------------------------------------------------

def test_create_and_get_claim(capi):
    data = dict(
        claim_ref="CLM-TEST-001",
        policy_number="POL-123",
        id_number="12345678",
        vehicle_reg="KCA 123A",
        phone="0712345678",
        incident_date="2025-01-01",
        incident_type="Motor Bumper",
        description="Rear bumper damaged",
        submitted_by="tester@example.com",
        estimated_amount=50000,
    )
    assert capi.create_claim(**data) is True
    claim = capi.get_claim("CLM-TEST-001")
    assert claim is not None
    assert claim["claim_ref"] == "CLM-TEST-001"
    assert claim["vehicle_reg"] == "KCA 123A"
    assert claim["estimated_amount"] == 50000.0


def test_get_claim_not_found(capi):
    assert capi.get_claim("CLM-NONEXISTENT") is None


def test_get_claims_empty(capi):
    claims = capi.get_claims()
    assert claims == []


def test_get_claims_after_create(capi):
    capi.create_claim(claim_ref="CLM-TEST-001", incident_type="Motor", submitted_by="test")
    capi.create_claim(claim_ref="CLM-TEST-002", incident_type="Fire", submitted_by="test")
    all_claims = get_claims()
    assert len(all_claims) == 2


def test_get_claims_with_status_filter(capi):
    capi.create_claim(claim_ref="CLM-A", incident_type="Motor", submitted_by="t")
    capi.create_claim(claim_ref="CLM-B", incident_type="Fire", submitted_by="t")
    capi.update_claim_status("CLM-B", "Settled", changed_by="test")
    submitted = get_claims(status_filter="Submitted")
    assert len(submitted) == 1
    assert submitted[0]["claim_ref"] == "CLM-A"


# ---------------------------------------------------------------------------
# Status history
# ---------------------------------------------------------------------------

def test_update_claim_status(capi):
    capi.create_claim(claim_ref="CLM-STAT-001", submitted_by="test")
    assert capi.update_claim_status("CLM-STAT-001", "Assigned", changed_by="officer")
    claim = capi.get_claim("CLM-STAT-001")
    assert claim["status"] == "Assigned"


def test_record_status_change_returns_event_id(capi):
    event_id = capi.record_status_change("CLM-STAT-002", "Assigned", from_status="Submitted", changed_by="agent")
    assert event_id.startswith("EVT-")


def test_get_timeline(capi):
    capi.create_claim(claim_ref="CLM-TL-001", submitted_by="test")
    capi.update_claim_status("CLM-TL-001", "Assigned", changed_by="officer")
    capi.update_claim_status("CLM-TL-001", "Assessment", changed_by="officer")
    timeline = get_timeline("CLM-TL-001")
    assert isinstance(timeline, list)
    assert len(timeline) >= 2


# ---------------------------------------------------------------------------
# Reserves
# ---------------------------------------------------------------------------

def test_set_and_approve_reserve(capi):
    reserve_id = set_reserve("CLM-RES-001", "initial", 50000, "assessment", "officer")
    assert reserve_id.startswith("RSV-")
    assert approve_reserve(reserve_id, "hoc@insure.demo") is True

    reserves_df = get_reserves("CLM-RES-001")
    assert len(reserves_df) == 1
    assert reserves_df.iloc[0]["status"] == "approved"

    total = get_total_reserves("CLM-RES-001")
    assert total == 50000.0


def test_reserve_rejects_zero_amount(capi):
    result = set_reserve("CLM-RES-002", "initial", 0, "test", "officer")
    assert result is None


# ---------------------------------------------------------------------------
# Diary entries
# ---------------------------------------------------------------------------

def test_diary_entry_lifecycle(capi):
    entry_id = add_diary_entry("CLM-DRY-001", "Review documents", "2025-12-31", "officer", "high", "officer")
    assert entry_id.startswith("DRY-")

    entries = get_diary_entries("CLM-DRY-001")
    assert len(entries) == 1
    assert entries.iloc[0]["task"] == "Review documents"
    assert entries.iloc[0]["priority"] == "high"

    assert complete_diary_entry(entry_id) is True

    entries_after = get_diary_entries("CLM-DRY-001")
    assert entries_after.iloc[0]["status"] == "done"


# ---------------------------------------------------------------------------
# Communications
# ---------------------------------------------------------------------------

def test_log_communication(capi):
    comm_id = log_communication(
        "CLM-COMM-001", "sms", "outbound",
        "Acknowledgement sent", "officer",
        contact_name="John Mwangi", contact_phone="0711111111",
    )
    assert comm_id.startswith("COM-")

    comms = get_communications("CLM-COMM-001")
    assert len(comms) == 1
    assert comms.iloc[0]["channel"] == "sms"
    assert comms.iloc[0]["direction"] == "outbound"
    assert comms.iloc[0]["contact_name"] == "John Mwangi"


# ---------------------------------------------------------------------------
# Expert assignments
# ---------------------------------------------------------------------------

def test_assign_and_update_expert(capi):
    assignment_id = assign_expert(
        "CLM-EXP-001", "garage", "Kiambu Auto Works", "0711234567",
        "Kiambu Auto Works Ltd", "officer@insure.demo", 45000,
        "Rear bumper repair",
    )
    assert assignment_id.startswith("ASN-")

    asns = get_assignments("CLM-EXP-001")
    assert len(asns) == 1
    assert asns.iloc[0]["expert_type"] == "garage"

    assert update_assignment_status(assignment_id, "completed", 42000) is True
    asns_after = get_assignments("CLM-EXP-001")
    assert asns_after.iloc[0]["status"] == "completed"
    assert asns_after.iloc[0]["actual_cost"] == 42000


def test_update_job_status(capi):
    assign_expert("CLM-EXP-002", "garage", "Test Garage", "0700000000",
                  "Test Garage Ltd", "officer", 0, "")
    result = update_job_status("CLM-EXP-002", "accepted", actor="garage")
    assert result is True
    assignments = core_api.get_assignments("CLM-EXP-002")
    assert assignments.iloc[0]["status"] == "accepted"


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def test_register_and_get_documents(capi):
    doc_id = register_document(
        "CLM-DOC-001", "assessment_report", "report.pdf",
        1024, "application/pdf", "assessor@example.com",
        core_doc_id="DOC-123", note="Initial assessment",
    )
    assert doc_id.startswith("DOC-")

    docs = get_documents("CLM-DOC-001")
    assert len(docs) == 1
    assert docs.iloc[0]["doc_type"] == "assessment_report"
    assert docs.iloc[0]["version"] == 1


def test_document_version_increment(capi):
    register_document("CLM-DOC-002", "quote", "q1.pdf", 100, "application/pdf", "garage")
    register_document("CLM-DOC-002", "quote", "q2.pdf", 200, "application/pdf", "garage")
    docs = get_documents("CLM-DOC-002")
    assert len(docs) == 2
    assert set(docs["version"]) == {1, 2}


# ---------------------------------------------------------------------------
# Settlements
# ---------------------------------------------------------------------------

def test_recommend_and_approve_settlement(capi):
    settlement_id = recommend_settlement(
        "CLM-STL-001", 100000, "John Mwangi", "insured",
        "officer@insure.demo", wht_rate=0.05,
    )
    assert settlement_id.startswith("STL-")

    stl = core_api.get_settlements("CLM-STL-001")
    assert len(stl) == 1
    assert stl.iloc[0]["amount"] == 100000
    assert stl.iloc[0]["wht_amount"] == 5000
    assert stl.iloc[0]["net_amount"] == 95000

    assert approve_settlement(settlement_id, "hoc@insure.demo") is True
    assert mark_settlement_paid(settlement_id, "EFT-2025-001") is True
    stl_after = core_api.get_settlements("CLM-STL-001")
    assert stl_after.iloc[0]["status"] == "paid"


# ---------------------------------------------------------------------------
# Payment status (service_provider.py compatibility)
# ---------------------------------------------------------------------------

def test_update_payment_status(capi):
    data = {
        "status": "Invoice Received",
        "invoice_number": "INV-2025-001",
        "invoice_date": "2025-07-15",
        "amount": 45000,
        "kra_pin": "P000123456A",
        "bank_name": "Equity Bank",
        "bank_account": "123456789",
        "bank_branch": "Nairobi CBD",
        "submitted_by": "garage@insure.demo",
        "submitted_at": "2025-07-15T10:00:00Z",
    }
    assert update_payment_status("CLM-PAY-001", data) is True
    payments = core_api.get_service_payments("CLM-PAY-001")
    assert len(payments) == 1
    assert payments.iloc[0]["invoice_number"] == "INV-2025-001"
    assert payments.iloc[0]["invoice_amount"] == 45000


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def test_log_and_get_audit(capi):
    log_id = log_audit("claim_created", "tester@example.com", "CLM-TEST-001")
    assert log_id.startswith("AUD-")
    audit = get_audit_log(limit=10)
    assert len(audit) >= 1
    assert audit.iloc[0]["action"] == "claim_created"


# ---------------------------------------------------------------------------
# SLA
# ---------------------------------------------------------------------------

def test_sla_status(capi):
    result = get_sla_status("CLM-SLA-001", "2025-01-01T10:00:00")
    assert "ack_deadline" in result
    assert "settle_deadline" in result
    assert result["days_to_ack"] >= 0


def test_sla_status_invalid_date(capi):
    result = get_sla_status("CLM-SLA-002", "not-a-date")
    assert "error" in result


# ---------------------------------------------------------------------------
# Disputes
# ---------------------------------------------------------------------------

def test_add_and_get_dispute(capi):
    dispute_id = add_dispute(
        "CLM-DSP-001", "Acme Corp", "Litigation", "high", 500000, "Adv. Ochieng"
    )
    assert dispute_id.startswith("DSP-")
    disputes = get_disputes(stage_filter="Litigation")
    assert any(d["dispute_id"] == dispute_id for d in disputes)


def test_get_disputes_empty(capi):
    disputes = get_disputes()
    assert disputes == []


# ---------------------------------------------------------------------------
# Cache invalidation (no-op in SQLite mode)
# ---------------------------------------------------------------------------

def test_invalidate_claim_cache(capi):
    result = invalidate_claim_cache("CLM-NOCACHE-001")
    assert result is None


# ---------------------------------------------------------------------------
# Module-level wrapper parity with CoreAPI methods
# ---------------------------------------------------------------------------

def test_module_level_wrappers_match_class(capi):
    """Verify key module-level wrappers delegate to the class correctly."""
    capi.create_claim(claim_ref="CLM-WRAP-001", submitted_by="test")
    assert get_claim("CLM-WRAP-001") == core_api_instance.get_claim("CLM-WRAP-001")
    assert get_claims()[0]["claim_ref"] == core_api_instance.get_claims()[0]["claim_ref"]


# ---------------------------------------------------------------------------
# Database schema
# ---------------------------------------------------------------------------

def test_all_tables_exist(capi):
    conn = core_api._get_conn()
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    expected = {
        "claims", "status_history", "reserves", "diary_entries",
        "communications", "expert_assignments", "claim_documents",
        "settlements", "service_payments", "client_messages",
        "audit_log", "disputes",
    }
    missing = expected - tables
    assert not missing, f"Missing tables: {missing}"
