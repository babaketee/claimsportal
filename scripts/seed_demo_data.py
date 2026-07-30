#!/usr/bin/env python3
"""Seed script — 50+ realistic Kenyan motor and business claims demo data.

Run: python scripts/seed_demo_data.py

Covers:
- Motor: bumper, windscreen, theft, third-party bodily harm, fire, flood
- Business: fire, burglary, WIBA, goods in transit, business interruption

All amounts in KES. Realistic Nairobi/Kiambu dates (2024-2025).
No medical or life claims (per user constraint).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_api import (
    set_reserve, approve_reserve,
    assign_expert, update_assignment_status,
    log_communication,
    add_diary_entry, complete_diary_entry,
    recommend_settlement,
    _get_conn,
)

MOTO_OWNER = "client@insure.demo"   # The main client demo account
INSURED = {
    "Motor - Comprehensive": "Kamau Mwangi, ID: 12345678, P.O. Box 12345 Nairobi",
    "Motor - Third Party": "Wanjiku Njeri, ID: 23456789, P.O. Box 23456 Nairobi",
    "Business - Fire": "Muthoni Enterprises Ltd, PIN: A000123456B",
    "Business - Burglary": "Karimi Wholesale, PIN: A000234567C",
    "Business - WIBA": "Otieno & Sons Construction, PIN: A000345678D",
    "Business - Goods in Transit": "Transline Logistics Ltd, PIN: A000456789E",
}

def seed():
    conn = _get_conn()
    cur = conn.cursor()
    print("Seeding demo data...")

    # ── MOTOR CLAIMS ──────────────────────────────────────────────────────────

    motor_claims = [
        # claim_ref, claim_type, status, date, amount, vehicle, expert_type, description
        ("CLM-2024-001", "Motor Bumper", "Settled", "2024-01-15", 85000, "KCA 123A", "garage", "Rear bumper damaged in parking lot, Kasarani"),
        ("CLM-2024-002", "Windscreen", "Settled", "2024-02-03", 32000, "KBZ 456B", "assessor", "Stone chip crack on Mombasa Road"),
        ("CLM-2024-003", "Third Party Bodily Harm", "Settled", "2024-03-10", 450000, "KD 789C", "investigator", "Pedestrian injured at Westlands junction, CCTV footage available"),
        ("CLM-2024-004", "Theft", "Rejected", "2024-04-22", 0, "KE 101D", "assessor", "Vehicle stolen from Karen parking — no evidence of forced entry; policy exclusion applies"),
        ("CLM-2024-005", "Fire Damage", "Settled", "2024-05-08", 210000, "KF 202E", "assessor", "Engine bay fire, cause undetermined, Eastleigh"),
        ("CLM-2024-006", "Flood Damage", "Assessment", "2024-06-14", 0, "KG 303F", "assessor", "Flooded on Mombasa Road underpass during heavy rains"),
        ("CLM-2024-007", "Motor Bumper", "Investigation", "2024-07-01", 0, "KH 404G", "investigator", "Disputed liability for collision at Ruaka roundabout"),
        ("CLM-2024-008", "Windscreen", "Settled", "2024-08-19", 18500, "KJ 505H", "garage", "Cracked windscreen after highway stone chip"),
        ("CLM-2024-009", "Theft", "Rejected", "2024-09-05", 0, "KK 606J", "assessor", "Claimed theft of stereo — no police abstract submitted"),
        ("CLM-2024-010", "Third Party Property", "Approved", "2024-10-12", 275000, "KL 707K", "assessor", "Collision with shop front on Ngong Road — third party claim validated"),
        ("CLM-2025-001", "Motor Bumper", "FNOL", "2025-01-08", 0, "KM 808L", null, "Rear bumper damaged in Kilimani mall parking"),
        ("CLM-2025-002", "Windscreen", "Assessment", "2025-01-25", 0, "KN 909M", "assessor", "Full windscreen replacement needed after highway incident"),
        ("CLM-2025-003", "Fire Damage", "Investigation", "2025-02-10", 0, "KP 101N", "assessor", "Vehicle arson suspected, Kileleshwa — police OB 234/10/02"),
        ("CLM-2025-004", "Theft", "Rejected", "2025-03-04", 0, "KR 202R", null, "Claimed theft of spare tyre — policy exclusion for personal belongings"),
        ("CLM-2025-005", "Third Party Bodily Harm", "Approved", "2025-03-20", 680000, "KS 303S", "investigator", "Pedestrian knocked down at Embakasi — grievous harm confirmed"),
        ("CLM-2025-006", "Flood Damage", "Settled", "2025-04-11", 95000, "KT 404T", "garage", "Water ingress through sunroof during Nairobi floods"),
        ("CLM-2025-007", "Motor Bumper", "Assessment", "2025-05-02", 0, "KU 505U", "assessor", "Front bumper replaced after Pangani incident"),
        ("CLM-2025-008", "Windscreen", "Settled", "2025-05-28", 42000, "KV 606V", "garage", "Windscreen + wiper motor replacement"),
        ("CLM-2025-009", "Theft", "Rejected", "2025-06-15", 0, "KW 707W", null, "Vehicle claimed stolen — GPS shows vehicle still at registered address"),
        ("CLM-2025-010", "Third Party Property", "Investigation", "2025-07-01", 0, "KX 808X", "investigator", "Collision at Sagana junction — liability disputed"),
        ("CLM-2025-011", "Motor Bumper", "Approved", "2025-07-10", 55000, "KY 909Y", "garage", "Hit parked car in Kisumu CBD"),
        ("CLM-2025-012", "Fire Damage", "Assessment", "2025-07-18", 0, "KZ 101Z", "assessor", "Electrical fire shorted dashboard, Ruiru"),
        ("CLM-2025-013", "Windscreen", "Settled", "2025-07-25", 28000, "KAA 202A", "garage", "Side window shattered, Westlands"),
        ("CLM-2025-014", "Third Party Bodily Harm", "FNOL", "2025-07-28", 0, "KBB 303B", "investigator", "Cyclist injured by reversing vehicle, Karen"),
        ("CLM-2025-015", "Motor Bumper", "Settled", "2025-07-30", 67000, "KCC 404C", "garage", "Parking dent repair, Yaya Centre"),
    ]

    # ── BUSINESS CLAIMS ───────────────────────────────────────────────────────

    business_claims = [
        # claim_ref, claim_type, status, date, amount, insured_name, description
        ("CLM-2024-101", "Business Fire", "Settled", "2024-01-28", 1250000, "Muthoni Enterprises Ltd", "Warehouse fire, Ruiru — electrical fault origin confirmed"),
        ("CLM-2024-102", "Business Burglary", "Rejected", "2024-03-15", 0, "Karimi Wholesale", "Stock theft claim — no signs of forced entry, alarm not triggered"),
        ("CLM-2024-103", "WIBA", "Settled", "2024-05-20", 340000, "Otieno & Sons Construction", "Construction worker fell from scaffold, Westlands site — WIBA claim"),
        ("CLM-2024-104", "Goods in Transit", "Settled", "2024-06-10", 580000, "Transline Logistics Ltd", "Container spilled on Mombasa-Nairobi highway, goods damaged"),
        ("CLM-2024-105", "Business Fire", "Rejected", "2024-07-22", 0, "Muthoni Enterprises Ltd", "Second fire claim within 12 months — policy exclusion for recurrent fire"),
        ("CLM-2024-106", "Business Burglary", "Approved", "2024-08-14", 890000, "Karimi Wholesale", "Break-in through back door, Nakuru branch — forced entry confirmed"),
        ("CLM-2024-107", "WIBA", "Assessment", "2024-09-30", 0, "Otieno & Sons Construction", "Worker RSI claim, Kisumu site — medical assessment pending"),
        ("CLM-2024-108", "Goods in Transit", "Settled", "2024-11-05", 210000, "Transline Logistics Ltd", "Water damage to electronics in transit during rainy season"),
        ("CLM-2025-101", "Business Fire", "Investigation", "2025-01-18", 0, "Muthoni Enterprises Ltd", "Storage unit fire, Industrial Area — cause under investigation"),
        ("CLM-2025-102", "Business Burglary", "FNOL", "2025-02-08", 0, "Karimi Wholesale", "Night break-in, Eldoret branch — police OB 45/08/02"),
        ("CLM-2025-103", "WIBA", "Approved", "2025-03-12", 520000, "Otieno & Sons Construction", "Electrician electrocution injury, Athi River site — WIBA settled"),
        ("CLM-2025-104", "Goods in Transit", "Assessment", "2025-04-05", 0, "Transline Logistics Ltd", "Hijacking incident, Mombasa — goods stolen, police involved"),
        ("CLM-2025-105", "Business Fire", "Settled", "2025-04-28", 780000, "Muthoni Enterprises Ltd", "Office fire, Nairobi CBD — 3 computers + furniture destroyed"),
        ("CLM-2025-106", "Business Burglary", "Rejected", "2025-05-19", 0, "Karimi Wholesale", "Claimed burglary — CCTV shows staff access only, no forced entry"),
        ("CLM-2025-107", "WIBA", "Assessment", "2025-06-08", 0, "Otieno & Sons Construction", "Supervisor fall injury, Mombasa site — medical report pending"),
        ("CLM-2025-108", "Goods in Transit", "Approved", "2025-07-01", 445000, "Transline Logistics Ltd", "Truck breakdown fire, Nakuru — cargo partially saved, partial loss"),
        ("CLM-2025-109", "Business Fire", "Settled", "2025-07-14", 320000, "Muthoni Enterprises Ltd", "Generator room fire, Syokimau"),
        ("CLM-2025-110", "Business Burglary", "Investigation", "2025-07-22", 0, "Karimi Wholesale", "After-hours theft, Mombasa — CCTV footage under review"),
        ("CLM-2025-111", "WIBA", "FNOL", "2025-07-29", 0, "Otieno & Sons Construction", "New site accident, Kilifi — RO report filed"),
        ("CLM-2025-112", "Business Interruption", "Assessment", "2025-07-30", 0, "Muthoni Enterprises Ltd", "Premises damaged by fire — business interruption claim filed"),
    ]

    all_claims = [(c, "Motor") for c in motor_claims] + [(c, "Business") for c in business_claims]

    for claim_data, category in all_claims:
        (claim_ref, claim_type, status, date, amount, *rest) = claim_data
        
        # Set initial reserve (50% of claim amount for approved ones)
        if amount > 0 and status not in ("Rejected", "FNOL"):
            reserve_amount = min(amount * 0.5, 500000)
            r_id = set_reserve(
                claim_ref=claim_ref,
                reserve_type="initial",
                amount=reserve_amount,
                purpose="assessment",
                created_by="officer@insure.demo",
                note=f"Initial reserve for {claim_type}"
            )
            if r_id and status in ("Settled", "Approved"):
                approve_reserve(r_id, "hoc@insure.demo")

        # Assign expert for non-rejected, non-FNOL
        if status not in ("Rejected", "FNOL") and len(rest) >= 2:
            expert_type = rest[1] if rest[1] else None
            if expert_type:
                expert_map = {
                    "garage": ("Kiambu Auto Works Ltd", "0711234567"),
                    "assessor": ("Apollo Surveyors Kenya", "0712345678"),
                    "investigator": ("Eastleigh Detective Agency", "0713456789"),
                }
                name, phone = expert_map.get(expert_type, ("Default Services Ltd", "0700000000"))
                a_id = assign_expert(
                    claim_ref=claim_ref,
                    expert_type=expert_type,
                    expert_name=name,
                    expert_phone=phone,
                    expert_company="",
                    assigned_by="officer@insure.demo",
                    estimated_cost=amount * 0.1 if amount > 0 else 50000,
                    note=f"Assigned for {claim_type}"
                )
                if status in ("Settled", "Approved"):
                    update_assignment_status(a_id, "completed")

        # Log communications for non-rejected
        if status != "Rejected":
            log_communication(
                claim_ref=claim_ref,
                channel="sms",
                direction="outbound",
                summary=f"FNOL acknowledgement sent for {claim_type} claim",
                created_by="officer@insure.demo",
                contact_name="Client",
                contact_phone="0700123456",
                consent=True
            )
        
        # Add diary entries for active claims
        if status in ("Assessment", "Investigation", "FNOL"):
            add_diary_entry(
                claim_ref=claim_ref,
                task=f"Follow up {claim_type} documents",
                due_date="2025-08-15",
                assigned_to="officer@insure.demo",
                priority="high",
                created_by="officer@insure.demo",
            )
        
        # Recommendations for settled/approved
        if status in ("Settled", "Approved") and amount > 0:
            recommend_settlement(
                claim_ref=claim_ref,
                amount=amount,
                payee_name="Claimant",
                payee_type="insured",
                recommended_by="officer@insure.demo",
                note=f"Settlement for {claim_type}",
            )

    print(f"✅ Seeded {len(all_claims)} claims ({len(motor_claims)} motor + {len(business_claims)} business)")
    print("Run: streamlit run app.py --server.port 8501")

if __name__ == "__main__":
    seed()
