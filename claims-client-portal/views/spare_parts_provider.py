"""Spare Parts Provider Portal — Bid on RFQs broadcast from garages."""
from __future__ import annotations

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

# ---------------------------------------------------------------------------
# Sample data  (replace with Delta / core_api queries in production)
# ---------------------------------------------------------------------------

BROADCASTS = [
    {
        "RFQ Ref":          "RFQ-20250715001",
        "Claim Ref":        "CLM-20250715123456",
        "Garage":           "AutoFix Garage — Nairobi",
        "Part Description": "Toyota Corolla Front Bumper (2020)",
        "Part Number":      "52119-02900",
        "Qty":              1,
        "Condition Reqd":   "New",
        "Required By":      "2025-07-20",
        "Broadcast Date":   "2025-07-15",
        "Status":           "Open",
    },
    {
        "RFQ Ref":          "RFQ-20250715002",
        "Claim Ref":        "CLM-20250715123456",
        "Garage":           "AutoFix Garage — Nairobi",
        "Part Description": "Toyota Corolla Bonnet (2020)",
        "Part Number":      "53301-02500",
        "Qty":              1,
        "Condition Reqd":   "New",
        "Required By":      "2025-07-20",
        "Broadcast Date":   "2025-07-15",
        "Status":           "Open",
    },
    {
        "RFQ Ref":          "RFQ-20250714001",
        "Claim Ref":        "CLM-20250714098765",
        "Garage":           "SpeedMaster Repairs — Mombasa",
        "Part Description": "Toyota Hilux Side Mirror (LHS)",
        "Part Number":      "87940-0K370",
        "Qty":              1,
        "Condition Reqd":   "New or OEM",
        "Required By":      "2025-07-19",
        "Broadcast Date":   "2025-07-14",
        "Status":           "Open",
    },
    {
        "RFQ Ref":          "RFQ-20250710001",
        "Claim Ref":        "CLM-20250710054321",
        "Garage":           "Elite Panel Beaters — Kisumu",
        "Part Description": "Nissan X-Trail Windscreen",
        "Part Number":      "72700-4BA0A",
        "Qty":              1,
        "Condition Reqd":   "New",
        "Required By":      "2025-07-15",
        "Broadcast Date":   "2025-07-10",
        "Status":           "✅ Closed — Awarded",
    },
]

MY_BIDS = [
    {
        "Bid Ref":          "BID-20250715001",
        "RFQ Ref":          "RFQ-20250715001",
        "Part":             "Toyota Corolla Front Bumper (2020)",
        "Unit Price (KES)": "12,500.00",
        "Lead Time (days)": 3,
        "Warranty":         "6 months",
        "Submitted":        "2025-07-15",
        "Status":           "🟡 Pending Review",
        "Result Notes":     "",
    },
    {
        "Bid Ref":          "BID-20250710001",
        "RFQ Ref":          "RFQ-20250710001",
        "Part":             "Nissan X-Trail Windscreen",
        "Unit Price (KES)": "38,000.00",
        "Lead Time (days)": 2,
        "Warranty":         "12 months",
        "Submitted":        "2025-07-10",
        "Status":           "🏆 Won",
        "Result Notes":     "Best price & delivery rating",
    },
    {
        "Bid Ref":          "BID-20250708001",
        "RFQ Ref":          "RFQ-20250708001",
        "Part":             "Subaru Forester Headlamp Assembly",
        "Unit Price (KES)": "28,500.00",
        "Lead Time (days)": 4,
        "Warranty":         "6 months",
        "Submitted":        "2025-07-08",
        "Status":           "❌ Lost",
        "Result Notes":     "Outbid on price",
    },
]

ACTIVE_ORDERS = [
    {
        "Order Ref":         "ORD-20250710001",
        "RFQ Ref":           "RFQ-20250710001",
        "Part":              "Nissan X-Trail Windscreen",
        "Qty":               1,
        "Garage":            "Elite Panel Beaters — Kisumu",
        "Delivery Address":  "Oginga Odinga St, Kisumu",
        "Payer":             "Insurance Company",
        "Order Value (KES)": "38,000.00",
        "Delivery Status":   "🚚 In Transit",
        "Expected Delivery": "2025-07-17",
    },
]

PAYMENT_SAMPLE = [
    {
        "Order Ref":    "ORD-20250710001",
        "Invoice No":   "INV-SP-001",
        "Invoice Date": "2025-07-17",
        "Amount (KES)": "38,000.00",
        "Payer":        "Insurance Company",
        "Status":       "🔵 Under Review",
        "Payment Date": "—",
        "Payment Ref":  "—",
        "Notes":        "Finance team processing",
    },
    {
        "Order Ref":    "ORD-20250630001",
        "Invoice No":   "INV-SP-002",
        "Invoice Date": "2025-07-03",
        "Amount (KES)": "28,500.00",
        "Payer":        "Garage",
        "Status":       "✅ Paid",
        "Payment Date": "2025-07-06",
        "Payment Ref":  "PAY-SP-20250706001",
        "Notes":        "Paid by SpeedMaster Repairs",
    },
]

NOTIFICATIONS = [
    {
        "Date":    "2025-07-15 09:12",
        "Type":    "📢 New Broadcast",
        "Message": "New RFQ: Toyota Corolla Front Bumper (2020) — RFQ-20250715001. Bid closes 2025-07-20.",
        "Read":    False,
    },
    {
        "Date":    "2025-07-15 09:12",
        "Type":    "📢 New Broadcast",
        "Message": "New RFQ: Toyota Corolla Bonnet (2020) — RFQ-20250715002. Bid closes 2025-07-20.",
        "Read":    False,
    },
    {
        "Date":    "2025-07-14 11:00",
        "Type":    "📢 New Broadcast",
        "Message": "New RFQ: Toyota Hilux Side Mirror (LHS) — RFQ-20250714001. Bid closes 2025-07-19.",
        "Read":    False,
    },
    {
        "Date":    "2025-07-11 14:30",
        "Type":    "🏆 Bid Won",
        "Message": "Your bid BID-20250710001 for Nissan X-Trail Windscreen (RFQ-20250710001) has been awarded. Order ORD-20250710001 created. Proceed to deliver and submit invoice.",
        "Read":    True,
    },
    {
        "Date":    "2025-07-09 10:05",
        "Type":    "❌ Bid Lost",
        "Message": "Your bid BID-20250708001 for Subaru Forester Headlamp Assembly was not selected. Thank you for participating.",
        "Read":    True,
    },
]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render() -> None:
    st.title("🔩 Spare Parts Provider Portal")

    unread = sum(1 for n in NOTIFICATIONS if not n["Read"])
    if unread:
        st.warning(f"🔔 You have **{unread}** unread notification(s). Check the **Notifications** tab.")

    tabs = st.tabs([
        "📢 Open Broadcasts",
        "📝 Submit Bid",
        "📊 My Bids",
        "📦 Active Orders",
        "🧾 Submit Invoice",
        "💳 Payment Status",
        "🔔 Notifications",
    ])
    with tabs[0]: _open_broadcasts()
    with tabs[1]: _submit_bid()
    with tabs[2]: _my_bids()
    with tabs[3]: _active_orders()
    with tabs[4]: _submit_invoice()
    with tabs[5]: _payment_status()
    with tabs[6]: _notifications()


# ---------------------------------------------------------------------------
# Tab 1: Open Broadcasts
# ---------------------------------------------------------------------------

def _open_broadcasts() -> None:
    st.subheader("Open RFQ Broadcasts")
    st.info(
        "These requests have been broadcast to **all registered spare parts providers**. "
        "Submit your most competitive bid via the **Submit Bid** tab before the Required By date. "
        "Bids are evaluated on price and provider rating."
    )

    # TODO: Query Delta table for open RFQs
    #   spark.sql("""
    #     SELECT rfq_ref, claim_ref, garage_name, part_description, part_number,
    #            quantity, condition_required, required_by, broadcast_date, status
    #     FROM claims.rfq_broadcasts
    #     WHERE status = 'Open'
    #     ORDER BY required_by ASC
    #   """)

    open_rfqs   = [r for r in BROADCASTS if r["Status"] == "Open"]
    closed_rfqs = [r for r in BROADCASTS if r["Status"] != "Open"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Open RFQs",   len(open_rfqs))
    c2.metric("Closed RFQs", len(closed_rfqs))
    c3.metric("Total",       len(BROADCASTS))

    st.markdown(f"**{len(open_rfqs)} open RFQ(s) available for bidding**")
    st.dataframe(open_rfqs, use_container_width=True)

    if closed_rfqs:
        with st.expander(f"Closed / Awarded RFQs ({len(closed_rfqs)})"):
            st.dataframe(closed_rfqs, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab 2: Submit Bid
# ---------------------------------------------------------------------------

def _submit_bid() -> None:
    st.subheader("Submit a Bid")
    st.info(
        "Bids are evaluated on **unit price** and **provider rating** (delivery track record, quality). "
        "The winning provider is notified automatically once the evaluation is complete."
    )

    open_rfq_refs = [r["RFQ Ref"] for r in BROADCASTS if r["Status"] == "Open"]

    with st.form("submit_bid"):
        c1, c2 = st.columns(2)
        rfq_ref      = c1.selectbox(
            "Select RFQ Reference *",
            options=open_rfq_refs if open_rfq_refs else ["No open RFQs at this time"],
        )
        company_name = c2.text_input("Your Company / Trading Name *")

        st.markdown("**Part Details**")
        c1, c2, c3 = st.columns(3)
        brand        = c1.text_input("Brand / Manufacturer *")
        condition    = c2.selectbox(
            "Condition *",
            ["New (Genuine OEM)", "New (Aftermarket)", "Refurbished / Reconditioned"],
        )
        your_part_no = c3.text_input("Your Part Number / SKU")

        st.markdown("**Pricing & Delivery**")
        c1, c2, c3 = st.columns(3)
        unit_price    = c1.number_input("Unit Price (KES) *",          min_value=0.0, format="%.2f")
        delivery_days = c2.number_input("Delivery Lead Time (days) *",  min_value=1,  step=1, value=3)
        warranty      = c3.text_input("Warranty Offered",               placeholder="e.g. 6 months")

        delivery_from = st.text_input("Dispatching From (City / Town) *")
        notes         = st.text_area("Additional Notes / Payment Terms")
        quote_doc     = st.file_uploader("Attach Quotation (PDF, optional)", type=["pdf"])

        submitted = st.form_submit_button("Submit Bid", type="primary", use_container_width=True)

    if submitted:
        missing = not rfq_ref or "No open" in rfq_ref or not company_name or not brand or unit_price <= 0 or not delivery_from
        if missing:
            st.error("Please complete all required fields (*).")
        else:
            # TODO: INSERT INTO claims.rfq_bids
            # TODO: Notify claims officer / garage that a new bid was received
            bid_ref = f"BID-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            st.success(
                f"Bid **{bid_ref}** submitted for **{rfq_ref}**. "
                "You will receive a notification once the evaluation is complete."
            )


# ---------------------------------------------------------------------------
# Tab 3: My Bids
# ---------------------------------------------------------------------------

def _my_bids() -> None:
    st.subheader("My Bids")
    st.caption("Bids are evaluated on price and provider rating. Won bids trigger an order and payment workflow.")

    # TODO: Query claims.rfq_bids WHERE provider_id = current_user_id

    st.dataframe(MY_BIDS, use_container_width=True)

    st.divider()
    total   = len(MY_BIDS)
    won     = sum(1 for b in MY_BIDS if "Won"  in b["Status"])
    lost    = sum(1 for b in MY_BIDS if "Lost" in b["Status"])
    pending = total - won - lost

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Bids",     total)
    c2.metric("Won",             won)
    c3.metric("Lost",            lost)
    c4.metric("Pending Review",  pending)
    if total:
        st.caption(f"Win rate: **{won / total * 100:.0f}%**")


# ---------------------------------------------------------------------------
# Tab 4: Active Orders
# ---------------------------------------------------------------------------

def _active_orders() -> None:
    st.subheader("Active Orders")
    st.info(
        "Orders are created automatically when your bid is awarded. "
        "Deliver the parts and update the delivery status below. "
        "You can then submit your invoice from the **Submit Invoice** tab."
    )

    # TODO: Query claims.spare_part_orders WHERE provider_id = current_user_id

    if not ACTIVE_ORDERS:
        st.info("No active orders at this time.")
        return

    st.dataframe(ACTIVE_ORDERS, use_container_width=True)

    st.divider()
    st.markdown("**Update Delivery Status**")
    with st.form("update_delivery"):
        c1, c2 = st.columns(2)
        order_ref       = c1.selectbox("Order Reference *", [o["Order Ref"] for o in ACTIVE_ORDERS])
        delivery_status = c2.selectbox(
            "New Delivery Status *",
            ["Pending Dispatch", "In Transit", "Delivered"],
        )
        c1, c2 = st.columns(2)
        delivery_note   = c1.file_uploader("Delivery Note / Waybill (PDF)", type=["pdf"])
        actual_date     = c2.date_input("Actual Delivery Date (if delivered)", value=None)
        submitted       = st.form_submit_button("Update Status", type="primary", use_container_width=True)

    if submitted:
        if not order_ref:
            st.error("Select an order reference.")
        else:
            # TODO: UPDATE claims.spare_part_orders SET delivery_status = ... WHERE order_ref = ...
            st.success(f"Order **{order_ref}** status updated to **{delivery_status}**.")


# ---------------------------------------------------------------------------
# Tab 5: Submit Invoice
# ---------------------------------------------------------------------------

def _submit_invoice() -> None:
    st.subheader("Submit Invoice")
    st.info(
        "Submit your invoice after parts have been delivered and accepted. "
        "Payment may be made directly by the **Insurance Company** or by the **Garage**, "
        "depending on what was agreed at order creation."
    )

    order_refs = [o["Order Ref"] for o in ACTIVE_ORDERS]

    with st.form("sp_invoice"):
        c1, c2 = st.columns(2)
        order_ref      = c1.selectbox(
            "Order Reference *",
            options=order_refs if order_refs else ["No active orders"],
        )
        invoice_number = c2.text_input("Invoice Number *")

        c1, c2 = st.columns(2)
        invoice_date   = c1.date_input("Invoice Date *", value=datetime.date.today())
        invoice_amount = c2.number_input("Invoice Amount (KES) *", min_value=0.0, format="%.2f")

        payer = st.radio(
            "Payment Instruction — Payer *",
            ["Insurance Company (direct payment to supplier)", "Garage (garage pays supplier)"],
            horizontal=True,
        )

        c1, c2 = st.columns(2)
        invoice_file  = c1.file_uploader("Invoice PDF *",                        type=["pdf"])
        delivery_note = c2.file_uploader("Proof of Delivery (delivery note PDF) *", type=["pdf"])

        st.markdown("**Banking / Payment Details**")
        c1, c2 = st.columns(2)
        kra_pin      = c1.text_input("KRA PIN *")
        bank_name    = c2.text_input("Bank Name *")
        bank_account = c1.text_input("Account Number *")
        bank_branch  = c2.text_input("Branch Name")

        submitted = st.form_submit_button("Submit Invoice", type="primary", use_container_width=True)

    if submitted:
        required = [order_ref, invoice_number, invoice_file, delivery_note, kra_pin, bank_name, bank_account]
        if not all(required) or "No active" in str(order_ref):
            st.error("All required fields (*) must be completed and both documents uploaded.")
        else:
            # TODO: INSERT INTO claims.sp_invoices
            # TODO: Notify finance team for payment processing
            payer_label = payer.split(" (")[0]
            st.success(
                f"Invoice **{invoice_number}** submitted for order **{order_ref}**. "
                f"Payer: **{payer_label}**. Routed to accounts payable."
            )


# ---------------------------------------------------------------------------
# Tab 6: Payment Status
# ---------------------------------------------------------------------------

def _payment_status() -> None:
    st.subheader("Payment Status")
    st.info(
        "Track payment status for your submitted invoices. "
        "Payments may originate from the Insurance Company or directly from the Garage."
    )

    # TODO: Query claims.sp_payments WHERE provider_id = current_user_id

    st.dataframe(PAYMENT_SAMPLE, use_container_width=True)

    st.divider()
    total  = len(PAYMENT_SAMPLE)
    paid   = sum(1 for p in PAYMENT_SAMPLE if "Paid" in p["Status"])
    pending = total - paid
    try:
        paid_amount = sum(
            float(p["Amount (KES)"].replace(",", ""))
            for p in PAYMENT_SAMPLE if "Paid" in p["Status"]
        )
    except Exception:
        paid_amount = 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Invoices",   total)
    c2.metric("Paid",              paid)
    c3.metric("Pending",           pending)
    c4.metric("Total Paid (KES)",  f"{paid_amount:,.2f}")


# ---------------------------------------------------------------------------
# Tab 7: Notifications
# ---------------------------------------------------------------------------

def _notifications() -> None:
    st.subheader("Notifications")
    st.caption("Broadcasts, bid results, and order confirmations appear here in real time.")

    # TODO: Query claims.notifications WHERE recipient_id = current_user_id ORDER BY notification_date DESC

    unread = [n for n in NOTIFICATIONS if not n["Read"]]
    read   = [n for n in NOTIFICATIONS if n["Read"]]

    if unread:
        st.markdown(f"#### Unread ({len(unread)})")
        for n in unread:
            with st.container(border=True):
                c1, c2 = st.columns([1, 5])
                c1.markdown(f"**{n['Type']}**")
                c2.markdown(n["Message"])
                st.caption(n["Date"])
    else:
        st.success("All notifications read.")

    if read:
        with st.expander(f"Read Notifications ({len(read)})"):
            for n in read:
                c1, c2 = st.columns([1, 5])
                c1.markdown(f"**{n['Type']}**")
                c2.markdown(n["Message"])
                st.caption(n["Date"])

    if not NOTIFICATIONS:
        st.info("No notifications yet.")
