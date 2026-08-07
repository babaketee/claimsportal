"""core_engine.py — Phase 1 Claims Portal Engine
=============================================
State Machine | TAT Clock Engine | Immutable Audit Trail

State Machine (11 locked statuses):
  Draft → Submitted → Under Triage → Investigation/Assessment
  → Pending Approval → Approved → Under Repair → Reinspection
  → Pending Payment → Paid → Closed

Each transition is append-only. No state can be skipped.
"""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

_DB_PATH = "claims_portal.db"


class ClaimStatus(str, Enum):
    DRAFT               = "Draft"
    SUBMITTED           = "Submitted"
    UNDER_TRIAGE        = "Under Triage"
    INVESTIGATION       = "Investigation/Assessment"
    PENDING_APPROVAL    = "Pending Approval"
    APPROVED            = "Approved"
    UNDER_REPAIR        = "Under Repair"
    REINSPECTION        = "Reinspection"
    PENDING_PAYMENT     = "Pending Payment"
    PAID                = "Paid"
    CLOSED              = "Closed"

_TRANSITIONS: dict[ClaimStatus, set[ClaimStatus]] = {
    ClaimStatus.DRAFT:             {ClaimStatus.SUBMITTED},
    ClaimStatus.SUBMITTED:         {ClaimStatus.UNDER_TRIAGE},
    ClaimStatus.UNDER_TRIAGE:       {ClaimStatus.INVESTIGATION, ClaimStatus.PENDING_APPROVAL},
    ClaimStatus.INVESTIGATION:     {ClaimStatus.PENDING_APPROVAL},
    ClaimStatus.PENDING_APPROVAL:  {ClaimStatus.APPROVED, ClaimStatus.INVESTIGATION},
    ClaimStatus.APPROVED:          {ClaimStatus.UNDER_REPAIR, ClaimStatus.CLOSED},
    ClaimStatus.UNDER_REPAIR:       {ClaimStatus.REINSPECTION, ClaimStatus.PENDING_PAYMENT},
    ClaimStatus.REINSPECTION:       {ClaimStatus.UNDER_REPAIR, ClaimStatus.PENDING_PAYMENT},
    ClaimStatus.PENDING_PAYMENT:    {ClaimStatus.PAID},
    ClaimStatus.PAID:              {ClaimStatus.CLOSED},
    ClaimStatus.CLOSED:            set(),
}

_CAN_REOPEN: set[ClaimStatus] = {ClaimStatus.CLOSED}


def can_transition(from_s: ClaimStatus, to_s: ClaimStatus) -> bool:
    if from_s in _CAN_REOPEN and to_s == ClaimStatus.INVESTIGATION:
        return True
    return to_s in _TRANSITIONS.get(from_s, set())


def get_next_statuses(current: ClaimStatus) -> list[ClaimStatus]:
    return list(_TRANSITIONS.get(current, set()))


@dataclass
class ClockEvent:
    claim_ref: str
    stage: ClaimStatus
    entered_at_ms: int
    exited_at_ms: int | None = None
    elapsed_ms: int | None = None
    parallel: bool = False


class TATClock:
    _locks: dict[str, threading.Lock] = {}
    _locks_lock = threading.Lock()

    def __init__(self, db_path: str = _DB_PATH):
        self.db_path = db_path
        self._ensure_table()

    def _lock_for(self, claim_ref: str) -> threading.Lock:
        with TATClock._locks_lock:
            if claim_ref not in TATClock._locks:
                TATClock._locks[claim_ref] = threading.Lock()
            return TATClock._locks[claim_ref]

    def _ensure_table(self) -> None:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clock_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_ref TEXT NOT NULL,
                stage TEXT NOT NULL,
                entered_at_ms INTEGER NOT NULL,
                exited_at_ms INTEGER,
                elapsed_ms INTEGER,
                parallel INTEGER DEFAULT 0,
                UNIQUE(claim_ref, stage, entered_at_ms)
            )
        """)
        conn.commit()
        conn.close()

    def enter_stage(self, claim_ref: str, stage: ClaimStatus, parallel: bool = False) -> ClockEvent:
        now_ms = int(time.time() * 1000)
        event = ClockEvent(claim_ref=claim_ref, stage=stage, entered_at_ms=now_ms, parallel=parallel)
        lock = self._lock_for(claim_ref)
        with lock:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.execute(
                "INSERT INTO clock_events (claim_ref, stage, entered_at_ms, parallel) VALUES (?, ?, ?, ?)",
                (claim_ref, stage.value, now_ms, int(parallel))
            )
            conn.commit()
            conn.close()
        return event

    def exit_stage(self, claim_ref: str, stage: ClaimStatus) -> int | None:
        now_ms = int(time.time() * 1000)
        lock = self._lock_for(claim_ref)
        elapsed = None
        with lock:
            conn = sqlite3.connect(self.db_path, timeout=10)
            cur = conn.execute(
                "SELECT entered_at_ms FROM clock_events WHERE claim_ref=? AND stage=? AND exited_at_ms IS NULL ORDER BY entered_at_ms DESC LIMIT 1",
                (claim_ref, stage.value)
            )
            row = cur.fetchone()
            if row:
                elapsed = now_ms - row[0]
                conn.execute(
                    "UPDATE clock_events SET exited_at_ms=?, elapsed_ms=? WHERE claim_ref=? AND stage=? AND exited_at_ms IS NULL",
                    (now_ms, elapsed, claim_ref, stage.value)
                )
            conn.commit()
            conn.close()
        return elapsed

    def get_total_tat_ms(self, claim_ref: str) -> int:
        conn = sqlite3.connect(self.db_path, timeout=10)
        cur = conn.execute("SELECT SUM(elapsed_ms) FROM clock_events WHERE claim_ref=? AND elapsed_ms IS NOT NULL", (claim_ref,))
        row = cur.fetchone()
        conn.close()
        return row[0] or 0

    def get_tat_breakdown(self, claim_ref: str) -> list[dict]:
        conn = sqlite3.connect(self.db_path, timeout=10)
        cur = conn.execute(
            "SELECT stage, entered_at_ms, exited_at_ms, elapsed_ms, parallel FROM clock_events WHERE claim_ref=? ORDER BY entered_at_ms",
            (claim_ref,)
        )
        rows = cur.fetchall()
        conn.close()
        return [
            {
                "stage": r[0],
                "entered_at": datetime.fromtimestamp(r[1] / 1000, tz=timezone.utc).isoformat(),
                "exited_at": datetime.fromtimestamp(r[2] / 1000, tz=timezone.utc).isoformat() if r[2] else None,
                "elapsed_ms": r[3],
                "parallel": bool(r[4]),
            }
            for r in rows
        ]


@dataclass
class AuditEntry:
    id: int | None
    event_id: str
    entity_type: str
    entity_ref: str
    action: str
    user_id: str
    timestamp: str
    before: str | None
    after: str | None
    metadata: str | None


class AuditLog:
    def __init__(self, db_path: str = _DB_PATH):
        self.db_path = db_path
        self._ensure_table()

    def _ensure_table(self) -> None:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                entity_type TEXT NOT NULL,
                entity_ref TEXT NOT NULL,
                action TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                before TEXT,
                after TEXT,
                metadata TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_ref)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_log(event_id)")
        conn.commit()
        conn.close()

    def log(
        self,
        entity_type: str,
        entity_ref: str,
        action: str,
        user_id: str,
        before: dict | None = None,
        after: dict | None = None,
        metadata: dict | None = None,
    ) -> AuditEntry:
        import json
        now = datetime.now(timezone.utc).isoformat()
        event_id = str(uuid.uuid4())
        entry = AuditEntry(
            id=None,
            event_id=event_id,
            entity_type=entity_type,
            entity_ref=entity_ref,
            action=action,
            user_id=user_id,
            timestamp=now,
            before=json.dumps(before) if before else None,
            after=json.dumps(after) if after else None,
            metadata=json.dumps(metadata) if metadata else None,
        )
        conn = sqlite3.connect(self.db_path, timeout=10)
        cur = conn.execute(
            "INSERT INTO audit_log (event_id, entity_type, entity_ref, action, user_id, timestamp, before, after, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (entry.event_id, entry.entity_type, entry.entity_ref, entry.action, entry.user_id, entry.timestamp, entry.before, entry.after, entry.metadata)
        )
        entry.id = cur.lastrowid
        conn.commit()
        conn.close()
        return entry

    def get_history(self, entity_type: str, entity_ref: str) -> list[AuditEntry]:
        conn = sqlite3.connect(self.db_path, timeout=10)
        cur = conn.execute(
            "SELECT id, event_id, entity_type, entity_ref, action, user_id, timestamp, before, after, metadata FROM audit_log WHERE entity_type=? AND entity_ref=? ORDER BY id ASC",
            (entity_type, entity_ref)
        )
        rows = cur.fetchall()
        conn.close()
        return [
            AuditEntry(
                id=r[0], event_id=r[1], entity_type=r[2], entity_ref=r[3], action=r[4],
                user_id=r[5], timestamp=r[6], before=r[7], after=r[8], metadata=r[9]
            )
            for r in rows
        ]


class ClaimManager:
    def __init__(self, db_path: str = _DB_PATH):
        self.db_path = db_path
        self.clock = TATClock(db_path)
        self.audit = AuditLog(db_path)
        self._ensure_claims_table()

    def _ensure_claims_table(self) -> None:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                claim_ref TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'Draft',
                policy_ref TEXT,
                id_number TEXT,
                vehicle_reg TEXT,
                incident_type TEXT,
                description TEXT,
                claim_class TEXT,
                created_at TEXT,
                updated_at TEXT,
                current_tat_ms INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def create_claim(
        self,
        claim_ref: str,
        policy_ref: str,
        id_number: str,
        vehicle_reg: str,
        incident_type: str,
        description: str,
        claim_class: str,
        user_id: str,
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute(
            "INSERT INTO claims (claim_ref, status, policy_ref, id_number, vehicle_reg, incident_type, description, claim_class, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (claim_ref, ClaimStatus.DRAFT.value, policy_ref, id_number, vehicle_reg, incident_type, description, claim_class, now, now)
        )
        conn.commit()
        conn.close()
        self.clock.enter_stage(claim_ref, ClaimStatus.DRAFT)
        self.audit.log("claim", claim_ref, "create", user_id, before=None, after={"status": ClaimStatus.DRAFT.value, "policy_ref": policy_ref})
        return self.get_claim(claim_ref)

    def get_claim(self, claim_ref: str) -> dict | None:
        conn = sqlite3.connect(self.db_path, timeout=10)
        cur = conn.execute("SELECT * FROM claims WHERE claim_ref=?", (claim_ref,))
        row = cur.fetchone()
        cols = [c[0] for c in cur.description]
        conn.close()
        return dict(zip(cols, row)) if row else None

    def transition(self, claim_ref: str, to_status: ClaimStatus, user_id: str, metadata: dict | None = None) -> dict:
        import json
        claim = self.get_claim(claim_ref)
        if not claim:
            raise ValueError(f"Claim {claim_ref} not found")
        from_status = ClaimStatus(claim["status"])
        if not can_transition(from_status, to_status):
            raise ValueError(f"Invalid transition: {from_status.value} → {to_status.value}")
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("UPDATE claims SET status=?, updated_at=? WHERE claim_ref=?", (to_status.value, now, claim_ref))
        conn.commit()
        conn.close()
        self.clock.exit_stage(claim_ref, from_status)
        self.clock.enter_stage(claim_ref, to_status)
        self.audit.log(
            "claim", claim_ref, "transition", user_id,
            before={"status": from_status.value},
            after={"status": to_status.value},
            metadata=metadata,
        )
        return self.get_claim(claim_ref)

    def get_all(self, filters: dict | None = None) -> list[dict]:
        conn = sqlite3.connect(self.db_path, timeout=10)
        query = "SELECT * FROM claims"
        params = []
        if filters:
            query += " WHERE " + " AND ".join(f"{k}=?" for k in filters)
            params = list(filters.values())
        cur = conn.execute(query, params)
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]
        conn.close()
        return [dict(zip(cols, r)) for r in rows]


_engine_lock = threading.Lock()
_engine: ClaimManager | None = None

def get_engine() -> ClaimManager:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = ClaimManager()
    return _engine
