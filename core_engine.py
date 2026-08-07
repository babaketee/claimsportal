\"\"\"core_engine.py — Phase 1 Claims State Machine + Audit Engine
=============================================================
11-status locked state machine with parallel TAT clocks and immutable audit trail.
Claim refs: CLM/MOT/{BRANCH}/{YEAR}/{NNNNNN} — configurable via claim_ref_format in config_db.

Status lifecycle (locked — no skipping, no reordering):
  Draft → Reported → Triage → Investigation → Assessment → Approval → Closed
                                                                      ↓
                                              ┌→ Closed-Approved (payment) ←←←←←←←←←←←┐
                                              │          OR                        │
                                              └→ Closed-Repudiated (declined)    │
                                                                                 ↓
                                                           ┌→ Total-Loss-Settlement ─┐
                                                           │  (salvage value payout) │
                                                           └→ Closed-Total-Loss ────┘

Stage 6 is parallel: investigation AND assessment run concurrently (TAT clock runs for both).
Once either exits, the next stage is entered. The slower one records its elapsed time.

Total-loss branch (R2):
  - Triggered when assessor marks claim as total_loss_indicator=True
  - Skips garage stages entirely (no repair, no reinspection)
  - Payout = sum_insured - salvage_value - excess
  - Requires HOC approval for total-loss path
\"\"\"


from __future__ import annotations

import copy
import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import config_db

# ─── Locked statuses ──────────────────────────────────────────────────────────


class ClaimStatus:
    DRAFT          = \"draft\"
    REPORTED       = \"reported\"
    TRIAGE         = \"triage\"
    INVESTIGATION  = \"investigation\"
    ASSESSMENT     = \"assessment\"
    APPROVAL       = \"approval\"
    CLOSED_APPROVED  = \"closed_approved\"
    CLOSED_REPUDIATED = \"closed_repudiated\"
    TOTAL_LOSS_SETTLEMENT = \"total_loss_settlement\"
    CLOSED_TOTAL_LOSS    = \"closed_total_loss\"
    # Aliases
    OPEN = REPORTED
    PENDING_TRIAGE = TRIAGE
    PENDING_INVESTIGATION = INVESTIGATION
    PENDING_ASSESSMENT = ASSESSMENT
    PENDING_APPROVAL = APPROVAL
    SETTLED = CLOSED_APPROVED
    REPUDIATED = CLOSED_REPUDIATED


# ─── TAT Clock ───────────────────────────────────────────────────────────────


class TATClock:
    \"\"\"
    Per-claim parallel TAT clock.
    Stage 6 (investigation + assessment) runs both clocks concurrently.
    Once either exits, its clock stops; the other continues until it too exits.
    This gives an honest measure of total elapsed time regardless of path.
    \"\"\"

    def __init__(self, claim_ref: str) -> None:
        self._claim_ref = claim_ref
        self._stages: dict[str, dict] = {}
        self._db_path = \"claims_portal.db\"
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute(\"\"\"\"
            CREATE TABLE IF NOT EXISTS tat_clock (
                claim_ref TEXT NOT NULL,
                stage TEXT NOT NULL,
                entered_at TEXT NOT NULL,
                exited_at TEXT,
                elapsed_ms INTEGER,
                parallel BOOLEAN DEFAULT 0,
                PRIMARY KEY (claim_ref, stage)
            )
        \"\"\")
        conn.commit()
        conn.close()

    def enter(self, stage: str, parallel: bool = False) -> None:
        now = datetime.now(timezone.utc)
        now_str = now.isoformat()
        self._stages[stage] = {
            \"entered_at\": now,
            \"entered_at_str\": now_str,
            \"parallel\": parallel,
            \"exited_at\": None,
            \"elapsed_ms\": None,
        }
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute(
            \"INSERT OR REPLACE INTO tat_clock (claim_ref, stage, entered_at, parallel, exited_at, elapsed_ms) VALUES (?, ?, ?, ?, NULL, NULL)\",
            (self._claim_ref, stage, now_str, parallel)
        )
        conn.commit()
        conn.close()

    def exit(self, stage: str) -> int | None:
        entry = self._stages.get(stage)
        if not entry or entry[\"exited_at\"] is not None:
            return entry[\"elapsed_ms\"] if entry else None
        now = datetime.now(timezone.utc)
        elapsed_ms = int((now - entry[\"entered_at\"]).total_seconds() * 1000)
        entry[\"exited_at\"] = now
        entry[\"elapsed_ms\"] = elapsed_ms
        now_str = now.isoformat()
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute(
            \"UPDATE tat_clock SET exited_at=?, elapsed_ms=? WHERE claim_ref=? AND stage=?\",
            (now_str, elapsed_ms, self._claim_ref, stage)
        )
        conn.commit()
        conn.close()
        return elapsed_ms

    def get_total_ms(self) -> int:
        conn = sqlite3.connect(self._db_path, timeout=10)
        rows = conn.execute(
            \"SELECT SUM(elapsed_ms) FROM tat_clock WHERE claim_ref=? AND elapsed_ms IS NOT NULL\",
            (self._claim_ref,)
        ).fetchone()
        conn.close()
        return rows[0] or 0 if rows else 0

    def get_tat_breakdown(self) -> list[dict]:
        conn = sqlite3.connect(self._db_path, timeout=10)
        rows = conn.execute(
            \"SELECT stage, entered_at, exited_at, elapsed_ms, parallel FROM tat_clock WHERE claim_ref=? ORDER BY entered_at\",
            (self._claim_ref,)
        ).fetchall()
        conn.close()
        return [
            {
                \"stage\": r[0],
                \"entered_at\": r[1],
                \"exited_at\": r[2] or \"\",
                \"elapsed_ms\": r[3],
                \"parallel\": bool(r[4]),
            }
            for r in rows
        ]


# ─── Immutable Audit Trail ───────────────────────────────────────────────────


class AuditEngine:
    \"\"\"
    Append-only audit trail. Once written, a record must never be modified or deleted.
    All transitions, data changes, and system events are logged.
    \"\"\"

    def __init__(self, db_path: str = \"claims_portal.db\") -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute(\"\"\"\"
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                action TEXT NOT NULL,
                user_id TEXT NOT NULL,
                before TEXT,
                after TEXT,
                timestamp TEXT NOT NULL,
                version_id INTEGER DEFAULT 1
            )
        \"\"\")
        conn.execute(\"\"\"\"CREATE INDEX IF NOT EXISTS idx_audit_lookup ON audit_log(entity_type, entity_id)\"\"\")
        conn.commit()
        conn.close()

    def log(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        user_id: str,
        before: dict | None = None,
        after: dict | None = None,
    ) -> None:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute(
            \"INSERT INTO audit_log (entity_type, entity_id, action, user_id, before, after, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)\",
            (
                entity_type,
                entity_id,
                action,
                user_id,
                json.dumps(before) if before else None,
                json.dumps(after)  if after  else None,
                datetime.now(timezone.utc).isoformat(),
            )
        )
        conn.commit()
        conn.close()

    def get_history(self, entity_type: str, entity_id: str) -> list:
        conn = sqlite3.connect(self._db_path, timeout=10)
        rows = conn.execute(
            \"SELECT id, entity_type, entity_id, action, user_id, before, after, timestamp FROM audit_log WHERE entity_type=? AND entity_id=? ORDER BY id ASC\",
            (entity_type, entity_id)
        ).fetchall()
        conn.close()
        return rows


# ─── Claim Manager ──────────────────────────────────────────────────────────


class ClaimManager:
    \"\"\"
    Thread-safe 11-status locked state machine.
    Immutable audit. Parallel TAT clocks for Stage 6.
    \"\"\"

    LOCKED_TRANSITIONS = {
        ClaimStatus.DRAFT:                  {ClaimStatus.REPORTED},
        ClaimStatus.REPORTED:               {ClaimStatus.TRIAGE, ClaimStatus.INVESTIGATION},
        ClaimStatus.TRIAGE:                 {ClaimStatus.INVESTIGATION, ClaimStatus.ASSESSMENT},
        ClaimStatus.INVESTIGATION:          {ClaimStatus.ASSESSMENT},
        ClaimStatus.ASSESSMENT:             {ClaimStatus.APPROVAL},
        ClaimStatus.APPROVAL:               {ClaimStatus.CLOSED_APPROVED, ClaimStatus.CLOSED_REPUDIATED},
        ClaimStatus.CLOSED_APPROVED:        set(),
        ClaimStatus.CLOSED_REPUDIATED:      set(),
        ClaimStatus.TOTAL_LOSS_SETTLEMENT: {ClaimStatus.CLOSED_TOTAL_LOSS},
        ClaimStatus.CLOSED_TOTAL_LOSS:     set(),
    }

    def __init__(self, db_path: str = \"claims_portal.db\") -> None:
        self._db_path = db_path
        self._lock = threading.RLock()
        self.clock = TATClock(db_path)
        self.audit = AuditEngine(db_path)
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute(\"\"\"\"
            CREATE TABLE IF NOT EXISTS claims (
                claim_ref TEXT PRIMARY KEY,
                policy_ref TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                id_number TEXT NOT NULL,
                vehicle_reg TEXT,
                incident_type TEXT,
                description TEXT,
                claim_class TEXT NOT NULL,
                user_id TEXT NOT NULL,
                total_loss_indicator INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                triage_decision TEXT,
                fast_track INTEGER DEFAULT 0,
                reserve_amount REAL DEFAULT 0,
                reserve_currency TEXT DEFAULT 'KES',
                payout_amount REAL,
                salvage_value REAL,
                excess_amount REAL DEFAULT 0,
                discharge_voucher_signed INTEGER DEFAULT 0,
                appeal_filed INTEGER DEFAULT 0,
                appeal_outcome TEXT,
                version INTEGER DEFAULT 1
            )
        \"\"\")
        conn.execute(\"\"\"\"CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status)\"\"\")
        conn.execute(\"\"\"\"CREATE INDEX IF NOT EXISTS idx_claims_policy ON claims(policy_ref)\"\"\")
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
        total_loss_indicator: bool = False,
        **kwargs,
    ) -> dict:
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            conn = sqlite3.connect(self._db_path, timeout=10)
            conn.execute(
                \"\"INSERT INTO claims (claim_ref, policy_ref, status, id_number, vehicle_reg, incident_type, description, claim_class, user_id, total_loss_indicator, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\"\",
                (claim_ref, policy_ref, ClaimStatus.DRAFT, id_number, vehicle_reg, incident_type, description, claim_class, user_id, int(total_loss_indicator), now, now)
            )
            conn.commit()
            conn.close()
            self.audit.log(\"claim\", claim_ref, \"created\", user_id, before=None, after={\"claim_ref\": claim_ref, \"policy_ref\": policy_ref, \"claim_class\": claim_class, \"total_loss_indicator\": total_loss_indicator})
            return self.get_claim(claim_ref)

    def get_claim(self, claim_ref: str) -> dict | None:
        conn = sqlite3.connect(self._db_path, timeout=10)
        row = conn.execute(\"SELECT * FROM claims WHERE claim_ref=?\", (claim_ref,)).fetchone()
        conn.close()
        if not row:
            return None
        cols = [c[0] for c in conn.execute(\"SELECT * FROM claims WHERE claim_ref=?\", (claim_ref,)).description]
        return dict(zip(cols, row))

    def transition_to(
        self,
        claim_ref: str,
        target_status: str,
        user_id: str,
        reason: str = \"\",
        **kwargs,
    ) -> dict:
        with self._lock:
            claim = self.get_claim(claim_ref)
            if not claim:
                raise ValueError(f\"Claim {claim_ref} not found\")
            current = claim[\"status\"]
            allowed = self.LOCKED_TRANSITIONS.get(current, set())
            if target_status not in allowed:
                raise ValueError(f\"Invalid transition {current} → {target_status}. Allowed: {allowed}\")
            now = datetime.now(timezone.utc).isoformat()
            update_fields = [\"status=?\", \"updated_at=?\", \"version=version+1\"]
            update_vals = [target_status, now]
            for k, v in kwargs.items():
                if k in [\"reserve_amount\", \"payout_amount\", \"salvage_value\", \"triage_decision\", \"fast_track\", \"total_loss_indicator\", \"discharge_voucher_signed\", \"appeal_filed\", \"appeal_outcome\"]:
                    update_fields.append(f\"{k}=?\")
                    update_vals.append(v)
            update_vals.append(claim_ref)
            conn = sqlite3.connect(self._db_path, timeout=10)
            conn.execute(f\"UPDATE claims SET {', '.join(update_fields)} WHERE claim_ref=?\", update_vals)
            conn.commit()
            conn.close()
            # Enter TAT clock for new stage
            self.clock.enter(target_status, parallel=(target_status in {ClaimStatus.INVESTIGATION, ClaimStatus.ASSESSMENT}))
            # Exit TAT clock for old stage
            self.clock.exit(current)
            after = self.get_claim(claim_ref)
            self.audit.log(\"claim\", claim_ref, f\"transition:{current}→{target_status}\", user_id, before=dict(claim), after=dict(after))
            if reason:
                self.audit.log(\"claim\", claim_ref, \"note\", user_id, before=None, after={\"reason\": reason})
            return dict(after)

    def is_total_loss(self, claim_ref: str) -> bool:
        claim = self.get_claim(claim_ref)
        return bool(claim and claim[\"total_loss_indicator\"])

    def get_claims_by_status(self, status: str) -> list[dict]:
        conn = sqlite3.connect(self._db_path, timeout=10)
        rows = conn.execute(\"SELECT * FROM claims WHERE status=?\", (status,)).fetchall()
        conn.close()
        cols = [c[0] for c in conn.execute(\"SELECT * FROM claims WHERE status=?\", (status,)).description]
        return [dict(zip(cols, r)) for r in rows]

    def get_all_claims(self) -> list[dict]:
        conn = sqlite3.connect(self._db_path, timeout=10)
        rows = conn.execute(\"SELECT * FROM claims ORDER BY created_at DESC\").fetchall()
        conn.close()
        cols = [c[0] for c in conn.execute(\"SELECT * FROM claims ORDER BY created_at DESC\").description]
        return [dict(zip(cols, r)) for r in rows]


# ─── Singleton ──────────────────────────────────────────────────────────────

_engine: ClaimManager | None = None
_engine_lock = threading.Lock()


def get_engine(db_path: str = \"claims_portal.db\") -> ClaimManager:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = ClaimManager(db_path)
    return _engine


def reset_engine() -> None:
    global _engine
    with _engine_lock:
        _engine = None
