# Definite Assurance Claims Portal

A role-based claims management system for Definite Assurance Insurance, Kenya.
Built with Streamlit and SQLite.

**Live App:** https://claimsapp-gy3mrzy3af6hiyuqxczhcc.streamlit.app

---

## Overview

The Claims Portal manages the full lifecycle of insurance claims from intake through to
payment discharge. Five distinct personas, each with a tailored view, handle motor,
medical, life, and business insurance claims.

---

## Demo Accounts (password: Demo#99)

| Email | Role | Name |
|---|---|---|
| client@insure.demo | client | Assured |
| claims_officer@insure.demo | claims_officer | Caleb Officer |
| head_of_claims@insure.demo | head_of_claims | Diana HOC |
| finance@insure.demo | finance | Francis Finance |
| legal@insure.demo | legal | Grace Legal |
| operations@insure.demo | operations | Henry Ops |
| motor_fleet@insure.demo | motor_fleet | Ian Fleet |
| medical@insure.demo | medical | Joan Medical |
| life@insure.demo | life | Kevin Life |
| business@insure.demo | business | Laura Business |
| admin@insure.demo | admin | Admin |
| invoice@insure.demo | invoice | Invoice |
| counsel@insure.demo | counsel | Counsel |

---

## Claim Classes

- **Motor** - Vehicle damage, third-party liability, windscreen, theft
- **Medical** - Inpatient, outpatient, maternity, dental, optical
- **Life** - Death benefit, critical illness, disability
- **Business** - Fire, burglary, public liability, WIBA

---

## Claim Lifecycle

Draft -> Intake -> Triage -> Assessment -> Approval -> Reserves Set -> Payment Processing -> Discharged

Status transitions are one-directional. Legal can flag a claim for appeal creating a workflow branch.

---

## Page Structure

**Claimant (public)**
- Dashboard - Claim status tracker, submitted claim history

**Intake (claims_officer, head_of_claims)**
- Queue - All new claims awaiting triage

**Provider (medical, life)**
- Assigned Claims - Claims assigned to the provider for review

**Finance (finance, cfo)**
- Reserves - Claims at Approval / Approved / Pending Payment stages

**Legal (legal)**
- Legal Review - Claims flagged for legal review or with appeal filed

**Operations (operations)**
- Discharge Voucher - Final payment authorisation before settlement

**Admin (admin)**
- Overview - System-wide dashboard: claim counts, status breakdown, TAT metrics

---

## Architecture

| Layer | Technology |
|---|---|
| Frontend | Streamlit (Python) |
| Database | SQLite (claims_portal.db) |
| Auth | Session-state RBAC (Phase 1) |
| Secrets | Streamlit Cloud Secrets |
| Hosting | Streamlit Cloud |
| Source control | GitHub babaketee/claimsportal |

---

## Key Files

| File | Purpose |
|---|---|
| app.py | Main entry point, role-based navigation |
| core_engine.py | ClaimsEngine - all DB operations, seed data |
| lib/auth.py | DEMO_USERS, login form, session helpers |
| lib/helpers.py | Date utils, TAT formatters, claim ref generators |
| lib/models.py | SCHEMA_SQL - table definitions |
| lib/document_store.py | Document attachment storage |
| pages/ | Streamlit multi-page navigation files |
| scripts/ | Seed scripts for demo data |

---

## Database Schema

**claims** (25 columns): id, claim_ref, policy_ref, claimant_email, status,
status_changed_at, created_at, updated_at, incident_date, incident_type,
incident_location, incident_description, estimated_amount, claim_class,
fast_track, total_loss_indicator, assigned_to, assigned_role, external_ref,
salvage_value, discharge_voucher_signed, discharge_voucher_date, appeal_filed,
appeal_ref, extra_data

**reserve_movements** (6 columns): id, claim_ref, movement_type, amount,
currency, created_at, created_by

**audit_log** (7 columns): id, claim_ref, action, actor, timestamp, ip_address, details

**documents** (8 columns): id, claim_ref, filename, uploaded_by, uploaded_at,
file_path, mime_type, file_size

---

## Demo Data

On first startup (or when DB is empty), ClaimsEngine.__init__ calls _seed_demo_if_empty()
which populates:
- 15 sample claims across all four classes and multiple statuses
- Reserve movement history for finance workflow
- Audit log entries
- Document placeholders

DB is **ephemeral on Streamlit Cloud** - data resets on every redeploy.
Demo data re-seeds automatically on first boot.

---

## Kenyan Regulatory Context

- **IRA** - Insurance Regulatory Authority governs all claims handling
- **TIMS** - Motor claims via the Motor Insurance Database
- **NHIF** - Medical covers supplement National Health Insurance Fund
- **WIBA** - Workers Compensation Act coverage for business class

---

## Deployment

**Streamlit Cloud:**
1. Push to GitHub repo (babaketee/claimsportal)
2. Connect at share.streamlit.io
3. Set branch to railway-migration
4. Add secret: DEMO_PASSWORD=Demo#99
5. Redeploy - demo data seeds automatically

**Local Development:**
```
git clone https://github.com/babaketee/claimsportal.git
cd claimsportal
pip install streamlit pandas
streamlit run app.py
```

---

## Known Issues

- DB is ephemeral on Streamlit Cloud - data resets on redeploy
- Auth is session-state demo auth (Phase 1) - swap for OIDC/SSO in production

---

Internal use only - Definite Assurance Insurance Ltd.
IRA Licensed Insurer - Kenya