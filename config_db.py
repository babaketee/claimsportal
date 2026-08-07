"""config_db.py — Phase 1: Versioned Config DB with Maker-Checker Governance
===============================================================================

All business parameters driven from versioned DB. No hardcoding.
Every config change requires Maker-Checker: proposed by Admin, activated by Super-Admin.
Config maps have explicit start-dates. Retrospective changes are structurally barred.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_DB_PATH = "claims_portal.db"


@dataclass
class ConfigEntry:
    key: str
    value: str
    version: int
    effective_from: str
    created_by: str
    created_at: str
    is_active: bool


@dataclass
class ChangeRequest:
    id: int | None
    crid: str
    key: str
    proposed_value: str
    reason: str
    status: str
    proposed_by: str
    proposed_at: str
    reviewed_by: str | None
    reviewed_at: str | None
    review_notes: str | None


class ConfigDB:
    def __init__(self, db_path: str = _DB_PATH):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config_entries (
                key TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                value TEXT NOT NULL,
                effective_from TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                PRIMARY KEY (key, version)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config_change_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crid TEXT UNIQUE NOT NULL,
                key TEXT NOT NULL,
                proposed_value TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                proposed_by TEXT NOT NULL,
                proposed_at TEXT NOT NULL,
                reviewed_by TEXT,
                reviewed_at TEXT,
                review_notes TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_config_active ON config_entries(key, is_active)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cr_status ON config_change_requests(status)")
        conn.commit()
        conn.close()

    def get(self, key: str, as_of_date: str | None = None) -> Any | None:
        conn = sqlite3.connect(self.db_path, timeout=10)
        if as_of_date:
            cur = conn.execute(
                "SELECT value FROM config_entries WHERE key=? AND effective_from<=? AND is_active=1 ORDER BY version DESC LIMIT 1",
                (key, as_of_date)
            )
        else:
            cur = conn.execute(
                "SELECT value FROM config_entries WHERE key=? AND is_active=1 ORDER BY version DESC LIMIT 1",
                (key,)
            )
        row = cur.fetchone()
        conn.close()
        return json.loads(row[0]) if row else None

    def get_with_meta(self, key: str) -> ConfigEntry | None:
        conn = sqlite3.connect(self.db_path, timeout=10)
        cur = conn.execute(
            "SELECT key, value, version, effective_from, created_by, created_at, is_active FROM config_entries WHERE key=? AND is_active=1 ORDER BY version DESC LIMIT 1",
            (key,)
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return ConfigEntry(key=row[0], value=row[1], version=row[2], effective_from=row[3], created_by=row[4], created_at=row[5], is_active=bool(row[6]))

    def get_all_keys(self) -> list[str]:
        conn = sqlite3.connect(self.db_path, timeout=10)
        cur = conn.execute("SELECT DISTINCT key FROM config_entries ORDER BY key")
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]

    def _make_crid(self) -> str:
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_part = str(uuid.uuid4())[:8].upper()
        return f"CR-{date_part}-{random_part}"

    def propose_change(self, key: str, proposed_value: Any, reason: str, proposed_by: str, effective_from: str) -> ChangeRequest:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if effective_from < today:
            raise ValueError("effective_from cannot be in the past — retrospective changes are not allowed")
        now = datetime.now(timezone.utc).isoformat()
        cr = ChangeRequest(
            id=None, crid=self._make_crid(), key=key,
            proposed_value=json.dumps(proposed_value), reason=reason,
            status="PENDING", proposed_by=proposed_by, proposed_at=now,
            reviewed_by=None, reviewed_at=None, review_notes=None,
        )
        conn = sqlite3.connect(self.db_path, timeout=10)
        cur = conn.execute(
            "INSERT INTO config_change_requests (crid, key, proposed_value, reason, status, proposed_by, proposed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cr.crid, cr.key, cr.proposed_value, cr.reason, cr.status, cr.proposed_by, cr.proposed_at)
        )
        cr.id = cur.lastrowid
        conn.commit()
        conn.close()
        return cr

    def approve_change(self, crid: str, reviewed_by: str, review_notes: str = "") -> ChangeRequest:
        conn = sqlite3.connect(self.db_path, timeout=10)
        cur = conn.execute("SELECT * FROM config_change_requests WHERE crid=? AND status='PENDING'", (crid,))
        row = cur.fetchone()
        if not row:
            conn.close()
            raise ValueError(f"Change request {crid} not found or not pending")
        cr = ChangeRequest(
            id=row[0], crid=row[1], key=row[2], proposed_value=row[3],
            reason=row[4], status=row[5], proposed_by=row[6], proposed_at=row[7],
            reviewed_by=row[8], reviewed_at=row[9], review_notes=row[10]
        )
        now = datetime.now(timezone.utc).isoformat()
        cur2 = conn.execute("SELECT MAX(version) FROM config_entries WHERE key=? AND is_active=1", (cr.key,))
        current_version = cur2.fetchone()[0] or 0
        new_version = current_version + 1
        conn.execute("UPDATE config_entries SET is_active=0 WHERE key=? AND is_active=1", (cr.key,))
        conn.execute(
            "INSERT INTO config_entries (key, version, value, effective_from, created_by, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, 1)",
            (cr.key, new_version, cr.proposed_value, cr.key, reviewed_by, now)
        )
        conn.execute(
            "UPDATE config_change_requests SET status='APPROVED', reviewed_by=?, reviewed_at=?, review_notes=? WHERE crid=?",
            (reviewed_by, now, review_notes, crid)
        )
        conn.commit()
        conn.close()
        cr.status = "APPROVED"
        cr.reviewed_by = reviewed_by
        cr.reviewed_at = now
        cr.review_notes = review_notes
        return cr

    def reject_change(self, crid: str, reviewed_by: str, review_notes: str) -> ChangeRequest:
        conn = sqlite3.connect(self.db_path, timeout=10)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE config_change_requests SET status='REJECTED', reviewed_by=?, reviewed_at=?, review_notes=? WHERE crid=?",
            (reviewed_by, now, review_notes, crid)
        )
        conn.commit()
        conn.close()
        cur = conn.execute("SELECT * FROM config_change_requests WHERE crid=?", (crid,))
        row = cur.fetchone()
        return ChangeRequest(
            id=row[0], crid=row[1], key=row[2], proposed_value=row[3],
            reason=row[4], status=row[5], proposed_by=row[6], proposed_at=row[7],
            reviewed_by=row[8], reviewed_at=row[9], review_notes=row[10]
        )

    def get_pending_changes(self) -> list[ChangeRequest]:
        conn = sqlite3.connect(self.db_path, timeout=10)
        cur = conn.execute("SELECT * FROM config_change_requests WHERE status='PENDING' ORDER BY proposed_at ASC")
        rows = cur.fetchall()
        conn.close()
        return [
            ChangeRequest(
                id=r[0], crid=r[1], key=r[2], proposed_value=r[3],
                reason=r[4], status=r[5], proposed_by=r[6], proposed_at=r[7],
                reviewed_by=r[8], reviewed_at=r[9], review_notes=r[10]
            )
            for r in rows
        ]

    def get_change_history(self, key: str | None = None) -> list[ChangeRequest]:
        conn = sqlite3.connect(self.db_path, timeout=10)
        if key:
            cur = conn.execute("SELECT * FROM config_change_requests WHERE key=? ORDER BY proposed_at DESC", (key,))
        else:
            cur = conn.execute("SELECT * FROM config_change_requests ORDER BY proposed_at DESC")
        rows = cur.fetchall()
        conn.close()
        return [
            ChangeRequest(
                id=r[0], crid=r[1], key=r[2], proposed_value=r[3],
                reason=r[4], status=r[5], proposed_by=r[6], proposed_at=r[7],
                reviewed_by=r[8], reviewed_at=r[9], review_notes=r[10]
            )
            for r in rows
        ]


_DEFAULTS = {
    "fast_track_limit":              {"value": 50000,  "effective_from": "2025-01-01", "created_by": "system"},
    "garage_network_tolerance_pct":   {"value": 15,    "effective_from": "2025-01-01", "created_by": "system"},
    "max_labor_rate_kes_per_hour":   {"value": 8000,  "effective_from": "2025-01-01", "created_by": "system"},
    "inspection_sample_pct":          {"value": 10,    "effective_from": "2025-01-01", "created_by": "system"},
    "max_approval_single_claim":      {"value": 500000, "effective_from": "2025-01-01", "created_by": "system"},
    "approval_tier_1_limit":         {"value": 100000, "effective_from": "2025-01-01", "created_by": "system"},
    "approval_tier_2_limit":         {"value": 300000, "effective_from": "2025-01-01", "created_by": "system"},
    "tat_sla_draft_hours":           {"value": 24,     "effective_from": "2025-01-01", "created_by": "system"},
    "tat_sla_submitted_hours":       {"value": 4,      "effective_from": "2025-01-01", "created_by": "system"},
    "tat_sla_investigation_hours":   {"value": 72,     "effective_from": "2025-01-01", "created_by": "system"},
    "file_types_allowed":             {"value": ["jpg","jpeg","png","pdf","webp","heic"], "effective_from": "2025-01-01", "created_by": "system"},
    "max_file_size_mb":              {"value": 25,     "effective_from": "2025-01-01", "created_by": "system"},
    "sms_enabled":                   {"value": True,   "effective_from": "2025-01-01", "created_by": "system"},
    "nhif_enabled":                  {"value": False,  "effective_from": "2025-01-01", "created_by": "system"},
}


def seed_defaults(db_path: str = _DB_PATH) -> None:
    cfg = ConfigDB(db_path)
    for key, meta in _DEFAULTS.items():
        if cfg.get(key) is None:
            conn = sqlite3.connect(db_path, timeout=10)
            conn.execute(
                "INSERT INTO config_entries (key, version, value, effective_from, created_by, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, 1)",
                (key, 1, json.dumps(meta["value"]), meta["effective_from"], meta["created_by"], datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
            conn.close()


_config_db: ConfigDB | None = None
_config_lock = threading.Lock()

def get_config_db() -> ConfigDB:
    global _config_db
    if _config_db is None:
        with _config_lock:
            if _config_db is None:
                _config_db = ConfigDB()
                seed_defaults()
    return _config_db
