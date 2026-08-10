"""core_api.py — Definite Assurance Claims Portal API Client
===========================================================
Phase 1: SQLite-based demo data store + API stubs.
In production: replace stubs with real HTTP calls to the core insurance system.

Exchanges:
  1. GET  /policies?identity=       — live policy pull (stub: SQLite demo)
  2. POST /claims/notification       — register loss + initial reserve
  3. PUSH /portal/claims/{ref}/triage — routing decision from core
  4. PUSH /claims/{ref}/reports     — investigation + assessment packet
  5. PUSH /portal/claims/{ref}/decision — approved payout or repudiation
  6. PUSH /claims/{ref}/settlement   — final payout notification
"""

from __future__ import annotations

import io
import sqlite3
import uuid
import random
from datetime import datetime, timezone
from typing import Any

_DB_PATH = "claims_portal.db"

DEMO_POLICIES = [
    {"policy_ref": "POL-MOT-2026-001", "product": "Motor Comprehensive", "id_number": "12345678","vehicle_reg": "KBZ 000A",  "sum_insured": 2_500_000, "premium_status": "paid", "cover_start": "2026-01-01", "cover_end": "2026-12-31"},
    {"policy_ref": "POL-MOT-2026-002", "product": "Motor Third Party",   "id_number": "23456789","vehicle_reg": "KAZ 111B",  "sum_insured": None,             "premium_status": "paid", "cover_start": "2026-01-01", "cover_end": "2026-12-31"},
    {"policy_ref": "POL-MOT-2026-003", "product": "Motor Comprehensive", "id_number": "34567890","vehicle_reg": "KBC 222C",  "sum_insured": 1_800_000, "premium_status": "paid", "cover_start": "2026-01-01", "cover_end": "2026-12-31"},
    {"policy_ref": "POL-MOT-2026-004", "product": "Motor Comprehensive", "id_number": "45678901","vehicle_reg": "KBJ 333D",  "sum_insured": 3_000_000, "premium_status": "pending", "cover_start": "2026-01-01", "cover_end": "2026-12-31"},
    {"policy_ref": "POL-MOT-2026-005", "product": "Motor Third Party",   "id_number": "56789012","vehicle_reg": "KCD 444E",  "sum_insured": None,             "premium_status": "paid", "cover_start": "2026-01-01", "cover_end": "2026-12-31"},
]

DEMO_VEHICLES = {p["vehicle_reg"]: p for p in DEMO_POLICIES if p.get("vehicle_reg")}


def verify_policy(identity: str) -> dict | None:
    for p in DEMO_POLICIES:
        if (p["id_number"] == identity or
            p["policy_ref"].lower() == identity.lower() or
            p.get("vehicle_reg","").upper().replace(" ","") == identity.upper().replace(" ","")):
            return p
    return None


def verify_vehicle_reg(reg: str) -> dict | None:
    key = reg.upper().replace(" ", "")
    return DEMO_VEHICLES.get(key)


def get_policy(policy_ref: str) -> dict | None:
    for p in DEMO_POLICIES:
        if p["policy_ref"] == policy_ref:
            return p
    return None


def notify_claim(claim_ref: str, policy_ref: str, payload: dict) -> dict:
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    cur = conn.execute("SELECT 1 FROM demo_claims WHERE claim_ref=?", (claim_ref,))
    if not cur.fetchone():
        conn.execute(
            "INSERT INTO demo_claims (claim_ref, policy_ref, status, created_at) VALUES (?, ?, ?, ?)",
            (claim_ref, policy_ref, "notified", datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
    conn.close()
    return {"success": True, "claim_ref": claim_ref, "policy_ref": policy_ref}


def reserve_movement(claim_ref: str, movement_type: str, amount: float, currency: str = "KES") -> dict:
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reserve_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_ref TEXT NOT NULL,
            movement_type TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'KES',
            created_at TEXT NOT NULL,
            UNIQUE(claim_ref, movement_type, created_at)
        )
    """)
    conn.execute(
        "INSERT INTO reserve_movements (claim_ref, movement_type, amount, currency, created_at) VALUES (?, ?, ?, ?, ?)",
        (claim_ref, movement_type, amount, currency, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()
    return {"success": True, "claim_ref": claim_ref, "movement_type": movement_type, "amount": amount}


def receive_triage_decision(claim_ref: str, triage_decision: str, assigned_to: str) -> dict:
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS triage_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_ref TEXT UNIQUE NOT NULL,
            triage_decision TEXT NOT NULL,
            assigned_to TEXT,
            received_at TEXT NOT NULL
        )
    """)
    conn.execute(
        "INSERT OR REPLACE INTO triage_decisions (claim_ref, triage_decision, assigned_to, received_at) VALUES (?, ?, ?, ?)",
        (claim_ref, triage_decision, assigned_to, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()
    return {"success": True, "claim_ref": claim_ref}


def receive_approval_decision(claim_ref: str, decision: str, payout_amount: float | None, reason_code: str | None, approver_id: str) -> dict:
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS approval_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_ref TEXT UNIQUE NOT NULL,
            decision TEXT NOT NULL,
            payout_amount REAL,
            reason_code TEXT,
            approver_id TEXT NOT NULL,
            received_at TEXT NOT NULL
        )
    """)
    conn.execute(
        "INSERT OR REPLACE INTO approval_decisions (claim_ref, decision, payout_amount, reason_code, approver_id, received_at) VALUES (?, ?, ?, ?, ?, ?)",
        (claim_ref, decision, payout_amount, reason_code, approver_id, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()
    return {"success": True, "claim_ref": claim_ref, "decision": decision}


def extract_gps_metadata(file_bytes: bytes) -> dict | None:
    """
    Extract GPS EXIF metadata from an image file (JPG/JPEG/PNG/WebP).
    Returns dict with lat, lon, altitude, timestamp if GPS data present, else None.
    Phase 1: uses PIL/Pillow EXIF extraction.
    Production: use exifread for more complete EXIF support.
    """
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
        import io
        img = Image.open(io.BytesIO(file_bytes))
        exif = img._getexif()
        if not exif:
            return None
        gps_ifd = {}
        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                for key, val in value.items():
                    gps_tag = GPSTAGS.get(key, key)
                    gps_ifd[gps_tag] = val
        if not gps_ifd:
            return None
        def _convert(gps_data, ref):
            d, m, s = gps_data
            result = d + m / 60 + s / 3600
            if ref in ["S", "W"]:
                result = -result
            return result
        lat = lon = None
        if "GPSLatitude" in gps_ifd and "GPSLatitudeRef" in gps_ifd:
            lat = _convert(gps_ifd["GPSLatitude"], gps_ifd["GPSLatitudeRef"])
        if "GPSLongitude" in gps_ifd and "GPSLongitudeRef" in gps_ifd:
            lon = _convert(gps_ifd["GPSLongitude"], gps_ifd["GPSLongitudeRef"])
        altitude = gps_ifd.get("GPSAltitude")
        ts = gps_ifd.get("GPSTimeStamp")
        return {"lat": lat, "lon": lon, "altitude": altitude, "timestamp": str(ts)} if lat is not None else None
    except Exception:
        return None


def store_document_metadata(claim_ref: str, file_name: str, file_size: int, gps_metadata: dict | None) -> dict:
    """
    Store document metadata including GPS coordinates extracted from photo EXIF.
    Phase 1: logs to SQLite document_metadata table.
    Retention governed by document.gps_metadata.retention_days in config.
    """
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_ref TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_size INTEGER,
            gps_lat REAL,
            gps_lon REAL,
            gps_altitude REAL,
            gps_timestamp TEXT,
            uploaded_at TEXT NOT NULL
        )
    """)
    lat = gps_metadata.get("lat") if gps_metadata else None
    lon = gps_metadata.get("lon") if gps_metadata else None
    alt = gps_metadata.get("altitude") if gps_metadata else None
    ts  = gps_metadata.get("timestamp") if gps_metadata else None
    conn.execute(
        "INSERT INTO document_metadata (claim_ref, file_name, file_size, gps_lat, gps_lon, gps_altitude, gps_timestamp, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (claim_ref, file_name, file_size, lat, lon, alt, ts, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()
    return {"claim_ref": claim_ref, "file_name": file_name, "gps": gps_metadata}


def get_user(email: str) -> dict | None:
    users = {
        "client@insure.demo":               {"email": "client@insure.demo",               "name": "Jane Policyholder",  "role": "client"},
        "claims_officer@insure.demo":       {"email": "claims_officer@insure.demo",       "name": "Caleb Officer",      "role": "claims_officer"},
        "head_of_claims@insure.demo":       {"email": "head_of_claims@insure.demo",       "name": "Diana HOC",          "role": "head_of_claims"},
        "assessor@insure.demo":             {"email": "assessor@insure.demo",             "name": "Felix Assessor",     "role": "assessor"},
        "investigator@insure.demo":         {"email": "investigator@insure.demo",         "name": "Ivan Investigator",  "role": "investigator"},
        "garage@insure.demo":               {"email": "garage@insure.demo",               "name": "George Garage",      "role": "garage"},
        "spare_parts@insure.demo":          {"email": "spare_parts@insure.demo",          "name": "Sara Spares",        "role": "spare_parts"},
        "admin@insure.demo":                {"email": "admin@insure.demo",                "name": "Ada Admin",          "role": "admin"},
        "super@insure.demo":                 {"email": "super@insure.demo",                 "name": "Sam Super",           "role": "super_admin"},
    }
    return users.get(email)


def get_all_users() -> list[dict]:
    return [get_user(email) for email in [
        "client@insure.demo", "claims_officer@insure.demo", "head_of_claims@insure.demo",
        "assessor@insure.demo", "investigator@insure.demo", "garage@insure.demo",
        "spare_parts@insure.demo", "admin@insure.demo", "super@insure.demo",
    ] if get_user(email) is not None]

# ---------------------------------------------------------------------------
# Demo API helpers (implement missing endpoints used by Streamlit views)
# ---------------------------------------------------------------------------
import pandas as pd
import os

def is_configured() -> bool:
    """Return True to allow views to use core_api demo endpoints instead of no-op mode."""
    return True

def get_assignments(expert_type: str | None = None) -> list[dict]:
    """Return demo assignments filtered by expert_type."""
    demo = [
        {"claim_ref": "CLM-20250701-001", "claim_type": "Motor Bumper", "status": "pending", "assigned_at": "2025-07-02", "vehicle": "KBZ 000A", "estimated_cost": 85000, "expert_type": "assessor"},
        {"claim_ref": "CLM-20250710-004", "claim_type": "Theft", "status": "accepted", "assigned_at": "2025-07-11", "vehicle": "KAZ 111B", "estimated_cost": 0, "expert_type": "investigator"},
        {"claim_ref": "CLM-20250715-005", "claim_type": "Third Party", "status": "in_progress", "assigned_at": "2025-07-16", "vehicle": "KBC 222C", "estimated_cost": 145000, "expert_type": "garage"},
    ]
    if expert_type:
        return [d for d in demo if d.get("expert_type") == expert_type]
    return demo

def get_documents(claim_ref: str) -> list[dict]:
    """Return demo document list for a claim_ref."""
    docs = [
        {"claim_ref": claim_ref, "doc_type": "Police Report", "filename": "Police Abstract.pdf", "uploaded_at": "2025-07-02T10:00:00Z", "status": "Received"},
        {"claim_ref": claim_ref, "doc_type": "Scene Photos",   "filename": "Photos.zip",          "uploaded_at": "2025-07-02T10:05:00Z", "status": "Received"},
    ]
    return docs

def post_claim(claim: dict) -> dict:
    """Register a claim in the demo SQLite store."""
    try:
        claim_ref = claim.get("claim_ref") or f"CLM-{int(pd.Timestamp.utcnow().timestamp())}"
        notify_claim(claim_ref, claim.get("policy_ref", "UNKNOWN"), claim)
        return {"success": True, "claim_ref": claim_ref}
    except Exception:
        return {"success": False}

def post_document(claim_ref: str, filename: str, mime: str, data: bytes, doc_type: str) -> dict | None:
    """Save document bytes to a local demo folder and record metadata."""
    try:
        storage_dir = os.path.join(os.path.dirname(__file__), 'demo_documents')
        os.makedirs(storage_dir, exist_ok=True)
        path = os.path.join(storage_dir, f"{claim_ref}__{filename}")
        with open(path, 'wb') as fh:
            fh.write(data)
        # record metadata to sqlite
        try:
            from datetime import datetime, timezone
            conn = sqlite3.connect(_DB_PATH, timeout=10)
            conn.execute('''CREATE TABLE IF NOT EXISTS documents (claim_ref TEXT, filename TEXT, uploaded_at TEXT, doc_type TEXT)''')
            conn.execute('INSERT INTO documents (claim_ref, filename, uploaded_at, doc_type) VALUES (?, ?, ?, ?)', (claim_ref, filename, datetime.now(timezone.utc).isoformat(), doc_type))
            conn.commit()
            conn.close()
        except Exception:
            pass
        return {"saved": True, "path": path}
    except Exception:
        return None

def get_settlements_by_status(status_list: list[str]) -> pd.DataFrame:
    """Return demo settlements as a pandas DataFrame (used by finance views)."""
    rows = [
        {"settlement_id": "SET-20250701-001", "claim_ref": "CLM-20250701-001", "payee_name": "Jane Policyholder", "payee_type": "Client", "amount": 85000, "net_amount": 80750, "status": "approved", "recommended_by": "Officer", "recommended_at": "2025-07-10", "wht_amount": 4250},
        {"settlement_id": "SET-20250710-002", "claim_ref": "CLM-20250710-004", "payee_name": "Westlands Auto Garage", "payee_type": "Garage", "amount": 21500, "net_amount": 20425, "status": "pending", "recommended_by": "HoC", "recommended_at": "2025-07-11", "wht_amount": 1075},
    ]
    df = pd.DataFrame(rows)
    return df[df['status'].isin(status_list)] if status_list else df


# --------------------------
# Mock action handlers & stores
# --------------------------

def invalidate_claim_cache(claim_ref: str) -> bool:
    """Backward-compat no-op used by views after pushing changes to core_api."""
    return True


def update_job_status(job_ref: str, status: str) -> dict:
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_ref TEXT NOT NULL,
            expert_type TEXT,
            status TEXT,
            assigned_at TEXT
        )
    ''')
    conn.execute('UPDATE assignments SET status=? WHERE id=?', (status, job_ref))
    conn.commit()
    conn.close()
    return {"success": True}


def log_communication(claim_ref: str, sender: str, message: str) -> dict:
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS communications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_ref TEXT NOT NULL,
            sender TEXT,
            message TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    from datetime import datetime, timezone
    conn.execute('INSERT INTO communications (claim_ref, sender, message, created_at) VALUES (?, ?, ?, ?)',
                 (claim_ref, sender, message, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()
    return {"success": True}


def register_document(claim_ref: str, filename: str, doc_type: str) -> dict:
    # Lightweight wrapper around post_document metadata tracking
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY AUTOINCREMENT, claim_ref TEXT, filename TEXT, uploaded_at TEXT, doc_type TEXT)
    ''')
    from datetime import datetime, timezone
    conn.execute('INSERT INTO documents (claim_ref, filename, uploaded_at, doc_type) VALUES (?, ?, ?, ?)',
                 (claim_ref, filename, datetime.now(timezone.utc).isoformat(), doc_type))
    conn.commit()
    conn.close()
    return {"success": True}


def update_claim_status(claim_ref: str, status: str, actor_id: str | None = None) -> dict:
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS demo_claims (id INTEGER PRIMARY KEY AUTOINCREMENT, claim_ref TEXT UNIQUE NOT NULL, policy_ref TEXT, status TEXT, created_at TEXT)
    ''')
    # Upsert
    cur = conn.execute('SELECT 1 FROM demo_claims WHERE claim_ref=?', (claim_ref,))
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    if cur.fetchone():
        conn.execute('UPDATE demo_claims SET status=?, created_at=? WHERE claim_ref=?', (status, now, claim_ref))
    else:
        conn.execute('INSERT INTO demo_claims (claim_ref, policy_ref, status, created_at) VALUES (?, ?, ?, ?)',
                     (claim_ref, 'UNKNOWN', status, now))
    conn.commit()
    conn.close()
    return {"success": True, "claim_ref": claim_ref, "status": status}


def update_payment_status(claim_ref: str, payment_info: dict) -> dict:
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, claim_ref TEXT, amount REAL, status TEXT, created_at TEXT)
    ''')
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn.execute('INSERT INTO payments (claim_ref, amount, status, created_at) VALUES (?, ?, ?, ?)',
                 (claim_ref, payment_info.get('amount', 0), payment_info.get('status', 'pending'), now))
    conn.commit()
    conn.close()
    return {"success": True}


def get_settlements(claim_ref: str) -> list[dict]:
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settlements (id INTEGER PRIMARY KEY AUTOINCREMENT, settlement_id TEXT, claim_ref TEXT, payee_name TEXT, amount REAL, net_amount REAL, status TEXT, bank_ref TEXT, created_at TEXT)
    ''')
    cur = conn.execute('SELECT settlement_id, claim_ref, payee_name, amount, net_amount, status, bank_ref, created_at FROM settlements WHERE claim_ref=?', (claim_ref,))
    rows = cur.fetchall()
    conn.close()
    return [dict(zip(["settlement_id","claim_ref","payee_name","amount","net_amount","status","bank_ref","created_at"], r)) for r in rows]


def mark_settlement_paid(settlement_id: str, bank_ref: str) -> dict:
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute('UPDATE settlements SET status=?, bank_ref=? WHERE settlement_id=?', ('paid', bank_ref, settlement_id))
    conn.commit()
    conn.close()
    return {"success": True}


def get_timeline(claim_ref: str) -> list[dict]:
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS timeline (id INTEGER PRIMARY KEY AUTOINCREMENT, claim_ref TEXT, event_type TEXT, note TEXT, created_at TEXT)
    ''')
    cur = conn.execute('SELECT event_type, note, created_at FROM timeline WHERE claim_ref=? ORDER BY created_at ASC', (claim_ref,))
    rows = cur.fetchall()
    conn.close()
    return [dict(zip(["event_type","note","created_at"], r)) for r in rows]


def send_message(claim_ref: str, sender: str, message: str) -> dict:
    return log_communication(claim_ref, sender, message)


def get_overdue_entries() -> list[dict]:
    # Used by head_of_claims view - return empty list for now
    return []


def get_settlements_by_status(status_list: list[str]) -> pd.DataFrame:
    # keep existing df-backed implementation but ensure it returns requested statuses
    rows = [
        {"settlement_id": "SET-20250701-001", "claim_ref": "CLM-20250701-001", "payee_name": "Jane Policyholder", "payee_type": "Client", "amount": 85000, "net_amount": 80750, "status": "approved", "recommended_by": "Officer", "recommended_at": "2025-07-10", "wht_amount": 4250},
        {"settlement_id": "SET-20250710-002", "claim_ref": "CLM-20250710-004", "payee_name": "Westlands Auto Garage", "payee_type": "Garage", "amount": 21500, "net_amount": 20425, "status": "pending", "recommended_by": "HoC", "recommended_at": "2025-07-11", "wht_amount": 1075},
    ]
    df = pd.DataFrame(rows)
    return df[df['status'].isin(status_list)] if status_list else df


# Auto-seed demo claims on import if the demo_claims table is empty.
def _auto_seed_demo_if_empty():
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=10)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS demo_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_ref TEXT UNIQUE NOT NULL,
                policy_ref TEXT,
                status TEXT,
                created_at TEXT
            )
        ''')
        cur = conn.execute('SELECT count(1) FROM demo_claims')
        cnt = cur.fetchone()[0]
        if not cnt:
            now = datetime.now(timezone.utc).isoformat()
            demo_rows = [
                ("CLM-20250701-001", "POL-MOT-2026-001", "notified", now),
                ("CLM-20250710-004", "POL-MOT-2026-002", "notified", now),
                ("CLM-20250715-005", "POL-MOT-2026-003", "in_progress", now),
            ]
            conn.executemany('INSERT OR IGNORE INTO demo_claims (claim_ref, policy_ref, status, created_at) VALUES (?, ?, ?, ?)', demo_rows)
            conn.commit()
        conn.close()
    except Exception:
        pass

_auto_seed_demo_if_empty()
