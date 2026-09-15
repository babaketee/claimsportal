import Database from "better-sqlite3";
import path from "node:path";
import fs from "node:fs";

// ---------------------------------------------------------------------------
// Singleton SQLite connection (survives Next.js dev hot-reload via global).
// ---------------------------------------------------------------------------

const DATA_DIR = path.join(process.cwd(), "data");
const DB_PATH = path.join(DATA_DIR, "claims.db");

declare global {
  // eslint-disable-next-line no-var
  var __claimsDb: Database.Database | undefined;
}

function createConnection(): Database.Database {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
  const db = new Database(DB_PATH);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  initSchema(db);
  return db;
}

export function getDb(): Database.Database {
  if (!global.__claimsDb) {
    global.__claimsDb = createConnection();
  }
  return global.__claimsDb;
}

function initSchema(db: Database.Database) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      email       TEXT PRIMARY KEY,
      password    TEXT NOT NULL,
      role        TEXT NOT NULL,
      full_name   TEXT NOT NULL,
      phone       TEXT
    );

    CREATE TABLE IF NOT EXISTS claims (
      claim_ref        TEXT PRIMARY KEY,
      category          TEXT NOT NULL,
      claim_type        TEXT NOT NULL,
      status            TEXT NOT NULL,
      policy_number     TEXT NOT NULL,
      insured_name      TEXT NOT NULL,
      client_email      TEXT,
      vehicle_reg       TEXT,
      location          TEXT NOT NULL,
      date_of_loss      TEXT,
      date_reported     TEXT NOT NULL,
      claim_amount      REAL NOT NULL DEFAULT 0,
      urgency           TEXT NOT NULL DEFAULT 'Medium',
      description       TEXT NOT NULL DEFAULT '',
      assigned_officer  TEXT,
      expert_type       TEXT,
      created_at        TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
    CREATE INDEX IF NOT EXISTS idx_claims_client ON claims(client_email);
    CREATE INDEX IF NOT EXISTS idx_claims_officer ON claims(assigned_officer);

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
    CREATE INDEX IF NOT EXISTS idx_reserves_claim ON reserves(claim_ref);

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
    CREATE INDEX IF NOT EXISTS idx_diary_claim ON diary_entries(claim_ref);

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
    CREATE INDEX IF NOT EXISTS idx_comms_claim ON communications(claim_ref);

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
    CREATE INDEX IF NOT EXISTS idx_assign_claim ON expert_assignments(claim_ref);

    CREATE TABLE IF NOT EXISTS claim_documents (
      doc_id          TEXT PRIMARY KEY,
      claim_ref       TEXT NOT NULL,
      doc_type        TEXT NOT NULL,
      filename        TEXT NOT NULL,
      file_size       INTEGER,
      mime_type       TEXT,
      file_path       TEXT,
      uploaded_by     TEXT,
      uploaded_at     TEXT NOT NULL,
      version         INTEGER NOT NULL DEFAULT 1,
      note            TEXT,
      ocr_status      TEXT NOT NULL DEFAULT 'pending',
      ocr_text        TEXT,
      exif_json       TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_docs_claim ON claim_documents(claim_ref);

    CREATE TABLE IF NOT EXISTS claim_status_history (
      history_id      TEXT PRIMARY KEY,
      claim_ref       TEXT NOT NULL,
      from_status     TEXT,
      to_status       TEXT NOT NULL,
      changed_by      TEXT NOT NULL,
      changed_at      TEXT NOT NULL,
      note            TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_history_claim ON claim_status_history(claim_ref);

    CREATE TABLE IF NOT EXISTS fraud_assessments (
      assessment_id     TEXT PRIMARY KEY,
      claim_ref         TEXT NOT NULL,
      score             REAL NOT NULL,
      risk_band         TEXT NOT NULL,
      indicators_json   TEXT NOT NULL,
      recommended_action TEXT NOT NULL,
      computed_at       TEXT NOT NULL,
      computed_by       TEXT NOT NULL DEFAULT 'system',
      review_status     TEXT NOT NULL DEFAULT 'pending_review',
      reviewed_by       TEXT,
      reviewed_at       TEXT,
      review_decision   TEXT,
      review_note       TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_fraud_claim ON fraud_assessments(claim_ref);
    CREATE INDEX IF NOT EXISTS idx_fraud_band ON fraud_assessments(risk_band);

    CREATE TABLE IF NOT EXISTS configurations (
      config_key      TEXT NOT NULL,
      version         INTEGER NOT NULL,
      value_json      TEXT NOT NULL,
      status          TEXT NOT NULL DEFAULT 'approved',
      proposed_by     TEXT NOT NULL,
      proposed_at     TEXT NOT NULL,
      approved_by     TEXT,
      approved_at     TEXT,
      effective_date  TEXT NOT NULL,
      note            TEXT,
      PRIMARY KEY (config_key, version)
    );
    CREATE INDEX IF NOT EXISTS idx_config_key ON configurations(config_key);

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
    CREATE INDEX IF NOT EXISTS idx_settle_claim ON settlements(claim_ref);

    CREATE TABLE IF NOT EXISTS rfqs (
      rfq_ref          TEXT PRIMARY KEY,
      claim_ref        TEXT NOT NULL,
      part_description TEXT NOT NULL,
      quantity         INTEGER NOT NULL DEFAULT 1,
      status           TEXT NOT NULL DEFAULT 'open',
      created_by       TEXT,
      created_at       TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS bids (
      bid_ref       TEXT PRIMARY KEY,
      rfq_ref       TEXT NOT NULL,
      provider      TEXT NOT NULL,
      brand         TEXT,
      condition     TEXT,
      unit_price    REAL NOT NULL,
      lead_days     INTEGER,
      warranty      TEXT,
      rating        REAL,
      submitted_at  TEXT NOT NULL,
      status        TEXT NOT NULL DEFAULT 'submitted'
    );
    CREATE INDEX IF NOT EXISTS idx_bids_rfq ON bids(rfq_ref);

    CREATE TABLE IF NOT EXISTS docuseal_submissions (
      submission_id           TEXT PRIMARY KEY,
      claim_ref                TEXT NOT NULL,
      workflow                 TEXT NOT NULL,
      form_key                 TEXT,
      template_id              TEXT,
      docuseal_submission_id   TEXT,
      signer_name               TEXT NOT NULL,
      signer_email               TEXT NOT NULL,
      status                    TEXT NOT NULL DEFAULT 'pending',
      embed_src                 TEXT,
      created_by                TEXT,
      created_at                TEXT NOT NULL,
      completed_at               TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_docuseal_claim ON docuseal_submissions(claim_ref);

    CREATE TABLE IF NOT EXISTS investigator_reports (
      report_id        TEXT PRIMARY KEY,
      claim_ref        TEXT NOT NULL,
      investigator_name TEXT NOT NULL,
      mode_of_report   TEXT,
      accident_datetime TEXT,
      location         TEXT,
      police_station   TEXT,
      injured_count    INTEGER DEFAULT 0,
      deceased_count   INTEGER DEFAULT 0,
      fraud_suspected  TEXT NOT NULL DEFAULT 'no',
      fraud_basis      TEXT,
      created_by       TEXT,
      created_at       TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_invreports_claim ON investigator_reports(claim_ref);

    CREATE TABLE IF NOT EXISTS meta (
      key   TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );
  `);
}

export function isSeeded(): boolean {
  const db = getDb();
  const row = db.prepare("SELECT value FROM meta WHERE key = 'seeded_at'").get() as
    | { value: string }
    | undefined;
  return !!row;
}

export function markSeeded() {
  const db = getDb();
  db.prepare(
    "INSERT INTO meta (key, value) VALUES ('seeded_at', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value"
  ).run(new Date().toISOString());
}
