"""Finance Portal — Accounts Payable and Financial Control."""
from __future__ import annotations
import datetime
import streamlit as st

import core_api
import pandas as pd

FINANCE_HEAD_LIMIT = 5_000_000  # KES — above this needs Board / Management resolution
ROLE_LABELS = {"finance":"Finance / Accounts Payable","finance_head":"Finance Head"}


def render(role: str) -> None:
    st.title(f"💰 {ROLE_LABELS.get(role, 'Finance Portal')}")
    if role == "finance_head":
        tabs = st.tabs(["📊 Dashboard","✅ High-Value Approvals","📥 Payment Queue","💸 Process Payment","🔄 Payment Status","📑 Reports"])
        with tabs[0]: _financial_dashboard()
        with tabs[1]: _high_value_approvals()
        with tabs[2]: _payment_queue()
        with tabs[3]: _process_payment()
        with tabs[4]: _update_payment_status()
        with tabs[5]: _financial_reports()
    else:
        tabs = st.tabs(["📥 Payment Queue","💸 Process Payment","🔄 Update Status","📊 Reconciliation"])
        with tabs[0]: _payment_queue()
        with tabs[1]: _process_payment()
        with tabs[2]: _update_payment_status()
        with tabs[3]: _reconciliation()


def _payment_queue() -> None:
    st.subheader("Approved Payments Awaiting Processing")
    st.success("All items here have been approved by the Claims Officer and / or Head of Claims.")
    c1, c2 = st.columns(2)
    c1.selectbox("Payment Type", ["All","Client Settlement","Garage / Repairer","Assessor Fee","Investigator Fee","Third-Party"])
    c2.selectbox("Priority", ["All","High","Normal"])
    queue = [
        {"Ref":"CLM-20250712055431","Payee":"Peter Ochieng",        "Type":"Client Settlement","Net (KES)":"850,000","Approved By":"HoC",    "Priority":"High",  "SLA":"2025-07-19"},
        {"Ref":"CLM-20250710033210","Payee":"Westlands Auto Garage", "Type":"Garage / Repairer","Net (KES)":"21,500", "Approved By":"Officer","Priority":"Normal","SLA":"2025-07-20"},
        {"Ref":"CLM-20250714098765","Payee":"J. Kamau & Associates", "Type":"Assessor Fee",     "Net (KES)":"8,000",  "Approved By":"Officer","Priority":"Normal","SLA":"2025-07-21"},
        {"Ref":"CLM-20250709012345","Payee":"David Otieno",          "Type":"Client Settlement","Net (KES)":"620,000","Approved By":"HoC",    "Priority":"High",  "SLA":"2025-07-18"},
    ]
    st.dataframe(queue, use_container_width=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Items in Queue","4"); c2.metric("Total Payable (KES)","1,499,500"); c3.metric("High Priority","2")


def _process_payment(settlement_id: str, claim_ref: str) -> None:
    """Mark a settlement as paid. Finance role only."""
    st.subheader("Process Payment")
    
    # Get settlement details
    settlements = core_api.get_settlements(claim_ref)
    settlement = None
    if not settlements.empty:
        settlement = settlements[settlements['settlement_id'] == settlement_id]
        if settlement.empty:
            settlement = None
        else:
            settlement = settlement.iloc[0]
    
    if settlement is None:
        st.error("Settlement not found.")
        return
    
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Settlement ID", settlement_id)
    with col2: st.metric("Gross Amount", f"KES {settlement['amount']:,.0f}")
    with col3: st.metric("Net Payable", f"KES {settlement['net_amount']:,.0f}")
    
    st.markdown(f"**Payee:** {settlement['payee_name']} ({settlement['payee_type']})")
    if settlement.get('wht_amount', 0) > 0:
        st.markdown(f"**WHT:** {settlement['wht_rate']*100:.0f}% = KES {settlement['wht_amount']:,.0f}")
    st.markdown(f"**Status:** {settlement['status']}")
    
    if settlement['status'] == 'paid':
        st.success(f"✅ Already paid — bank ref: {settlement.get('bank_ref', 'N/A')}")
        return
    
    if settlement['status'] != 'approved':
        st.warning(f"Cannot pay — settlement status is '{settlement['status']}', must be 'approved' first.")
        return
    
    with st.form(key=f"pay_form_{settlement_id}"):
        bank_ref = st.text_input("Bank Transfer Reference", key=f"bank_ref_{settlement_id}", placeholder="e.g. EFT-2025-07-15-001")
        submitted = st.form_submit_button("Confirm Payment")
        if submitted:
            if not bank_ref.strip():
                st.error("Bank reference is required.")
                return
            ok = core_api.mark_settlement_paid(settlement_id, bank_ref.strip())
            if ok:
                st.success(f"✅ Payment confirmed — {settlement_id}")
                # Log communication
                core_api.log_communication(
                    claim_ref=claim_ref,
                    channel="sms",
                    direction="outbound",
                    summary=f"Payment processed: KES {settlement['net_amount']:,.0f} to {settlement['payee_name']}",
                    created_by=st.session_state.get("user", ""),
                    contact_phone=""
                )
            else:
                st.error("Failed to record payment.")


def _payment_dashboard() -> None:
    """Show all settlements pending or approved for payment."""
    st.subheader("Payment Dashboard")
    
    # Show settlements needing payment (approved status)
    conn = core_api._get_conn()
    df = pd.read_sql(
        "SELECT s.*, 'STL-' || substr(s.settlement_id,1,10) as short_id FROM settlements s WHERE s.status IN ('approved', 'pending') ORDER BY s.recommended_at DESC",
        conn
    )
    conn.close()
    
    if df.empty:
        st.info("No settlements awaiting payment.")
        return
    
    st.markdown(f"**{len(df)} settlement(s) awaiting payment**")
    for _, row in df.iterrows():
        with st.expander(f"**{row['claim_ref']}** — {row['payee_name']} — KES {row['amount']:,.0f} — {row['status']}"):
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Gross", f"KES {row['amount']:,.0f}")
            with col2: st.metric("WHT", f"KES {row.get('wht_amount', 0):,.0f}")
            with col3: st.metric("Net", f"KES {row.get('net_amount', 0):,.0f}")
            st.markdown(f"**Payee:** {row['payee_name']} ({row['payee_type']})")
            st.markdown(f"**Recommended by:** {row['recommended_by']} on {row['recommended_at']}")
            if row['status'] == 'approved':
                if st.button(f"Process Payment: {row['settlement_id']}", key=f"pay_{row['settlement_id']}"):
                    st.session_state['process_settlement_id'] = row['settlement_id']
                    st.session_state['process_claim_ref'] = row['claim_ref']
                    st.rerun()
            else:
                st.info("Awaiting HoC approval before payment can be processed.")


def _update_payment_status() -> None:
    st.subheader("Update Payment Status")
    st.caption("Use after bank confirms credit, or when a payment is returned or delayed.")
    with st.form("update_status"):
        c1, c2 = st.columns(2)
        claim_ref  = c1.text_input("Claim Reference *")
        payee_name = c2.text_input("Payee Name *")
        new_status = st.selectbox("New Status *", [
            "Payment Initiated","Payment Confirmed by Bank",
            "EFT Returned — Payee Bank Error","EFT Returned — Wrong Account Number",
            "RTGS Delayed — Bank Holiday","Cancelled — Refer Back to Claims Officer",
        ])
        st.text_input("Bank Reference / SWIFT Ref")
        st.text_area("Notes")
        submitted = st.form_submit_button("Update Status", type="primary", use_container_width=True)
    if submitted:
        if not claim_ref or not payee_name:
            st.error("Claim reference and payee name are required.")
        else:
            st.success(f"Payment status for **{claim_ref}** updated to **{new_status}**.")
    st.divider()
    st.markdown("**Recent Status Updates**")
    st.dataframe([
        {"Ref":"CLM-20250708020011","Payee":"James Kamau",        "Status":"Payment Confirmed by Bank",    "Updated":"2025-07-18 14:30","By":"M. Wangari"},
        {"Ref":"CLM-20250706013345","Payee":"Nairobi Garage Ltd.","Status":"EFT Returned — Wrong Account","Updated":"2025-07-17 11:00","By":"M. Wangari"},
        {"Ref":"CLM-20250704009876","Payee":"Faith Achieng",       "Status":"Payment Confirmed by Bank",    "Updated":"2025-07-16 16:15","By":"P. Njoroge"},
    ], use_container_width=True)


def _reconciliation() -> None:
    st.subheader("Monthly Reconciliation")
    c1, c2 = st.columns([2, 1])
    c1.selectbox("Period", ["July 2025","June 2025","May 2025"])
    c2.button("Export to Excel", use_container_width=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Processed","KES 12.4M"); c2.metric("Client Settlements","KES 8.2M")
    c3.metric("Service Provider Pmts","KES 3.1M"); c4.metric("WHT to KRA","KES 155K")
    st.divider()
    st.dataframe([
        {"Ref":"CLM-20250708020011","Payee":"James Kamau",       "Amount (KES)":"320,000","Type":"Settlement","Status":"Reconciled","Bank Ref":"KCB-20250718-0041"},
        {"Ref":"CLM-20250706013345","Payee":"Nairobi Garage Ltd.","Amount (KES)":"78,500", "Type":"Garage Fee","Status":"Returned",  "Bank Ref":"EQT-20250717-0012"},
        {"Ref":"CLM-20250704009876","Payee":"Faith Achieng",      "Amount (KES)":"45,000", "Type":"Settlement","Status":"Reconciled","Bank Ref":"ABB-20250716-0089"},
    ], use_container_width=True)
    st.warning("1 unreconciled item — EFT return for Nairobi Garage Ltd. Re-process or return to Claims Officer.")


def _financial_dashboard() -> None:
    st.subheader("Financial Dashboard — Claims Costs")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Reserves (KES M)","48.6","+2.1 MoM"); c2.metric("YTD Claims Paid (KES M)","142.3","+18% vs LY")
    c3.metric("Loss Ratio (YTD)","68%","+3%"); c4.metric("Recoveries / Salvage (KES M)","4.2","+0.5")
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Payments by Type — This Month**")
        st.dataframe([
            {"Type":"Client Cash Settlements","KES":"6,400,000"},{"Type":"Write-Off Payments","KES":"1,800,000"},
            {"Type":"Garage / Repair Fees","KES":"3,100,000"},{"Type":"Assessor Fees","KES":"480,000"},
            {"Type":"Investigator Fees","KES":"120,000"},{"Type":"Third-Party Settlements","KES":"500,000"},
        ], use_container_width=True)
    with col2:
        st.markdown("**Reserve vs Actual — by Claim Type**")
        st.dataframe([
            {"Type":"Motor Accident",  "Reserve (M)":"24.1","Paid (M)":"16.8","IBNR (M)":"7.3"},
            {"Type":"Theft",           "Reserve (M)":"9.4", "Paid (M)":"7.1", "IBNR (M)":"2.3"},
            {"Type":"Fire",            "Reserve (M)":"8.2", "Paid (M)":"5.4", "IBNR (M)":"2.8"},
            {"Type":"Natural Disaster","Reserve (M)":"4.1", "Paid (M)":"2.9", "IBNR (M)":"1.2"},
            {"Type":"Windscreen",      "Reserve (M)":"2.8", "Paid (M)":"2.2", "IBNR (M)":"0.6"},
        ], use_container_width=True)
    st.info("IBNR = Incurred But Not Reported. Connect Delta tables for live figures.")


def _high_value_approvals() -> None:
    st.subheader(f"High-Value Settlements — Referred by Head of Claims")
    st.warning(f"Items above KES {FINANCE_HEAD_LIMIT:,} require Board / Management resolution.")
    st.dataframe([
        {"Ref":"CLM-20250705088812","Client":"Mercy Holdings Ltd.","Type":"Commercial Write-Off","Amount (KES)":"3,200,000","HoC":"J. Mwathi","Submitted":"2025-07-15"},
    ], use_container_width=True)
    st.divider()
    with st.form("fh_approve"):
        c1, c2 = st.columns(2)
        claim_ref   = c1.text_input("Claim Reference *")
        decision    = c2.selectbox("Decision *", [
            "Approve — Proceed to Payment","Escalate to Board",
            "Reject — Refer Back to Head of Claims","Request Reinsurance Recovery First",
        ])
        fh_comments = st.text_area("Finance Head Comments *")
        st.file_uploader("Board Resolution / Management Letter (if applicable)", type=["pdf"])
        submitted   = st.form_submit_button("Record Decision", type="primary", use_container_width=True)
    if submitted:
        if not claim_ref or not fh_comments:
            st.error("Claim reference and comments are required.")
        else:
            st.success(f"Decision **{decision}** recorded for **{claim_ref}**. Head of Claims and Finance notified.")


def _financial_reports() -> None:
    st.subheader("Financial Reports")
    c1, c2 = st.columns(2)
    report = c1.selectbox("Report Type", [
        "Monthly Claims Cost Summary","YTD Loss Ratio by Line","Reserve Adequacy Report",
        "Reinsurance Recovery Report","Withholding Tax (WHT) Schedule","Accounts Payable Aging",
    ])
    period = c2.selectbox("Period", ["July 2025","June 2025","Q2 2025 (Apr-Jun)","YTD 2025"])
    if st.button("Generate Report", type="primary", use_container_width=True):
        st.info(f"Generating **{report}** for **{period}** … Connect Delta tables for live output.")

def show() -> None:
    if 'process_settlement_id' in st.session_state:
        _process_payment(st.session_state['process_settlement_id'], st.session_state['process_claim_ref'])
    else:
        _payment_dashboard()
