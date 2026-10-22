# Definite Assurance Claims Portal — Documentation

> **Definite Assurance Co. Ltd.** — *You Are Definitely Covered*
> A Streamlit-based insurance claims management system built for the Kenyan market.
>
| Meta | Value |
|------|-------|
| **Version** | 2.1.0 |
| **Build** | 2025-07-30 |
| **Phase** | phase2-complete |
| **Branch** | railway-migration |
| **Runtime** | Python 3.11+, Streamlit ≥ 1.35 |
| **Data layer** | SQLite (local) with optional external REST / Databricks analytics |
| **Currency** | Kenyan Shillings (KES) |

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture](#2-system-architecture)
3. [UI/UX Design System](#3-uiux-design-system)
4. [Role Reference](#4-role-reference)
5. [Demo Accounts](#5-demo-accounts)
6. [API Reference](#6-api-reference)
7. [Database Schema](#7-database-schema)
8. [Kenya Features](#8-kenya-features)
9. [Deployment Guide](#9-deployment-guide)
10. [Testing Guide](#10-testing-guide)
11. [Seeding](#11-seeding)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Overview

The **Definite Assurance Claims Portal** is a unified web application that manages
the end-to-end claims lifecycle for Kenya's leading motor and commercial insurer. It
replaces ad-hoc email, phone, and spreadsheet workflows with a single, brand-aligned
interface used by policyholders, claims handlers, assessors, garages, investigators,
finance teams, legal officers, and system administrators.

### Core Capabilities

- **First Notification of Loss (FNOL)** — clients submit claims with policy details,
  incident information, third-party data, police OB references, and document uploads
  (driver's licence, NTSA logbook, police abstract, scene photos).
- **Claims Assignment & Workflow** — claims officers assign assessors, garages, and
  investigators; track status through an auditable timeline; manage reserves and
  diary follow-ups.
- **Settlement Engine** — officer recommendations with automatic Withholding Tax
  calculation, Head-of-Claims approval gates, Finance Head co-approval for high-value
  claims, and bank-payment confirmation.
- **Service Provider Portals** — assessors submit reports, garages submit estimates and
  invoices, investigators file investigation reports — all with per-claim payment
  status tracking.
- **Spare Parts RFQ Marketplace** — garages broadcast RFQs; spare-parts providers
  submit bids scored automatically on price (60 %) + provider rating (40 %).
- **Legal & Dispute Management** — repudiation workflow, litigation tracker, demand
  letters, offers to settle, IRA/ombudsman complaints, and recovery/subrogation.
- **Super Admin** — user management, role configuration, API configuration, view
  permissions matrix, business-rule tuning, audit log, and database management.
- **Analytics & KPIs** — live charts (claims by type, status distribution, settlement
  trend, cycle time, reserve adequacy, WHT summary) backed by Databricks or SQLite.

### Regulatory Alignment

The portal encodes Kenya-specific requirements throughout:

- **Insurance Act (Cap 111)** — Section 75 (14-day acknowledgment) and Section 76
  (30-day settlement) SLA rules.
- **Data Protection Act 2019 (DPA 2019)** — explicit consent checkbox on the FNOL
  form; DPA consent captured per communication logged.
- **Kenya Revenue Authority (KRA)** — Withholding Tax applied at source on service
  provider payments (5 % / 10 % by provider type).
- **Insurance Regulatory Authority (IRA)** — statutory response deadlines tracked
  for regulator complaints; reinsurance escalation at KES 2,000,000.

---

## 2. System Architecture

### 2.1 Component Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Browser / Streamlit UI                        │
│                                                                      │
│  ┌─────────────┐  ┌──────────────────────────────────────────────┐  │
│  │ views/      │  │  views/brand.py — CSS + Plotly theme          │  │
│  │  *.py       │  │  (Aberdare Green / Uhuru Red palette)          │  │
│  │  (11 views) │  │                                              │  │
│  └──────┬──────┘  └──────────────────────────────────────────────┘  │
│         │ imports                                                     │
│         ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    core_api.py                                  │ │
│  │  • CoreAPI class (module-level instance: core_api)              │ │
│  │  • SQLite connection (_get_conn, _init_db)                      │ │
│  │  • Business-rule constants (SLA, limits, WHT)                   │ │
│  │  • ID generators (CLM-, EVT-, RSV-, ASN-, DOC-, STL-, …)        │ │
│  │  • Module-level wrapper functions                               │ │
│  │  • Optional external REST sync (CORE_API_BASE_URL)              │ │
│  └──────┬─────────────────────────────┬───────────────────────────┘ │
│         │                             │                             │
│         ▼                             ▼                             │
│  ┌───────────────┐          ┌─────────────────┐                    │
│  │ claims_       │          │ views/          │                    │
│  │ operations.db │          │ analytics_      │                    │
│  │  (SQLite)     │          │ charts.py       │                    │
│  └───────────────┘          │  • Databricks   │                    │
│                             │    SQL API      │                    │
│                             │  • SQLAlchemy   │                    │
│                             │  • Demo mode    │                    │
│                             └─────────────────┘                    │
└────────────────────────────────────────┬─────────────────────────────┘
                                         │ optional sync
                                         ▼
                              ┌─────────────────────┐
                              │  External Core API   │
                              │  (REST + Bearer)    │
                              └─────────────────────┘
```

### 2.2 Data Flow

| Step | Flow |
|------|------|
| 1 | **Client** submits FNOL → `client_portal._db_write_fnol()` → `core_api.create_claim()` (SQLite `INSERT`) → `core_api.post_claim()` (optional REST push) → documents uploaded via `core_api.post_document()`. |
| 2 | **Claims Officer** opens a claim → `core_api.get_claim()` + `core_api.get_timeline()` (cached 30s) → assigns expert → `core_api.assign_expert()` → logs SMS → `core_api.log_communication()`. |
| 3 | **Assessor/Garage/Investigator** updates status → `core_api.update_assignment_status()` → `core_api.invalidate_claim_cache()` triggers UI refresh. |
| 4 | **Claims Officer** recommends settlement → `core_api.recommend_settlement()` auto-calculates WHT → `core_api.approve_settlement()` (HoC gate). |
| 5 | **Finance** processes payment → `core_api.mark_settlement_paid()` + `core_api.log_communication()` (SMS to client). |
| 6 | **Super Admin** changes business rules → updates env vars → app restart applies. |

### 2.3 Layer Summary

| Layer | File(s) | Responsibility |
|-------|---------|----------------|
| **Entry point** | `app.py` | Page config, brand injection, login, sidebar, role router. |
| **Data / API** | `core_api.py` | `CoreAPI` class, SQLite schema, CRUD, business rules, external sync. |
| **Views** | `views/*.py` (11 modules) | Role-specific UI rendering. |
| **Branding** | `views/brand.py` | CSS variables, Plotly theme, logo renderers, badge helpers. |
| **Analytics** | `views/analytics_charts.py` | KPI loaders + Plotly chart grid (Databricks/SQLAlchemy/demo). |
| **Seed data** | `scripts/seed_demo_data.py` | 35 demo claims with reserves, assignments, communications, settlements. |
| **Tests** | `tests/test_core_api.py`, `tests/test_views_import.py` | Unit + import tests. |
| **Deployment** | `Procfile`, `start.sh`, `app.yaml`, `railway.toml` | Streamlit server config for Heroku / Railway / Databricks. |
| **CI/CD** | `.github/workflows/python-app.yml` | flake8 lint + pytest + coverage. |

### 2.4 Key Design Decisions

- **SQLite-first with external fallback.** All write and read operations hit local
  SQLite for sub-second response. When `CORE_API_BASE_URL` is set, writes are also
  POSTed to the external core system; reads still prefer SQLite (see `core_api.py`
  docstring). This enables offline work and gradual migration.
- **Dual API surface.** Every capability is exposed both as a `CoreAPI` instance
  method (used by views) and as a module-level function (used by the seed script and
  tests). This ensures parity and testability.
- **Cache invalidation hooks.** Views call `core_api.invalidate_claim_cache()` after
  writes; in SQLite mode this is a no-op, but it provides the extension point for a
  future Redis/Databricks cache layer.
- **Demo-first authentication.** Login is a stub keyed to `DEMO_ACCOUNTS` in `app.py`.
  Production replaces this with IMS REST API, Okta/Azure AD SSO, or OTP via Africa's
  Talking / Twilio (see `app.py` TODO comments).
- **Graceful degradation.** Service-provider and spare-parts views detect
  `core_api.is_configured()` and fall back to demo/sample data when no external API
  is configured.

---

## 3. UI/UX Design System

The full brand specification lives in `DESIGN.md` and is implemented in
`views/brand.py`. A condensed reference follows.

### 3.1 Colour Palette

| Name | Hex | Usage |
|------|-----|-------|
| **Aberdare Green** | `#0f4f48` | Primary brand — headings, sidebar background, metric values |
| **Uhuru Red** | `#eb2229` | Accent — primary buttons, active tabs, alerts, status urgency |
| **Institutional Blue** | `#00567a` | Secondary — table headers, outline buttons, links |
| **Solid Black** | `#000000` | Headings, body text |
| **Urban White** | `#ffffff` | Page and card backgrounds |

**Tint scale** — Green 70 % (`#3e756f`), 30 % (`#a8c7c4`), 10 % (`#e5f0ef`);
Red 70 % (`#f17075`), 10 % (`#fce8e9`).

### 3.2 Typography

| Role | Font Stack | Weight |
|------|-----------|--------|
| Headlines | Gotham / Roboto Black | 900, ≥ 24 pt |
| Subheaders | Gotham / Roboto Bold | 700, 16–24 pt |
| Body | Gotham / Roboto Regular | 400, 12–16 pt |
| UI labels | Gotham / Roboto Medium | 500 |
| Metric cards | Roboto | 700 |

Roboto weights 300, 400, 500, 700, 900 are loaded via Google Fonts `@import`.

### 3.3 Components

- **Buttons** — Primary (Uhuru Red `#eb2229`, white text, hover `#c41e24`);
  Secondary (white, green text); Ghost (transparent, green border).
- **Metric cards** — KPI cards with a 4 px coloured left accent; value in green
  (700 weight), label muted grey.
- **Data tables** — `--da-blue` header on white text, zebra striping on
  `--da-bg-subtle`, hover `--da-blue-10`, numeric columns right-aligned.
- **Tabs** — Active tab gets a 3 px solid Uhuru Red underline; inactive tabs
  muted. Used in Claims Officer (7 tabs), Finance (6 tabs), Legal (7 tabs), etc.
- **Status badges** — `da-badge` with colour + explicit text label (WCAG
  1.4.1 compliant — never colour-only). Variants: green (Active), red (Blocked),
  blue (Review), amber (Pending), gray (Neutral).
- **Forms** — Required fields marked `*`; primary submit button full-width;
  inputs 4 px border with green focus ring.

### 3.4 Status Badge Semantic Mapping

| Colour variant | Default label | Typical use |
|----------------|--------------|-------------|
| green | Active | Settled, Approved, Paid |
| red | Blocked | Repudiated, Rejected, Investigation |
| blue | Review | Under Assessment, Pending Approval |
| amber | Pending | Under Review, Awaiting Payment |
| gray | Neutral | Submitted, FNOL |

### 3.5 Plotly Theme

`register_plotly_theme()` (auto-called on import) creates the
`definite_assurance` template:

- **Colorway**: 8-stop `DA_COLORWAY` (green → red).
- **Sequential scale**: `DA_SCALE_GREEN_RED` — green = good/fast, red = urgent/slow.
- **Font**: Gotham/Roboto, `#333333`, size 12.
- **Hover labels**: Aberdare Green background, white text.
- **Paper/plot background**: `#ffffff`.

### 3.6 Chart Inventory

| Chart | Type | Data source |
|-------|------|-------------|
| Claims by Type | Bar (categorical) | `claims.claims_kpi_view` or demo |
| Status Distribution | Donut | Same |
| Settlement Trend | Line (multi-series) | Same |
| Avg Cycle Time by Type | Horizontal bar (RdYlGn) | Same |
| Reserve vs Actual | Stacked bar | Same |
| Payments by Type | Bar | Same |
| SLA Compliance | — | `core_api.get_sla_status()` |
| Expert Performance | — | `claims.claims_kpi_view` |
| WHT Summary | Stacked bar | `settlements` table |

### 3.7 Iconography

Icons are Unicode emojis embedded in Streamlit strings (no external icon library):

| Purpose | Icon |
|---------|------|
| Claims list | 📋 |
| My Claims | 📥 |
| Assign Experts | 👥 |
| Reserve Management | 💼 |
| Settlement | ✅ |
| Payment Authorisation | 💸 |
| Correspondence | 📨 |
| Bid Comparison | 🏷️ |
| Dashboard | 📊 |
| Analytics | 📈 |
| Reports | 📑 |
| RFQ Bids | 🛒 |
| Legal / Litigation | ⚖️ |
| Payment Status | 🔄 |

### 3.8 Layout Structure

```
┌─ Brand Strip (logo + "You Are Definitely Covered") ──────────┐
├─ Sidebar (Aberdare Green) ─┬─ Role label, user email ───────┤
│                           └─ Sign Out button ──────────────┤
├─ Main Content (white) ───────────────────────────────────────┤
│  ┌─ Title + subtitle ──────────────────────────────────────┐ │
│  ├─ Tabs / expanders ─────────────────────────────────────┤ │
│  ├─ Data tables, metrics, charts ─────────────────────────┤ │
│  └─ Forms with validation ────────────────────────────────┘ │
```

---

## 4. Role Reference

The portal defines **12 roles** in the `ROLES` registry (`app.py`). Each role
maps to a dedicated view module. Finance and Finance Head share the same view
module (`views/finance.py`) but have different tabs and a different approval
limit, giving **11 distinct functional roles**.

| # | Role key | Display name | View module | Primary responsibilities |
|---|----------|-------------|-------------|-------------------------|
| 1 | `client` | Policyholder / Client | `views/client_portal.py` | Submit FNOL, track claims, upload/view documents, message experts. |
| 2 | `claims_officer` | Claims Officer | `views/claims_officer.py` | Process FNOL, assign experts, set/supplement reserves, recommend settlements, authorise service payments, log communications, compare spare-parts bids. **Auto-approve limit: KES 500,000.** |
| 3 | `head_of_claims` | Head of Claims | `views/head_of_claims.py` | Dashboard, SLA monitoring, pending approvals (KES 500k–2M), repudiation decisions, performance analytics. **Approval limit: KES 2,000,000.** |
| 4 | `assessor` | Assessor | `views/service_provider.py` | View assigned jobs, submit assessment reports, approve/reject garage estimates, check payment status. **WHT: 5 %.** |
| 5 | `garage` | Garage / Repairer | `views/service_provider.py` | View jobs, submit repair estimates, request supplementary approvals, submit invoices, track payment status. **WHT: 5 %.** |
| 6 | `investigator` | Investigator | `views/service_provider.py` | View assigned claims, submit investigation reports, update claim status, track payment status. **WHT: 5 %.** |
| 7 | `finance` | Finance / Accounts Payable | `views/finance.py` | Process approved payments, update payment status, reconciliation, reports. |
| 8 | `finance_head` | Finance Head | `views/finance.py` | All finance functions + high-value settlement approvals (above KES 2M). **Limit: KES 5,000,000.** |
| 9 | `spare_parts` | Spare Parts Provider | `views/spare_parts_provider.py` | View open RFQ broadcasts, submit bids, track bid results, manage active orders, submit invoices, track payment status. **WHT: 10 %.** |
| 10 | `legal` | Legal Officer | `views/legal.py` | Dispute register, repudiation appeals, litigation tracker, demand letters, offers to settle, IRA complaints, recovery & subrogation. |
| 11 | `admin` | Internal Staff / Admin | `views/admin_dashboard.py` | Internal claims dashboard, SLA monitor, vendor management, audit log, analytics. |
| 12 | `super_admin` | Super Admin | `views/super_admin.py` | Full system — user management, role config, API configuration, view-permission matrix, business-rule tuning, database management, audit log. |

### Role Routing Logic (`app.py` `main()`)

```python
if role == "client":          → from views.client_portal import render; render()
elif role == "claims_officer": → from views.claims_officer import render; render()
elif role == "head_of_claims": → from views.head_of_claims import render; render()
elif role in ("assessor", "garage", "investigator"):
                               → from views.service_provider import render; render(role)
elif role in ("finance", "finance_head"):
                               → from views.finance import render; render(role)
elif role == "spare_parts":    → from views.spare_parts_provider import render; render()
elif role == "legal":          → from views.legal import render; render()
elif role == "super_admin":    → super_admin_show()
elif role == "admin":          → from views.admin_dashboard import render; render()
```

### Approval Authority Limits

| Role | Auto-Approve Limit | Notes |
|------|-------------------|-------|
| Claims Officer | KES 500,000 | Above this → Head of Claims sign-off required. |
| Head of Claims | KES 2,000,000 | Above this → Finance Head co-approval required. |
| Finance Head | KES 5,000,000 | Above this → Board / Management resolution required. |
| Reinsurance trigger | KES 2,000,000 | Total incurred (reserves + settlements) exceeding this flags for reinsurance recovery. |

---

## 5. Demo Accounts

All demo accounts use the password shown below. Passwords follow a memorable
convention (the role name's first letters + `#99`).

| Email | Password | Role | Full name (per Super Admin) |
|-------|----------|------|-----------------------------|
| `client@insure.demo` | `Assured#99` | client | Kamau Mwangi |
| `officer@insure.demo` | `Handler#99` | claims_officer | Grace Wanjiku |
| `hoc@insure.demo` | `Oversee#99` | head_of_claims | David Ochieng |
| `assessor@insure.demo` | `Survey#99` | assessor | James Kariuki |
| `garage@insure.demo` | `Wrench#99` | garage | Peter Kamau |
| `investigator@insure.demo` | `Sleuth#99` | investigator | Robert Mutua |
| `finance@insure.demo` | `Invoice#99` | finance | Susan Achieng |
| `cfo@insure.demo` | `Reserves#99` | finance_head | *(name not in Super Admin seed)* |
| `spares@insure.demo` | `Catalog#99` | spare_parts | Francis Ngugi |
| `legal@insure.demo` | `Counsel#99` | legal | Michael Odhiambo |
| `admin@insure.demo` | `SysCtrl#99` | admin | System Admin |
| `super@insure.demo` | `Super#99` | super_admin | Super Admin |

> **Note:** Auth is a stub. In production, replace the `DEMO_ACCOUNTS` lookup in
> `app.py` `show_login()` with one of:
> - IMS REST API → `POST /api/auth/login`
> - Okta / Azure AD SSO → OIDC redirect
> - OTP via Africa's Talking / Twilio

### Login Flow

1. Enter email (or policy number) + password.
2. Credentials checked against `DEMO_ACCIENTS`.
3. On success, session state set: `authenticated=True`, `role=<role>`, `user=<email>`.
4. `st.rerun()` → `main()` → routed to role view.
5. **Sign Out** button clears session state and returns to login.

---

## 6. API Reference

The data layer is exposed through the module-level singleton **`core_api`**
(an instance of `CoreAPI` in `core_api.py`). Views import it as
`from core_api import core_api`. Module-level wrapper functions exist for every
method (used by the seed script and tests).

### 6.1 Configuration

| Constant | Type | Default | Environment variable | Description |
|----------|------|---------|---------------------|-------------|
| `_DB_PATH` | `str` | `claims_operations.db` | `CLAIMS_DB_PATH` | SQLite database file path. |
| `_CORE_API_BASE_URL` | `str` | `""` | `CORE_API_BASE_URL` | External core system REST endpoint. |
| `_CORE_API_KEY` | `str` | `""` | `CORE_API_KEY` | Bearer token for external API. |
| `REINSURANCE_THRESHOLD` | `int` | `2_000_000` | `REINSURANCE_THRESHOLD` | KES threshold for reinsurance flag. |
| `OFFICER_AUTO_APPROVE_LIMIT` | `int` | `500_000` | `OFFICER_AUTO_APPROVE_LIMIT` | Claims Officer auto-approval ceiling. |
| `HOC_APPROVE_LIMIT` | `int` | `2_000_000` | `HOC_APPROVE_LIMIT` | Head of Claims approval ceiling. |
| `FINANCE_HEAD_LIMIT` | `int` | `5_000_000` | `FINANCE_HEAD_LIMIT` | Finance Head approval ceiling. |
| `SLA_ACK_DAYS` | `int` | `14` | `SLA_ACK_DAYS` | Acknowledgment SLA in days. |
| `SLA_SETTLE_DAYS` | `int` | `30` | `SLA_SETTLE_DAYS` | Settlement SLA in days. |
| `WHT_RATES` | `dict` | (see §8.1) | — | Kenya Revenue withholding-tax rates by provider type. |

### 6.2 ID Generation

| Prefix | Entity | Format | Example |
|--------|--------|--------|---------|
| `CLM-` | Claim | `CLM-` + `YYYYMMDDHHMMSS` + microsecond | `CLM-20250715123456` |
| `EVT-` | Status history event | `EVT-` + `YYYYMMDD` + 6-char hex | `EVT-20250715-A1B2C3` |
| `RSV-` | Reserve | `RSV-` + `YYYYMMDD` + 6-char hex | `RSV-20250715-ABC123` |
| `DRY-` | Diary entry | `DRY-` + `YYYYMMDD` + 6-char hex | |
| `COM-` | Communication | `COM-` + `YYYYMMDD` + 6-char hex | |
| `ASN-` | Expert assignment | `ASN-` + `YYYYMMDD` + 6-char hex | `ASN-20250730-ABC123` |
| `DOC-` | Document | `DOC-` + `YYYYMMDD` + 6-char hex | |
| `STL-` | Settlement | `STL-` + `YYYYMMDD` + 6-char hex | |
| `PAY-` | Service payment | `PAY-` + `YYYYMMDD` + 6-char hex | |
| `MSG-` | Client message | `MSG-` + `YYYYMMDD` + 6-char hex | |
| `DSP-` | Dispute | `DSP-` + `YYYYMMDD` + 6-char hex | `DSP-20250730-ABC123` |
| `AUD-` | Audit log entry | `AUD-` + `YYYYMMDD` + 6-char hex | |
| `ORD-` | Spare parts order | `ORD-` + `YYYYMMDDHHMMSS` | `ORD-20250715093000` |
| `RFQ-` | RFQ broadcast | `RFQ-` + timestamp | |

### 6.3 Claims

| Method / Function | Signature | Returns | Description |
|---|---|---|---|
| `create_claim` | `(claim_ref, policy_number="", id_number="", vehicle_reg="", phone="", incident_date="", incident_time="", incident_location="", incident_type="", description="", third_party=False, tp_vehicle_reg="", tp_driver_name="", tp_phone="", tp_insurer="", police_station="", ob_number="", submitted_by="", estimated_amount=0.0)` | `bool` | Insert or replace a claim row (`INSERT OR REPLACE`). |
| `get_claim` | `(claim_ref)` | `dict \| None` | Fetch a single claim by reference. |
| `get_claims` | `(status_filter="", assigned_to="", limit=500)` | `list[dict]` | List claims, optionally filtered by status and assignee. |
| `update_claim_status` | `(claim_ref, to_status, changed_by="", note="", source="portal")` | `bool` | Update claim status + record in `status_history`. |
| `record_status_change` | `(claim_ref, to_status, from_status="", changed_by="", source="portal", note="")` | `str` (event_id) | Insert a `status_history` row. |
| `get_timeline` | `(claim_ref)` | `list[dict]` | Unified chronological timeline (status changes + assignments + communications). |
| `invalidate_claim_cache` | `(claim_ref)` | `None` | Cache invalidation hook (no-op in SQLite mode). |

### 6.4 Reserves

| Method / Function | Signature | Returns | Description |
|---|---|---|---|
| `set_reserve` | `(claim_ref, reserve_type, amount, purpose, created_by, note="")` | `str \| None` | Create a reserve (`initial` or `supplemental`). Returns `None` if amount ≤ 0. |
| `approve_reserve` | `(reserve_id, approved_by)` | `bool` | Set status to `approved`. |
| `release_reserve` | `(reserve_id, released_by, note="")` | `bool` | Set status to `released`. |
| `get_reserves` | `(claim_ref)` | `pd.DataFrame` | All reserves for a claim. |
| `get_total_reserves` | `(claim_ref)` | `float` | Sum of **approved** reserves. |

**Reserve lifecycle:** `pending` → `approved` (by HoC) or `released` (by officer).

### 6.5 Diary Entries

| Method / Function | Signature | Returns | Description |
|---|---|---|---|
| `add_diary_entry` | `(claim_ref, task, due_date, assigned_to, priority, created_by, note="")` | `str \| None` | Create a follow-up task. |
| `complete_diary_entry` | `(entry_id)` | `bool` | Mark as `done` + set `completed_at`. |
| `get_diary_entries` | `(claim_ref)` | `pd.DataFrame` | All diary entries for a claim. |
| `get_overdue_entries` | `(assigned_to=None)` | `pd.DataFrame` | Open entries past due date, optionally filtered. |

### 6.6 Communications

| Method / Function | Signature | Returns | Description |
|---|---|---|---|
| `log_communication` | `(claim_ref, channel, direction, summary, created_by, contact_name="", contact_phone="", outcome="", consent=True)` | `str \| None` | Log SMS/call/email/WhatsApp/letter. |
| `get_communications` | `(claim_ref)` | `pd.DataFrame` | All communications for a claim. |

**Channels:** `sms`, `call`, `email`, `letter`, `whatsapp`.
**Directions:** `outbound`, `inbound`.
DPA 2019 consent is captured per-log (`consent_obtained` column, default `yes`).

### 6.7 Expert Assignments

| Method / Function | Signature | Returns | Description |
|---|---|---|---|
| `assign_expert` | `(claim_ref, expert_type, expert_name, expert_phone, expert_company, assigned_by, estimated_cost=0, note="")` | `str \| None` | Assign assessor/garage/investigator. |
| `update_assignment_status` | `(assignment_id, status, actual_cost=None)` | `bool` | Update to `accepted`, `completed`, `rejected`. |
| `update_job_status` | `(claim_ref, new_status, actor="")` | `bool` | Alias — update by claim_ref. |
| `get_assignments` | `(claim_ref=None, expert_type=None)` | `pd.DataFrame` | Filter by claim or expert type. |

**Assignment lifecycle:** `pending` → `accepted` → `completed`. Also supports `rejected`.

### 6.8 Documents

| Method / Function | Signature | Returns | Description |
|---|---|---|---|
| `register_document` | `(claim_ref, doc_type, filename, file_size, mime_type, uploaded_by, core_doc_id="", note="")` | `str \| None` | Register metadata (auto-increments `version`). |
| `get_documents` | `(claim_ref)` | `pd.DataFrame` | All documents for a claim. |
| `post_document` | `(claim_ref, filename, mime_type, file_bytes, doc_type="")` | `str \| None` | POST to external API; falls back to local registration. |

**Document types:** `drivers_license`, `police_abstract`, `logbook`, `scene_photo`,
`assessment_report`, `repair_estimate`, `invoice`, `investigation_report`, `quote`,
`demand_letter`.

### 6.9 Settlements

| Method / Function | Signature | Returns | Description |
|---|---|---|---|
| `recommend_settlement` | `(claim_ref, amount, payee_name, payee_type, recommended_by, wht_rate=0.0, note="")` | `str \| None` | Create recommendation with WHT auto-calculation. |
| `approve_settlement` | `(settlement_id, approved_by)` | `bool` | Set status to `approved` (HoC gate). |
| `mark_settlement_paid` | `(settlement_id, bank_ref)` | `bool` | Set status to `paid` + bank reference. |
| `get_settlements` | `(claim_ref)` | `pd.DataFrame` | All settlements for a claim. |

**Settlement lifecycle:** `pending` → `approved` → `paid`.

### 6.10 Service Payments

| Method / Function | Signature | Returns | Description |
|---|---|---|---|
| `authorise_service_payment` | `(claim_ref, provider_name, invoice_number, invoice_amount, decision, authorised_by, note="")` | `str \| None` | Record payment authorisation. |
| `get_service_payments` | `(claim_ref=None)` | `pd.DataFrame` | All service payments, optionally filtered. |
| `update_payment_status` | `(claim_ref, data)` | `bool` | Record invoice/payment tracking data. |

### 6.11 Messages

| Method / Function | Signature | Returns | Description |
|---|---|---|---|
| `send_message` | `(claim_ref, sent_by, recipient_type, recipient_name, subject, body)` | `str \| None` | Insert a `client_messages` row. |
| `get_messages` | `(claim_ref)` | `list[dict]` | All messages for a claim. |

### 6.12 Disputes

| Method / Function | Signature | Returns | Description |
|---|---|---|---|
| `add_dispute` | `(claim_ref, client_name="", stage="Repudiation Appeal", urgency="normal", claim_amount=0.0, advocate="")` | `str` | Create a dispute record. |
| `get_disputes` | `(stage_filter="", urgency_filter="", search="")` | `list[dict]` | Filter disputes by stage, urgency, or search. |

**Dispute stages:** `Repudiation Appeal`, `Pre-Litigation`, `Litigation`, `Consent Order`.

### 6.13 Audit & SLA

| Method / Function | Signature | Returns | Description |
|---|---|---|---|
| `log_audit` | `(action, actor="", detail="")` | `str` | Append to `audit_log`. |
| `get_audit_log` | `(limit=200)` | `pd.DataFrame` | Recent audit entries. |
| `get_sla_status` | `(claim_ref, submitted_at)` | `dict` | SLA timers (acknowledgement + settlement). |

`get_sla_status` return keys: `acknowledged_overdue`, `settlement_overdue`,
`ack_deadline`, `settle_deadline`, `days_to_ack`, `days_to_settle`.

### 6.14 External API Sync

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `is_configured` | `()` | `bool` | True when `CORE_API_BASE_URL` is set. |
| `post_claim` | `(data: dict)` | `bool` | POST claim to external API (no-op if not configured). |

### 6.15 Analytics API

The `views/analytics_charts.py` module provides `render_analytics(show_refresh=False)`
which renders a 2×2 Plotly grid. Data loaders (`_load_claims_by_type`,
`_load_status_distribution`, `_load_settlement_trend`, `_load_avg_cycle_time`,
`_load_reserve_vs_actual`, `_load_sla_compliance`, `_load_claims_aging`,
`_load_expert_performance`, `_load_wht_summary`) auto-detect demo vs live mode based
on the `ANALYTICS_SQL_*` environment variables.

---

## 7. Database Schema

All tables are created by `_init_db()` in `core_api.py` (idempotent). The database
file defaults to `claims_operations.db` (overridable via `CLAIMS_DB_PATH`).

### 7.1 Schema Summary

| Table | Purpose | Primary key |
|-------|---------|-------------|
| `claims` | Core claim records (FNOL data + status) | `claim_ref` |
| `status_history` | Chronological audit trail of status changes | `event_id` |
| `reserves` | Claim reserve amounts (initial + supplemental) | `reserve_id` |
| `diary_entries` | Follow-up tasks with due dates | `entry_id` |
| `communications` | SMS/call/email/WhatsApp log per claim | `comm_id` |
| `expert_assignments` | Assessor/garage/investigator assignments | `assignment_id` |
| `claim_documents` | Document metadata | `doc_id` |
| `settlements` | Settlement recommendations, approvals, payments | `settlement_id` |
| `service_payments` | Service provider payment authorisations | `payment_id` |
| `client_messages` | Messages between clients and service providers | `message_id` |
| `disputes` | Disputed claims, litigation, appeals | `dispute_id` |
| `audit_log` | System-wide audit trail | `log_id` |

### 7.2 Table: `claims`

| Column | Type | Notes |
|--------|------|-------|
| `claim_ref` | TEXT (PK) | e.g. `CLM-20250715-001` |
| `policy_number` | TEXT | |
| `id_number` | TEXT | National ID / Passport |
| `vehicle_reg` | TEXT | |
| `phone` | TEXT | SMS contact |
| `incident_date` | TEXT | ISO date |
| `incident_time` | TEXT | |
| `incident_location` | TEXT | |
| `incident_type` | TEXT | e.g. Motor Bumper, Theft, Fire Damage |
| `description` | TEXT | Free-text incident description |
| `third_party` | INTEGER | 0/1 flag |
| `tp_vehicle_reg` | TEXT | Third-party vehicle registration |
| `tp_driver_name` | TEXT | |
| `tp_phone` | TEXT | |
| `tp_insurer` | TEXT | |
| `police_station` | TEXT | |
| `ob_number` | TEXT | Occurrence Book reference |
| `submitted_by` | TEXT | User who submitted FNOL |
| `submitted_at` | TEXT | ISO timestamp |
| `status` | TEXT | Default `Submitted` |
| `assigned_to` | TEXT | Claims officer assigned |
| `assigned_at` | TEXT | |
| `last_updated` | TEXT | |
| `estimated_amount` | REAL | Default 0 |
| `actual_amount` | REAL | Default 0 |

### 7.3 Table: `status_history`

| Column | Type | Notes |
|--------|------|-------|
| `event_id` | TEXT (PK) | `EVT-` prefix |
| `claim_ref` | TEXT (FK) | → claims.claim_ref |
| `from_status` | TEXT | Previous status (empty on first) |
| `to_status` | TEXT | New status |
| `changed_by` | TEXT | Actor |
| `source` | TEXT | Default `portal` |
| `note` | TEXT | |
| `changed_at` | TEXT | ISO timestamp |

### 7.4 Table: `reserves`

| Column | Type | Notes |
|--------|------|-------|
| `reserve_id` | TEXT (PK) | `RSV-` prefix |
| `claim_ref` | TEXT (FK) | |
| `reserve_type` | TEXT | `initial` or `supplemental` |
| `amount` | REAL | |
| `purpose` | TEXT | `assessment`, `repair`, `legal`, `investigation`, `other` |
| `created_by` | TEXT | |
| `created_at` | TEXT | ISO timestamp |
| `approved_by` | TEXT | |
| `approved_at` | TEXT | |
| `status` | TEXT | Default `pending` |
| `note` | TEXT | |

### 7.5 Table: `diary_entries`

| Column | Type | Notes |
|--------|------|-------|
| `entry_id` | TEXT (PK) | `DRY-` prefix |
| `claim_ref` | TEXT (FK) | |
| `task` | TEXT | |
| `due_date` | TEXT | ISO date |
| `assigned_to` | TEXT | |
| `priority` | TEXT | Default `normal` |
| `status` | TEXT | Default `open` |
| `created_by` | TEXT | |
| `created_at` | TEXT | ISO timestamp |
| `completed_at` | TEXT | |
| `note` | TEXT | |

### 7.6 Table: `communications`

| Column | Type | Notes |
|--------|------|-------|
| `comm_id` | TEXT (PK) | `COM-` prefix |
| `claim_ref` | TEXT (FK) | |
| `channel` | TEXT | `sms`, `call`, `email`, `letter`, `whatsapp` |
| `direction` | TEXT | `outbound` / `inbound` |
| `contact_name` | TEXT | |
| `contact_phone` | TEXT | |
| `summary` | TEXT | |
| `outcome` | TEXT | |
| `consent_obtained` | TEXT | `yes`/`no` (DPA 2019) |
| `created_by` | TEXT | |
| `created_at` | TEXT | ISO timestamp |

### 7.7 Table: `expert_assignments`

| Column | Type | Notes |
|--------|------|-------|
| `assignment_id` | TEXT (PK) | `ASN-` prefix |
| `claim_ref` | TEXT (FK) | |
| `expert_type` | TEXT | `assessor`, `garage`, `investigator`, `loss_adjuster` |
| `expert_name` | TEXT | |
| `expert_phone` | TEXT | |
| `expert_company` | TEXT | |
| `status` | TEXT | Default `pending` |
| `assigned_by` | TEXT | |
| `assigned_at` | TEXT | ISO timestamp |
| `accepted_at` | TEXT | |
| `completed_at` | TEXT | |
| `estimated_cost` | REAL | |
| `actual_cost` | REAL | |
| `note` | TEXT | |

### 7.8 Table: `claim_documents`

| Column | Type | Notes |
|--------|------|-------|
| `doc_id` | TEXT (PK) | `DOC-` prefix |
| `claim_ref` | TEXT (FK) | |
| `doc_type` | TEXT | e.g. `drivers_license`, `assessment_report` |
| `filename` | TEXT | |
| `file_size` | INTEGER | |
| `mime_type` | TEXT | |
| `uploaded_by` | TEXT | |
| `uploaded_at` | TEXT | ISO timestamp |
| `version` | INTEGER | Default 1 (auto-incremented) |
| `core_doc_id` | TEXT | External system reference |
| `note` | TEXT | |

### 7.9 Table: `settlements`

| Column | Type | Notes |
|--------|------|-------|
| `settlement_id` | TEXT (PK) | `STL-` prefix |
| `claim_ref` | TEXT (FK) | |
| `settlement_type` | TEXT | Default `officer_recommend` |
| `amount` | REAL | Gross amount |
| `payee_name` | TEXT | |
| `payee_type` | TEXT | `assessor`, `garage`, `investigator`, `spare_parts`, `third_party`, `insured` |
| `wht_rate` | REAL | e.g. 0.05 (5 %) |
| `wht_amount` | REAL | Computed: `amount × wht_rate` |
| `net_amount` | REAL | Computed: `amount − wht_amount` |
| `status` | TEXT | Default `pending` |
| `recommended_by` | TEXT | |
| `recommended_at` | TEXT | |
| `approved_by` | TEXT | |
| `approved_at` | TEXT | |
| `paid_at` | TEXT | |
| `bank_ref` | TEXT | Payment reference |
| `note` | TEXT | |

### 7.10 Table: `service_payments`

| Column | Type | Notes |
|--------|------|-------|
| `payment_id` | TEXT (PK) | `PAY-` prefix |
| `claim_ref` | TEXT (FK) | |
| `provider_name` | TEXT | |
| `provider_type` | TEXT | `service_provider` |
| `invoice_number` | TEXT | |
| `invoice_amount` | REAL | |
| `decision` | TEXT | |
| `authorised_by` | TEXT | |
| `authorised_at` | TEXT | |
| `status` | TEXT | Default `pending` |
| `note` | TEXT | |
| `created_at` | TEXT | Added by migration |

> **Migration note:** `created_at` is added to `service_payments` at runtime via
> `ALTER TABLE` wrapped in `try/except` for backward compatibility with existing DBs.

### 7.11 Table: `client_messages`

| Column | Type | Notes |
|--------|------|-------|
| `message_id` | TEXT (PK) | `MSG-` prefix |
| `claim_ref` | TEXT (FK) | |
| `sent_by` | TEXT | |
| `recipient_type` | TEXT | |
| `recipient_name` | TEXT | |
| `subject` | TEXT | |
| `body` | TEXT | |
| `sent_at` | TEXT | ISO timestamp |
| `read_at` | TEXT | |

### 7.12 Table: `disputes`

| Column | Type | Notes |
|--------|------|-------|
| `dispute_id` | TEXT (PK) | `DSP-` prefix |
| `claim_ref` | TEXT (FK) | |
| `stage` | TEXT | Default `Repudiation Appeal` |
| `urgency` | TEXT | Default `normal` |
| `claim_amount` | REAL | |
| `client_name` | TEXT | |
| `advocate` | TEXT | |
| `status` | TEXT | Default `open` |
| `created_at` | TEXT | ISO timestamp |
| `updated_at` | TEXT | ISO timestamp |

### 7.13 Table: `audit_log`

| Column | Type | Notes |
|--------|------|-------|
| `log_id` | TEXT (PK) | `AUD-` prefix |
| `action` | TEXT | e.g. `service_payment_authorised` |
| `actor` | TEXT | |
| `detail` | TEXT | |
| `created_at` | TEXT | ISO timestamp |

### 7.14 Indexes

| Index | Table | Column |
|-------|-------|--------|
| `idx_claims_status` | claims | `status` |
| `idx_claims_assigned` | claims | `assigned_to` |
| `idx_diary_claim` | diary_entries | `claim_ref` |
| `idx_comm_claim` | communications | `claim_ref` |
| `idx_assign_claim` | expert_assignments | `claim_ref` |
| `idx_docs_claim` | claim_documents | `claim_ref` |
| `idx_settle_claim` | settlements | `claim_ref` |
| `idx_status_claim` | status_history | `claim_ref` |
| `idx_msg_claim` | client_messages | `claim_ref` |
| `idx_disputes_claim` | disputes | `claim_ref` |

---

## 8. Kenya Features

### 8.1 Withholding Tax (WHT) Rates — Kenya Revenue Authority

Defined in `core_api.py` as the `WHT_RATES` dictionary and mirrored in
`views/claims_officer.py` for the settlement recommendation form.

| Provider type | WHT rate | Applied to |
|---------------|----------|------------|
| Assessor | 5 % | Assessment/investigation reports |
| Garage | 5 % | Repair invoices |
| Investigator | 5 % | Investigation fees |
| Spare Parts | 10 % | Parts procurement |
| Third Party | 0 % | External liability payees |
| Insured | 0 % | Direct client settlements |

**Computation** (in `recommend_settlement`):
```python
wht_amount = round(amount * wht_rate, 2)
net_amount = round(amount - wht_amount, 2)
```

> **Note:** The WHT rate is selected at settlement-recommendation time based on the
> `payee_type`, not dynamically looked up. The `WHT_RATES` dict in `core_api.py`
> exists as the canonical reference; the claims officer form hardcodes the same values.
> Super Admin can adjust the standard (5 %) and spare-parts (10 %) rates via the
> System Config → Business Rules form.

### 8.2 SLA — Service Level Agreements

Two SLA regimes apply:

#### 8.2.1 Insurance Act (Cap 111) Statutory SLAs

| Milestone | Statutory requirement | Portal configuration |
|-----------|----------------------|---------------------|
| Acknowledgment | 14 days from FNOL | `SLA_ACK_DAYS = 14` (`SLA_ACK_DAYS` env var) |
| Full Settlement | 30 days from date of loss | `SLA_SETTLE_DAYS = 30` (`SLA_SETTLE_DAYS` env var) |

`core_api.get_sla_status()` computes:
- `ack_deadline` = submitted_at + 14 days
- `settle_deadline` = submitted_at + 30 days
- `acknowledged_overdue` / `settlement_overdue` — boolean flags
- `days_to_ack` / `days_to_settle` — remaining days (0 if past)

#### 8.2.2 Operational SLAs (Head of Claims dashboard)

| Stage | SLA |
|-------|-----|
| Assessor Assignment | 4 business hours after FNOL |
| Assessment Completion | 48 hours after appointment |
| Garage Estimate Submission | 48 hours after repair authorisation |
| Invoice Payment | 7 business days after invoice receipt |
| Final Settlement | 30 days from date of loss |

These are displayed as reference thresholds in `views/admin_dashboard.py`
(`_sla_thresholds()`).

### 8.3 Reinsurance Threshold

- **KES 2,000,000** (`REINSURANCE_THRESHOLD`).
- When total incurred (approved reserves + approved/paid settlements) exceeds this,
  `is_reinsurance_flag()` returns `True` and the claim is flagged for reinsurance
  recovery.
- Configured via `REINSURANCE_THRESHOLD` environment variable.

### 8.4 Approval Authority Limits

| Role | Limit (KES) | Above this → |
|------|-------------|-------------|
| Claims Officer | 500,000 | Head of Claims sign-off |
| Head of Claims | 2,000,000 | Finance Head co-approval |
| Finance Head | 5,000,000 | Board / Management resolution |

### 8.5 Data Protection Act 2019 (DPA 2019)

- **FNOL form** includes a mandatory consent checkbox:
  *"I confirm the information provided is accurate and I consent to the processing
  of my personal data in accordance with the Data Protection Act 2019."*
- **Communications** log captures DPA consent per entry
  (`consent_obtained` column, default `yes`).
- **Service Provider portals** display a DPA reminder on the investigation report
  form.

### 8.6 Regulatory References in Code

| Regulation | Where implemented |
|-----------|-------------------|
| Insurance Act Cap 111 §75 (14-day ack) | `core_api.SLA_ACK_DAYS`, `get_sla_status()` |
| Insurance Act Cap 111 §76 (30-day settlement) | `core_api.SLA_SETTLE_DAYS`, `get_sla_status()` |
| DPA 2019 consent | FNOL form checkbox, `communications.consent_obtained` |
| KRA WHT rates | `core_api.WHT_RATES`, `views/claims_officer.py` settlement form |
| IRA statutory deadlines | `views/legal.py` — response deadline tracking |

---

## 9. Deployment Guide

### 9.1 Prerequisites

- **Python** 3.11+ (runtime pinned to 3.11.0 in `claims-client-portal/runtime.txt`)
- **pip** for dependency installation

### 9.2 Dependencies

From `requirements.txt`:

```
streamlit>=1.35.0
psycopg2-binary>=2.9.9
pandas>=2.0.0
requests>=2.31.0
plotly>=5.18.0
```

Install:
```bash
pip install -r requirements.txt
```

### 9.3 Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Seed demo data
python scripts/seed_demo_data.py

# 3. Run the app
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

App URL: http://localhost:8501

### 9.4 Deployment Options

#### Heroku

```bash
heroku create claims-portal
git push heroku main
```
Uses `Procfile`:
```
web: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

#### Railway

Uses `railway.toml`:
```toml
[railway]
  name = "claims-portal"
  runtime = "python"

[build]
  command = "pip install -r requirements.txt"
  builder = "python"

[deploy]
  numReplicas = 1
  restartPolicyType = "ON_FAILURE"
  restartPolicyMaxRetries = 10
```
Environment variables (set in Railway dashboard):
- `CORE_API_BASE_URL` — external core system endpoint
- `CORE_API_TOKEN` — bearer token
- `CLAIMS_HISTORY_DB` — `claims_history.db`
- Business rules: `REINSURANCE_THRESHOLD`, `OFFICER_AUTO_APPROVE_LIMIT`,
  `HOC_APPROVE_LIMIT`, `FINANCE_HEAD_LIMIT`, `SLA_ACK_DAYS`, `SLA_SETTLE_DAYS`

#### Databricks Apps

Uses `app.yaml`:
```yaml
command:
  - streamlit
  - run
  - app.py
  - --server.port
  - $DATABRICKS_APP_PORT
  - --server.address
  - "0.0.0.0"

env:
  - name: CORE_API_BASE_URL
    value: ""
  - name: CORE_API_TOKEN
    value: ""
```

Deploy via:
```bash
databricks apps deploy claims-portal --source-code-path . --output JSON
```
Or use `run-grants-and-deploy.py` for an end-to-end deploy with SQL grants.

#### Docker (manual)

```bash
docker build -t definite-assurance-portal .
docker run -p 8501:8501 \
  -e CORE_API_BASE_URL=https://core.example.com/api/v1 \
  -e CORE_API_KEY=your-key \
  definite-assurance-portal
```
*(A Dockerfile would need to be authored — not present in the repo.)*

### 9.5 Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLAIMS_DB_PATH` | No | `claims_operations.db` | SQLite database file path. |
| `CORE_API_BASE_URL` | No | `""` | External core system REST endpoint. |
| `CORE_API_KEY` | No | `""` | Bearer token for external API. |
| `REINSURANCE_THRESHOLD` | No | `2000000` | KES reinsurance trigger. |
| `OFFICER_AUTO_APPROVE_LIMIT` | No | `500000` | Claims Officer limit. |
| `HOC_APPROVE_LIMIT` | No | `2000000` | Head of Claims limit. |
| `FINANCE_HEAD_LIMIT` | No | `5000000` | Finance Head limit. |
| `SLA_ACK_DAYS` | No | `14` | Acknowledgment SLA days. |
| `SLA_SETTLE_DAYS` | No | `30` | Settlement SLA days. |
| `ANALYTICS_SQL_HOST` | No | `""` | Databricks host for analytics. |
| `ANALYTICS_SQL_TOKEN` | No | `""` | Databricks PAT for analytics. |
| `ANALYTICS_SQL_WAREHOUSE_ID` | No | `""` | Databricks warehouse ID. |
| `ANALYTICS_SQL_CONNECTION_STRING` | No | `""` | SQLAlchemy connection string. |
| `ANALYTICS_KPI_VIEW` | No | `claims.claims_kpi_view` | Analytics KPI view name. |
| `PORT` | Yes (platform) | — | Server port (set by platform). |
| `VERSION` | No | `2.1.0` | App version (Super Admin health check). |

### 9.6 Streamlit Configuration

`.streamlit/config.toml`:
```toml
[server]
port = 8501
headless = true

[theme]
primaryColor = "#006400"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
font = "sans serif"
```

> **Note:** The theme in `config.toml` (`primaryColor = "#006400"`) is overridden
> at runtime by the CSS injected in `views/brand.py` (`inject_brand_css()`), which
> sets the full Definite Assurance palette. The config theme is a fallback.

### 9.7 Production Checklist

- [ ] Replace demo authentication with real auth (IMS API / Okta SSO / OTP).
- [ ] Set `CORE_API_BASE_URL` and `CORE_API_KEY` secrets.
- [ ] Configure `ANALYTICS_SQL_HOST` + `ANALYTICS_SQL_TOKEN` for live KPIs.
- [ ] Set `AFRICAS_TALKING_USERNAME` + `AFRICAS_TALKING_API_KEY` for SMS notifications.
- [ ] Set `M_PESA_CONSUMER_KEY` + `M_PESA_CONSUMER_SECRET` + `M_PESA_SHORTCODE` for payments.
- [ ] Rotate all demo passwords.
- [ ] Configure `.env`/secrets management (never commit real credentials).

---

## 10. Testing Guide

The portal uses **pytest** with **pytest-cov** for coverage. Configuration lives in
`pytest.ini`.

### 10.1 Running Tests

```bash
# Run all tests with coverage
pytest --cov=. --cov-report=term-missing -v

# Run a specific test file
pytest tests/test_core_api.py -v

# Run without coverage
pytest -v

# Run with short tracebacks
pytest --tb=short -v
```

### 10.2 Test Files

| File | Scope |
|------|-------|
| `tests/conftest.py` | Pytest fixtures: isolated temp SQLite DB per test, `capi` fixture (fresh `CoreAPI` instance). |
| `tests/test_core_api.py` | 30 tests covering claim CRUD, status history, reserves, diary, communications, expert assignments, documents, settlements, payments, audit, SLA, disputes, cache invalidation, module-level wrapper parity, and schema validation. |
| `tests/test_views_import.py` | Import smoke tests for all 11 view modules + brand exports + core_api symbol exports + app routing checks. |

### 10.3 Test Isolation Strategy

`tests/conftest.py` provides an **autouse fixture** `_isolated_db` that:

1. Redirects `CLAIMS_DB_PATH` to a temp file via `monkeypatch.setenv()`.
2. Monkey-patches `core_api._DB_PATH`, `_CORE_API_BASE_URL`, and `_CORE_API_KEY`
   to test-safe values.
3. Calls `core_api._init_db()` to create a fresh schema.
4. Each test gets a clean database — no cross-test contamination.

The `capi` fixture returns a fresh `CoreAPI()` instance per test.

### 10.4 What's Tested

| Area | Tests | Key assertions |
|------|-------|----------------|
| Configuration | `test_is_configured_default_false`, `test_is_configured_true`, `test_module_level_is_configured` | External API detection |
| Claim CRUD | `test_create_and_get_claim`, `test_get_claim_not_found`, `test_get_claims_empty`, `test_get_claims_after_create`, `test_get_claims_with_status_filter` | Create, read, filter |
| Status history | `test_update_claim_status`, `test_record_status_change_returns_event_id`, `test_get_timeline` | Audit trail, timeline |
| Reserves | `test_set_and_approve_reserve`, `test_reserve_rejects_zero_amount` | Reserve lifecycle, validation |
| Diary | `test_diary_entry_lifecycle` | Full lifecycle (add → complete) |
| Communications | `test_log_communication` | Channel, direction, contact capture |
| Expert assignments | `test_assign_and_update_expert`, `test_update_job_status` | Assignment lifecycle |
| Documents | `test_register_and_get_documents`, `test_document_version_increment` | Version auto-increment |
| Settlements | `test_recommend_and_approve_settlement` | WHT calculation, lifecycle |
| Payments | `test_update_payment_status` | Invoice tracking |
| Audit | `test_log_and_get_audit` | Audit logging |
| SLA | `test_sla_status`, `test_sla_status_invalid_date` | Deadline computation, error handling |
| Disputes | `test_add_and_get_dispute`, `test_get_disputes_empty` | Dispute creation/filtering |
| Cache | `test_invalidate_claim_cache` | No-op in SQLite |
| Wrapper parity | `test_module_level_wrappers_match_class` | Class vs function consistency |
| Schema | `test_all_tables_exist` | All 12 tables present |

### 10.5 CI/CD Pipeline

`.github/workflows/python-app.yml`:

1. **Checkout** code (GitHub Actions, `ubuntu-latest`, Python 3.11).
2. **Install** dependencies: `pip install flake8 pytest pytest-cov`, then
   `pip install -r requirements.txt`.
3. **Lint** with flake8:
   - Hard errors: `--select=E9,F63,F7,F82` (syntax errors, undefined names — **fail build**)
   - Style warnings: `--max-complexity=10 --max-line-length=127 --exit-zero`
4. **Test** with pytest: `pytest --cov=. --cov-report=xml -v`.
5. **Coverage** uploaded to Codecov (`fail_ci_if_error: false`).

### 10.6 Writing New Tests

```python
# Use the capi fixture for an isolated CoreAPI instance
def test_my_feature(capi):
    result = capi.my_new_method("arg1", "arg2")
    assert result is True

# Use module-level functions for direct calls
def test_wrapper():
    from core_api import create_claim
    assert create_claim(claim_ref="CLM-TEST", submitted_by="test") is True
```

---

## 11. Seeding

### 11.1 Seed Script

`scripts/seed_demo_data.py` populates the SQLite database with **35 realistic
Kenyan claims** (15 motor + 20 business).

```bash
python scripts/seed_demo_data.py
```

### 11.2 Seed Coverage

| Category | Claim types | Count |
|----------|------------|-------|
| Motor | Bumper, Windscreen, Theft, Third Party Bodily Harm, Fire Damage, Flood Damage, Third Party Property | 15 |
| Business | Business Fire, Business Burglary, WIBA, Goods in Transit, Business Interruption | 20 |

### 11.3 What Gets Seeded Per Claim

For every claim, the seed script exercises the full data pipeline:

1. **Claim record** — `create_claim()` with vehicle/insured details, incident type, description.
2. **Status history** — `update_claim_status()` transitions the claim to its target status
   (e.g. `Settled`, `Rejected`, `Assessment`, `Investigation`, `Approved`).
3. **Reserve** — `set_reserve()` creates an initial reserve (50 % of claim amount, capped at
   KES 500,000). For settled/approved claims, `approve_reserve()` is called.
4. **Expert assignment** — `assign_expert()` assigns a assessor, garage, or investigator with
   realistic Kenyan vendor names and phone numbers.
5. **Assignment status** — For settled/approved claims, `update_assignment_status()` marks
   the assignment `completed`.
6. **Communication** — `log_communication()` records an SMS acknowledgement (for non-rejected claims).
7. **Diary entry** — For active claims (Assessment, Investigation, FNOL), a high-priority
   follow-up task is created.
8. **Settlement** — For settled/approved claims, `recommend_settlement()` creates a settlement
   recommendation.

### 11.4 Sample Vendors

| Expert type | Vendor | Phone |
|-------------|--------|-------|
| Garage | Kiambu Auto Works Ltd | 0711234567 |
| Assessor | Apollo Surveyors Kenya | 0712345678 |
| Investigator | Eastleigh Detective Agency | 0713456789 |

### 11.5 Sample Insureds

| Policy type | Client |
|-------------|--------|
| Motor - Comprehensive | Kamau Mwangi, ID: 12345678 |
| Motor - Third Party | Wanjiku Njeri, ID: 23456789 |
| Business - Fire | Muthoni Enterprises Ltd, PIN: A000123456B |
| Business - Burglary | Karimi Wholesale, PIN: A000234567C |
| Business - WIBA | Otieno & Sons Construction, PIN: A000345678D |
| Business - Goods in Transit | Transline Logistics Ltd, PIN: A000456789E |

### 11.6 Seeding Notes

- All amounts are in **KES** with realistic Nairobi/Kiambu/Mombasa/Kisumu dates (2024–2025).
- No medical or life claims (per project constraint).
- Rejected claims have `amount = 0` and no reserve/settlement.
- FNOL claims are the earliest stage — no expert assigned yet.
- Seeding is idempotent for individual claim refs but does not check for existing records
  (re-running appends duplicates if using `INSERT OR REPLACE` — claims are replaced, but
  reserves/assignments accumulate).

---

## 12. Troubleshooting

### 12.1 Common Issues

#### Issue: "No module named 'core_api'" on import

**Cause:** The working directory or `sys.path` does not include the project root.

**Fix:**
```bash
cd C:\Users\Administrator\claimsportal-rebuild
streamlit run app.py
```
The `app.py` and each view module prepend the project root to `sys.path` via
`sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))`.

#### Issue: Database not creating / `claims_operations.db` not found

**Cause:** The `claims/` directory doesn't exist or there's a permissions issue.

**Fix:** The database path defaults to `claims_operations.db` in the current working
directory. Ensure the process has write permissions. Override with:
```bash
set CLAIMS_DB_PATH=C:/path/to/writable/dir/claims_operations.db
```

#### Issue: Tests fail with "database is locked"

**Cause:** Concurrent SQLite access or a stale connection.

**Fix:** The `_get_conn()` function uses `check_same_thread=False, timeout=30`.
Ensure no other process has the DB open. For tests, the `_isolated_db` fixture
redirects to a fresh temp file per test. Delete `test_claims_operations.db` if
stuck.

#### Issue: Views show demo data even after configuring Core API

**Cause:** `CORE_API_BASE_URL` is not set or the app wasn't restarted.

**Fix:**
1. Set the environment variable:
   ```bash
   set CORE_API_BASE_URL=https://core.example.com/api/v1
   set CORE_API_KEY=your-bearer-token
   ```
2. **Restart** the Streamlit app (`Ctrl+C` then re-run).
3. Verify in Super Admin → System Config → App Health shows "Connected".

#### Issue: Analytics charts show "Demo data"

**Cause:** Analytics environment variables are not set.

**Fix:** Set at minimum:
```bash
set ANALYTICS_SQL_HOST=https://dbc-xxx.cloud.databricks.net
set ANALYTICS_SQL_TOKEN=your-databricks-token
```
Optionally set `ANALYTICS_SQL_WAREHOUSE_ID` and `ANALYTICS_KPI_VIEW`.

#### Issue: WHT not applied to settlement

**Cause:** `wht_rate` defaults to 0.0 in `recommend_settlement()`. The claims officer
form auto-selects the rate based on `payee_type`, but if called directly via API, it
must be passed explicitly.

**Fix:** Always pass `wht_rate` when calling `recommend_settlement()` programmatically:
```python
core_api.recommend_settlement(
    claim_ref="CLM-XXXX",
    amount=100000,
    payee_name="Kiambu Auto Works",
    payee_type="garage",
    recommended_by="officer@insure.demo",
    wht_rate=0.05,  # 5% for garage
)
```

#### Issue: Claim reference format incorrect

**Cause:** `client_portal.py` generates references as
`CLM-` + `datetime.utcnow().strftime("%Y%m%d%H%M%S%f")[:18]` (18 digits),
producing 17-digit timestamps. The `core_api` `_gen_id()` uses
`CLM-` + `YYYYMMDD` + 6-char hex (shorter). Both formats are accepted by the
database schema (`claim_ref TEXT PRIMARY KEY`).

**Fix:** Either format works. For consistency, prefer the `core_api` format
`CLM-20250715-A1B2C3` for system-generated claims.

#### Issue: Flake8 lint errors in CI

**Cause:** The CI runs `flake8 . --select=E9,F63,F7,F82` which **fails the build**
on syntax errors and undefined names.

**Fix:**
```bash
pip install flake8
flake8 . --select=E9,F63,F7,F82  # hard errors
flake8 . --max-complexity=10 --max-line-length=127  # style warnings
```

#### Issue: Streamlit port already in use

**Fix:**
```bash
streamlit run app.py --server.port 8502 --server.address 0.0.0.0
```

#### Issue: Login page doesn't show brand colors

**Cause:** `inject_brand_css()` must be called after `st.set_page_config()` in
`app.py`. The brand CSS is injected via `st.markdown(_CSS, unsafe_allow_html=True)`.

**Fix:** Ensure `views/brand.py` is imported and `inject_brand_css()` is called
before any other rendering. Check that SVG logo assets exist in `assets/`.

### 12.2 Diagnostic Commands

```bash
# Check Python version
python --version

# Verify dependencies
python -c "import streamlit, pandas, plotly, requests; print('OK')"

# Check database tables
python -c "import sqlite3; c = sqlite3.connect('claims_operations.db'); print([r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")])"

# Run tests with verbose output
pytest -v --tb=long

# Test Core API configuration
python -c "from core_api import core_api; print('Configured:', core_api.is_configured())"

# Verify all views import
python -c "import app; print('Roles:', list(app.ROLES.keys()))"
```

### 12.3 Super Admin Health Check

Navigate to **Super Admin → System Config → App Health** to view:

| Component | Status values |
|-----------|--------------|
| Core API | `Connected` or `Demo mode` |
| Analytics DB | `Not configured` or connected |
| SMS | `Not configured` or connected |
| M-Pesa | `Not configured` or connected |
| Database | `claims_operations.db` filename |
| App Version | `2.1.0` (from `VERSION` file) |

---

*Document generated for Definite Assurance Claims Portal v2.1.0 (phase2-complete, railway-migration).*
