"""
core_engine.py - Definite Assurance Claims Portal
Phase 2 additions: record_reserve_movement, file_appeal, sign_discharge_voucher
"""

import sqlite3, json, time, uuid, os
from datetime import datetime, timezone
from typing import Optional

DB_PATH = os.environ.get("CLAIMS_DB", "data/claims.db")

class ClaimStatus:
    DRAFT                 = "Draft"
    REPORTED              = "Reported"
    TRIAGE                = "Triage"
    INVESTIGATION         = "Investigation"
    ASSESSMENT            = "Assessment"
    APPROVAL              = "Approval"
    APPROVED              = "Approved"
    UNDER_REPAIR          = "Under Repair"
    REINSPECTION          = "Reinspection"
    PENDING_PAYMENT       = "Pending Payment"
    PAID                  = "Paid"
    CLOSED                = "Closed"
    CLOSED_APPROVED       = "Closed_Approved"
    CLOSED_REPUDIATED     = "Closed_Repudiated"
    TOTAL_LOSS_SETTLEMENT = "Total_Loss_Settlement"
    CLOSED_TOTAL_LOSS     = "Closed_Total_Loss"

STATUSES = [
    ClaimStatus.DRAFT, ClaimStatus.REPORTED, ClaimStatus.TRIAGE,
    ClaimStatus.INVESTIGATION, ClaimStatus.ASSESSMENT, ClaimStatus.APPROVAL,
    ClaimStatus.APPROVED, ClaimStatus.UNDER_REPAIR, ClaimStatus.REINSPECTION,
    ClaimStatus.PENDING_PAYMENT, ClaimStatus.PAID, ClaimStatus.CLOSED,
    ClaimStatus.CLOSED_APPROVED, ClaimStatus.CLOSED_REPUDIATED,
    ClaimStatus.TOTAL_LOSS_SETTLEMENT, ClaimStatus.CLOSED_TOTAL_LOSS,
]

TRANSITIONS = {
    ClaimStatus.DRAFT:                 [ClaimStatus.REPORTED],
    ClaimStatus.REPORTED:              [ClaimStatus.TRIAGE, ClaimStatus.DRAFT],
    ClaimStatus.TRIAGE:                [ClaimStatus.INVESTIGATION, ClaimStatus.DRAFT],
    ClaimStatus.INVESTIGATION:         [ClaimStatus.ASSESSMENT, ClaimStatus.TRIAGE],
    ClaimStatus.ASSESSMENT:            [ClaimStatus.APPROVAL, ClaimStatus.INVESTIGATION],
    ClaimStatus.APPROVAL:              [ClaimStatus.APPROVED, ClaimStatus.INVESTIGATION],
    ClaimStatus.APPROVED:              [ClaimStatus.UNDER_REPAIR, ClaimStatus.REINSPECTION, ClaimStatus.PENDING_PAYMENT],
    ClaimStatus.UNDER_REPAIR:          [ClaimStatus.REINSPECTION, ClaimStatus.PENDING_PAYMENT],
    ClaimStatus.REINSPECTION:         [ClaimStatus.APPROVAL, ClaimStatus.UNDER_REPAIR],
    ClaimStatus.PENDING_PAYMENT:       [ClaimStatus.PAID, ClaimStatus.APPROVED],
    ClaimStatus.PAID:                 [ClaimStatus.CLOSED, ClaimStatus.CLOSED_APPROVED],
    ClaimStatus.CLOSED:               [],
    ClaimStatus.CLOSED_APPROVED:      [],
    ClaimStatus.CLOSED_REPUDIATED:    [],
    ClaimStatus.TOTAL_LOSS_SETTLEMENT:[ClaimStatus.CLOSED_TOTAL_LOSS],
    ClaimStatus.CLOSED_TOTAL_LOSS:    [],
}

LOCKED_TRANSITIONS = {
    (ClaimStatus.INVESTIGATION, ClaimStatus.TOTAL_LOSS_SETTLEMENT): "Total loss route only -- cannot skip garage stages",
}

TAT_STAGES = [
    "Reported", "Triage", "Investigation", "Assessment",
    "Approval", "Under Repair", "Reinspection", "Pending Payment",
]

class AuditLogger:
    def __init__(self, db):
        self.db = db
    def write(self, claim_ref: str, actor_id: str, actor_role: str,
              action: str, before: dict, after: dict) -> int:
        delta = json.dumps(self._diff(before, after))
        now = time.time() * 1000
        self.db.execute("""
            INSERT INTO audit_log (claim_ref, actor_id, actor_role, action,
            before_state, after_state, delta, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (claim_ref, actor_id, actor_role, action,
                  json.dumps(before), json.dumps(after), delta, now))
        self.db.commit()
        return self.db.execute("SELECT last_insert_rowid()").fetchone()[0]
    def get_history(self, entity: str, ref: str):
        rows = self.db.execute("""
            SELECT * FROM audit_log WHERE claim_ref=? ORDER BY created_at ASC
        """, (ref,)).fetchall()
        cols = [d[0] for d in self.db.execute("PRAGMA table_info(audit_log)").fetchall()]
        return [dict(zip(cols, r)) for r in rows]
    def _diff(self, a, b):
        return {k: {"from": a.get(k), "to": b.get(k)}
                for k in set(a.keys()) | set(b.keys()) if a.get(k) != b.get(k)}

class ClaimsEngine:
    def __init__(self, db_path: str = DB_PATH):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.audit = AuditLogger(self.db)
        self._init_schema()
        self._seed_demo_if_empty()

    def _init_schema(self):
        self.db.executescript('''
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
        CREATE TABLE IF NOT EXISTS reserve_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_ref TEXT NOT NULL,
            movement_type TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'KES',
            created_at REAL NOT NULL,
            created_by TEXT NOT NULL
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
        CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
        CREATE INDEX IF NOT EXISTS idx_claims_email ON claims(claimant_email);
        CREATE INDEX IF NOT EXISTS idx_audit_claim ON audit_log(claim_ref);
        CREATE INDEX IF NOT EXISTS idx_tat_claim ON claim_tat_clocks(claim_ref);
        CREATE INDEX IF NOT EXISTS idx_reserves_claim ON reserve_movements(claim_ref);
        ''')
        self.db.commit()

    def _seed_demo_if_empty(self):
        count = self.db.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        if count > 0:
            return
        now = time.time() * 1000
        demos = [
            ("CLM-00000001", "POL-2024-001", "Jane Policyholder",
             "client@insure.demo", "Reported", 250000, "motor", 0),
            ("CLM-00000002", "POL-2024-002", "John Motorist",
             "client@insure.demo", "Triage", 85000, "motor", 1),
            ("CLM-00000003", "POL-2024-003", "Alice Third Party",
             "client@insure.demo", "Investigation", 450000, "motor_tp", 0),
            ("CLM-00000004", "POL-2024-004", "Bob Fleet Driver",
             "motor_fleet@insure.demo", "Assessment", 120000, "motor", 1),
            ("CLM-00000005", "POL-2024-005", "Carol Medical",
             "client@insure.demo", "Approval", 75000, "medical", 0),
            ("CLM-00000006", "POL-2024-006", "Dave Insured",
             "client@insure.demo", "Pending Payment", 310000, "motor", 0),
            ("CLM-00000007", "POL-2024-007", "Eve Third Party BI",
             "client@insure.demo", "Reported", 1200000, "motor_tp_bi", 0),
            ("CLM-00000008", "POL-2024-008", "Frank Owner",
             "client@insure.demo", "Closed_Approved", 95000, "motor", 0),
            ("CLM-00000009", "POL-2024-009", "Grace Insured",
             "client@insure.demo", "Closed_Repudiated", 200000, "motor", 0),
            ("CLM-00000010", "POL-2024-010", "Henry Total Loss",
             "client@insure.demo", "Closed_Total_Loss", 1800000, "motor", 0),
        ]
        for ref, pol, name, email, status, amt, cls, ft in demos:
            self.db.execute("""
                INSERT INTO claims (claim_ref, policy_ref, claimant_email, status,
                status_changed_at, created_at, updated_at, estimated_amount,
                claim_class, fast_track, incident_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ref, pol, email, status, now, now - 86400000*3,
                      now - 86400000*2, amt, cls, ft,
                      "Demo claim for " + name))
        self.db.commit()

    def is_total_loss(self, claim_ref: str) -> bool:
        row = self.db.execute("SELECT estimated_amount, sum_insured FROM claims WHERE claim_ref=?",
                               (claim_ref,)).fetchone()
        if not row:
            return False
        amt = row[0] or 0
        si = row[1] or (amt * 2)
        return amt >= si * 0.75

    def transition_to(self, claim_ref: str, to_status: str, actor_id: str = "system",
                       notes: str = None, findings: str = None, recommended_amount: float = None,
                       triage_decision: str = None, **kwargs) -> dict:
        row = self.db.execute("SELECT * FROM claims WHERE claim_ref=?", (claim_ref,)).fetchone()
        if not row:
            raise ValueError(f"Claim {claim_ref} not found")
        cols = [d[0] for d in self.db.execute("PRAGMA table_info(claims)").fetchall()]
        before = dict(zip(cols, row))
        current = before["status"]
        if to_status == current:
            return {"status": current, "changed": False}
        allowed = TRANSITIONS.get(current, [])
        lock_key = (current, to_status)
        if lock_key in LOCKED_TRANSITIONS:
            raise ValueError(LOCKED_TRANSITIONS[lock_key])
        if to_status not in allowed:
            raise ValueError(f"Transition {current} -> {to_status} not allowed")
        now = time.time() * 1000
        extra = json.loads(before.get("extra_data", "{}"))
        if notes:     extra["notes"] = notes
        if findings:  extra["findings"] = findings
        if recommended_amount is not None:
            extra["recommended_amount"] = recommended_amount
        if triage_decision:
            extra["triage_decision"] = triage_decision
        for k, v in kwargs.items():
            extra[k] = v
        self.db.execute("""
            UPDATE claims SET status=?, status_changed_at=?, updated_at=?,
            extra_data=? WHERE claim_ref=?
        """, (to_status, now, now, json.dumps(extra), claim_ref))
        self.audit.write(claim_ref, actor_id, "claims_officer",
                          f"transition: {current} -> {to_status}", before,
                          {**before, "status": to_status, "extra_data": extra})
        self.db.commit()
        return {"status": to_status, "changed": True, "from": current}

    def create_claim(self, claim_ref: str, policy_ref: str, id_number: str = None,
                     vehicle_reg: str = None, incident_type: str = None,
                     description: str = None, claim_class: str = "motor",
                     user_id: str = None, **kwargs) -> str:
        now = time.time() * 1000
        extra = {}
        if id_number:    extra["id_number"] = id_number
        if vehicle_reg:  extra["vehicle_reg"] = vehicle_reg
        if description:  extra["incident_description"] = description
        if incident_type: extra["incident_type"] = incident_type
        for k, v in kwargs.items():
            extra[k] = v
        self.db.execute("""
            INSERT INTO claims (claim_ref, policy_ref, claimant_email, status,
            status_changed_at, created_at, updated_at, claim_class, extra_data)
            VALUES (?, ?, ?, 'Draft', ?, ?, ?, ?, ?)
        """, (claim_ref, policy_ref, user_id or "unknown@insure.demo",
                  now, now, now, claim_class, json.dumps(extra)))
        self.audit.write(claim_ref, user_id or "system", "client",
                          "claim_created", {}, {**extra, "status": "Draft"})
        self.db.commit()
        return claim_ref

    def get_claim(self, claim_ref: str) -> Optional[dict]:
        row = self.db.execute("SELECT * FROM claims WHERE claim_ref=?", (claim_ref,)).fetchone()
        if not row:
            return None
        cols = [d[0] for d in self.db.execute("PRAGMA table_info(claims)").fetchall()]
        return dict(zip(cols, row))

    def get_claims_by_status(self, status: str) -> list[dict]:
        rows = self.db.execute("SELECT * FROM claims WHERE status=?", (status,)).fetchall()
        cols = [d[0] for d in self.db.execute("PRAGMA table_info(claims)").fetchall()]
        return [dict(zip(cols, r)) for r in rows]

    def record_reserve_movement(self, claim_ref: str, movement_type: str,
                                  amount: float, actor_id: str = "finance") -> int:
        """Record a reserve debit/credit movement on a claim. Phase 2 R3."""
        now = time.time() * 1000
        self.db.execute("""
            INSERT INTO reserve_movements (claim_ref, movement_type, amount, created_at, created_by)
            VALUES (?, ?, ?, ?, ?)
        """, (claim_ref, movement_type, amount, now, actor_id))
        self.audit.write(claim_ref, actor_id, "finance",
                          f"reserve_movement:{movement_type}",
                          {"reserve": 0}, {"reserve": amount})
        self.db.commit()
        return self.db.execute("SELECT last_insert_rowid()").fetchone()[0]

    def file_appeal(self, claim_ref: str, appeal_ref: str, actor_id: str = "legal") -> None:
        """File an appeal for a repudiated claim. Phase 2 R6."""
        row = self.db.execute("SELECT status FROM claims WHERE claim_ref=?", (claim_ref,)).fetchone()
        if not row:
            raise ValueError(f"Claim {claim_ref} not found")
        if row[0] != ClaimStatus.CLOSED_REPUDIATED:
            raise ValueError(f"Can only appeal repudiated claims. Current: {row[0]}")
        now = time.time() * 1000
        self.db.execute("""
            UPDATE claims SET appeal_filed=1, appeal_ref=?, updated_at=? WHERE claim_ref=?
        """, (appeal_ref, now, claim_ref))
        self.audit.write(claim_ref, actor_id, "legal", "appeal_filed",
                          {"appeal_filed": 0}, {"appeal_filed": 1, "appeal_ref": appeal_ref})
        self.db.commit()

    def sign_discharge_voucher(self, claim_ref: str, actor_id: str = "finance") -> None:
        """Mark the discharge voucher as signed for a claim. Phase 2 R5."""
        row = self.db.execute("SELECT status, discharge_voucher_signed FROM claims WHERE claim_ref=?",
                               (claim_ref,)).fetchone()
        if not row:
            raise ValueError(f"Claim {claim_ref} not found")
        if row[1]:
            raise ValueError(f"Discharge voucher already signed for {claim_ref}")
        now = time.time() * 1000
        self.db.execute("""
            UPDATE claims SET discharge_voucher_signed=1, discharge_voucher_date=?,
            updated_at=? WHERE claim_ref=?
        """, (now, now, claim_ref))
        self.audit.write(claim_ref, actor_id, "finance", "discharge_voucher_signed",
                          {"discharge_voucher_signed": 0}, {"discharge_voucher_signed": 1})
        self.db.commit()

_ENGINE = None

def get_engine() -> ClaimsEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ClaimsEngine()
    return _ENGINE