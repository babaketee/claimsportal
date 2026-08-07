"""config_db.py — Versioned Configuration Database
===============================================
Phase 1: SQLite-based versioned config store with Maker-Checker approval workflow.
In production: swap SQLite for a proper distributed config store (etcd, Consul, etc.).

All claim, workflow, notification, and integration parameters are stored here.
No hardcoded values in application code — everything flows through this module.

Maker-Checker: all writes require a second user to approve before being applied.
Auto-approved: values from approved_keys (e.g. development mode flags) bypass approval.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

_DB_PATH = "claims_portal.db"
_DEFAULTS = {
    # ─── Claim reference format (Appendix B) ────────────────────────────────
    "claim.ref_format":                "CLM/{claim_class_upper}/{branch}/{year}/{seq:06d}",
    "claim.ref_format.example":         "CLM/MOT/NRB/2026/000123",

    # ─── Roles & RBAC ──────────────────────────────────────────────────────
    "auth.roles":                       ["client","claims_officer","head_of_claims","assessor","investigator","garage","spare_parts","admin","super_admin","legal","manager","surveyor","motor_fleet","finance","cfo"],
    "auth.maker_checker_roles":        ["head_of_claims","admin","super_admin"],
    "auth.approval_threshold":         1_000_000,          # KES — amounts above need HOC approval

    # ─── Workflow — TAT targets (SLA, in hours) ────────────────────────────
    "workflow.tat.fast_track":          4,                   # hours
    "workflow.tat.standard":           720,                 # hours = 30 days
    "workflow.tat.escalated":          1440,                # hours = 60 days
    "workflow.triage.sla_hours":       24,
    "workflow.investigation.sla_hours": 168,                # 7 days
    "workflow.assessment.sla_hours":   336,                # 14 days
    "workflow.approval.sla_hours":      72,                 # 3 days
    "workflow.settlement.sla_hours":    48,                 # 2 days

    # ─── Fast-track (Section 3.1 — R7) ──────────────────────────────────────
    "claim.motor.fast_track.eligible_min_age_days": 30,
    "claim.motor.fast_track.max_claim_amount": 100_000,    # KES
    "claim.motor.fast_track.sampling_rate": 0.05,           # 5% sampled for review
    "claim.motor.fast_track.sla_hours": 4,

    # ─── Document checklists per claim type (Appendix C) ──────────────────────
    "claim.motor.own_damage.documents.mandatory": ["claim_form","driving_licence","log_book","police_abstract","photos","repair_estimate"],
    "claim.motor.own_damage.documents.conditional": ["financier_consent","interpreter_statement"],
    "claim.motor.tp_property.documents.mandatory": ["claim_form","tp_demand","police_abstract","photos","tp_repair_estimate","insured_driver_statement"],
    "claim.motor.tp_property.documents.conditional": ["court_documents"],
    "claim.motor.tp_bodily_injury.documents.mandatory": ["claim_form","police_abstract","medical_report","treatment_records","demand_letter"],
    "claim.motor.tp_bodily_injury.documents.conditional": ["death_certificate","wage_records"],
    "claim.medical.documents.mandatory": ["claim_form","member_id","discharge_summary","itemised_bill","receipts"],
    "claim.medical.documents.conditional": ["pre_authorisation","referral_letter"],

    # ─── Total-loss (R2) ───────────────────────────────────────────────────
    "claim.motor.total_loss.salvage_rate_default": 0.15,    # 15% of sum_insured
    "claim.motor.total_loss.min_payout_ratio": 0.5,        # min 50% of sum_insured

    # ─── Reserve movements (R3) ────────────────────────────────────────────
    "claim.reserve.approval_required_above": 500_000,       # KES
    "claim.reserve.revision_requires_evidence": True,
    "claim.reserve.release_requires_hoc": True,

    # ─── Appeals register (R6) ─────────────────────────────────────────────
    "claim.appeal.filing_deadline_days": 30,                 # days from decision
    "claim.appeal.review_tat_hours": 168,                   # 7 days
    "claim.appeal.valid_reasons": ["procedural_error","new_evidence","misinformation","quantum_dispute"],

    # ─── Discharge voucher (R5) ────────────────────────────────────────────
    "claim.discharge_voucher.required_for_settlement_above": 50_000,  # KES
    "claim.discharge_voucher.signature_required": True,
    "claim.discharge_voucher.photocopy_required": True,

    # ─── Document upload / GPS metadata (p1-gap-8) ──────────────────────────
    "document.gps_metadata.required": True,                # photos must carry GPS coordinates
    "document.gps_metadata.retention_days": 2555,           # ~7 years for audit trail

    # ─── Exchange integrations ──────────────────────────────────────────────
    "exchange.1.policy_lookup.url":           "https://core.insure.example/api/v1/policies",
    "exchange.2.claim_notification.url":      "https://core.insure.example/api/v1/claims",
    "exchange.3.triage_push.url":             "https://core.insure.example/api/v1/portal/claims/triage",
    "exchange.4.reports_push.url":           "https://core.insure.example/api/v1/claims/reports",
    "exchange.5.decision_push.url":          "https://core.insure.example/api/v1/portal/claims/decision",
    "exchange.6.settlement_push.url":         "https://core.insure.example/api/v1/claims/settlement",
    "exchange.retry.max_attempts":            3,
    "exchange.retry.backoff_seconds":         [1, 4, 16],
    "exchange.timeout_seconds":               30,

    # ─── M-Pesa payment rails ──────────────────────────────────────────────
    "payment.mpesa.paybill":                  "123456",
    "payment.mpesa.account_format":           "CLM{ref}",
    "payment.mpesa.stk_push.shortcode":       "654321",
    "payment.mpesa.stk_push.callback_url":    "https://portal.definiteassurance.co.ke/mpesa/callback",

    # ─── Notification templates ──────────────────────────────────────────────
    "notification.email.claims_officer_on_new":  "You have a new claim: {claim_ref}. Please triage within {triage_sla_hours}h.",
    "notification.sms.claimant_on_submission":  "Definite Assurance: Your claim {claim_ref} has been received. Track at https://portal.definiteassurance.co.ke/track",
    "notification.email.claimant_on_decision":   "Your claim {claim_ref} has been {decision}. Amount: KES {amount}. Thank you.",
}

_APPROVED_KEYS = {
    "development_mode",
    "debug",
    "testing",
    "_audit_read",
}
_MAKER_CHECKER_DISABLED = {
    "debug",
    "development_mode",
    "testing",
}


class ConfigStore:
    def __init__(self, db_path: str = _DB_PATH) -> None:
        self._db_path = db_path
        self._lock = threading.RLock()
        self._defaults = dict(_DEFAULTS)
        self._init_db()
        self._seed_defaults()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config_entries (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config_approvals (
                approval_id TEXT PRIMARY KEY,
                key TEXT NOT NULL,
                proposed_value TEXT NOT NULL,
                proposed_by TEXT NOT NULL,
                proposed_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                decided_by TEXT,
                decided_at TEXT,
                UNIQUE(key, proposed_by, status)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                version INTEGER NOT NULL,
                changed_at TEXT NOT NULL,
                changed_by TEXT NOT NULL,
                change_type TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def _seed_defaults(self) -> None:
        conn = sqlite3.connect(self._db_path, timeout=10)
        for key, value in self._defaults.items():
            existing = conn.execute("SELECT value FROM config_entries WHERE key=?", (key,)).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO config_entries (key, value, version, updated_at, updated_by) VALUES (?, ?, 1, ?, ?)",
                    (key, json.dumps(value), datetime.now(timezone.utc).isoformat(), "system")
                )
        conn.commit()
        conn.close()

    def get(self, key: str, default: Any = None) -> Any:
        conn = sqlite3.connect(self._db_path, timeout=10)
        row = conn.execute("SELECT value FROM config_entries WHERE key=?", (key,)).fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return self._defaults.get(key, default)

    def set(self, key: str, value: Any, user_id: str = "system", skip_approval: bool = False) -> dict:
        if key in _MAKER_CHECKER_DISABLED or skip_approval:
            return self._apply_change(key, value, user_id)
        return self._propose_change(key, value, user_id)

    def _propose_change(self, key: str, value: Any, user_id: str) -> dict:
        with self._lock:
            approval_id = str(uuid.uuid4())
            conn = sqlite3.connect(self._db_path, timeout=10)
            conn.execute(
                "INSERT INTO config_approvals (approval_id, key, proposed_value, proposed_by, proposed_at, status) VALUES (?, ?, ?, ?, ?, ?)",
                (approval_id, key, json.dumps(value), user_id, datetime.now(timezone.utc).isoformat(), "pending")
            )
            conn.commit()
            conn.close()
            return {"status": "pending_approval", "approval_id": approval_id, "key": key}

    def _apply_change(self, key: str, value: Any, user_id: str) -> dict:
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            conn = sqlite3.connect(self._db_path, timeout=10)
            current = conn.execute("SELECT value, version FROM config_entries WHERE key=?", (key,)).fetchone()
            version = (current[1] + 1) if current else 1
            conn.execute(
                "INSERT OR REPLACE INTO config_entries (key, value, version, updated_at, updated_by) VALUES (?, ?, ?, ?, ?)",
                (key, json.dumps(value), version, now, user_id)
            )
            conn.execute(
                "INSERT INTO config_history (key, value, version, changed_at, changed_by, change_type) VALUES (?, ?, ?, ?, ?, ?)",
                (key, json.dumps(value), version, now, user_id, "applied")
            )
            conn.commit()
            conn.close()
            return {"status": "applied", "key": key, "version": version}

    def approve(self, approval_id: str, approver_id: str) -> dict:
        with self._lock:
            conn = sqlite3.connect(self._db_path, timeout=10)
            row = conn.execute("SELECT key, proposed_value, status FROM config_approvals WHERE approval_id=?", (approval_id,)).fetchone()
            if not row:
                conn.close()
                return {"status": "error", "message": "Approval not found"}
            key, proposed_value, status = row
            if status != "pending":
                conn.close()
                return {"status": "error", "message": f"Already {status}"}
            value = json.loads(proposed_value)
            conn.execute("UPDATE config_approvals SET status=?, decided_by=?, decided_at=? WHERE approval_id=?",
                ("approved", approver_id, datetime.now(timezone.utc).isoformat(), approval_id))
            conn.commit()
            conn.close()
            return self._apply_change(key, value, approver_id)

    def reject(self, approval_id: str, rejecter_id: str) -> dict:
        with self._lock:
            conn = sqlite3.connect(self._db_path, timeout=10)
            conn.execute("UPDATE config_approvals SET status=?, decided_by=?, decided_at=? WHERE approval_id=?",
                ("rejected", rejecter_id, datetime.now(timezone.utc).isoformat(), approval_id))
            conn.commit()
            conn.close()
            return {"status": "rejected", "approval_id": approval_id}

    def get_pending_approvals(self) -> list[dict]:
        conn = sqlite3.connect(self._db_path, timeout=10)
        rows = conn.execute("SELECT approval_id, key, proposed_value, proposed_by, proposed_at FROM config_approvals WHERE status=? ORDER BY proposed_at", ("pending",)).fetchall()
        conn.close()
        return [{"approval_id": r[0], "key": r[1], "proposed_value": json.loads(r[2]), "proposed_by": r[3], "proposed_at": r[4]} for r in rows]

    def history(self, key: str) -> list[dict]:
        conn = sqlite3.connect(self._db_path, timeout=10)
        rows = conn.execute("SELECT id, key, value, version, changed_at, changed_by, change_type FROM config_history WHERE key=? ORDER BY version ASC", (key,)).fetchall()
        conn.close()
        return [{"id": r[0], "key": r[1], "value": json.loads(r[2]), "version": r[3], "changed_at": r[4], "changed_by": r[5], "change_type": r[6]} for r in rows]

    def all_keys(self) -> list[str]:
        conn = sqlite3.connect(self._db_path, timeout=10)
        rows = conn.execute("SELECT key FROM config_entries ORDER BY key").fetchall()
        conn.close()
        return [r[0] for r in rows]

    def dump(self) -> dict[str, Any]:
        result = dict(self._defaults)
        for key in self.all_keys():
            result[key] = self.get(key)
        return result


_config: ConfigStore | None = None
_config_lock = threading.Lock()


def get_config(db_path: str = _DB_PATH) -> ConfigStore:
    global _config
    if _config is None:
        with _config_lock:
            if _config is None:
                _config = ConfigStore(db_path)
    return _config


def reset_config() -> None:
    global _config
    with _config_lock:
        _config = None
