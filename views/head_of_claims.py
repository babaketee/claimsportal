"""Head of Claims Portal — oversight, high-value approvals, performance management."""
from __future__ import annotations
import streamlit as st
import os
from datetime import date, datetime, timedelta
from views.analytics_charts import render_analytics

HOC_AUTHORITY_LIMIT = 2_000_000  # KES — above this the Finance Head must co-approve
REINSURANCE_THRESHOLD = int(os.environ.get("REINSURANCE_THRESHOLD", "2000000"))  # KES

# ─── Helpers ───────────────────────────────────────────────────────────────────

def get_sla_badge(claim_ref: str, submitted_at: str) -> str:
    """
    Returns an HTML SLA countdown badge.
    Acknowledgement SLA: 3 days  |  Settlement SLA: 30 days
    Colour: green (>7 days left), amber (≤7 days), red (past deadline).
    """
    try:
        submitted = datetime.strptime(submitted_at[:10], "%Y-%m-%d")
    except Exception:
        return "⚪ Invalid date"

    today = datetime.now().date()
    ack_deadline  = (submitted + timedelta(days=3)).date()
    settle_deadline = (submitted + timedelta(days=30)).date()

    ack_days   = (ack_deadline  - today).days
    settle_days = (settle_deadline - today).days

    def _colour(days):
        if days < 0:  return "🔴"
        if days <= 7: return "🟡"
        return "🟢"

    ack_sym   = _colour(ack_days)
    sett_sym  = _colour(settle_days)
    return (
        f"<span title='Ack SLA'>{ack_sym} Ack:{ack_days}d</span>&nbsp;"
        f"<span title='Settlement SLA'>{sett_sym} Settle:{settle_days}d</span>"
    )


def is_reinsurance_flag(claim_ref: str, core_api) -> bool:
    """True when total incurred (reserves + settlements) exceeds REINSURANCE_THRESHOLD."""
    try:
        reserves    = core_api.get_total_reserves(claim_ref) or 0
        settlements = sum(
            (s.get("amount") or 0)
            for s in core_api.get_settlements(claim_ref) or []
        )
        return (reserves + settlements) > REINSURANCE_THRESHOLD
    except Exception:
        return False

def render_overdue_alerts(core_api) -> None:
    """Renders a dismissible alert banner for all overdue diary entries."""
    try:
        entries = core_api.get_overdue_entries() or []
    except Exception:
        entries = []
    if not entries:
        return
    st.error(f"⚠️ {len(entries)} overdue task(s) require immediate attention.")
    rows = []
    for e in entries:
        rows.append({
            "Claim":       e.get("claim_ref", ""),
            "Task":        e.get("description", e.get("task", "")),
            "Due":         e.get("due_date", ""),
            "Days Over":   e.get("days_overdue", ""),
            "Owner":       e.get("assigned_to", ""),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


# ─── Page ──────────────────────────────────────────────────────────────────────

def render() -> None:
    st.title("🏛️ Head of Claims Portal")
    tabs = st.tabs(["📊 Dashboard", "✅ Pending Approvals", "📋 All Claims", "🚫 Repudiation", "📈 Performance"])
    with tabs[0]: _dashboard()
    with tabs[1]: _pending_approvals()
    with tabs[2]: _all_claims()
    with tabs[3]: _repudiation()
    with tabs[4]: _performance()

def _dashboard() -> None:
    st.subheader("Claims Overview")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Open Claims",             "142", "+8 today")
    c2.metric("Pending HoC Approval",     "7",   "+2")
    c3.metric("Avg. Settlement Days",    "18",  "-2 vs last month")
    c4.metric("Total Reserves (KES M)", "48.6","")
    c5.metric("Settled This Month",      "89",  "+12 vs last")
    st.divider()
    st.markdown("#### Live Analytics")
    render_analytics(show_refresh=True)
    st.divider()
    st.markdown("**Active Escalations**")
    st.dataframe([
        {"Ref":"CLM-20250712055431","Client":"Peter Ochieng", "Issue":"Reserve exceeds sum insured","Days":3},
        {"Ref":"CLM-20250710033210","Client":"Grace Njoki",   "Issue":"Third-party dispute",        "Days":7},
        {"Ref":"CLM-20250709012345","Client":"David Otieno",  "Issue":"Fraud referral — inv. pending","Days":2},
    ], use_container_width=True)

def _pending_approvals() -> None:
    st.subheader("Settlements Awaiting Head of Claims Approval")
    st.warning(f"Settlements between KES 500,001 and KES {HOC_AUTHORITY_LIMIT:,} require your sign-off before Finance processes payment.")
    pending = [
        {"Ref":"CLM-20250712055431","Type":"Write-Off",       "Net (KES)":"850,000",  "Officer":"S. Karimi","Submitted":"2025-07-16"},
        {"Ref":"CLM-20250709012345","Type":"Cash Settlement", "Net (KES)":"620,000",  "Officer":"T. Mutua", "Submitted":"2025-07-17"},
        {"Ref":"CLM-20250705088812","Type":"Third-Party",     "Net (KES)":"1,200,000","Officer":"J. Njeru", "Submitted":"2025-07-15"},
    ]
    st.dataframe(pending, use_container_width=True)
    st.divider()
    with st.form("hoc_approve"):
        c1, c2 = st.columns(2)
        claim_ref    = c1.text_input("Claim Reference *")
        decision     = c2.selectbox("Decision *", [
            "Approve — Send to Finance",
            "Refer to Finance Head (above KES 2M)",
            "Reject — Return to Claims Officer",
            "Request Further Information",
        ])
        hoc_comments = st.text_area("Comments / Conditions *")
        submitted    = st.form_submit_button("Record Decision", type="primary", use_container_width=True)
    if submitted:
        if not claim_ref or not hoc_comments:
            st.error("Claim reference and comments are required.")
        elif decision == "Approve — Send to Finance":
            st.success(f"Settlement for **{claim_ref}** approved. Finance notified.")
        elif decision == "Refer to Finance Head (above KES 2M)":
            st.info(f"**{claim_ref}** referred to Finance Head for co-approval.")
        else:
            st.warning(f"Decision **{decision}** recorded for **{claim_ref}**. Claims Officer notified.")

def _all_claims() -> None:
    st.subheader("All Claims")
    c1, c2, c3, c4 = st.columns(4)
    c1.selectbox("Status", ["All","Open","Pending Settlement","Settled","Repudiated","Litigation"])
    c2.selectbox("Officer", ["All","S. Karimi","T. Mutua","J. Njeru"])
    c3.date_input("From")
    c4.date_input("To")
    st.dataframe([
        {"Ref":"CLM-20250715123456","Client":"John Mwangi",   "Type":"Motor Accident","Status":"Under Assessment",  "Officer":"S. Karimi","Reserve (KES)":"320,000"},
        {"Ref":"CLM-20250714098765","Client":"Amina Wanjiru", "Type":"Theft",          "Status":"Awaiting Report",   "Officer":"T. Mutua", "Reserve (KES)":"180,000"},
        {"Ref":"CLM-20250712055431","Client":"Peter Ochieng", "Type":"Fire",           "Status":"Pending Settlement","Officer":"S. Karimi","Reserve (KES)":"850,000"},
        {"Ref":"CLM-20250710033210","Client":"Grace Njoki",   "Type":"Windscreen",     "Status":"Awaiting Payment",  "Officer":"J. Njeru", "Reserve (KES)":"22,000"},
        {"Ref":"CLM-20250709012345","Client":"David Otieno",  "Type":"Motor Accident","Status":"Pending HoC Appr.", "Officer":"T. Mutua", "Reserve (KES)":"620,000"},
    ], use_container_width=True)

def _repudiation() -> None:
    st.subheader("Repudiation / Claim Rejection")
    st.error("Repudiation is irreversible. Ensure all investigation findings, policy conditions, and legal sign-off are documented before proceeding.")
    with st.form("repudiation"):
        c1, c2 = st.columns(2)
        claim_ref      = c1.text_input("Claim Reference *")
        policy_section = c2.text_input("Policy Section / Exclusion Clause *")
        grounds        = st.multiselect("Grounds for Repudiation *", [
            "Non-disclosure / Misrepresentation","Fraud / Inflated Claim","Exclusion Clause",
            "Policy Lapse — non-payment of premium","Driving under influence (DUI)",
            "No valid driving licence","Use outside policy purpose",
            "Wear and tear / Mechanical breakdown","Other",
        ])
        st.text_input("Investigation Report Reference (if any)")
        legal_ok      = st.checkbox("Legal team consulted and sign-off obtained")
        repud_notes   = st.text_area("Detailed Grounds *", height=150, help="Forms the basis of the formal decline letter.")
        submitted     = st.form_submit_button("Issue Repudiation", type="primary", use_container_width=True)
    if submitted:
        if not claim_ref or not policy_section or not grounds or not repud_notes:
            st.error("All starred fields and at least one repudiation ground are required.")
        elif not legal_ok:
            st.warning("Please confirm legal team sign-off before issuing repudiation.")
        else:
            # Persist repudiation record via core_api
            try:
                core_api.upsert_claim_status(
                    claim_ref,
                    status="Repudiated",
                    reason=", ".join(grounds),
                    notes=repud_notes,
                    policy_section=policy_section,
                )
                st.success(f"Claim **{claim_ref}** repudiated on: {', '.join(grounds)}. Decline letter queued for dispatch.")
            except Exception as e:
                st.error(f"Failed to persist repudiation: {e}")

def _performance() -> None:
    st.subheader("Claims Officers Performance — 30-Day Rolling")
    st.dataframe([
        {"Officer":"S. Karimi","Open":52,"Settled":31,"Avg Days":16,"Within SLA":"92%","Reserve Accuracy":"94%"},
        {"Officer":"T. Mutua", "Open":45,"Settled":28,"Avg Days":19,"Within SLA":"87%","Reserve Accuracy":"89%"},
        {"Officer":"J. Njeru", "Open":45,"Settled":30,"Avg Days":17,"Within SLA":"93%","Reserve Accuracy":"91%"},
    ], use_container_width=True)
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("SLA Compliance", "91%", "+3% vs last month")
    c2.metric("Avg Days Open",  "17.4","-1.2")
    c3.metric("Claims Settled", "89",  "+12")
    c4.metric("Escalations",    "7",   "+2")
    st.info("Connect to claims.claims_kpi_view for live performance data.")
