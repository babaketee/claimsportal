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

import sqlite3
import uuid
import random
from datetime import datetime, timezone
from typing import Any

_DB_PATH = "claims_portal.db"

# ─── Demo data store (Phase 1 — replace with real API calls in production) ────

DEMO_POLICIES = [
    {"policy_ref": "POL-MOT-2026-001", "product": "Motor Comprehensive", "id_number": "12345678","vehicle_reg": "KBZ 000A",  "sum_insured": 2_500_000, "premium_status": "paid", "cover_start": "2026-01-01", "cover_end": "2026-12-31"},
    {"policy_ref": "POL-MOT-2026-002", "product": "Motor Third Party",   "id_number": "23456789","vehicle_reg": "KAZ 111B",  "sum_insured": None,             "premium_status": "paid", "cover_start": "2026-01-01", "cover_end": "2026-12-31"},
    {"policy_ref": "POL-MOT-2026-003", "product": "Motor Comprehensive", "id_number": "34567890","vehicle_reg": "KBC 222C",  "sum_insured": 1_800_000, "premium_status": "paid", "cover_start": "2026-01-01", "cover_end": "2026-12-31"},
    {"policy_ref": "POL-MOT-2026-004", "product": "Motor Comprehensive", "id_number": "45678901","vehicle_reg": "KBJ 333D",  "sum_insured": 3_000_000, "premium_status": "pending", "cover_start": "2026-01-01", "cover_end": "2026-12-31"},
    {"policy_ref": "POL-MOT-2026-005", "product": "Motor Third Party",   "id_number": "56789012","vehicle_reg": "KCD 444E",  "sum_insured": None,             "premium_status": "paid", "cover_start": "2026-01-01", "cover_end": "2026-12-31"},
]

DEMO_VEHICLES = {p["vehicle_reg"]: p for p in DEMO_POLICIES if p.get("vehicle_reg")}

# ─── Policy verification ─────────────────────────────────────────────────────────

def verify_policy(identity: str) -> dict | None:
    """
    Lookup policy by ID number, passport number, or policy reference.
    Phase 1: searches DEMO_POLICIES.
    Production: calls core system Exchange 1 — GET /policies?identity=ID
    """
    for p in DEMO_POLICIES:
        if (p["id_number"] == identity or
            p["policy_ref"].lower() == identity.lower() or
            p.get("vehicle_reg","").upper().replace(" ","") == identity.upper().replace(" ","")):
            return p
    return None


def verify_vehicle_reg(reg: str) -> dict | None:
    """
    Third-party vehicle lookup by registration number.
    Returns policy info if the vehicle is insured with Definite Assurance.
    Used for third-party claimant guest intake (R1).
    Phase 1: searches DEMO_VEHICLES.
    Production: calls core system — GET /vehicles?reg=KBZ000A
    """
    key = reg.upper().replace(" ", "")
    return DEMO_VEHICLES.get(key)


def get_policy(policy_ref: str) -> dict | None:
    """Get full policy record by reference."""
    for p in DEMO_POLICIES:
        if p["policy_ref"] == policy_ref:
            return p
    return None


# ─── Claim notification ─────────────────────────────────────────────────────────

def notify_claim(claim_ref: str, policy_ref: str, payload: dict) -> dict:
    """
    Register a claim with the core system (Exchange 2).
    Phase 1: logs to SQLite demo_claims table.
    Production: POST /claims/notification with idempotency key.
    """
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    cur = conn.execute(
        "SELECT 1 FROM demo_claims WHERE claim_ref=?", (claim_ref,)
    )
    if not cur.fetchone():
        conn.execute(
            "INSERT INTO demo_claims (claim_ref, policy_ref, status, created_at) VALUES (?, ?, ?, ?)",
            (claim_ref, policy_ref, "notified", datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
    conn.close()
    return {"success": True, "claim_ref": claim_ref, "policy_ref": policy_ref}


# ─── Reserve movements (R3) ──────────────────────────────────────────────────────

def reserve_movement(claim_ref: str, movement_type: str, amount: float, currency: str = "KES") -> dict:
    """
    Record a reserve movement on a claim.
    movement_type: "initial" | "revision" | "release"
    Phase 1: logs to SQLite reserve_movements table.
    Production: calls core system — PATCH /claims/{ref}/reserve
    """
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


# ─── Inbound webhook stubs (Exchanges 3 & 5 — core → portal) ──────────────────

def receive_triage_decision(claim_ref: str, triage_decision: str, assigned_to: str) -> dict:
    """
    Exchange 3: Core → Portal. Push triage/routing decision.
    decision: "fast_track" | "standard" | "escalated"
    """
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
    """
    Exchange 5: Core → Portal. Push approval or repudiation decision.
    decision: "approved" | "repudiated"
    Must be idempotent — calling twice with same decision returns success both times.
    """
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
    # Idempotent — use INSERT OR REPLACE
    conn.execute(
        "INSERT OR REPLACE INTO approval_decisions (claim_ref, decision, payout_amount, reason_code, approver_id, received_at) VALUES (?, ?, ?, ?, ?, ?)",
        (claim_ref, decision, payout_amount, reason_code, approver_id, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()
    return {"success": True, "claim_ref": claim_ref, "decision": decision}


# ─── Demo users ─────────────────────────────────────────────────────────────────

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
    return list(get_user(email) for email in [
        "client@insure.demo", "claims_officer@insure.demo", "head_of_claims@insure.demo",
        "assessor@insure.demo", "investigator@insure.demo", "garage@insure.demo",
        "spare_parts@insure.demo", "admin@insure.demo", "super@insure.demo",
    ] if get_user(email) is not None)
