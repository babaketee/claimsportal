-- PostgreSQL schema for claimsportal (Railway deployment)
-- Run this against your PostgreSQL database to create all tables.
-- The app also calls CREATE TABLE IF NOT EXISTS on startup.

-- Enable UUID extension (optional, for future use)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------
-- claims_history
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claims_history (
    id              BIGSERIAL PRIMARY KEY,
    claim_ref       TEXT UNIQUE NOT NULL,
    client          TEXT NOT NULL,
    claim_type      TEXT NOT NULL,
    insurer         TEXT,
    claim_cause     TEXT,
    status          TEXT NOT NULL DEFAULT 'Reported',
    location        TEXT,
    vehicle_reg     TEXT,
    date_filed      TEXT,
    last_updated    TEXT
);

CREATE INDEX IF NOT EXISTS idx_claims_status     ON claims_history(status);
CREATE INDEX IF NOT EXISTS idx_claims_claim_type ON claims_history(claim_type);
CREATE INDEX IF NOT EXISTS idx_claims_client     ON claims_history(client);

-- -----------------------------------------------------------------------
-- status_history
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS status_history (
    id          BIGSERIAL PRIMARY KEY,
    claim_ref   TEXT NOT NULL,
    action      TEXT NOT NULL,
    user_email  TEXT,
    timestamp   TEXT NOT NULL,
    notes       TEXT
);

CREATE INDEX IF NOT EXISTS idx_status_claim_ref ON status_history(claim_ref);

-- -----------------------------------------------------------------------
-- reserves
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reserves (
    id              BIGSERIAL PRIMARY KEY,
    claim_ref       TEXT NOT NULL,
    reserve_amount  REAL NOT NULL DEFAULT 0,
    amount_paid     REAL NOT NULL DEFAULT 0,
    reserve_type    TEXT,
    reason          TEXT,
    status          TEXT DEFAULT 'Active',
    set_by          TEXT,
    set_date        TEXT
);

CREATE INDEX IF NOT EXISTS idx_reserves_claim_ref ON reserves(claim_ref);
CREATE INDEX IF NOT EXISTS idx_reserves_status     ON reserves(status);

-- -----------------------------------------------------------------------
-- diary_entries
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS diary_entries (
    id          BIGSERIAL PRIMARY KEY,
    claim_ref   TEXT NOT NULL,
    entry_text  TEXT,
    entry_date  TEXT,
    entered_by  TEXT,
    due_date    TEXT,
    priority    TEXT DEFAULT 'Medium',
    status      TEXT DEFAULT 'Open'
);

CREATE INDEX IF NOT EXISTS idx_diary_claim_ref ON diary_entries(claim_ref);
CREATE INDEX IF NOT EXISTS idx_diary_status   ON diary_entries(status);

-- -----------------------------------------------------------------------
-- communications
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS communications (
    id          BIGSERIAL PRIMARY KEY,
    claim_ref   TEXT NOT NULL,
    direction   TEXT,
    channel     TEXT,
    recipient   TEXT,
    message     TEXT,
    sent_at     TEXT,
    status      TEXT DEFAULT 'Sent'
);

CREATE INDEX IF NOT EXISTS idx_comm_claim_ref ON communications(claim_ref);

-- -----------------------------------------------------------------------
-- expert_assignments
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS expert_assignments (
    id              BIGSERIAL PRIMARY KEY,
    claim_ref       TEXT NOT NULL,
    expert_name     TEXT,
    expert_type     TEXT,
    assigned_date   TEXT,
    status          TEXT DEFAULT 'Assigned',
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_expert_claim_ref ON expert_assignments(claim_ref);
CREATE INDEX IF NOT EXISTS idx_expert_status   ON expert_assignments(status);

-- -----------------------------------------------------------------------
-- claim_documents
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claim_documents (
    id          BIGSERIAL PRIMARY KEY,
    claim_ref   TEXT NOT NULL,
    doc_type    TEXT,
    file_name   TEXT,
    uploaded_at TEXT,
    uploaded_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_docs_claim_ref ON claim_documents(claim_ref);

-- -----------------------------------------------------------------------
-- settlements
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS settlements (
    id                  BIGSERIAL PRIMARY KEY,
    claim_ref           TEXT NOT NULL,
    settlement_amount   REAL NOT NULL DEFAULT 0,
    wht_amount          REAL DEFAULT 0,
    net_amount          REAL DEFAULT 0,
    settlement_date     TEXT,
    settlement_type     TEXT,
    status              TEXT DEFAULT 'Recommended',
    approved_by         TEXT,
    approved_date       TEXT
);

CREATE INDEX IF NOT EXISTS idx_settlements_claim_ref ON settlements(claim_ref);
CREATE INDEX IF NOT EXISTS idx_settlements_status     ON settlements(status);
