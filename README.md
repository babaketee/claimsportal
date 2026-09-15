# Definite Assurance — Claims Portal (v4.0)

A ground-up revamp of the claims portal: **Next.js 14 (App Router) + TypeScript +
Tailwind**, a normalized **SQLite** data layer, 220 generated demo claims across
their full lifecycle, **DocuSeal** e-signature on 7 real claim forms plus 3
back-office workflows, a rules-based **AI fraud screening engine**, **OCR** and
**EXIF photo-metadata** extraction on uploaded evidence, and a lightweight
**configuration engine** with maker-checker approval — all modelled on the
Stackwire "Proposed Claims Portal Workflow Design" document supplied for this
build.

The original app (`babaketee/claimsportal`) was a Python/Streamlit application.
This revamp keeps the same domain model, roles, demo accounts and brand identity,
but rebuilds the frontend as a proper multi-user web app so DocuSeal's React SDK
(`@docuseal/react`) can be used natively — Streamlit has no React runtime.

## What's new in v4.0

This build closes the gap between the original v3 revamp and the workflow
design document, on top of everything already in v3:

1. **10-stage claim lifecycle & 14-state status model**, taken directly from
   the design document (`lib/types.ts` → `ClaimStatus`, `LIFECYCLE_STAGES`).
   Every claim shows its current stage and an **immutable status-history audit
   trail** on a new **Lifecycle** tab.
2. **7 real Definite Assurance claim forms, DocuSeal-fillable.** The Motor
   Accident, Windscreen, All Risks, Personal Baggage/Property Loss, WIBA,
   Personal Accident and Notification-of-Incident (investigator) forms you
   supplied were transcribed field-for-field into `lib/claim-forms.ts` and are
   used during claim submission — the client signs the actual form for their
   claim type (not a generic consent form), via the DocuSeal `claim_form`
   workflow. Each form also carries its own mandatory/conditional document
   checklist (from Appendix C of the design doc).
3. **AI-assisted fraud screening & triage** (`lib/fraud.ts`) — a deterministic,
   explainable rules engine, not a black box: it scores every claim 0–100 on
   named, weighted indicators (claim frequency, amount outliers, late
   notification, duplicate vehicle claims, missing mandatory documents, photo
   metadata mismatches, investigator-raised suspicion) and routes it into a
   Low/Medium/High risk band. **It only scores and routes — it never approves
   or declines a claim.** High-risk claims are held with a diary task for the
   Head of Claims; every band gets a human review action on the claim's new
   **Fraud & Risk** tab, and a live queue sits on the Head of Claims dashboard.
4. **OCR on uploaded documents** (`lib/ocr.ts`) — images are OCR'd with
   `tesseract.js` (English-language data bundled locally, no network call at
   runtime); digital PDFs have their embedded text extracted via `pdf-parse`.
5. **Photo/accident metadata retrieval** (`lib/exif.ts`) — capture date and
   GPS coordinates are pulled from uploaded photo EXIF data and compared
   against the claimed loss date, exactly per the design document's callout
   that "photograph capture date and location metadata... are among the
   strongest available indicators of a staged or recycled loss."
6. **Investigator "Notification of Incident" report** — the 7th claim form,
   filed by the investigator (not the client) from the claim's Fraud & Risk
   tab, including its Fraud-Risk & Report Log — which feeds directly into the
   fraud engine as a high-weight indicator.
7. **Lightweight configuration engine** (`lib/config.ts`, `/app/admin/config`)
   — fraud thresholds, claim-frequency window, TAT/SLA targets and approval
   authority limits are versioned, effective-dated settings changed only
   through a **maker-checker** flow (one admin proposes, a *different* admin
   approves) with a full version history, per design-doc section 10.
8. **Real file storage** for uploaded documents (`data/uploads/<claim_ref>/`),
   replacing the metadata-only placeholder from v3.
9. **Discharge voucher as a hard precondition to payment** (recommendation R5):
   Finance's "mark paid" action is blocked server-side until a completed
   `settlement_discharge` DocuSeal submission exists for the claim.
10. **Reserve movements pushed at triage**, not only at final payout
    (recommendation R3) — an initial reserve is set automatically the moment a
    claim clears Stage 5 fraud screening.

## Stack

- **Next.js 14** (App Router, Server Components, Server Actions) + TypeScript
- **Tailwind CSS**, themed to the Definite Assurance brand (Aberdare Green
  `#0f4f48`, Uhuru Red `#eb2229`)
- **better-sqlite3** — a single-file `data/claims.db`, zero external services
  required to run the demo
- **iron-session** — encrypted, httpOnly cookie sessions (swap for real
  SSO/OTP/core-IMS auth before production — see `lib/accounts.ts`)
- **@docuseal/react** — `DocusealForm` embedded signing, backed by a small
  server-side client (`lib/docuseal.ts`) that talks to a **self-hosted DocuSeal**
  instance's REST API
- **tesseract.js** + **pdf-parse** — OCR / text extraction on uploaded documents
- **exifr** — photo capture-date/GPS metadata extraction
- **Recharts** — analytics charts for Head of Claims / Super Admin

## Getting started

```bash
npm install
npm run seed     # wipes data/claims.db and data/uploads, generates 220 demo claims
npm run dev      # http://localhost:3000
```

Log in with any account from the table on the login page (also in
`lib/accounts.ts`), e.g. `officer@insure.demo` / `Handler#99`, or
`hoc@insure.demo` / `Oversee#99` to see the fraud review queue.

## Project layout

```
app/
  actions/                Server Actions (auth, claim workflow, documents,
                           fraud review, config engine, DocuSeal)
  app/                     Protected area (layout does the auth check)
    page.tsx               Role → dashboard dispatcher
    admin/config/          Configuration engine (maker-checker)
    claims/[ref]/          Shared claim detail page — tabs: Overview,
                            Lifecycle, Reserves, Assignments, Diary &
                            Correspondence, Documents, Fraud & Risk,
                            Settlements, (Spare Parts RFQ), E-Signatures
  login/                   Public login page
components/
  dashboards/              One component per role (or role group)
  claim/panels.tsx         Most claim-detail tab contents
  claim/FraudPanel.tsx     Fraud score, indicators, human review form
  claim/InvestigatorReportPanel.tsx   Notification-of-Incident filing
  charts/                  Recharts wrappers, brand-colored
  ui/                      Card, Table, Tabs, Badge, StatCard — the small kit
  DocusealPanel.tsx        The e-signature widget, parameterized per workflow
                           and (for claim_form) per claim-type form
lib/
  db.ts                    SQLite connection + schema
  repo.ts                  All data access (mirrors the original core_api.py)
  types.ts                 Shared domain types, status model, lifecycle stages
  claim-forms.ts           The 7 real claim forms as structured field/section
                           definitions + Appendix C document checklists
  docuseal.ts              DocuSeal REST client (server-only)
  fraud.ts                 AI-assisted fraud screening & triage engine
  ocr.ts                   OCR (tesseract.js for images, pdf-parse for PDFs)
  exif.ts                  Photo capture-date/GPS metadata extraction
  storage.ts               Local disk storage for uploaded documents
  config.ts                Configuration engine defaults & accessors
  accounts.ts              Demo accounts (swap for real auth)
  session.ts               iron-session config
scripts/
  seed.ts                  Demo data generator (220 claims + full lifecycle,
                           including fraud assessments and investigator reports)
  smoke-test.mjs           Playwright smoke test covering the new features
  smoke-upload.mjs         Playwright test for the upload → OCR → EXIF pipeline
  screenshots.mjs          Playwright screenshot capture for visual QA
```

## Roles & demo accounts

Same 12 roles as the original app: Policyholder/Client, Claims Officer, Head of
Claims, Assessor, Garage/Repairer, Investigator, Finance, Finance Head, Spare
Parts Provider, Legal, Admin, Super Admin. Full list of demo logins is in
`lib/accounts.ts` and shown on the login page.

## The 10-stage lifecycle & status model

| Stage | Name | Status(es) |
|---|---|---|
| 1–3 | Login/Policy Pull, Policy Selection, Claim Details/Evidence | Draft |
| 4 | Submission | Submitted |
| 5 | Fraud Screening and Triage | Under triage |
| 6 | Parallel Investigation + Assessment | Under investigation and assessment, On hold - awaiting information |
| 7 | Core System Review / Human Approval | Pending approval |
| 8 | Repair / Parts / Reinspection | Approved, Under repair, Awaiting reinspection |
| 9 | Finance Disbursement | Pending payment |
| 10 | Closure | Paid, Closed, Repudiated, Withdrawn, Reopened |

A new claim is auto-triaged the moment it's submitted: `lib/fraud.ts`'s
`triageNewClaim()` runs the fraud engine, sets an initial reserve, and routes
the claim into Stage 6 — or, if it scores High risk, holds it on
"On hold - awaiting information" with an urgent diary task for the Head of
Claims, exactly per the design document's Stage 5 spec.

## AI-assisted fraud screening

`lib/fraud.ts` computes a 0–100 score from named, weighted, fully-explained
indicators — every point is traceable to a reason, shown on the claim's
**Fraud & Risk** tab:

- Elevated claim frequency (same client/policy, configurable window)
- Duplicate vehicle claimed twice in a short window
- Claim amount is a significant outlier for its claim type
- Suspiciously round claim amount
- Late notification of loss (claimed date vs. reported date)
- Photo capture date doesn't match the claimed loss date (EXIF)
- All uploaded photos missing capture metadata
- Fewer documents uploaded than the mandatory checklist requires
- Investigator reported suspected fraud indicators (Notification of Incident)

The resulting risk band (Low/Medium/High) only ever **recommends** a routing —
proceed, escalate to investigator, or hold for review. A human always makes
the final call, recorded on the same tab. Thresholds and the frequency window
are configurable, without a code change, from `/app/admin/config`.

## OCR & photo metadata

Upload a document from any claim's **Documents** tab and the app will:

- OCR it (images via `tesseract.js`, with English-language data bundled
  locally so there's no network dependency at runtime; digital PDFs via
  `pdf-parse` — scanned/image-only PDFs aren't OCR'd in this demo, and the UI
  says so rather than pretending);
- for photos, extract EXIF capture date and GPS coordinates, flag missing
  metadata, and flag a capture date more than 2 days from the claimed loss
  date;
- re-run the fraud engine, so new evidence can change a claim's risk band.

## The 7 claim forms, via DocuSeal

`lib/claim-forms.ts` holds structured field/section definitions transcribed
from the 7 uploaded Definite Assurance forms, each mapped to the claim types
it covers:

| Form | Claim types |
|---|---|
| Motor Accident Claim Form | Motor Bumper, Own Damage, Theft, Third Party Property, Fire, Flood |
| Windscreen / Glass Claim Form | Windscreen |
| All Risks Claim Form | Business Fire, Business Burglary |
| Personal Baggage / Property Loss Claim Form | Goods in Transit |
| Workmen's Compensation (WIBA) Claim Form | WIBA |
| Personal Accident Claim Form | Third Party Bodily Harm |
| Notification of Incident Form (Investigators) | filed by investigators, any claim |
| General Claim Declaration & Consent | any class without a dedicated form |

On the claim detail page's **E-Signatures** tab, the claimant signs the real
form for their claim type — its section/field list is shown for review, and
its declaration + DPA 2019 consent + signature block is the DocuSeal document
(or the demo-mode fallback when no real template is configured).

Three more DocuSeal workflows cover the back office, unchanged from v3:
Settlement Discharge Voucher, Demand Letter / Repudiation Notice, and Service
Provider Engagement Letter.

### Configuring a real self-hosted DocuSeal instance

1. Deploy DocuSeal (see docuseal.com/on-premises) or point at your existing
   instance.
2. Settings → API → generate an API key.
3. Create one template per workflow (upload a PDF/DOCX and drop signature
   fields on it, or build it with the DocuSeal builder) — 7 claim-form
   templates plus the 3 back-office ones — and note each template's numeric ID.
4. Copy `.env.example` to `.env.local`, set `DOCUSEAL_HOST` /
   `DOCUSEAL_API_KEY`, and fill in the template ID env vars you need.
5. Restart the app. Each workflow/form lights up independently — you can
   configure just one template to start. The Super Admin dashboard shows
   configured-vs-demo-mode status for every workflow and form.

**Without configuration**, every signing workflow still works end-to-end in
"demo mode": requesting a signature creates a tracked record and the reviewer
can mark it signed manually, so the whole claims lifecycle (including
payment, which requires a signed discharge voucher) can still be demoed
without a live DocuSeal server.

## Configuration engine

`/app/admin/config` (Admin / Super Admin only) lists the active value of each
configurable setting, its version history, and a form to propose a new value.
A proposal sits as `pending_approval` until a **different** admin account
approves it — the maker-checker rule is enforced server-side
(`repo.approveConfig`), not just hidden in the UI.

## Demo data

`npm run seed` generates:

- **220 claims** (≈68% Motor, 32% Business) spread across 2024–2026, with
  realistic Kenyan names, locations, vehicle plates and claim types, weighted
  across the full 14-state status pipeline
- Reserves, diary entries, communications, expert assignments, settlements
  (with WHT calculated per payee type), and documents (with simulated OCR
  text / EXIF metadata for demo realism) for every claim, proportional to how
  far along it is
- A **fraud assessment for every claim past Submitted**, computed by the real
  production engine — claims well past triage are pre-marked reviewed, so the
  Head of Claims queue reflects an actively-worked backlog rather than 200+
  untouched items
- Investigator "Notification of Incident" reports for ~55% of
  investigator-assigned claims, ~16% of those flagging suspected fraud
- ~25 spare-parts RFQs with multiple competing bids (some awarded)
- A slice of pre-completed DocuSeal signature records (claim forms, demand
  letters, discharge vouchers, engagement letters) so every role's dashboard
  has signing history to show, while newer/active claims are left open for
  you to try the live signing flow yourself

Re-run `npm run seed` any time to reset to a fresh dataset (it wipes
`data/claims.db` and `data/uploads` first).

## QA scripts

With the app built and running on port 3100 (`npm run build && npm run start -- -p 3100`):

```bash
node scripts/smoke-test.mjs     # 13 checks across fraud, lifecycle, config, submission
node scripts/smoke-upload.mjs   # exercises the real upload → OCR → EXIF pipeline
node scripts/screenshots.mjs    # saves screenshots of key screens to /tmp
```

These use the Chromium binary at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`
in this environment — update the `executablePath` if running elsewhere, or
delete it to use Playwright's own managed browser.

## Notes / next steps before production

- Swap `lib/accounts.ts` demo credentials for real authentication (SSO/OIDC,
  OTP, or your core insurance system's auth API) — `app/actions/auth.ts` is
  the one place that checks credentials.
- `better-sqlite3` is great for a demo/single-instance deploy; for multi-instance
  production, point `lib/db.ts` at Postgres/MySQL instead (the `repo.ts`
  functions are the seam to swap).
- Uploaded documents are stored on local disk (`data/uploads/`) — swap
  `lib/storage.ts` for S3/GCS/Azure Blob before deploying to more than one
  instance.
- The fraud engine is a deterministic rules engine by design (explainable,
  auditable, no ML infra required). If/when a real ML fraud-scoring service
  is available, `lib/fraud.ts` is the seam to call it instead of (or
  alongside) the rules — keep the "scores and routes, never decides"
  contract.
- OCR on scanned/image-only PDFs isn't implemented (only digital PDFs and
  images are handled) — add a PDF-to-image rasterisation step before OCR if
  that's needed.
- This build covers all claim classes for demo richness; the design document
  scopes the actual phased rollout to motor claims first (Phase 1), with
  other classes following in Phase 2 largely by configuration.
- Run `npm audit` before deploying; a couple of advisories exist upstream in
  Next.js 14.2.x that may need attention depending on your deployment target.
