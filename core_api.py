"""Core API client — local SQLite + optional external REST core.

Local SQLite database: claims_operations.db (separate from claims_history.db
which is read-only audit log). Created automatically.

Tables added here:
  reserves          — claim reserve amounts (initial + supplemental)
  diary_entries     — follow-up tasks with due dates
  communications    — SMS/call/email log per claim
  expert_assignments— assessor/garage/investigator assignments
  claim_documents   — document metadata (actual files go to core API)

All functions are no-ops when CORE_API_BASE_URL is not configured.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# SQLite setup
# ---------------------------------------------------------------------------

_DB_PATH = "claims_operations.db"


def _get_conn():
    import sqlite3
    return sqlite3.connect(_DB_PATH, check_same_thread=False)


def _init_db():
    import sqlite3
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS reserves (
        reserve_id      TEXT PRIMARY KEY,
        claim_ref       TEXT NOT NULL,
        reserve_type    TEXT NOT NULL,   -- initial | supplemental
        amount          REAL NOT NULL,
        purpose         TEXT,             -- assessment | repair | legal | other
        created_by      TEXT,
        created_at      TEXT NOT NULL,
        approved_by     TEXT,
        approved_at     TEXT,
        status          TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | released
        note            TEXT
    );

    CREATE TABLE IF NOT EXISTS diary_entries (
        entry_id        TEXT PRIMARY KEY,
        claim_ref       TEXT NOT NULL,
        task            TEXT NOT NULL,
        due_date        TEXT NOT NULL,
        assigned_to     TEXT,
        priority        TEXT NOT NULL DEFAULT 'normal',  -- low | normal | high | urgent
        status          TEXT NOT NULL DEFAULT 'open',   -- open | done | overdue
        created_by      TEXT,
        created_at      TEXT NOT NULL,
        completed_at    TEXT,
        note            TEXT
    );

    CREATE TABLE IF NOT EXISTS communications (
        comm_id         TEXT PRIMARY KEY,
        claim_ref       TEXT NOT NULL,
        channel         TEXT NOT NULL,    -- sms | call | email | letter | whatsapp
        direction       TEXT NOT NULL,    -- inbound | outbound
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
        expert_type     TEXT NOT NULL,    -- assessor | garage | investigator | loss_adjuster
        expert_name     TEXT NOT NULL,
        expert_phone    TEXT,
        expert_company  TEXT,
        status          TEXT NOT NULL DEFAULT 'pending',  -- pending | accepted | in_progress | completed | rejected
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
        doc_type        TEXT NOT NULL,    -- police_abstract | medical_report | invoice | surveyor_report | demand_letter | id_document | photo | other
        filename        TEXT NOT NULL,
        file_size       INTEGER,
        mime_type       TEXT,
        uploaded_by     TEXT,
        uploaded_at     TEXT NOT NULL,
        version         INTEGER NOT NULL DEFAULT 1,
        core_doc_id     TEXT,             -- ID returned by core API post_document
        note            TEXT
    );

    CREATE TABLE IF NOT EXISTS settlements (
        settlement_id   TEXT PRIMARY KEY,
        claim_ref       TEXT NOT NULL,
        settlement_type TEXT NOT NULL,    -- officer_recommend | hoc_approval | finance_payment
        amount          REAL NOT NULL,
        payee_name      TEXT,
        payee_type      TEXT,             -- assessor | garage | investigator | spare_parts | third_party | insured
        wht_rate        REAL,             -- withholding tax rate (e.g. 0.05)
        wht_amount      REAL,
        net_amount      REAL,
        status          TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected | paid | cancelled
        recommended_by  TEXT,
        recommended_at  TEXT,
        approved_by     TEXT,
        approved_at     TEXT,
        paid_at         TEXT,
        bank_ref        TEXT,
        note            TEXT
    );
    """)
    conn.commit()
    conn.close()


# Init on module load
try:
    _init_db()
except Exception:
    pass


# ---------------------------------------------------------------------------
# Reserve management
# ---------------------------------------------------------------------------

def set_reserve(claim_ref: str, reserve_type: str, amount: float,
                purpose: str, created_by: str,
                note: str = "") -> Optional[str]:
    """Create a new reserve (initial or supplemental). Returns reserve_id."""
    if not claim_ref or amount <= 0:
        return None
    reserve_id = f"RSV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now().isoformat()
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
    now = datetime.now().isoformat()
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
    now = datetime.now().isoformat()
    cur = conn.execute(
        "UPDATE reserves SET status='released', approved_by=?, approved_at=?, note=? WHERE reserve_id=?",
        (released_by, now, note, reserve_id)
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def get_reserves(claim_ref: str) -> pd.DataFrame:
    """Return all reserves for a claim."""
    conn = _get_conn()
    df = pd.read_sql(
        "SELECT * FROM reserves WHERE claim_ref=? ORDER BY created_at ASC",
        conn, params=(claim_ref,)
    )
    conn.close()
    return df


def get_total_reserves(claim_ref: str) -> float:
    conn = _get_conn()
    cur = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM reserves WHERE claim_ref=? AND status='approved'",
        (claim_ref,)
    )
    total = cur.fetchone()[0]
    conn.close()
    return float(total)


# ---------------------------------------------------------------------------
# Diary entries
# ---------------------------------------------------------------------------

def add_diary_entry(claim_ref: str, task: str, due_date: str,
                    assigned_to: str, priority: str, created_by: str,
                    note: str = "") -> Optional[str]:
    """Add a follow-up diary entry. due_date in YYYY-MM-DD format."""
    entry_id = f"DRY-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now().isoformat()
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
    now = datetime.now().isoformat()
    cur = conn.execute(
        "UPDATE diary_entries SET status='done', completed_at=? WHERE entry_id=?",
        (now, entry_id)
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def get_diary_entries(claim_ref: str) -> pd.DataFrame:
    conn = _get_conn()
    df = pd.read_sql(
        "SELECT * FROM diary_entries WHERE claim_ref=? ORDER BY due_date ASC",
        conn, params=(claim_ref,)
    )
    conn.close()
    return df


def get_overdue_entries(assigned_to: Optional[str] = None) -> pd.DataFrame:
    today = datetime.now().strftime('%Y-%m-%d')
    conn = _get_conn()
    if assigned_to:
        df = pd.read_sql(
            "SELECT * FROM diary_entries WHERE status='open' AND due_date < ? AND assigned_to=? ORDER BY due_date",
            conn, params=(today, assigned_to)
        )
    else:
        df = pd.read_sql(
            "SELECT * FROM diary_entries WHERE status='open' AND due_date < ? ORDER BY due_date",
            conn, params=(today,)
        )
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Communications log
# ---------------------------------------------------------------------------

def log_communication(claim_ref: str, channel: str, direction: str,
                      summary: str, created_by: str,
                      contact_name: str = "", contact_phone: str = "",
                      outcome: str = "", consent: bool = True) -> Optional[str]:
    """Log an SMS/call/email/etc. against a claim."""
    comm_id = f"COM-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now().isoformat()
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
        conn, params=(claim_ref,)
    )
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Expert assignments
# ---------------------------------------------------------------------------

def assign_expert(claim_ref: str, expert_type: str, expert_name: str,
                  expert_phone: str, expert_company: str,
                  assigned_by: str, estimated_cost: float = 0,
                  note: str = "") -> Optional[str]:
    """Assign an assessor/garage/investigator to a claim."""
    assignment_id = f"ASN-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now().isoformat()
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
    now = datetime.now().isoformat()
    conn = _get_conn()
    if status == 'completed' and actual_cost is not None:
        cur = conn.execute(
            "UPDATE expert_assignments SET status=?, completed_at=?, actual_cost=? WHERE assignment_id=?",
            (status, now, actual_cost, assignment_id)
        )
    elif status == 'accepted':
        cur = conn.execute(
            "UPDATE expert_assignments SET status=?, accepted_at=? WHERE assignment_id=?",
            (status, now, assignment_id)
        )
    else:
        cur = conn.execute(
            "UPDATE expert_assignments SET status=? WHERE assignment_id=?",
            (status, assignment_id)
        )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def get_assignments(claim_ref: str) -> pd.DataFrame:
    conn = _get_conn()
    df = pd.read_sql(
        "SELECT * FROM expert_assignments WHERE claim_ref=? ORDER BY assigned_at DESC",
        conn, params=(claim_ref,)
    )
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Document metadata
# ---------------------------------------------------------------------------

def register_document(claim_ref: str, doc_type: str, filename: str,
                      file_size: int, mime_type: str,
                      uploaded_by: str, core_doc_id: str = "",
                      note: str = "") -> Optional[str]:
    """Register a document's metadata. Actual file content goes to core API."""
    doc_id = f"DOC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now().isoformat()
    conn = _get_conn()
    # Check for existing version of same type
    cur = conn.execute(
        "SELECT COALESCE(MAX(version),0) FROM claim_documents WHERE claim_ref=? AND doc_type=?",
        (claim_ref, doc_type)
    )
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
        conn, params=(claim_ref,)
    )
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Settlements
# ---------------------------------------------------------------------------

def recommend_settlement(claim_ref: str, amount: float, payee_name: str,
                         payee_type: str, recommended_by: str,
                         wht_rate: float = 0.0,
                         note: str = "") -> Optional[str]:
    """Officer recommends a settlement for HoC approval."""
    settlement_id = f"STL-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now().isoformat()
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
    now = datetime.now().isoformat()
    cur = conn.execute(
        "UPDATE settlements SET status='approved', approved_by=?, approved_at=? WHERE settlement_id=?",
        (approved_by, now, settlement_id)
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def mark_settlement_paid(settlement_id: str, bank_ref: str) -> bool:
    conn = _get_conn()
    now = datetime.now().isoformat()
    cur = conn.execute(
        "UPDATE settlements SET status='paid', paid_at=?, bank_ref=? WHERE settlement_id=?",
        (now, bank_ref, settlement_id)
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def get_settlements(claim_ref: str) -> pd.DataFrame:
    conn = _get_conn()
    df = pd.read_sql(
        "SELECT * FROM settlements WHERE claim_ref=? ORDER BY recommended_at ASC",
        conn, params=(claim_ref,)
    )
    conn.close()
    return df


# ---------------------------------------------------------------------------
# SLA helpers
# ---------------------------------------------------------------------------

def get_sla_status(claim_ref: str, submitted_at: str) -> dict:
    """Return SLA timers for a claim. Returns {acknowledged_sla, settlement_sla} with status."""
    submitted = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))
    ack_deadline = submitted + timedelta(days=14)
    settle_deadline = submitted + timedelta(days=30)
    now = datetime.now()
    acknowledged = now >= ack_deadline
    settled = now >= settle_deadline
    return {
        "acknowledged_overdue": acknowledged,
        "settlement_overdue": settled,
        "ack_deadline": ack_deadline.strftime("%Y-%m-%d"),
        "settle_deadline": settle_deadline.strftime("%Y-%m-%d"),
        "days_to_ack": max(0, (ack_deadline - now).days),
        "days_to_settle": max(0, (settle_deadline - now).days),
    }
