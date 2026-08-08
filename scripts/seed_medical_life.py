#!/usr/bin/env python3
"""Seed medical and life claims — supplementary demo data.

Covers:
- Medical claims: hospital admission, surgery, outpatient, maternity, dental, optical
- Life claims: death benefit, critical illness, disability, funeral expense

Run AFTER scripts/seed_demo_data.py to add medical/life coverage.
Requires the app's DB connection (Railway PostgreSQL or local SQLite fallback).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_api import (
    set_reserve, approve_reserve,
    assign_expert,
    log_communication,
    add_diary_entry,
    recommend_settlement,
    _get_conn,
)


def seed_medical_life():
    conn = _get_conn()
    cur = conn.cursor()
    print("Seeding medical and life claims...")

    now = "2025-07-30"

    # ── MEDICAL CLAIMS ───────────────────────────────────────────────────────
    medical_claims = [
        # (claim_ref, client_email, hospital, treatment_type, cause, status, amount, beneficiary, documents_flag)
        # Open / Intake stage
        ("CLM-MED-2025-001", "client@insure.demo",
         "Nairobi Hospital, Upper Hill",
         "Hospital Admission – Appendectomy",
         "Acute appendicitis, emergency admission",
         "FNOL", 0, "Kamau Mwangi", True),

        ("CLM-MED-2025-002", "manager@insure.demo",
         "Aga Khan University Hospital, Parklands",
         "Major Surgery – Cardiac bypass",
         "Coronary artery disease, blocked vessels",
         "Assessment", 0, "Mary Manager", True),

        # Processing / Investigation
        ("CLM-MED-2025-003", "officer@insure.demo",
         "Mater Hospital, Richmond Hill",
         "Maternity – Normal Delivery",
         "Childbirth, 38 weeks gestation",
         "Investigation", 0, "Caleb Officer", False),

        ("CLM-MED-2025-004", "legal@insure.demo",
         "Kenyatta National Hospital, Upper Hill",
         "Road Traffic Accident – Multiple fractures",
         "RTA on Mombasa Road, pedestrian hit",
         "Investigation", 0, "Lara Legal", True),

        # Approved / Reserves set
        ("CLM-MED-2025-005", "hoc@insure.demo",
         "Moi Teaching & Referral Hospital, Eldoret",
         "Major Surgery – Hip replacement",
         "Degenerative joint disease, fall at home",
         "Approved", 485000, "Diana HOC", True),

        ("CLM-MED-2025-006", "cfo@insure.demo",
         "Nairobi Hospital, Upper Hill",
         "Cancer Treatment – Chemotherapy",
         "Stage 2 breast cancer, confirmed diagnosis",
         "Approved", 920000, "Charles CFO", True),

        # Settled
        ("CLM-MED-2025-007", "assessor@insure.demo",
         "Aga Khan Hospital, Mombasa",
         "Emergency – Acute asthma attack",
         "Severe asthma exacerbation, ICU admission",
         "Settled", 178000, "Felix Assessor", False),

        ("CLM-MED-2025-008", "investigator@insure.demo",
         "Kenyatta National Hospital, Kasarani",
         "Outpatient – Dental surgery",
         "Impacted wisdom tooth removal",
         "Settled", 65000, "Ivan Investigator", True),

        # Rejected
        ("CLM-MED-2025-009", "garage@insure.demo",
         "Gertrude's Garden Hospital, Lavington",
         "Cosmetic Surgery – Tummy tuck",
         "Elective cosmetic procedure",
         "Rejected", 0, "George Garage", False),

        ("CLM-MED-2025-010", "spares@insure.demo",
         "MP Shah Hospital, Village Market",
         "Optical – Cataract surgery",
         "Age-related cataracts, both eyes",
         "Settled", 210000, "Sam Spares", True),
    ]

    # ── LIFE CLAIMS ──────────────────────────────────────────────────────────
    life_claims = [
        # (claim_ref, client_email, beneficiary_name, cause, status, amount, claim_type)
        # Open / Intake
        ("CLM-LIFE-2025-001", "client@insure.demo",
         "Kamau Mwangi (spouse)",
         "Death – Natural causes",
         "FNOL", 0, "Death Benefit"),

        ("CLM-LIFE-2025-002", "manager@insure.demo",
         "Mary Manager (self)",
         "Critical Illness – Stroke",
         "Assessment", 0, "Critical Illness"),

        # Processing
        ("CLM-LIFE-2025-003", "hoc@insure.demo",
         "Diana HOC (self)",
         "Total Permanent Disability – Accident",
         "Investigation", 0, "Disability"),

        ("CLM-LIFE-2025-004", "officer@insure.demo",
         "Caleb Officer (spouse)",
         "Death – Road Traffic Accident",
         "Investigation", 0, "Death Benefit"),

        # Approved
        ("CLM-LIFE-2025-005", "legal@insure.demo",
         "Lara Legal (self)",
         "Critical Illness – Cancer",
         "Approved", 1500000, "Critical Illness"),

        # Settled
        ("CLM-LIFE-2025-006", "cfo@insure.demo",
         "Charles CFO (spouse)",
         "Death – Heart attack",
         "Settled", 2000000, "Death Benefit"),

        ("CLM-LIFE-2025-007", "assessor@insure.demo",
         "Felix Assessor (self)",
         "Funeral Expense Reimbursement",
         "Settled", 85000, "Funeral Expense"),

        ("CLM-LIFE-2025-008", "investigator@insure.demo",
         "Ivan Investigator (spouse)",
         "Death – Natural causes",
         "Settled", 1800000, "Death Benefit"),

        # Rejected
        ("CLM-LIFE-2025-009", "garage@insure.demo",
         "George Garage (self)",
         "Critical Illness – Pre-existing condition",
         "Rejected", 0, "Critical Illness"),

        ("CLM-LIFE-2025-010", "spares@insure.demo",
         "Sam Spares (self)",
         "Total Permanent Disability – Self-inflicted",
         "Rejected", 0, "Disability"),
    ]

    # ── INSERT MEDICAL CLAIMS ──────────────────────────────────────────────
    for row in medical_claims:
        (ref, client, hospital, treatment, cause, status, amount, beneficiary, has_docs) = row
        insured = beneficiary
        insurer = "Insure Kenya Ltd"
        location = hospital.split(",")[0].strip()

        cur.execute("""
            INSERT INTO claims_history
                (claim_ref, client, claim_type, insurer, claim_cause, status, location, date_filed, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(claim_ref) DO NOTHING
        """, (ref, client, "Medical", insurer, cause, status, location, now, now))

        # Status history
        cur.execute("""
            INSERT INTO status_history (claim_ref, action, user_email, timestamp, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (ref, f"Claim {status}", "system", now, f"Medical claim – {treatment}"))

        # Reserves (for approved/settled)
        if amount > 0 and status in ("Approved", "Settled"):
            reserve_amount = min(amount * 0.8, 1_000_000)
            cur.execute("""
                INSERT INTO reserves (claim_ref, reserve_amount, amount_paid, reserve_type, reason, status, set_by, set_date)
                VALUES (?, ?, 0, ?, ?, ?, ?, ?)
            """, (ref, reserve_amount, "Initial Reserve", "Medical treatment cost", "Active", "officer@insure.demo", now))
            if status == "Settled":
                cur.execute("UPDATE reserves SET status='Released' WHERE claim_ref=? AND status='Active'", (ref,))

        # Expert assignment (assessment stage)
        if status in ("Assessment", "Investigation", "Approved"):
            cur.execute("""
                INSERT INTO expert_assignments (claim_ref, expert_name, expert_type, assigned_date, status, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ref, "Metropolitan Health Assessors", "medical_assessor", now, "Assigned",
                  f"Medical review – {treatment}"))

        # Diary entries for open claims
        if status in ("FNOL", "Assessment", "Investigation"):
            cur.execute("""
                INSERT INTO diary_entries (claim_ref, entry_text, entry_date, entered_by, due_date, priority, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ref, f"Follow up medical documents for {treatment}", now,
                  "officer@insure.demo", "2025-08-15", "High", "Open"))

        # Settlement for settled
        if status == "Settled" and amount > 0:
            wht = amount * 0.15
            net = amount - wht
            cur.execute("""
                INSERT INTO settlements
                    (claim_ref, settlement_amount, wht_amount, net_amount, settlement_date, settlement_type, status, approved_by, approved_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ref, amount, wht, net, now, "Bank Transfer", "Approved", "hoc@insure.demo", now))

    # ── INSERT LIFE CLAIMS ────────────────────────────────────────────────
    for row in life_claims:
        (ref, client, beneficiary, cause, status, amount, claim_type) = row
        insurer = "Insure Kenya Ltd"
        location = "Nairobi"

        cur.execute("""
            INSERT INTO claims_history
                (claim_ref, client, claim_type, insurer, claim_cause, status, location, date_filed, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(claim_ref) DO NOTHING
        """, (ref, client, "Life", insurer, cause, status, location, now, now))

        # Status history
        cur.execute("""
            INSERT INTO status_history (claim_ref, action, user_email, timestamp, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (ref, f"Claim {status}", "system", now, f"Life claim – {claim_type}"))

        # Reserves
        if amount > 0 and status in ("Approved", "Settled"):
            cur.execute("""
                INSERT INTO reserves (claim_ref, reserve_amount, amount_paid, reserve_type, reason, status, set_by, set_date)
                VALUES (?, ?, 0, ?, ?, ?, ?, ?)
            """, (ref, amount, "Life Benefit Reserve", f"Life claim – {claim_type}", "Active",
                  "officer@insure.demo", now))
            if status == "Settled":
                cur.execute("UPDATE reserves SET status='Released' WHERE claim_ref=? AND status='Active'", (ref,))

        # Expert for investigation
        if status == "Investigation":
            cur.execute("""
                INSERT INTO expert_assignments (claim_ref, expert_name, expert_type, assigned_date, status, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ref, "Forensic Life Underwriters", "life_examiner", now, "Assigned",
                  f"Life claim investigation – {cause}"))

        # Diary for open
        if status in ("FNOL", "Assessment", "Investigation"):
            cur.execute("""
                INSERT INTO diary_entries (claim_ref, entry_text, entry_date, entered_by, due_date, priority, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ref, f"Obtain death certificate / medical records for {claim_type}", now,
                  "officer@insure.demo", "2025-08-20", "Critical", "Open"))

        # Settlement for settled
        if status == "Settled" and amount > 0:
            wht = amount * 0.15
            net = amount - wht
            cur.execute("""
                INSERT INTO settlements
                    (claim_ref, settlement_amount, wht_amount, net_amount, settlement_date, settlement_type, status, approved_by, approved_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ref, amount, wht, net, now, "Bank Transfer", "Approved", "hoc@insure.demo", now))

    conn.commit()
    print(f"✅ Seeded {len(medical_claims)} medical + {len(life_claims)} life claims")


if __name__ == "__main__":
    seed_medical_life()
    print("Run: streamlit run app.py --server.port 8501")
