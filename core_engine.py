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
        # Delete any stale demo data so INSERT runs fresh
        self.db.execute("DELETE FROM claims")
        self.db.execute("DELETE FROM reserve_movements")
        now = time.time() * 1000
        claims_data = [
            # Motor claims
            ("CLM-00000001", "POL-2024-M001", "client@insure.demo", "Reported", now - 86400000*8, now - 86400000*8, now - 86400000*7, "2026-06-28", "Road Accident", "Ngong Road, Nairobi", "Rear-end collision on Ngong Road", 85000, "motor", 0, 0, None, None, "NRB/2026/4455", 78000, None, None, None, "{"vehicle_reg":"KAB-123A","claimant_name":"Assured","loss_date":"2026-06-28"}"),
            ("CLM-00000002", "POL-2024-M002", "client@insure.demo", "Assessment", now - 86400000*6, now - 86400000*6, now - 86400000*5, "2026-07-01", "Road Accident", "Waiyaki Way, Nairobi", "Side-impact collision Waiyaki Way", 120000, "motor", 0, 0, None, None, "NRB/2026/4488", 115000, None, None, None, "{"vehicle_reg":"KBC-456D","claimant_name":"Assured","loss_date":"2026-07-01"}"),
            ("CLM-00000003", "POL-2024-M003", "assessor@insure.demo", "Approved", now - 86400000*25, now - 86400000*25, now - 86400000*24, "2026-06-10", "Windscreen Damage", "Mombasa Road", "Windscreen damage Mombasa Rd", 65000, "motor", 0, 0, None, None, None, 62000, None, None, None, "{"vehicle_reg":"KCZ-789E","claimant_name":"Assured","loss_date":"2026-06-10"}"),
            ("CLM-00000004", "POL-2024-M004", "client@insure.demo", "Closed_Approved", now - 86400000*45, now - 86400000*45, now - 86400000*44, "2026-05-15", "Road Accident", "Karen, Nairobi", "Parked car hit by unknown vehicle", 45000, "motor", 0, 0, None, None, None, 43500, None, None, None, "{"vehicle_reg":"KDE-101F","claimant_name":"Assured","loss_date":"2026-05-15"}"),
            ("CLM-00000005", "POL-2024-M005", "investigator@insure.demo", "Closed_Repudiated", now - 86400000*38, now - 86400000*38, now - 86400000*37, "2026-05-28", "Theft", "Westlands, Nairobi", "Theft of vehicle from parking", 200000, "motor", 0, 0, None, None, None, None, None, None, None, "{"vehicle_reg":"KFG-202G","claimant_name":"Assured","loss_date":"2026-05-28"}"),
            ("CLM-00000006", "POL-2024-M006", "officer@insure.demo", "Reported", now - 86400000*4, now - 86400000*4, now - 86400000*3, "2026-07-06", "Road Accident", "Nairobi", "Minor dent on bonnet Highway", 95000, "motor", 0, 0, None, None, None, 90000, None, None, None, "{"vehicle_reg":"KHJ-303K","claimant_name":"Caleb Officer","loss_date":"2026-07-06"}"),
            ("CLM-00000007", "POL-2024-M007", "hoc@insure.demo", "Assessment", now - 86400000*5, now - 86400000*5, now - 86400000*4, "2026-07-02", "Road Accident", "Mombasa Road", "Multi-vehicle pile-up", 150000, "motor", 0, 0, None, None, "NRB/2026/4521", 140000, None, None, None, "{"vehicle_reg":"KKL-404L","claimant_name":"Diana HOC","loss_date":"2026-07-02"}"),
            ("CLM-00000008", "POL-2024-M008", "surveyor@insure.demo", "Closed_Approved", now - 86400000*95, now - 86400000*95, now - 86400000*94, "2026-04-05", "Windscreen Damage", "Kisumu", "Windscreen crack", 38000, "motor", 0, 0, None, None, None, 36500, None, None, None, "{"vehicle_reg":"KMN-505M","claimant_name":"Steve Surveyor","loss_date":"2026-04-05"}"),
            ("CLM-00000009", "POL-2024-M009", "motor_fleet@insure.demo", "Assessment", now - 86400000*1, now - 86400000*1, now, "2026-07-07", "Road Accident", "Mombasa", "Fleet vehicle accident Mombasa", 220000, "motor", 0, 0, None, None, "NRB/2026/4555", 210000, None, None, None, "{"vehicle_reg":"KOP-606P","claimant_name":"Molly Fleet","loss_date":"2026-07-07"}"),
            ("CLM-00000010", "POL-2024-M010", "manager@insure.demo", "Reported", now, now, now, "2026-07-08", "Road Accident", "Nairobi", "Rear mirror damage", 75000, "motor", 0, 0, None, None, None, None, None, None, None, "{"vehicle_reg":"KQR-707R","claimant_name":"Mary Manager","loss_date":"2026-07-08"}"),
            ("CLM-00000011", "POL-2024-M011", "officer@insure.demo", "Closed_Approved", now - 86400000*105, now - 86400000*105, now - 86400000*104, "2026-04-20", "Road Accident", "Eldoret", "Bumper damage Eldoret", 55000, "motor", 0, 0, None, None, None, 53000, None, None, None, "{"vehicle_reg":"KST-808S","claimant_name":"Caleb Officer","loss_date":"2026-04-20"}"),
            ("CLM-00000012", "POL-2024-M012", "surveyor@insure.demo", "Closed_Repudiated", now - 86400000*30, now - 86400000*30, now - 86400000*29, "2026-06-05", "Road Accident", "Thika Road", "Suspected fraud - staged accident", 180000, "motor", 0, 0, None, None, "NRB/2026/4388", None, None, None, None, "{"vehicle_reg":"KUV-909U","claimant_name":"Steve Surveyor","loss_date":"2026-06-05"}"),
            ("CLM-00000013", "POL-2024-M013", "legal@insure.demo", "Assessment", now - 86400000*7, now - 86400000*7, now - 86400000*6, "2026-06-28", "Road Accident", "Nairobi", "Third party bodily injury claim", 300000, "motor", 0, 0, None, None, "NRB/2026/4422", 290000, None, None, None, "{"vehicle_reg":"KWX-101X","claimant_name":"Lara Legal","loss_date":"2026-06-28"}"),
            # Medical claims
            ("CLM-00000014", "POL-2024-H001", "client@insure.demo", "Reported", now - 86400000*3, now - 86400000*3, now - 86400000*2, "2026-07-04", None, "Nairobi", "Emergency appendectomy", 350000, "medical", 0, 0, "Nairobi Hospital", None, None, None, None, None, None, "{"hospital_name":"Nairobi Hospital","claimant_name":"Assured","loss_date":"2026-07-04"}"),
            ("CLM-00000015", "POL-2024-H002", "assessor@insure.demo", "Assessment", now - 86400000*7, now - 86400000*7, now - 86400000*6, "2026-06-30", None, "Nairobi", "Cardiac bypass surgery", 850000, "medical", 0, 0, "Aga Khan University Hospital", None, None, None, None, None, None, "{"hospital_name":"Aga Khan University Hospital","claimant_name":"Assured","loss_date":"2026-06-30"}"),
            ("CLM-00000016", "POL-2024-H003", "investigator@insure.demo", "Investigation", now - 86400000*14, now - 86400000*14, now - 86400000*13, "2026-06-20", None, "Nairobi", "Maternity cover delivery complicated", 120000, "medical", 0, 0, "Mater Hospital", None, None, None, None, None, None, "{"hospital_name":"Mater Hospital","claimant_name":"Assured","loss_date":"2026-06-20"}"),
            ("CLM-00000017", "POL-2024-H004", "garage@insure.demo", "Approved", now - 86400000*30, now - 86400000*30, now - 86400000*29, "2026-06-05", None, "Nairobi", "RTA fractures sustained", 180000, "medical", 0, 0, "Kenyatta National Hospital", None, None, None, None, None, None, "{"hospital_name":"Kenyatta National Hospital","claimant_name":"George Garage","loss_date":"2026-06-05"}"),
            ("CLM-00000018", "POL-2024-H005", "client@insure.demo", "Closed_Approved", now - 86400000*60, now - 86400000*60, now - 86400000*59, "2026-05-10", None, "Mombasa", "Asthma attack ICU admission", 95000, "medical", 0, 0, "MP Shah Hospital", None, None, None, None, None, None, "{"hospital_name":"MP Shah Hospital","claimant_name":"Assured","loss_date":"2026-05-10"}"),
            ("CLM-00000019", "POL-2024-H006", "spares@insure.demo", "Closed_Repudiated", now - 86400000*38, now - 86400000*38, now - 86400000*37, "2026-05-28", None, "Nairobi", "Cosmetic dental procedure claim", 45000, "medical", 0, 0, "Gertrudes Children Hospital", None, None, None, None, None, None, "{"hospital_name":"Gertrudes Children Hospital","claimant_name":"Sam Spares","loss_date":"2026-05-28"}"),
            ("CLM-00000020", "POL-2024-H007", "spares@insure.demo", "Assessment", now - 86400000*11, now - 86400000*11, now - 86400000*10, "2026-06-25", None, "Eldoret", "Optical cataract surgery", 220000, "medical", 0, 0, "Moi Referral Hospital", None, None, None, None, None, None, "{"hospital_name":"Moi Referral Hospital","claimant_name":"Sam Spares","loss_date":"2026-06-25"}"),
            ("CLM-00000021", "POL-2024-H008", "motor_fleet@insure.demo", "Approved", now - 86400000*50, now - 86400000*50, now - 86400000*49, "2026-06-18", None, "Nairobi", "Employee health cover - appendectomy", 65000, "medical", 0, 0, "Gertrudes Hospital", None, None, None, None, None, None, "{"hospital_name":"Gertrudes Hospital","claimant_name":"Molly Fleet","loss_date":"2026-06-18"}"),
            ("CLM-00000022", "POL-2024-H009", "manager@insure.demo", "Investigation", now - 86400000*6, now - 86400000*6, now - 86400000*5, "2026-06-30", None, "Nairobi", "Cancer chemotherapy sessions", 500000, "medical", 0, 0, "Mater Hospital", None, None, None, None, None, None, "{"hospital_name":"Mater Hospital","claimant_name":"Mary Manager","loss_date":"2026-06-30"}"),
            ("CLM-00000023", "POL-2024-H010", "officer@insure.demo", "Assessment", now - 86400000*3, now - 86400000*3, now - 86400000*2, "2026-07-05", None, "Nairobi", "Accident emergency treatment", 140000, "medical", 0, 0, "Nairobi Hospital", None, None, None, None, None, None, "{"hospital_name":"Nairobi Hospital","claimant_name":"Caleb Officer","loss_date":"2026-07-05"}"),
            # Life claims
            ("CLM-00000024", "POL-2024-L001", "client@insure.demo", "Reported", now - 86400000*2, now - 86400000*2, now - 86400000*1, "2026-07-01", None, "Kisumu", "Death benefit - natural causes", 5000000, "life", 0, 0, None, "Grace Wanjiku", None, None, None, None, None, "{"beneficiary_name":"Grace Wanjiku","claimant_name":"Assured","loss_date":"2026-07-01"}"),
            ("CLM-00000025", "POL-2024-L002", "hoc@insure.demo", "Assessment", now - 86400000*8, now - 86400000*8, now - 86400000*7, "2026-06-28", None, "Nairobi", "Critical illness - cancer diagnosis", 3000000, "life", 0, 0, None, "John Mwangi", None, None, None, None, None, "{"beneficiary_name":"John Mwangi","claimant_name":"Diana HOC","loss_date":"2026-06-28"}"),
            ("CLM-00000026", "POL-2024-L003", "finance@insure.demo", "Approved", now - 86400000*25, now - 86400000*25, now - 86400000*24, "2026-06-10", None, "Eldoret", "Total Permanent Disability payout", 2000000, "life", 0, 0, None, "Mary Njeri", None, None, None, None, None, "{"beneficiary_name":"Mary Njeri","claimant_name":"Fatima Finance","loss_date":"2026-06-10"}"),
            ("CLM-00000027", "POL-2024-L004", "legal@insure.demo", "Closed_Approved", now - 86400000*75, now - 86400000*75, now - 86400000*74, "2026-05-20", None, "Nakuru", "Funeral expense reimbursement", 750000, "life", 0, 0, None, "Susan Ochieng", None, None, None, None, None, "{"beneficiary_name":"Susan Ochieng","claimant_name":"Lara Legal","loss_date":"2026-05-20"}"),
            ("CLM-00000028", "POL-2024-L005", "admin@insure.demo", "Closed_Repudiated", now - 86400000*34, now - 86400000*34, now - 86400000*33, "2026-05-30", None, "Nairobi", "Critical illness - stroke (pre-existing condition)", 1500000, "life", 0, 0, None, "James Kamau", None, None, None, None, None, "{"beneficiary_name":"James Kamau","claimant_name":"Ada Admin","loss_date":"2026-05-30"}"),
            ("CLM-00000029", "POL-2024-L006", "motor_fleet@insure.demo", "Approved", now - 86400000*52, now - 86400000*52, now - 86400000*51, "2026-06-15", None, "Mombasa", "Group life - employee death", 1000000, "life", 0, 0, None, "Ali Hassan", None, None, None, None, None, "{"beneficiary_name":"Ali Hassan","claimant_name":"Molly Fleet","loss_date":"2026-06-15"}"),
            ("CLM-00000030", "POL-2024-L007", "surveyor@insure.demo", "Reported", now - 86400000*1, now - 86400000*1, now, "2026-07-05", None, "Kisumu", "Critical illness - heart surgery", 2500000, "life", 0, 0, None, "Rose Atieno", None, None, None, None, None, "{"beneficiary_name":"Rose Atieno","claimant_name":"Steve Surveyor","loss_date":"2026-07-05"}"),
        ]
        self.db.executemany("""
            INSERT OR IGNORE INTO claims (claim_ref, policy_ref, claimant_email, status,
            status_changed_at, created_at, updated_at, incident_date, incident_type,
            incident_location, incident_description, estimated_amount, claim_class,
            fast_track, total_loss_indicator, assigned_to, assigned_role, external_ref,
            salvage_value, discharge_voucher_signed, discharge_voucher_date, appeal_filed,
            appeal_ref, extra_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, claims_data)
        # Seed reserve movements for selected claims
        reserves = [
            ("CLM-00000002", "increase", 100000, "finance", now - 86400000*5, "Initial reserve set"),
            ("CLM-00000007", "increase", 130000, "finance", now - 86400000*4, "Multi-vehicle reserve"),
            ("CLM-00000015", "increase", 800000, "finance", now - 86400000*6, "Cardiac case initial reserve"),
        ]
        self.db.executemany("""
            INSERT INTO claims (claim_ref, policy_ref, claimant_email, status,
            status_changed_at, created_at, updated_at, incident_date, incident_type,
            incident_location, incident_description, estimated_amount, claim_class,
            fast_track, total_loss_indicator, assigned_to, assigned_role, external_ref,
            salvage_value, discharge_voucher_signed, discharge_voucher_date, appeal_filed,
            appeal_ref, extra_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, claims_data)
        self.db.commit()
        self.db.executemany("""
            INSERT OR IGNORE INTO reserve_movements (claim_ref, movement_type, amount, created_by, created_at, currency)
            VALUES (?, ?, ?, ?, ?, 'KES')
        """, reserves)
        self.db.commit()    def is_total_loss(self, claim_ref: str) -> bool:
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