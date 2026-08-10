"""models.py — SQLite table definitions for the Claims Portal SoR"""

# All tables defined here. In production: swap SQLite for PostgreSQL.

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_ref TEXT UNIQUE NOT NULL,
    policy_ref TEXT NOT NULL,
    claimant_email TEXT,
    status TEXT NOT NULL DEFAULT 'Draft',
    status_changed_at REAL NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    incident_date REAL,
    incident_type TEXT,
    incident_location TEXT,
    incident_description TEXT,
    estimated_amount REAL DEFAULT 0,
    sum_insured REAL,
    excess REAL DEFAULT 0,
    salvage_value REAL DEFAULT 0,
    claim_class TEXT DEFAULT 'motor',
    fast_track INTEGER DEFAULT 0,
    total_loss_indicator INTEGER DEFAULT 0,
    assigned_to TEXT,
    assigned_role TEXT,
    triage_decision TEXT,
    external_ref TEXT,
    discharge_voucher_signed INTEGER DEFAULT 0,
    discharge_voucher_date REAL,
    appeal_filed INTEGER DEFAULT 0,
    appeal_ref TEXT,
    extra_data TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS claim_tat_clocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_ref TEXT NOT NULL,
    stage TEXT NOT NULL,
    clock_id TEXT NOT NULL,
    started_at REAL NOT NULL,
    frozen_at REAL,
    elapsed_ms INTEGER,
    UNIQUE(claim_ref, stage, clock_id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_ref TEXT,
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    action TEXT NOT NULL,
    before_state TEXT,
    after_state TEXT,
    delta TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS reserve_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_ref TEXT NOT NULL,
    movement_type TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'KES',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS document_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_ref TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    gps_lat REAL,
    gps_lon REAL,
    gps_altitude REAL,
    gps_timestamp TEXT,
    uploaded_at REAL NOT NULL,
    uploaded_by TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS api_outbound_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idempotency_key TEXT UNIQUE NOT NULL,
    exchange_idx INTEGER NOT NULL,
    claim_ref TEXT,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    next_retry_at REAL,
    created_at REAL NOT NULL,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS config_entries (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS config_approvals (
    approval_id TEXT PRIMARY KEY,
    key TEXT NOT NULL,
    proposed_value TEXT NOT NULL,
    proposed_by TEXT NOT NULL,
    proposed_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    decided_by TEXT,
    decided_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
CREATE INDEX IF NOT EXISTS idx_claims_email ON claims(claimant_email);
CREATE INDEX IF NOT EXISTS idx_audit_claim ON audit_log(claim_ref);
CREATE INDEX IF NOT EXISTS idx_tat_claim ON claim_tat_clocks(claim_ref);
"""

def get_schema() -> str:
    return SCHEMA_SQL
