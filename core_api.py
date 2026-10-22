"""Core API client — local SQLite data layer with optional external REST integration.

Provides a ``CoreAPI`` class (instantiated as module-level ``core_api``) that
all views import via ``from core_api import core_api`` or ``import core_api``.

Tables:
  - claims              — core claim records (FNOL data + current status)
  - status_history      — chronological audit trail of status changes
  - reserves            — claim reserve amounts (initial + supplemental)
  - diary_entries       — follow-up tasks with due dates
  - communications      — SMS/call/email/WhatsApp log per claim
  - expert_assignments  — assessor/garage/investigator assignments
  - claim_documents     — document metadata
  - settlements         — settlement recommendations, approvals, and payments
  - service_payments    — service provider payment authorisations
  - client_messages     — messages between clients and service providers
  - audit_log           — system-wide audit trail

When CORE_API_BASE_URL is configured, write operations also POST to the
external core system.  Read operations prefer SQLite for sub-second response.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
import os
from datetime import datetime, timedelta
from typing import Optional, Any
from functools import lru_cache

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DB_PATH = os.environ.get("CLAIMS_DB_PATH", "claims_operations.db")

# External core API (optional — used for cross-system sync)
_CORE_API_BASE_URL = os.environ.get("CORE_API_BASE_URL", "")
_CORE_API_KEY = os.environ.get("CORE_API_KEY", "")

# Business rules (defaults — overridable by Super Admin)
REINSURANCE_THRESHOLD = int(os.environ.get("REINSURANCE_THRESHOLD", "2000000"))
OFFICER_AUTO_APPROVE_LIMIT = int(os.environ.get("OFFICER_AUTO_APPROVE_LIMIT", "500000"))
HOC_APPROVE_LIMIT = int(os.environ.get("HOC_APPROVE_LIMIT", "2000000"))
FINANCE_HEAD_LIMIT = int(os.environ.get("FINANCE_HEAD_LIMIT", "5000000"))
SLA_ACK_DAYS = int(os.environ.get("SLA_ACK_DAYS", "14"))
SLA_SETTLE_DAYS = int(os.environ.get("SLA_SETTLE_DAYS", "30"))

# WHT rates (Kenya Revenue Authority)
WHT_RATES = {
    "assessor":     0.05,
    "garage":       0.05,
    "investigator": 0.05,
    "spare_parts":  0.10,
    "third_party":  0.00,
    "insured":      0.00,
}


# ---------------------------------------------------------------------------
# SQLite connection & schema
# ---------------------------------------------------------------------------

def _get_conn() -> sqlite3.Connection:
    """Return a SQLite connection (thread-safe for Streamlit)."""
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    """Create all tables if they do not exist.  Idempotent."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.executescript("""
    -- Core claims table (replaces external-only claims model)
    CREATE TABLE IF NOT EXISTS claims (
        claim_ref        TEXT PRIMARY KEY,
        policy_number    TEXT,
        id_number        TEXT,
        vehicle_reg      TEXT,
        phone            TEXT,
        incident_date      TEXT,
        incident_time      TEXT,
        incident_location  TEXT,
        incident_type      TEXT,
        description      TEXT,
        third_party      INTEGER DEFAULT 0,
        tp_vehicle_reg   TEXT,
        tp_driver_name   TEXT,
        tp_phone         TEXT,
        tp_insurer       TEXT,
        police_station   TEXT,
        ob_number        TEXT,
        submitted_by     TEXT,
        submitted_at     TEXT,
        status           TEXT DEFAULT 'Submitted',
        assigned_to      TEXT,           -- claims officer
        assigned_at      TEXT,
        last_updated     TEXT,
        estimated_amount REAL DEFAULT 0,
        actual_amount    REAL DEFAULT 0
    );

    -- Status audit trail
    CREATE TABLE IF NOT EXISTS status_history (
        event_id   TEXT PRIMARY KEY,
        claim_ref  TEXT NOT NULL,
        from_status TEXT,
        to_status   TEXT NOT NULL,
        changed_by  TEXT,
        source      TEXT DEFAULT 'portal',
        note        TEXT,
        changed_at  TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS reserves (
        reserve_id      TEXT PRIMARY KEY,
        claim_ref       TEXT NOT NULL,
        reserve_type    TEXT NOT NULL,
        amount          REAL NOT NULL,
        purpose         TEXT,
        created_by      TEXT,
        created_at      TEXT NOT NULL,
        approved_by     TEXT,
        approved_at     TEXT,
        status          TEXT NOT NULL DEFAULT 'pending',
        note            TEXT
    );

    CREATE TABLE IF NOT EXISTS diary_entries (
        entry_id        TEXT PRIMARY KEY,
        claim_ref       TEXT NOT NULL,
        task            TEXT NOT NULL,
        due_date        TEXT NOT NULL,
        assigned_to     TEXT,
        priority        TEXT NOT NULL DEFAULT 'normal',
        status          TEXT NOT NULL DEFAULT 'open',
        created_by      TEXT,
        created_at      TEXT NOT NULL,
        completed_at    TEXT,
        note            TEXT
    );

    CREATE TABLE IF NOT EXISTS communications (
        comm_id         TEXT PRIMARY KEY,
        claim_ref       TEXT NOT NULL,
        channel         TEXT NOT NULL,
        direction       TEXT NOT NULL,
        contact_name    TEXT,
        contact_phone   TEXT,
        summary         TEXT NOT NULL,
        outcome         TEXT,
        consent_obtained TEXT NOT NULL DEFAULT 'yes',
        created_by      TEXT,
        created_at      TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS expert_assignments (
        assignment_id   TEXT PRIMARY KEY,
        claim_ref       TEXT NOT NULL,
        expert_type     TEXT NOT NULL,
        expert_name     TEXT NOT NULL,
        expert_phone    TEXT,
        expert_company  TEXT,
        status          TEXT NOT NULL DEFAULT 'pending',
        assigned_by     TEXT,
        assigned_at     TEXT NOT NULL,
        accepted_at     TEXT,
        completed_at    TEXT,
        estimated_cost  REAL,
        actual_cost     REAL,
        note            TEXT
    );

    CREATE TABLE IF NOT EXISTS claim_documents (
        doc_id          TEXT PRIMARY KEY,
        claim_ref       TEXT NOT NULL,
        doc_type        TEXT NOT NULL,
        filename        TEXT NOT NULL,
        file_size       INTEGER,
        mime_type       TEXT,
        uploaded_by     TEXT,
        uploaded_at     TEXT NOT NULL,
        version         INTEGER NOT NULL DEFAULT 1,
        core_doc_id     TEXT,
        note            TEXT
    );

    CREATE TABLE IF NOT EXISTS settlements (
        settlement_id   TEXT PRIMARY KEY,
        claim_ref       TEXT NOT NULL,
        settlement_type TEXT NOT NULL,
        amount          REAL NOT NULL,
        payee_name      TEXT,
        payee_type      TEXT,
        wht_rate        REAL,
        wht_amount      REAL,
        net_amount      REAL,
        status          TEXT NOT NULL DEFAULT 'pending',
        recommended_by  TEXT,
        recommended_at  TEXT,
        approved_by     TEXT,
        approved_at     TEXT,
        paid_at         TEXT,
        bank_ref        TEXT,
        note            TEXT
    );

    CREATE TABLE IF NOT EXISTS service_payments (
        payment_id      TEXT PRIMARY KEY,
        claim_ref       TEXT NOT NULL,
        provider_name   TEXT,
        provider_type   TEXT,
        invoice_number  TEXT,
        invoice_amount  REAL,
        decision        TEXT,
        authorised_by   TEXT,
        authorised_at   TEXT,
        status          TEXT DEFAULT 'pending',
        note            TEXT,
        created_at      TEXT
    );

    CREATE TABLE IF NOT EXISTS client_messages (
        message_id      TEXT PRIMARY KEY,
        claim_ref       TEXT NOT NULL,
        sent_by         TEXT,
        recipient_type  TEXT,
        recipient_name  TEXT,
        subject         TEXT,
        body            TEXT,
        sent_at         TEXT NOT NULL,
        read_at         TEXT
    );

    CREATE TABLE IF NOT EXISTS disputes (
        dispute_id      TEXT PRIMARY KEY,
        claim_ref       TEXT NOT NULL,
        stage           TEXT DEFAULT 'Repudiation Appeal',
        urgency         TEXT DEFAULT 'normal',
        claim_amount    REAL,
        client_name     TEXT,
        advocate        TEXT,
        status          TEXT DEFAULT 'open',
        created_at      TEXT NOT NULL,
        updated_at      TEXT
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        log_id          TEXT PRIMARY KEY,
        action          TEXT NOT NULL,
        actor           TEXT,
        detail          TEXT,
        created_at      TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_claims_status   ON claims(status);
    CREATE INDEX IF NOT EXISTS idx_claims_assigned ON claims(assigned_to);
    CREATE INDEX IF NOT EXISTS idx_diary_claim     ON diary_entries(claim_ref);
    CREATE INDEX IF NOT EXISTS idx_comm_claim      ON communications(claim_ref);
    CREATE INDEX IF NOT EXISTS idx_assign_claim    ON expert_assignments(claim_ref);
    CREATE INDEX IF NOT EXISTS idx_docs_claim      ON claim_documents(claim_ref);
    CREATE INDEX IF NOT EXISTS idx_settle_claim    ON settlements(claim_ref);
    CREATE INDEX IF NOT EXISTS idx_status_claim    ON status_history(claim_ref);
    CREATE INDEX IF NOT EXISTS idx_msg_claim       ON client_messages(claim_ref);
    CREATE INDEX IF NOT EXISTS idx_disputes_claim  ON disputes(claim_ref);
    """)
    conn.commit()
    # Migration: add created_at to service_payments if missing (existing DBs)
    try:
        conn.execute("ALTER TABLE service_payments ADD COLUMN created_at TEXT")
        conn.commit()
    except Exception:
        pass
    conn.close()


# Init on module load
try:
    _init_db()
except Exception:
    pass


def _now() -> str:
    """ISO-format timestamp."""
    return datetime.now().isoformat()


def _gen_id(prefix: str) -> str:
    """Generate a human-readable ID like CLM-20250715-ABC123."""
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


# ---------------------------------------------------------------------------
# CoreAPI class — the object all views import
# ---------------------------------------------------------------------------

class CoreAPI:
    """Main data-access facade.  Instantiate once via ``core_api``."""

    # ---- Claim CRUD --------------------------------------------------------

    def is_configured(self) -> bool:
        """Return True when an external CORE_API_BASE_URL is set."""
        return bool(_CORE_API_BASE_URL)

    def create_claim(self, claim_ref: str, policy_number: str = "",
                     id_number: str = "", vehicle_reg: str = "",
                     phone: str = "", incident_date: str = "",
                     incident_time: str = "", incident_location: str = "",
                     incident_type: str = "", description: str = "",
                     third_party: bool = False, tp_vehicle_reg: str = "",
                     tp_driver_name: str = "", tp_phone: str = "",
                     tp_insurer: str = "", police_station: str = "",
                     ob_number: str = "", submitted_by: str = "",
                     estimated_amount: float = 0.0) -> bool:
        """Insert a claim row.  Returns True on success."""
        conn = _get_conn()
        now = _now()
        conn.execute("""
            INSERT OR REPLACE INTO claims
            (claim_ref, policy_number, id_number, vehicle_reg, phone,
             incident_date, incident_time, incident_location, incident_type,
             description, third_party, tp_vehicle_reg, tp_driver_name,
             tp_phone, tp_insurer, police_station, ob_number, submitted_by,
             submitted_at, last_updated, estimated_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (claim_ref, policy_number, id_number, vehicle_reg, phone,
              incident_date, incident_time, incident_location, incident_type,
              description, int(third_party), tp_vehicle_reg, tp_driver_name,
              tp_phone, tp_insurer, police_station, ob_number, submitted_by,
              now, now, estimated_amount))
        conn.commit()
        conn.close()
        return True

    def get_claim(self, claim_ref: str) -> Optional[dict]:
        """Fetch a single claim. Returns dict or None."""
        conn = _get_conn()
        row = conn.execute(
            "SELECT * FROM claims WHERE claim_ref=?", (claim_ref,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_claims(self, status_filter: str = "", assigned_to: str = "",
                   limit: int = 500) -> list[dict]:
        """Return a list of claims matching filters."""
        conn = _get_conn()
        sql = "SELECT * FROM claims"
        params: list = []
        conditions = []
        if status_filter:
            conditions.append("status=?")
            params.append(status_filter)
        if assigned_to:
            conditions.append("assigned_to=?")
            params.append(assigned_to)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY submitted_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_claim_status(self, claim_ref: str, to_status: str,
                            changed_by: str = "", note: str = "",
                            source: str = "portal") -> bool:
        """Update claim status and record in status_history."""
        from_status = None
        conn = _get_conn()
        row = conn.execute(
            "SELECT status FROM claims WHERE claim_ref=?", (claim_ref,)
        ).fetchone()
        if row:
            from_status = row["status"]

        now = _now()
        conn.execute(
            "UPDATE claims SET status=?, last_updated=? WHERE claim_ref=?",
            (to_status, now, claim_ref)
        )
        conn.commit()
        conn.close()
        self.record_status_change(
            claim_ref=claim_ref, from_status=from_status or "",
            to_status=to_status, changed_by=changed_by, source=source, note=note)
        return True

    def record_status_change(self, claim_ref: str, to_status: str,
                             from_status: str = "", changed_by: str = "",
                             source: str = "portal", note: str = "") -> str:
        """Insert a status_history row. Returns event_id."""
        event_id = _gen_id("EVT")
        conn = _get_conn()
        conn.execute("""
            INSERT INTO status_history
            (event_id, claim_ref, from_status, to_status, changed_by, source, note, changed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (event_id, claim_ref, from_status, to_status, changed_by, source, note, _now()))
        conn.commit()
        conn.close()
        return event_id

    def get_timeline(self, claim_ref: str) -> list[dict]:
        """Build a unified chronological timeline for a claim."""
        events: list[dict] = []
        conn = _get_conn()

        # Status changes
        for row in conn.execute(
            "SELECT changed_by as actor, to_status as title, changed_at as event_time, "
            "'status_change' as event_type, note FROM status_history WHERE claim_ref=? ORDER BY changed_at",
            (claim_ref,)
        ).fetchall():
            events.append(dict(row))

        # Assignments
        for row in conn.execute(
            "SELECT expert_name as actor, expert_type || ' assigned' as title, "
            "assigned_at as event_time, 'assignment' as event_type, note FROM expert_assignments "
            "WHERE claim_ref=? ORDER BY assigned_at",
            (claim_ref,)
        ).fetchall():
            events.append(dict(row))

        # Communications
        for row in conn.execute(
            "SELECT contact_name as actor, channel || ': ' || summary as title, "
            "created_at as event_time, 'communication' as event_type, outcome as note "
            "FROM communications WHERE claim_ref=? ORDER BY created_at",
            (claim_ref,)
        ).fetchall():
            events.append(dict(row))

        conn.close()
        events.sort(key=lambda e: e.get("event_time", ""))
        return events

    def invalidate_claim_cache(self, claim_ref: str) -> None:
        """Clear cached claim data (no-op in SQLite mode; for external API sync)."""
        # In external API mode this would clear Redis/Delta cache
        pass

    # ---- Reserve management (delegates to module functions) ----------------

    def set_reserve(self, claim_ref: str, reserve_type: str, amount: float,
                    purpose: str, created_by: str, note: str = "") -> Optional[str]:
        return set_reserve(claim_ref, reserve_type, amount, purpose, created_by, note)

    def approve_reserve(self, reserve_id: str, approved_by: str) -> bool:
        return approve_reserve(reserve_id, approved_by)

    def release_reserve(self, reserve_id: str, released_by: str, note: str = "") -> bool:
        return release_reserve(reserve_id, released_by, note)

    def get_reserves(self, claim_ref: str) -> pd.DataFrame:
        return get_reserves(claim_ref)

    def get_total_reserves(self, claim_ref: str) -> float:
        return get_total_reserves(claim_ref)

    # ---- Diary entries ------------------------------------------------------

    def add_diary_entry(self, claim_ref: str, task: str, due_date: str,
                        assigned_to: str, priority: str, created_by: str,
                        note: str = "") -> Optional[str]:
        return add_diary_entry(claim_ref, task, due_date, assigned_to, priority, created_by, note)

    def complete_diary_entry(self, entry_id: str) -> bool:
        return complete_diary_entry(entry_id)

    def get_diary_entries(self, claim_ref: str) -> pd.DataFrame:
        return get_diary_entries(claim_ref)

    def get_overdue_entries(self, assigned_to: Optional[str] = None) -> pd.DataFrame:
        return get_overdue_entries(assigned_to)

    # ---- Communications -----------------------------------------------------

    def log_communication(self, claim_ref: str, channel: str, direction: str,
                          summary: str, created_by: str,
                          contact_name: str = "", contact_phone: str = "",
                          outcome: str = "", consent: bool = True) -> Optional[str]:
        return log_communication(claim_ref, channel, direction, summary, created_by,
                                 contact_name, contact_phone, outcome, consent)

    def get_communications(self, claim_ref: str) -> pd.DataFrame:
        return get_communications(claim_ref)

    # ---- Expert assignments -------------------------------------------------

    def assign_expert(self, claim_ref: str, expert_type: str, expert_name: str,
                      expert_phone: str, expert_company: str,
                      assigned_by: str, estimated_cost: float = 0,
                      note: str = "") -> Optional[str]:
        return assign_expert(claim_ref, expert_type, expert_name, expert_phone,
                             expert_company, assigned_by, estimated_cost, note)

    def update_assignment_status(self, assignment_id: str, status: str,
                                  actual_cost: Optional[float] = None) -> bool:
        return update_assignment_status(assignment_id, status, actual_cost)

    def update_job_status(self, claim_ref: str, new_status: str,
                          actor: str = "") -> bool:
        """Alias for updating assignment status by claim_ref."""
        conn = _get_conn()
        cur = conn.execute(
            "UPDATE expert_assignments SET status=? WHERE claim_ref=?",
            (new_status, claim_ref)
        )
        conn.commit()
        affected = cur.rowcount
        conn.close()
        return affected > 0

    def get_assignments(self, claim_ref: Optional[str] = None,
                        expert_type: Optional[str] = None) -> pd.DataFrame:
        conn = _get_conn()
        if claim_ref:
            sql = "SELECT * FROM expert_assignments WHERE claim_ref=? ORDER BY assigned_at DESC"
            df = pd.read_sql(sql, conn, params=(claim_ref,))
        elif expert_type:
            sql = "SELECT * FROM expert_assignments WHERE expert_type=? ORDER BY assigned_at DESC"
            df = pd.read_sql(sql, conn, params=(expert_type,))
        else:
            df = pd.read_sql("SELECT * FROM expert_assignments ORDER BY assigned_at DESC", conn)
        conn.close()
        return df

    # ---- Document management ------------------------------------------------

    def register_document(self, claim_ref: str, doc_type: str, filename: str,
                          file_size: int, mime_type: str,
                          uploaded_by: str, core_doc_id: str = "",
                          note: str = "") -> Optional[str]:
        return register_document(claim_ref, doc_type, filename, file_size,
                                 mime_type, uploaded_by, core_doc_id, note)

    def get_documents(self, claim_ref: str) -> pd.DataFrame:
        return get_documents(claim_ref)

    def post_document(self, claim_ref: str, filename: str, mime_type: str,
                      file_bytes: bytes, doc_type: str = "") -> Optional[str]:
        """POST a document to the external core API.  Falls back to local registration."""
        if not self.is_configured():
            # Local fallback: register metadata without the file bytes
            return self.register_document(
                claim_ref=claim_ref, doc_type=doc_type or "other",
                filename=filename, file_size=len(file_bytes),
                mime_type=mime_type, uploaded_by="portal")
        try:
            import requests
            resp = requests.post(
                f"{_CORE_API_BASE_URL}/documents",
                headers={"Authorization": f"Bearer {_CORE_API_KEY}"},
                json={"claim_ref": claim_ref, "filename": filename,
                      "mime_type": mime_type, "doc_type": doc_type},
                timeout=30,
            )
            if resp.status_code in (200, 201):
                core_doc_id = resp.json().get("doc_id", "")
                self.register_document(
                    claim_ref=claim_ref, doc_type=doc_type or "other",
                    filename=filename, file_size=len(file_bytes),
                    mime_type=mime_type, uploaded_by="portal",
                    core_doc_id=core_doc_id)
                return core_doc_id
        except Exception:
            pass
        return None

    # ---- Settlements --------------------------------------------------------

    def recommend_settlement(self, claim_ref: str, amount: float, payee_name: str,
                             payee_type: str, recommended_by: str,
                             wht_rate: float = 0.0, note: str = "") -> Optional[str]:
        return recommend_settlement(claim_ref, amount, payee_name, payee_type,
                                    recommended_by, wht_rate, note)

    def approve_settlement(self, settlement_id: str, approved_by: str) -> bool:
        return approve_settlement(settlement_id, approved_by)

    def mark_settlement_paid(self, settlement_id: str, bank_ref: str) -> bool:
        return mark_settlement_paid(settlement_id, bank_ref)

    def get_settlements(self, claim_ref: str) -> pd.DataFrame:
        return get_settlements(claim_ref)

    def authorise_service_payment(self, claim_ref: str, provider_name: str,
                                  invoice_number: str, invoice_amount: float,
                                  decision: str, authorised_by: str,
                                  note: str = "") -> Optional[str]:
        """Record a service provider payment authorisation."""
        payment_id = _gen_id("PAY")
        now = _now()
        conn = _get_conn()
        conn.execute("""
            INSERT INTO service_payments
            (payment_id, claim_ref, provider_name, provider_type, invoice_number,
             invoice_amount, decision, authorised_by, authorised_at, status, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'authorised', ?)
        """, (payment_id, claim_ref, provider_name, "service_provider",
              invoice_number, invoice_amount, decision, authorised_by, now, note))
        conn.commit()
        conn.close()
        self.log_audit("service_payment_authorised", authorised_by,
                       f"{payment_id}: {provider_name} KES {invoice_amount:,.0f}")
        return payment_id

    def get_service_payments(self, claim_ref: Optional[str] = None) -> pd.DataFrame:
        conn = _get_conn()
        if claim_ref:
            df = pd.read_sql(
                "SELECT * FROM service_payments WHERE claim_ref=?",
                conn, params=(claim_ref,))
        else:
            df = pd.read_sql("SELECT * FROM service_payments", conn)
        conn.close()
        return df

    def update_payment_status(self, claim_ref: str, data: dict) -> bool:
        """Record payment status / invoice data for a service provider claim.
        Stores tracking data in service_payments; syncs to external API if configured."""
        payment_id = _gen_id("PAY")
        now = _now()
        conn = _get_conn()
        conn.execute("""
            INSERT INTO service_payments
            (payment_id, claim_ref, invoice_number, invoice_amount,
             decision, status, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (payment_id, claim_ref,
              data.get("invoice_number", ""),
              data.get("amount", 0),
              "",
              data.get("status", "pending"),
              json.dumps(data, default=str),
              data.get("submitted_at", now)))
        conn.commit()
        conn.close()
        self.log_audit("payment_status_updated", data.get("submitted_by", ""),
                       f"{claim_ref}: invoice {data.get('invoice_number', '')}")
        return True

    # ---- Messages -----------------------------------------------------------

    def send_message(self, claim_ref: str, sent_by: str, recipient_type: str,
                     recipient_name: str, subject: str, body: str) -> Optional[str]:
        """Insert a message into client_messages."""
        message_id = _gen_id("MSG")
        now = _now()
        conn = _get_conn()
        conn.execute("""
            INSERT INTO client_messages
            (message_id, claim_ref, sent_by, recipient_type, recipient_name,
             subject, body, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (message_id, claim_ref, sent_by, recipient_type, recipient_name,
              subject, body, now))
        conn.commit()
        conn.close()
        return message_id

    def get_messages(self, claim_ref: str) -> list[dict]:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT * FROM client_messages WHERE claim_ref=? ORDER BY sent_at DESC",
            (claim_ref,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ---- Disputes & Litigation ----------------------------------------------

    def get_disputes(self, stage_filter: str = "", urgency_filter: str = "",
                       search: str = "") -> list[dict]:
        conn = _get_conn()
        sql = "SELECT * FROM disputes"
        params: list = []
        conditions = []
        if stage_filter and stage_filter != "All":
            conditions.append("stage=?")
            params.append(stage_filter)
        if urgency_filter and urgency_filter != "All":
            conditions.append("urgency=?")
            params.append(urgency_filter)
        if search:
            conditions.append("(claim_ref LIKE ? OR client_name LIKE ? OR advocate LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY created_at DESC"
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_dispute(self, claim_ref: str, client_name: str = "",
                    stage: str = "Repudiation Appeal", urgency: str = "normal",
                    claim_amount: float = 0.0, advocate: str = "") -> str:
        dispute_id = _gen_id("DSP")
        now = _now()
        conn = _get_conn()
        conn.execute("""
            INSERT INTO disputes
            (dispute_id, claim_ref, stage, urgency, claim_amount, client_name, advocate, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (dispute_id, claim_ref, stage, urgency, claim_amount, client_name, advocate, now, now))
        conn.commit()
        conn.close()
        return dispute_id

    # ---- Audit --------------------------------------------------------------

    def log_audit(self, action: str, actor: str = "", detail: str = "") -> str:
        log_id = _gen_id("AUD")
        conn = _get_conn()
        conn.execute("""
            INSERT INTO audit_log (log_id, action, actor, detail, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (log_id, action, actor, detail, _now()))
        conn.commit()
        conn.close()
        return log_id

    def get_audit_log(self, limit: int = 200) -> pd.DataFrame:
        conn = _get_conn()
        df = pd.read_sql(
            "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?",
            conn, params=(limit,))
        conn.close()
        return df

    # ---- SLA helpers --------------------------------------------------------

    def get_sla_status(self, claim_ref: str, submitted_at: str) -> dict:
        """Return SLA timers for a claim."""
        try:
            submitted = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))
        except Exception:
            return {"error": "Invalid date"}
        ack_deadline = submitted + timedelta(days=SLA_ACK_DAYS)
        settle_deadline = submitted + timedelta(days=SLA_SETTLE_DAYS)
        now = datetime.now()
        return {
            "acknowledged_overdue": now >= ack_deadline,
            "settlement_overdue": now >= settle_deadline,
            "ack_deadline": ack_deadline.strftime("%Y-%m-%d"),
            "settle_deadline": settle_deadline.strftime("%Y-%m-%d"),
            "days_to_ack": max(0, (ack_deadline - now).days),
            "days_to_settle": max(0, (settle_deadline - now).days),
        }

    # ---- External API sync --------------------------------------------------

    def post_claim(self, data: dict) -> bool:
        """POST claim to external core API. No-op if not configured."""
        if not self.is_configured():
            return False
        try:
            import requests
            requests.post(
                f"{_CORE_API_BASE_URL}/claims",
                headers={"Authorization": f"Bearer {_CORE_API_KEY}"},
                json=data, timeout=30)
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Module-level instance (what views import)
# ---------------------------------------------------------------------------

core_api = CoreAPI()


# ---------------------------------------------------------------------------
# Backward-compatible module-level functions (used by seed script etc.)
# ---------------------------------------------------------------------------

def get_claims(status_filter: str = "", assigned_to: str = "") -> list[dict]:
    return core_api.get_claims(status_filter, assigned_to)


def record_status_change(claim_ref: str, to_status: str, from_status: str = "",
                         changed_by: str = "", source: str = "portal",
                         note: str = "") -> str:
    return core_api.record_status_change(claim_ref, to_status, from_status,
                                         changed_by, source, note)


# ---------------------------------------------------------------------------
# Reserve management (module-level wrappers)
# ---------------------------------------------------------------------------

def set_reserve(claim_ref: str, reserve_type: str, amount: float,
                purpose: str, created_by: str, note: str = "") -> Optional[str]:
    if not claim_ref or amount <= 0:
        return None
    reserve_id = _gen_id("RSV")
    now = _now()
    conn = _get_conn()
    conn.execute("""
        INSERT INTO reserves
        (reserve_id, claim_ref, reserve_type, amount, purpose,
         created_by, created_at, status, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (reserve_id, claim_ref, reserve_type, amount, purpose, created_by, now, note))
    conn.commit()
    conn.close()
    return reserve_id


def approve_reserve(reserve_id: str, approved_by: str) -> bool:
    conn = _get_conn()
    now = _now()
    cur = conn.execute(
        "UPDATE reserves SET approved_by=?, approved_at=?, status='approved' WHERE reserve_id=?",
        (approved_by, now, reserve_id)
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def release_reserve(reserve_id: str, released_by: str, note: str = "") -> bool:
    conn = _get_conn()
    now = _now()
    cur = conn.execute(
        "UPDATE reserves SET status='released', approved_by=?, approved_at=?, note=? WHERE reserve_id=?",
        (released_by, now, note, reserve_id)
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def get_reserves(claim_ref: str) -> pd.DataFrame:
    conn = _get_conn()
    df = pd.read_sql(
        "SELECT * FROM reserves WHERE claim_ref=? ORDER BY created_at ASC",
        conn, params=(claim_ref,))
    conn.close()
    return df


def get_total_reserves(claim_ref: str) -> float:
    conn = _get_conn()
    cur = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM reserves WHERE claim_ref=? AND status='approved'",
        (claim_ref,))
    total = cur.fetchone()[0]
    conn.close()
    return float(total)


# ---------------------------------------------------------------------------
# Diary entries (module-level wrappers)
# ---------------------------------------------------------------------------

def add_diary_entry(claim_ref: str, task: str, due_date: str,
                    assigned_to: str, priority: str, created_by: str,
                    note: str = "") -> Optional[str]:
    entry_id = _gen_id("DRY")
    now = _now()
    conn = _get_conn()
    conn.execute("""
        INSERT INTO diary_entries
        (entry_id, claim_ref, task, due_date, assigned_to, priority,
         status, created_by, created_at, note)
        VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?)
    """, (entry_id, claim_ref, task, due_date, assigned_to, priority, created_by, now, note))
    conn.commit()
    conn.close()
    return entry_id


def complete_diary_entry(entry_id: str) -> bool:
    conn = _get_conn()
    now = _now()
    cur = conn.execute(
        "UPDATE diary_entries SET status='done', completed_at=? WHERE entry_id=?",
        (now, entry_id))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def get_diary_entries(claim_ref: str) -> pd.DataFrame:
    conn = _get_conn()
    df = pd.read_sql(
        "SELECT * FROM diary_entries WHERE claim_ref=? ORDER BY due_date ASC",
        conn, params=(claim_ref,))
    conn.close()
    return df


def get_overdue_entries(assigned_to: Optional[str] = None) -> pd.DataFrame:
    today = datetime.now().strftime('%Y-%m-%d')
    conn = _get_conn()
    if assigned_to:
        df = pd.read_sql(
            "SELECT * FROM diary_entries WHERE status='open' AND due_date < ? AND assigned_to=? ORDER BY due_date",
            conn, params=(today, assigned_to))
    else:
        df = pd.read_sql(
            "SELECT * FROM diary_entries WHERE status='open' AND due_date < ? ORDER BY due_date",
            conn, params=(today,))
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Communications log (module-level wrappers)
# ---------------------------------------------------------------------------

def log_communication(claim_ref: str, channel: str, direction: str,
                      summary: str, created_by: str,
                      contact_name: str = "", contact_phone: str = "",
                      outcome: str = "", consent: bool = True) -> Optional[str]:
    comm_id = _gen_id("COM")
    now = _now()
    conn = _get_conn()
    conn.execute("""
        INSERT INTO communications
        (comm_id, claim_ref, channel, direction, contact_name, contact_phone,
         summary, outcome, consent_obtained, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (comm_id, claim_ref, channel, direction, contact_name, contact_phone,
          summary, outcome, "yes" if consent else "no", created_by, now))
    conn.commit()
    conn.close()
    return comm_id


def get_communications(claim_ref: str) -> pd.DataFrame:
    conn = _get_conn()
    df = pd.read_sql(
        "SELECT * FROM communications WHERE claim_ref=? ORDER BY created_at DESC",
        conn, params=(claim_ref,))
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Expert assignments (module-level wrappers)
# ---------------------------------------------------------------------------

def assign_expert(claim_ref: str, expert_type: str, expert_name: str,
                  expert_phone: str, expert_company: str,
                  assigned_by: str, estimated_cost: float = 0,
                  note: str = "") -> Optional[str]:
    assignment_id = _gen_id("ASN")
    now = _now()
    conn = _get_conn()
    conn.execute("""
        INSERT INTO expert_assignments
        (assignment_id, claim_ref, expert_type, expert_name, expert_phone,
         expert_company, status, assigned_by, assigned_at, estimated_cost, note)
        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
    """, (assignment_id, claim_ref, expert_type, expert_name, expert_phone,
          expert_company, assigned_by, now, estimated_cost, note))
    conn.commit()
    conn.close()
    return assignment_id


def update_assignment_status(assignment_id: str, status: str,
                             actual_cost: Optional[float] = None) -> bool:
    now = _now()
    conn = _get_conn()
    if status == 'completed' and actual_cost is not None:
        cur = conn.execute(
            "UPDATE expert_assignments SET status=?, completed_at=?, actual_cost=? WHERE assignment_id=?",
            (status, now, actual_cost, assignment_id))
    elif status == 'accepted':
        cur = conn.execute(
            "UPDATE expert_assignments SET status=?, accepted_at=? WHERE assignment_id=?",
            (status, now, assignment_id))
    else:
        cur = conn.execute(
            "UPDATE expert_assignments SET status=? WHERE assignment_id=?",
            (status, assignment_id))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def get_assignments(claim_ref: str) -> pd.DataFrame:
    conn = _get_conn()
    df = pd.read_sql(
        "SELECT * FROM expert_assignments WHERE claim_ref=? ORDER BY assigned_at DESC",
        conn, params=(claim_ref,))
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Document metadata (module-level wrappers)
# ---------------------------------------------------------------------------

def register_document(claim_ref: str, doc_type: str, filename: str,
                      file_size: int, mime_type: str,
                      uploaded_by: str, core_doc_id: str = "",
                      note: str = "") -> Optional[str]:
    doc_id = _gen_id("DOC")
    now = _now()
    conn = _get_conn()
    cur = conn.execute(
        "SELECT COALESCE(MAX(version),0) FROM claim_documents WHERE claim_ref=? AND doc_type=?",
        (claim_ref, doc_type))
    version = cur.fetchone()[0] + 1
    conn.execute("""
        INSERT INTO claim_documents
        (doc_id, claim_ref, doc_type, filename, file_size, mime_type,
         uploaded_by, uploaded_at, version, core_doc_id, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (doc_id, claim_ref, doc_type, filename, file_size, mime_type,
          uploaded_by, now, version, core_doc_id, note))
    conn.commit()
    conn.close()
    return doc_id


def get_documents(claim_ref: str) -> pd.DataFrame:
    conn = _get_conn()
    df = pd.read_sql(
        "SELECT * FROM claim_documents WHERE claim_ref=? ORDER BY uploaded_at DESC",
        conn, params=(claim_ref,))
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Settlements (module-level wrappers)
# ---------------------------------------------------------------------------

def recommend_settlement(claim_ref: str, amount: float, payee_name: str,
                         payee_type: str, recommended_by: str,
                         wht_rate: float = 0.0, note: str = "") -> Optional[str]:
    settlement_id = _gen_id("STL")
    now = _now()
    wht_amount = round(amount * wht_rate, 2)
    net_amount = round(amount - wht_amount, 2)
    conn = _get_conn()
    conn.execute("""
        INSERT INTO settlements
        (settlement_id, claim_ref, settlement_type, amount, payee_name, payee_type,
         wht_rate, wht_amount, net_amount, status,
         recommended_by, recommended_at, note)
        VALUES (?, ?, 'officer_recommend', ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
    """, (settlement_id, claim_ref, amount, payee_name, payee_type,
          wht_rate, wht_amount, net_amount, recommended_by, now, note))
    conn.commit()
    conn.close()
    return settlement_id


def approve_settlement(settlement_id: str, approved_by: str) -> bool:
    conn = _get_conn()
    now = _now()
    cur = conn.execute(
        "UPDATE settlements SET status='approved', approved_by=?, approved_at=? WHERE settlement_id=?",
        (approved_by, now, settlement_id))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def mark_settlement_paid(settlement_id: str, bank_ref: str) -> bool:
    conn = _get_conn()
    now = _now()
    cur = conn.execute(
        "UPDATE settlements SET status='paid', paid_at=?, bank_ref=? WHERE settlement_id=?",
        (now, bank_ref, settlement_id))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def get_settlements(claim_ref: str) -> pd.DataFrame:
    conn = _get_conn()
    df = pd.read_sql(
        "SELECT * FROM settlements WHERE claim_ref=? ORDER BY recommended_at ASC",
        conn, params=(claim_ref,))
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Module-level wrappers for methods used via `import core_api`
# ---------------------------------------------------------------------------

def is_configured() -> bool:
    """Return True when an external CORE_API_BASE_URL is set."""
    return bool(_CORE_API_BASE_URL)


def get_claim(claim_ref: str) -> Optional[dict]:
    """Fetch a single claim. Returns dict or None."""
    return core_api.get_claim(claim_ref)


def create_claim(**kwargs) -> bool:
    """Insert a claim row. Returns True on success."""
    return core_api.create_claim(**kwargs)


def get_claims(status_filter: str = "", assigned_to: str = "") -> list[dict]:
    return core_api.get_claims(status_filter, assigned_to)


def update_claim_status(claim_ref: str, to_status: str,
                        changed_by: str = "", note: str = "",
                        source: str = "portal") -> bool:
    return core_api.update_claim_status(claim_ref, to_status, changed_by, note, source)


def get_timeline(claim_ref: str) -> list[dict]:
    """Build a unified chronological timeline for a claim."""
    return core_api.get_timeline(claim_ref)


def invalidate_claim_cache(claim_ref: str) -> None:
    """Clear cached claim data."""
    core_api.invalidate_claim_cache(claim_ref)


def update_job_status(claim_ref: str, new_status: str, actor: str = "") -> bool:
    return core_api.update_job_status(claim_ref, new_status, actor)


def send_message(claim_ref: str, sent_by: str, recipient_type: str,
                 recipient_name: str, subject: str, body: str) -> Optional[str]:
    return core_api.send_message(claim_ref, sent_by, recipient_type, recipient_name, subject, body)


def post_claim(data: dict) -> bool:
    return core_api.post_claim(data)


def post_document(claim_ref: str, filename: str, mime_type: str,
                  file_bytes: bytes, doc_type: str = "") -> Optional[str]:
    return core_api.post_document(claim_ref, filename, mime_type, file_bytes, doc_type)


def get_disputes(stage_filter: str = "", urgency_filter: str = "",
                 search: str = "") -> list[dict]:
    return core_api.get_disputes(stage_filter, urgency_filter, search)


def log_audit(action: str, actor: str = "", detail: str = "") -> str:
    return core_api.log_audit(action, actor, detail)


def get_audit_log(limit: int = 200) -> pd.DataFrame:
    return core_api.get_audit_log(limit)


def get_sla_status(claim_ref: str, submitted_at: str) -> dict:
    return core_api.get_sla_status(claim_ref, submitted_at)


def record_status_change(claim_ref: str, to_status: str, from_status: str = "",
                         changed_by: str = "", source: str = "portal",
                         note: str = "") -> str:
    return core_api.record_status_change(claim_ref, to_status, from_status,
                                         changed_by, source, note)


# ---------------------------------------------------------------------------
# Reserve management (module-level wrappers)
# ---------------------------------------------------------------------------


def is_reinsurance_flag(claim_ref: str, api: CoreAPI) -> bool:
    """True when total incurred (reserves + settlements) exceeds threshold."""
    try:
        reserves = api.get_total_reserves(claim_ref) or 0
        settlements = sum(
            (s.get("amount") or 0)
            for s in api.get_settlements(claim_ref).to_dict('records') or []
        )
        return (reserves + settlements) > REINSURANCE_THRESHOLD
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Payment status (module-level wrapper)
# ---------------------------------------------------------------------------

def update_payment_status(claim_ref: str, data: dict) -> bool:
    """Record payment status / invoice tracking for a service provider claim."""
    return core_api.update_payment_status(claim_ref, data)


# ---------------------------------------------------------------------------
# Disputes & service payments (module-level wrappers)
# ---------------------------------------------------------------------------

def add_dispute(claim_ref: str, client_name: str = "",
                stage: str = "Repudiation Appeal", urgency: str = "normal",
                claim_amount: float = 0.0, advocate: str = "") -> str:
    """Create a dispute record. Returns dispute_id."""
    return core_api.add_dispute(claim_ref, client_name, stage, urgency,
                                claim_amount, advocate)


def get_service_payments(claim_ref: str = "") -> pd.DataFrame:
    """Return service payments, optionally filtered by claim_ref."""
    return core_api.get_service_payments(claim_ref)


def get_messages(claim_ref: str) -> list[dict]:
    """Return client messages for a claim."""
    return core_api.get_messages(claim_ref)
