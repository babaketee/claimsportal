import os
import sqlite3
import streamlit as st
from datetime import datetime, date
from typing import Optional
import random

_DB_PATH = "claims_history.db"

# -----------------------------------------------------------------------
# DB access — PostgreSQL in production, SQLite fallback for dev
# Set DATABASE_URL in Streamlit Cloud secrets:
#   DATABASE_URL=postgresql://user:pass@host:5432/dbname
# -----------------------------------------------------------------------

def _get_db():
    """Return a psycopg2 connection. Falls back to sqlite3 if DATABASE_URL is not set."""
    database_url = os.getenv("DATABASE_URL", "")
    if database_url:
        import psycopg2
        return psycopg2.connect(database_url)
    else:
        return sqlite3.connect(_DB_PATH)

def _ensure_tables():
    """Create all tables if they do not exist."""
    conn = _get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS claims_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_ref TEXT UNIQUE NOT NULL,
            client TEXT NOT NULL,
            claim_type TEXT NOT NULL,
            insurer TEXT,
            claim_cause TEXT,
            status TEXT NOT NULL DEFAULT 'Reported',
            location TEXT,
            vehicle_reg TEXT,
            date_filed TEXT,
            last_updated TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_ref TEXT NOT NULL,
            action TEXT NOT NULL,
            user_email TEXT,
            timestamp TEXT NOT NULL,
            notes TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reserves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_ref TEXT NOT NULL,
            reserve_amount REAL NOT NULL DEFAULT 0,
            amount_paid REAL NOT NULL DEFAULT 0,
            reserve_type TEXT,
            reason TEXT,
            status TEXT DEFAULT 'Active',
            set_by TEXT,
            set_date TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS diary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_ref TEXT NOT NULL,
            entry_text TEXT,
            entry_date TEXT,
            entered_by TEXT,
            due_date TEXT,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Open'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS communications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_ref TEXT NOT NULL,
            direction TEXT,
            channel TEXT,
            recipient TEXT,
            message TEXT,
            sent_at TEXT,
            status TEXT DEFAULT 'Sent'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expert_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_ref TEXT NOT NULL,
            expert_name TEXT,
            expert_type TEXT,
            assigned_date TEXT,
            status TEXT DEFAULT 'Assigned',
            notes TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS claim_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_ref TEXT NOT NULL,
            doc_type TEXT,
            file_name TEXT,
            uploaded_at TEXT,
            uploaded_by TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_ref TEXT NOT NULL,
            settlement_amount REAL NOT NULL DEFAULT 0,
            wht_amount REAL DEFAULT 0,
            net_amount REAL DEFAULT 0,
            settlement_date TEXT,
            settlement_type TEXT,
            status TEXT DEFAULT 'Recommended',
            approved_by TEXT,
            approved_date TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# -----------------------------------------------------------------------
# Core CRUD
# -----------------------------------------------------------------------

def get_claims(filters: Optional[dict] = None):
    _ensure_tables()
    conn = _get_db()
    cur = conn.cursor()
    query = "SELECT claim_ref, client, claim_type, insurer, claim_cause, status, location, vehicle_reg, date_filed, last_updated FROM claims_history WHERE 1=1"
    params = []
    if filters:
        if filters.get("claim_ref"):
            query += " AND claim_ref LIKE ?"
            params.append(f"%{filters['claim_ref']}%")
        if filters.get("status"):
            query += " AND status = ?"
            params.append(filters["status"])
        if filters.get("claim_type"):
            query += " AND claim_type = ?"
            params.append(filters["claim_type"])
    query += " ORDER BY date_filed DESC LIMIT 200"
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def create_claim(claim_ref, client, claim_type, insurer, claim_cause, status, location, vehicle_reg):
    _ensure_tables()
    conn = _get_db()
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO claims_history
            (claim_ref, client, claim_type, insurer, claim_cause, status, location, vehicle_reg, date_filed, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (claim_ref, client, claim_type, insurer, claim_cause, status, location, vehicle_reg, now, now))
    conn.commit()
    cur.close()
    conn.close()
    return claim_ref

def update_claim_status(claim_ref, new_status, user_email=None):
    _ensure_tables()
    conn = _get_db()
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute("UPDATE claims_history SET status = ?, last_updated = ? WHERE claim_ref = ?", (new_status, now, claim_ref))
    cur.execute("INSERT INTO status_history (claim_ref, action, user_email, timestamp, notes) VALUES (?, ?, ?, ?, ?)",
                (claim_ref, f"Status changed to {new_status}", user_email or "system", now, ""))
    conn.commit()
    cur.close()
    conn.close()

# -----------------------------------------------------------------------
# Reserves
# -----------------------------------------------------------------------

def set_reserve(claim_ref, amount, reserve_type, reason, set_by="system"):
    _ensure_tables()
    conn = _get_db()
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reserves (claim_ref, reserve_amount, amount_paid, reserve_type, reason, status, set_by, set_date)
        VALUES (?, ?, 0, ?, ?, 'Active', ?, ?)
    """, (claim_ref, amount, reserve_type, reason, set_by, now))
    conn.commit()
    cur.close()
    conn.close()

def get_reserves(claim_ref):
    _ensure_tables()
    conn = _get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, reserve_amount, amount_paid, reserve_type, reason, status, set_by, set_date FROM reserves WHERE claim_ref = ? ORDER BY set_date DESC", (claim_ref,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# -----------------------------------------------------------------------
# Diary
# -----------------------------------------------------------------------

def add_diary_entry(claim_ref, entry_text, entered_by, due_date=None, priority="Medium"):
    _ensure_tables()
    conn = _get_db()
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO diary_entries (claim_ref, entry_text, entry_date, entered_by, due_date, priority, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Open')
    """, (claim_ref, entry_text, now, entered_by, due_date, priority))
    conn.commit()
    cur.close()
    conn.close()

def get_diary_entries(claim_ref):
    _ensure_tables()
    conn = _get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, entry_text, entry_date, entered_by, due_date, priority, status FROM diary_entries WHERE claim_ref = ? ORDER BY entry_date DESC", (claim_ref,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# -----------------------------------------------------------------------
# Communications
# -----------------------------------------------------------------------

def log_communication(claim_ref, direction, channel, recipient, message):
    _ensure_tables()
    conn = _get_db()
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO communications (claim_ref, direction, channel, recipient, message, sent_at, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Sent')
    """, (claim_ref, direction, channel, recipient, message, now))
    conn.commit()
    cur.close()
    conn.close()

# -----------------------------------------------------------------------
# Expert Assignments
# -----------------------------------------------------------------------

def assign_expert(claim_ref, expert_name, expert_type):
    _ensure_tables()
    conn = _get_db()
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO expert_assignments (claim_ref, expert_name, expert_type, assigned_date, status)
        VALUES (?, ?, ?, ?, 'Assigned')
    """, (claim_ref, expert_name, expert_type, now))
    conn.commit()
    cur.close()
    conn.close()

def get_assignments(claim_ref):
    _ensure_tables()
    conn = _get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, expert_name, expert_type, assigned_date, status, notes FROM expert_assignments WHERE claim_ref = ? ORDER BY assigned_date DESC", (claim_ref,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def update_assignment_status(assignment_id, new_status):
    _ensure_tables()
    conn = _get_db()
    cur = conn.cursor()
    cur.execute("UPDATE expert_assignments SET status = ? WHERE id = ?", (new_status, assignment_id))
    conn.commit()
    cur.close()
    conn.close()

# -----------------------------------------------------------------------
# Settlements
# -----------------------------------------------------------------------

def recommend_settlement(claim_ref, amount, settlement_type, approved_by=None):
    _ensure_tables()
    conn = _get_db()
    now = datetime.now().isoformat()
    wht = round(amount * 0.05, 2)
    net = round(amount - wht, 2)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO settlements (claim_ref, settlement_amount, wht_amount, net_amount, settlement_date, settlement_type, status, approved_by, approved_date)
        VALUES (?, ?, ?, ?, ?, ?, 'Recommended', ?, ?)
    """, (claim_ref, amount, wht, net, now, settlement_type, approved_by, now))
    conn.commit()
    cur.close()
    conn.close()

def mark_settlement_paid(settlement_id):
    _ensure_tables()
    conn = _get_db()
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute("UPDATE settlements SET status = 'Paid', settlement_date = ? WHERE id = ?", (now, settlement_id))
    conn.commit()
    cur.close()
    conn.close()

def get_settlements(claim_ref):
    _ensure_tables()
    conn = _get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, settlement_amount, wht_amount, net_amount, settlement_date, settlement_type, status, approved_by, approved_date FROM settlements WHERE claim_ref = ? ORDER BY settlement_date DESC", (claim_ref,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# -----------------------------------------------------------------------
# Seed Demo Data (auto-runs on first import)
# -----------------------------------------------------------------------

def _seed_demo_data_if_empty():
    """Seed 45 Kenyan claims on first run. Run once via st.rerun scope."""
    _ensure_tables()
    conn = _get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM claims_history")
    count = cur.fetchone()[0]
    if count > 0:
        cur.close()
        conn.close()
        return
    cur.close()

    motor_claims = [
        ("MTR-2026-0001", "client@insure.demo", "Motor Comprehensive", "Kenya Direct", "Bodily Injury", "Reported - Under Investigation", "Nairobi", "KBA 123A"),
        ("MTR-2026-0002", "client@insure.demo", "Motor Comprehensive", "Kenya Direct", "Third Party Only", "Reserve Set - Pending Assessment", "Mombasa", "KBB 456B"),
        ("MTR-2026-0003", "officer@insure.demo", "Motor Third Party", "Jubilee Insurance", "Windscreen", "Closed - Settled", "Kisumu", "KBC 789C"),
        ("MTR-2026-0004", "assessor@insure.demo", "Motor Comprehensive", "Britam", "Theft", "Reported - Under Investigation", "Nairobi", "KBD 101D"),
        ("MTR-2026-0005", "garage@insure.demo", "Motor Comprehensive", "Kenya Direct", "Engine Failure", "Reserve Set - Awaiting Repair", "Nakuru", "KBE 202E"),
        ("MTR-2026-0006", "investigator@insure.demo", "Motor Third Party", "Jubilee Insurance", "Accident Damage", "Reported - Under Investigation", "Eldoret", "KBF 303F"),
        ("MTR-2026-0007", "client@insure.demo", "Motor Comprehensive", "CIC Insurance", "Total Loss", "Closed - Settled", "Nairobi", "KBG 404G"),
        ("MTR-2026-0008", "officer@insure.demo", "Motor Third Party", "First Assurance", "Third Party Liability", "Reserve Set - Pending Assessment", "Mombasa", "KBH 505H"),
        ("MTR-2026-0009", "assessor@insure.demo", "Motor Comprehensive", "Kenya Direct", "Fire Damage", "Reported - Under Investigation", "Nairobi", "KBI 606I"),
        ("MTR-2026-0010", "garage@insure.demo", "Motor Comprehensive", "Britam", "Partial Loss", "Reserve Set - Awaiting Repair", "Kisumu", "KBJ 707J"),
        ("MTR-2026-0011", "client@insure.demo", "Motor Third Party", "Jubilee Insurance", "Bodily Injury", "Reported - Under Investigation", "Nairobi", "KBK 808K"),
        ("MTR-2026-0012", "officer@insure.demo", "Motor Comprehensive", "CIC Insurance", "Theft", "Closed - Repudiated", "Mombasa", "KBL 909L"),
        ("MTR-2026-0013", "assessor@insure.demo", "Motor Comprehensive", "First Assurance", "Accident Damage", "Reserve Set - Pending Assessment", "Nairobi", "KBM 110M"),
        ("MTR-2026-0014", "garage@insure.demo", "Motor Third Party", "Kenya Direct", "Windscreen", "Closed - Settled", "Nakuru", "KBN 211N"),
        ("MTR-2026-0015", "investigator@insure.demo", "Motor Comprehensive", "Britam", "Theft", "Reported - Under Investigation", "Eldoret", "KBO 312O"),
        ("MTR-2026-0016", "client@insure.demo", "Motor Comprehensive", "Jubilee Insurance", "Engine Failure", "Reserve Set - Awaiting Repair", "Kisumu", "KBP 413P"),
        ("MTR-2026-0017", "officer@insure.demo", "Motor Third Party", "CIC Insurance", "Third Party Liability", "Reserve Set - Pending Assessment", "Nairobi", "KBQ 514Q"),
        ("MTR-2026-0018", "assessor@insure.demo", "Motor Comprehensive", "First Assurance", "Fire Damage", "Reported - Under Investigation", "Mombasa", "KBR 615R"),
        ("MTR-2026-0019", "garage@insure.demo", "Motor Comprehensive", "Kenya Direct", "Partial Loss", "Reserve Set - Awaiting Repair", "Nairobi", "KBS 716S"),
        ("MTR-2026-0020", "investigator@insure.demo", "Motor Third Party", "Britam", "Bodily Injury", "Reported - Under Investigation", "Nairobi", "KBT 817T"),
        ("MTR-2026-0021", "client@insure.demo", "Motor Comprehensive", "Jubilee Insurance", "Total Loss", "Closed - Settled", "Kisumu", "KBU 918U"),
        ("MTR-2026-0022", "officer@insure.demo", "Motor Comprehensive", "CIC Insurance", "Theft", "Reported - Under Investigation", "Nairobi", "KBV 019V"),
        ("MTR-2026-0023", "assessor@insure.demo", "Motor Third Party", "First Assurance", "Accident Damage", "Reserve Set - Pending Assessment", "Mombasa", "KBW 120W"),
        ("MTR-2026-0024", "garage@insure.demo", "Motor Comprehensive", "Kenya Direct", "Windscreen", "Closed - Settled", "Nairobi", "KBX 221X"),
        ("MTR-2026-0025", "investigator@insure.demo", "Motor Comprehensive", "Britam", "Fire Damage", "Reported - Under Investigation", "Eldoret", "KBY 322Y"),
    ]

    business_claims = [
        ("BSN-2026-0001", "client@insure.demo", "Business Insurance", "Jubilee Insurance", "Fire Damage", "Reported - Under Investigation", "Nairobi", "OFF-001"),
        ("BSN-2026-0002", "officer@insure.demo", "Business Insurance", "Britam", "Burglary", "Reserve Set - Pending Assessment", "Mombasa", "OFF-002"),
        ("BSN-2026-0003", "assessor@insure.demo", "Business Insurance", "CIC Insurance", "Theft", "Closed - Settled", "Kisumu", "OFF-003"),
        ("BSN-2026-0004", "garage@insure.demo", "Business Insurance", "First Assurance", "Water Damage", "Reported - Under Investigation", "Nairobi", "OFF-004"),
        ("BSN-2026-0005", "investigator@insure.demo", "Business Insurance", "Kenya Direct", "Burglary", "Reserve Set - Awaiting Repair", "Nakuru", "OFF-005"),
        ("BSN-2026-0006", "client@insure.demo", "Public Liability", "Jubilee Insurance", "Third Party Claim", "Reported - Under Investigation", "Nairobi", "OFF-006"),
        ("BSN-2026-0007", "officer@insure.demo", "Business Insurance", "Britam", "Fire Damage", "Closed - Settled", "Mombasa", "OFF-007"),
        ("BSN-2026-0008", "assessor@insure.demo", "Business Insurance", "CIC Insurance", "Equipment Breakdown", "Reserve Set - Pending Assessment", "Eldoret", "OFF-008"),
        ("BSN-2026-0009", "garage@insure.demo", "Public Liability", "First Assurance", "Public Injury", "Reported - Under Investigation", "Kisumu", "OFF-009"),
        ("BSN-2026-0010", "investigator@insure.demo", "Business Insurance", "Kenya Direct", "Burglary", "Closed - Repudiated", "Nairobi", "OFF-010"),
        ("BSN-2026-0011", "client@insure.demo", "Business Insurance", "Jubilee Insurance", "Theft", "Reserve Set - Awaiting Repair", "Mombasa", "OFF-011"),
        ("BSN-2026-0012", "officer@insure.demo", "Business Insurance", "Britam", "Fire Damage", "Reported - Under Investigation", "Nairobi", "OFF-012"),
        ("BSN-2026-0013", "assessor@insure.demo", "Public Liability", "CIC Insurance", "Third Party Claim", "Reserve Set - Pending Assessment", "Kisumu", "OFF-013"),
        ("BSN-2026-0014", "garage@insure.demo", "Business Insurance", "First Assurance", "Water Damage", "Closed - Settled", "Nairobi", "OFF-014"),
        ("BSN-2026-0015", "investigator@insure.demo", "Business Insurance", "Kenya Direct", "Burglary", "Reported - Under Investigation", "Nakuru", "OFF-015"),
        ("BSN-2026-0016", "client@insure.demo", "Business Insurance", "Jubilee Insurance", "Equipment Breakdown", "Reserve Set - Awaiting Repair", "Eldoret", "OFF-016"),
        ("BSN-2026-0017", "officer@insure.demo", "Public Liability", "Britam", "Public Injury", "Reported - Under Investigation", "Nairobi", "OFF-017"),
        ("BSN-2026-0018", "assessor@insure.demo", "Business Insurance", "CIC Insurance", "Fire Damage", "Closed - Settled", "Mombasa", "OFF-018"),
        ("BSN-2026-0019", "garage@insure.demo", "Business Insurance", "First Assurance", "Theft", "Reserve Set - Pending Assessment", "Kisumu", "OFF-019"),
        ("BSN-2026-0020", "investigator@insure.demo", "Business Insurance", "Kenya Direct", "Burglary", "Reported - Under Investigation", "Nairobi", "OFF-020"),
    ]

    now = "2026-07-30 12:00:00"
    conn = _get_db()
    cur = conn.cursor()

    for c in motor_claims + business_claims:
        cur.execute("""
            INSERT INTO claims_history
                (claim_ref, client, claim_type, insurer, claim_cause, status, location, vehicle_reg, date_filed, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (*c, now, now))

    for c in motor_claims + business_claims:
        reserve_amount = random.randint(50000, 500000)
        cur.execute("""
            INSERT INTO reserves (claim_ref, reserve_amount, amount_paid, reserve_type, reason, status, set_by, set_date)
            VALUES (?, ?, 0, 'Initial Reserve', 'Claim assessment', 'Active', 'system', ?)
        """, (c[0], reserve_amount, now))

    for c in motor_claims + business_claims:
        cur.execute("""
            INSERT INTO status_history (claim_ref, action, user_email, timestamp, notes)
            VALUES (?, 'Claim Reported', 'system', ?, 'Initial claim registration')
        """, (c[0], now))

    conn.commit()
    cur.close()
    conn.close()

# Auto-seed on module import
_seed_demo_data_if_empty()
