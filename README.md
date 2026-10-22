# Definite Assurance Claims Portal

A Streamlit-based insurance claims management portal designed for the Kenyan market. The application centralizes the full claims lifecycle—from first notification of loss (FNOL) through assignment, review, settlement, payments, and dispute handling—into a single role-based workflow.

## Overview

The Claims Portal helps insurers and service providers manage claims more efficiently across multiple teams:

- Policyholders submit new claims and track progress
- Claims officers triage and assign work
- Assessors, garages, and investigators submit updates
- Finance teams approve and reconcile payments
- Legal and admin teams monitor disputes and SLA compliance
- Super admins configure rules, permissions, and system settings

The system is designed to feel like a real operational insurance workflow while remaining easy to run locally or deploy to cloud platforms such as Railway, Heroku, or Databricks.

## Key features

- Role-based access for client, claims officer, finance, legal, admin, and super admin users
- SQLite-first data layer with optional external API sync
- Claims workflow with status history, diary tracking, and audit logs
- Reserve management and settlement recommendations
- Service payments and vendor tracking
- Document registration for claims evidence
- SLA awareness and Kenya-specific regulatory rules
- Built-in demo accounts for testing and walkthroughs
- Plotly-based analytics dashboard and KPI views

## Tech stack

- Python 3.11+
- Streamlit
- SQLite
- Pandas
- Plotly
- Requests

## Repository structure

```text
.
├── app.py                     # Main Streamlit entry point and role router
├── core_api.py               # Core business logic and data access layer
├── DESIGN.md                 # Product and visual design documentation
├── DOCUMENTATION.md          # Detailed technical and workflow docs
├── requirements.txt          # Python dependencies
├── Procfile                  # Heroku process definition
├── railway.toml              # Railway configuration
├── app.yaml                 # Databricks app configuration
├── start.sh                 # Startup helper script
├── VERSION                  # Package version
├── .streamlit               # Streamlit config
├── assets/                  # Static assets
├── scripts/                 # Data seeding and deployment scripts
├── tests/                   # Automated tests
├── views/                   # UI modules by role
└── claims-client-portal/    # Additional app/client assets
```

## Demo accounts

The app includes demo login credentials for testing the workflow:

| Email | Password | Role |
| --- | --- | --- |
| client@insure.demo | Assured#99 | Policyholder |
| officer@insure.demo | Handler#99 | Claims Officer |
| hoc@insure.demo | Oversee#99 | Head of Claims |
| assessor@insure.demo | Survey#99 | Assessor |
| garage@insure.demo | Wrench#99 | Garage |
| investigator@insure.demo | Sleuth#99 | Investigator |
| finance@insure.demo | Invoice#99 | Finance |
| cfo@insure.demo | Reserves#99 | Finance Head |
| spares@insure.demo | Catalog#99 | Spare Parts Provider |
| legal@insure.demo | Counsel#99 | Legal Officer |
| admin@insure.demo | SysCtrl#99 | Admin |
| super@insure.demo | Super#99 | Super Admin |

> Note: the authentication flow is demo-based by default and is intended to be replaced with a real identity provider in production.

## Local setup

1. Clone the repository.
2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. Optionally seed demo data:

```bash
python scripts/seed_demo_data.py
```

4. Run the app:

```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

Then open `http://localhost:8501` in your browser.

## Environment variables

This project supports several environment variables for configuration, including:

- `CORE_API_BASE_URL` — external core API endpoint
- `CORE_API_KEY` — bearer token for external integration
- `CLAIMS_DB_PATH` — path to the SQLite database file
- `REINSURANCE_THRESHOLD` — threshold for reinsurance events
- `OFFICER_AUTO_APPROVE_LIMIT` — claims officer approval ceiling
- `HOC_APPROVE_LIMIT` — head-of-claims approval ceiling
- `FINANCE_HEAD_LIMIT` — finance head approval ceiling
- `SLA_ACK_DAYS` — acknowledgment SLA window
- `SLA_SETTLE_DAYS` — settlement SLA window

## Documentation

Detailed system design and workflow guidance are available in:

- `DOCUMENTATION.md` — product architecture, roles, APIs, deployment guide, and regulatory notes
- `DESIGN.md` — branding and UI design specification

## License

This repository does not currently declare a license in the root directory. If you are planning to publish or distribute this project, you should add an explicit open-source license that matches your intended use.

## Contributing

This project is structured for internal operational demos and insurance workflow modeling. If you are extending it:

- keep the role-based workflow consistent
- preserve auditability for status changes and payments
- validate changes with the existing tests
- document business rules before altering approval logic

## Project intent

This project is focused on operational insurance claims management for a Kenyan insurer context, with emphasis on workflow clarity, compliance awareness, and role-based processing rather than generic CRM functionality.
