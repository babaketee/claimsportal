"""
Standalone seed script: load 45 realistic Kenyan claims into the DB.
Can be run independently with: python seed_demo_data.py
"""
import random
import sys
import os

# Ensure the app's db path is resolvable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_db():
    """Import and return the shared db connection from core_api."""
    from core_api import get_db as _get_db
    return _get_db()


def seed_demo_data():
    """Insert 45 Kenyan claims (25 motor + 20 business) if the table is empty."""
    conn = get_db()
    cur = conn.execute("SELECT COUNT(*) FROM claims_history")
    count = cur.fetchone()[0]
    if count > 0:
        print(f"Database already has {count} claims — skipping seed.")
        conn.close()
        return
    conn.close()

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

    conn = get_db()
    now = "2026-07-30 12:00:00"

    for c in motor_claims + business_claims:
        conn.execute("""
            INSERT INTO claims_history
                (claim_ref, client, claim_type, insurer, claim_cause, status, location, vehicle_reg, date_filed, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (*c, now, now))

    for c in motor_claims + business_claims:
        reserve_amount = random.randint(50000, 500000)
        conn.execute("""
            INSERT INTO reserves (claim_ref, reserve_amount, amount_paid, reserve_type, reason, status, set_by, set_date)
            VALUES (?, ?, 0, 'Initial Reserve', 'Claim assessment', 'Active', 'system', ?)
        """, (c[0], reserve_amount, now))

    for c in motor_claims + business_claims:
        conn.execute("""
            INSERT INTO status_history (claim_ref, action, user_email, timestamp, notes)
            VALUES (?, 'Claim Reported', 'system', ?, 'Initial claim registration')
        """, (c[0], now))

    conn.commit()
    conn.close()
    print(f"Seeded {len(motor_claims)} motor claims and {len(business_claims)} business claims (45 total).")


if __name__ == "__main__":
    seed_demo_data()
