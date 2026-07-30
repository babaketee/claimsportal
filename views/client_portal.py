"""Client (Policyholder) Portal Ã¢ÂÂ FNOL submission, claim tracking, documents."""
from __future__ import annotations

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core_api  # noqa: E402

import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Delta read helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=30, show_spinner=False)
def _fetch_claim(claim_ref: str) -> dict | None:
    """Fetch one claim row from SQLite (30-s cache). Returns {}, None, or dict."""
    try:
        return core_api.get_claim(claim_ref) or {}
    except Exception:  # noqa: BLE001
        return None


@st.cache_data(ttl=30, show_spinner=False)
def _fetch_assignments(claim_ref: str) -> list[dict]:
    """Fetch all expert assignments for a claim (30-s cache)."""
    try:
        return core_api.get_assignments(claim_ref) or []
    except Exception:  # noqa: BLE001
        return []


@st.cache_data(ttl=30, show_spinner=False)
def _fetch_timeline(claim_ref: str) -> list[dict]:
    """Build a unified chronological timeline for a claim from SQLite."""
    try:
        return core_api.get_timeline(claim_ref) or []
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------------------
# Delta write helpers
# ---------------------------------------------------------------------------

def _send_expert_message(
    claim_ref: str,
    sent_by: str,
    recipient_type: str,
    recipient_name: str,
    subject: str,
    body: str,
) -> bool:
    """INSERT one row into client_messages via SQLite."""
    try:
        return core_api.send_message(
            claim_ref=claim_ref,
            sent_by=sent_by,
            recipient_type=recipient_type,
            recipient_name=recipient_name,
            subject=subject,
            body=body,
        ) is not None
    except Exception:  # noqa: BLE001
        return False


def _db_write_fnol(
    policy_number: str,
    id_number: str,
    vehicle_reg: str,
    phone: str,
    incident_date: datetime.date,
    incident_time: str,
    incident_location: str,
    incident_type: str,
    description: str,
    third_party: bool,
    tp_vehicle_reg: str,
    tp_driver_name: str,
    tp_phone: str,
    tp_insurer: str,
    police_station: str,
    ob_number: str,
    submitted_by: str,
) -> str:
    """Insert one FNOL row and seed the status_history with 'Submitted'."""
    claim_ref = "CLM-" + datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")[:18]

    ok = core_api.create_claim(
        claim_ref=claim_ref,
        policy_number=policy_number,
        id_number=id_number,
        vehicle_reg=vehicle_reg,
        phone=phone,
        incident_date=str(incident_date),
        incident_time=incident_time,
        incident_location=incident_location,
        incident_type=incident_type,
        description=description,
        third_party=third_party,
        tp_vehicle_reg=tp_vehicle_reg,
        tp_driver_name=tp_driver_name,
        tp_phone=tp_phone,
        tp_insurer=tp_insurer,
        police_station=police_station,
        ob_number=ob_number,
        submitted_by=submitted_by,
    )
    if not ok:
        raise RuntimeError("SQLite insert failed")

    # Seed the status_history so the timeline starts from day one
    core_api.record_status_change(
        claim_ref=claim_ref,
        to_status="Submitted",
        from_status="",
        changed_by=submitted_by,
        source="portal",
        note=f"{incident_type} · {incident_location}",
    )

    return claim_ref


# ---------------------------------------------------------------------------
# Timeline renderer
# ---------------------------------------------------------------------------

# Client-facing labels for internal status values
_STATUS_LABELS: dict[str, str] = {
    "Submitted":            "Submitted",
    "Under Review":         "Under Review",
    "Assessor Appointed":   "Assessor Appointed",
    "Under Assessment":     "Being Assessed",
    "Approved for Repair":  "Repair Authorised",
    "Repair in Progress":   "Repair In Progress",
    "Estimate Submitted":   "Estimate Submitted",
    "Invoice Submitted":    "Payment Processing",
    "Pending Settlement":   "Pending Settlement",
    "Settled":              "Settled",
    "Repudiated":           "Claim Declined",
    "Under Investigation":  "Under Investigation",
    "Pending HoC Approval": "Pending Approval",
    "Awaiting Payment":     "Payment Pending",
}

_EVENT_STYLE: dict[str, tuple[str, str]] = {
    "submission":    ("\U0001f7e2", "#27ae60"),
    "status_change": ("\U0001f535", "#2980b9"),
    "assignment":    ("\U0001f7e0", "#e67e22"),
}


def _friendly_title(raw: str, event_type: str) -> str:
    """Convert an internal title to a client-readable string."""
    if raw.startswith("Status \u2192 "):
        inner = raw[9:]
        return "Status: " + _STATUS_LABELS.get(inner, inner)
    if event_type == "assignment":
        return raw
    return _STATUS_LABELS.get(raw, raw)


def _render_timeline(events: list[dict]) -> None:
    """Render a vertical HTML timeline of claim events."""
    if not events:
        st.info("No timeline events recorded for this claim yet.")
        return

    rows: list[str] = []
    n = len(events)

    for i, ev in enumerate(events):
        etype      = ev.get("event_type", "status_change")
        dot, color = _EVENT_STYLE.get(etype, ("\u26aa", "#95a5a6"))
        title      = _friendly_title(ev.get("title", ""), etype)
        actor      = ev.get("actor") or ""
        note       = ev.get("note") or ""
        ts_raw     = ev.get("event_time") or ""
        try:
            dt = datetime.datetime.fromisoformat(ts_raw[:19])
            ts = dt.strftime("%-d %b %Y, %H:%M")
        except Exception:
            ts = ts_raw[:16]

        connector = (
            ""
            if i == n - 1
            else (
                f"<div style='width:2px;min-height:24px;"
                f"background:linear-gradient({color},{color}90);"
                f"margin:2px 0 2px 10px'></div>"
            )
        )
        note_html = (
            f"<div style='font-size:0.78em;color:#888;margin-top:2px'>{note}</div>"
            if note else ""
        )
        rows.append(f"""
            <div style='display:flex;gap:14px'>
              <div style='display:flex;flex-direction:column;align-items:center;min-width:22px'>
                <span style='font-size:1.15em;line-height:1'>{dot}</span>
                {connector}
              </div>
              <div style='padding-bottom:10px;flex:1'>
                <div style='font-weight:600;font-size:0.94em;color:#1a1a1a'>{title}</div>
                <div style='font-size:0.78em;color:#666;margin-top:1px'>
                  {ts}{(" &nbsp;\u00b7&nbsp; " + actor) if actor else ""}
                </div>
                {note_html}
              </div>
            </div>
        """)

    st.markdown(
        "<div style='font-family:sans-serif;padding:6px 0'>"
        + "".join(rows)
        + "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# View entry point
# ---------------------------------------------------------------------------

def render() -> None:
    st.title("Client Portal")
    tab_fnol, tab_track, tab_docs = st.tabs(
        ["File a Claim (FNOL)", "Track My Claim", "My Documents"]
    )
    with tab_fnol:
        _fnol_form()
    with tab_track:
        _claim_tracker()
    with tab_docs:
        _my_documents()


# ---------------------------------------------------------------------------
# FNOL
# ---------------------------------------------------------------------------

def _fnol_form() -> None:
    st.subheader("First Notification of Loss (FNOL)")
    st.info("Complete all sections. Fields marked * are mandatory.")

    with st.form("fnol_form"):
        st.markdown("#### 1. Policyholder Verification")
        c1, c2 = st.columns(2)
        policy_number = c1.text_input("Policy Number *")
        id_number     = c2.text_input("ID / Passport Number *")
        vehicle_reg   = c1.text_input("Vehicle Registration *")
        phone         = c2.text_input("Mobile Number (for SMS updates) *")
        st.divider()

        st.markdown("#### 2. Incident Details")
        c1, c2 = st.columns(2)
        incident_date     = c1.date_input("Date of Incident *", max_value=datetime.date.today())
        incident_time     = c2.time_input("Time of Incident *")
        incident_location = st.text_input("Incident Location (GPS address or description) *")
        incident_type     = st.selectbox(
            "Type of Loss *",
            ["Motor Vehicle Accident", "Theft / Burglary", "Fire Damage",
             "Natural Disaster", "Windscreen / Glass", "Other"],
        )
        description = st.text_area("Description of What Happened *", height=120)
        st.divider()

        st.markdown("#### 3. Third-Party Involvement")
        third_party = st.checkbox("Third-party vehicle(s) involved")
        tp_reg = tp_name = tp_phone = tp_insurer = ""
        if third_party:
            c1, c2 = st.columns(2)
            tp_reg     = c1.text_input("Third-Party Vehicle Registration")
            tp_name    = c2.text_input("Third-Party Driver Name")
            tp_phone   = c1.text_input("Third-Party Phone Number")
            tp_insurer = c2.text_input("Third-Party Insurer (if known)")
        st.divider()

        st.markdown("#### 4. Police Report")
        c1, c2 = st.columns(2)
        police_stn = c1.text_input("Police Station Reported To")
        ob_number  = c2.text_input("OB Number (Occurrence Book Reference)")
        st.divider()

        st.markdown("#### 5. Document Upload")
        st.caption("Accepted: PDF, JPG, PNG  |  Max 10 MB per file")
        drivers_license = st.file_uploader("Driver's License *",            type=["pdf", "jpg", "png"])
        police_abstract = st.file_uploader("Police Abstract (if available)", type=["pdf", "jpg", "png"])
        logbook         = st.file_uploader("NTSA Logbook Copy *",            type=["pdf", "jpg", "png"])
        photos          = st.file_uploader(
            "Scene / Damage Photographs", type=["jpg", "png"], accept_multiple_files=True,
        )
        st.divider()

        consent = st.checkbox(
            "I confirm the information provided is accurate and I consent to the processing "
            "of my personal data in accordance with the Data Protection Act 2019 (DPA 2019). *"
        )
        submitted = st.form_submit_button("Submit Claim", use_container_width=True, type="primary")

    if submitted:
        missing: list[str] = []
        if not policy_number:   missing.append("Policy Number")
        if not id_number:       missing.append("ID / Passport Number")
        if not vehicle_reg:     missing.append("Vehicle Registration")
        if not phone:           missing.append("Mobile Number")
        if not description:     missing.append("Incident Description")
        if not drivers_license: missing.append("Driver's License")
        if not logbook:         missing.append("NTSA Logbook")
        if not consent:         missing.append("DPA consent checkbox")
        if missing:
            st.error(f"Please complete: {', '.join(missing)}")
            return

        with st.spinner("Saving your claim..."):
            try:
                claim_ref = _db_write_fnol(
                    policy_number=policy_number, id_number=id_number,
                    vehicle_reg=vehicle_reg,     phone=phone,
                    incident_date=incident_date, incident_time=str(incident_time),
                    incident_location=incident_location, incident_type=incident_type,
                    description=description,     third_party=third_party,
                    tp_vehicle_reg=tp_reg,       tp_driver_name=tp_name,
                    tp_phone=tp_phone,           tp_insurer=tp_insurer,
                    police_station=police_stn,   ob_number=ob_number,
                    submitted_by=st.session_state.get("user", ""),
                )
                core_api.post_claim({
                    "claim_ref": claim_ref, "policy_number": policy_number,
                    "incident_type": incident_type, "status": "Submitted",
                    "submitted_by": st.session_state.get("user", ""),
                })
                for f_obj, doc_type, label in [
                    (drivers_license, "drivers_license", "Driver's License"),
                    (police_abstract, "police_abstract", "Police Abstract"),
                    (logbook,         "logbook",         "NTSA Logbook"),
                ]:
                    if f_obj is not None:
                        mime = "application/pdf" if f_obj.name.lower().endswith(".pdf") else "image/jpeg"
                        if (core_api.post_document(claim_ref, f_obj.name, mime,
                                                   f_obj.getvalue(), doc_type) is None
                                and core_api.is_configured()):
                            st.warning(f"'{label}' saved locally but could not be posted to core system.")
                for photo in (photos or []):
                    core_api.post_document(claim_ref, photo.name, "image/jpeg",
                                           photo.getvalue(), "scene_photo")
                st.success(
                    f"Claim submitted! Reference: **{claim_ref}**  \n"
                    "Save this number \u2014 you\u2019ll need it to track your claim."
                )
                st.balloons()
            except Exception as exc:
                st.error(f"Submission failed: {exc}")


# ---------------------------------------------------------------------------
# Claim Tracker Ã¢ÂÂ shared constants
# ---------------------------------------------------------------------------

STATUS_STAGES = [
    "Submitted", "Under Review", "Assessor Appointed",
    "Under Assessment", "Approved for Repair", "Repair in Progress", "Settled",
]

_EXPERT_ICONS = {
    "Assessor":          "\U0001f50d",
    "Garage / Repairer": "\U0001f527",
    "Investigator":      "\U0001f575\ufe0f",
}


# ---------------------------------------------------------------------------
# Contact Expert dialog  (module-level Ã¢ÂÂ required by @st.dialog)
# ---------------------------------------------------------------------------

@st.dialog("\U0001f4de Contact Expert", width="small")
def _contact_dialog(expert: dict, claim_ref: str, user_email: str) -> None:
    """Modal for a client to call or send a message to an assigned expert."""
    etype  = expert.get("expert_type",  "Expert")
    ename  = expert.get("expert_name",  "\u2014")
    ephone = (expert.get("expert_phone") or "").strip()
    icon   = _EXPERT_ICONS.get(etype, "\U0001f464")

    # Ã¢ÂÂÃ¢ÂÂ Header card Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
    st.markdown(
        f"<div style='text-align:center;font-size:3em;padding-bottom:2px'>{icon}</div>"
        f"<div style='text-align:center;font-size:1.2em;font-weight:700'>{ename}</div>"
        f"<div style='text-align:center;color:#666;font-size:0.88em;margin-bottom:2px'>{etype}</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    # Ã¢ÂÂÃ¢ÂÂ Phone / tap-to-call Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
    if ephone:
        st.markdown(
            f"<div style='text-align:center;padding:10px 0 6px'>"
            f"  <div style='font-size:1.3em;font-weight:700;letter-spacing:0.5px'>"
            f"    \U0001f4de\u00a0{ephone}"
            f"  </div>"
            f"  <div style='margin-top:10px'>"
            f"    <a href='tel:{ephone}'"
            f"       style='display:inline-block;padding:9px 26px;"
            f"background:#27ae60;color:white;border-radius:6px;"
            f"text-decoration:none;font-weight:600;font-size:0.93em'>"
            f"      Tap to Call"
            f"    </a>"
            f"  </div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info(
            "No direct number on file.  \n"
            "Your claims officer will facilitate contact \u2014 use the form below."
        )

    st.divider()

    # Ã¢ÂÂÃ¢ÂÂ Message form Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
    st.markdown("**\U0001f4ac Send a Message**")
    st.caption("Your message will be logged and relayed by your claims officer.")

    subject = st.text_input(
        "Subject",
        value=f"Query about claim {claim_ref}",
        key="dlg_subject",
    )
    body = st.text_area(
        "Message",
        height=110,
        key="dlg_body",
        placeholder="Type your message here\u2026",
    )

    col_send, col_close = st.columns(2)
    with col_send:
        if st.button("Send", type="primary", use_container_width=True, key="dlg_send"):
            if not body.strip():
                st.error("Please enter a message before sending.")
            else:
                ok = _send_expert_message(
                    claim_ref=claim_ref,
                    sent_by=user_email,
                    recipient_type=etype,
                    recipient_name=ename,
                    subject=subject,
                    body=body,
                )
                if ok:
                    st.success("\u2705 Message sent! Your claims officer will follow up.")
                else:
                    st.error("Send failed. Please try again or call directly.")
    with col_close:
        if st.button("Close", use_container_width=True, key="dlg_close"):
            st.rerun()


# ---------------------------------------------------------------------------
# Claim Tracker
# ---------------------------------------------------------------------------

def _claim_tracker() -> None:
    st.subheader("Track My Claim")
    c1, c2 = st.columns([3, 1])
    ref    = c1.text_input("Claim Reference Number", placeholder="e.g. CLM-20250715123456")
    search = c2.button("Search", use_container_width=True, type="primary")

    if not (search and ref):
        return

    st.divider()

    with st.spinner("Fetching your claim details\u2026"):
        claim   = _fetch_claim(ref)
        experts = _fetch_assignments(ref)
        payment = core_api.get_payment_status(ref)
        events  = _fetch_timeline(ref)

    if claim is None:
        st.warning("Unable to retrieve claim data. Please try again in a moment.")
        return
    if claim == {}:
        st.error(
            f"Claim **{ref}** was not found.  \n"
            "Double-check the reference on your confirmation SMS/email."
        )
        return

    # Ã¢ÂÂÃ¢ÂÂ KPI metrics Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
    raw_status = claim.get("status", "Submitted")
    inc_type   = claim.get("incident_type", "\u2014")
    date_rep   = str(claim.get("incident_date") or claim.get("submitted_at") or "\u2014")[:10]

    st.markdown(f"#### Claim `{ref}`")
    c1, c2, c3 = st.columns(3)
    c1.metric("Current Status", _STATUS_LABELS.get(raw_status, raw_status))
    c2.metric("Incident Type",  inc_type)
    c3.metric("Date Reported",  date_rep)

    # Ã¢ÂÂÃ¢ÂÂ Progress bar Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
    st.markdown("##### Progress")
    try:
        cur_idx = STATUS_STAGES.index(raw_status)
    except ValueError:
        cur_idx = 0
    cols = st.columns(len(STATUS_STAGES))
    for i, stage in enumerate(STATUS_STAGES):
        icon = "\u2705" if i < cur_idx else ("\U0001f535" if i == cur_idx else "\u2b1c")
        cols[i].markdown(
            f"<div style='text-align:center;font-size:1.2em'>{icon}</div>"
            f"<div style='text-align:center'><small>{_STATUS_LABELS.get(stage, stage)}</small></div>",
            unsafe_allow_html=True,
        )

    # Ã¢ÂÂÃ¢ÂÂ Your Claim Team Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
    st.divider()
    st.markdown("##### Your Claim Team")
    visible = [e for e in experts if e.get("assignment_status") != "Replaced"]
    if not visible:
        st.info(
            "No experts have been assigned to your claim yet.  \n"
            "Your claims officer is currently reviewing your submission."
        )
    else:
        for i, expert in enumerate(visible):
            a_status  = expert.get("assignment_status", "Active")
            sla_state = expert.get("sla_state", "on_track")
            etype     = expert.get("expert_type", "Expert")
            ename     = expert.get("expert_name", "\u2014")
            ephone    = expert.get("expert_phone") or "\u2014"
            asgn_at   = (expert.get("assigned_at")  or "\u2014")[:16]
            sla_dl    = (expert.get("sla_deadline") or "\u2014")[:16]
            icon      = _EXPERT_ICONS.get(etype, "\U0001f464")

            if a_status == "Completed":
                badge = "\u2705 Work completed"
            elif sla_state == "pending":
                badge = "\u23f3 Response pending"
            elif sla_state == "due_soon":
                badge = "\U0001f7e1 Due soon"
            else:
                badge = "\U0001f7e2 Currently assigned"

            with st.container(border=True):
                ci, cd, cs, cc = st.columns([1, 3, 2, 1])
                with ci:
                    st.markdown(
                        f"<div style='font-size:2.2em;text-align:center'>{icon}</div>"
                        f"<div style='text-align:center;font-weight:600;font-size:0.85em'>{etype}</div>",
                        unsafe_allow_html=True,
                    )
                with cd:
                    st.markdown(f"**{ename}**")
                    if ephone != "\u2014":
                        st.caption(f"\U0001f4de {ephone}")
                    st.caption(f"Assigned: {asgn_at}")
                with cs:
                    st.markdown(f"**{badge}**")
                    if a_status == "Active" and sla_dl != "\u2014":
                        st.caption(f"Expected by: {sla_dl}")
                with cc:
                    # Vertical spacer to align button with middle of card
                    st.write("")
                    if st.button(
                        "\U0001f4de Contact",
                        key=f"contact_{i}",
                        use_container_width=True,
                        help=f"Call or message {ename}",
                    ):
                        _contact_dialog(
                            expert=expert,
                            claim_ref=ref,
                            user_email=st.session_state.get("user", ""),
                        )

    # Ã¢ÂÂÃ¢ÂÂ Payment Status Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
    st.divider()
    st.markdown("##### Payment Status")
    if payment is None or not core_api.is_configured():
        if raw_status == "Settled":
            st.success("Your claim has been settled. Payment has been processed.")
        elif raw_status in ("Invoice Submitted", "Pending Settlement", "Awaiting Payment"):
            st.info("Payment is being processed. Please allow 7 business days.")
        else:
            st.info("No payment record yet for this claim.")
    elif payment == {}:
        st.info("No payment record yet for this claim.")
    else:
        pc1, pc2, pc3 = st.columns(3)
        pc1.metric("Payment Status", payment.get("status",       "\u2014"))
        pc2.metric("Amount (KES)",   f"{float(payment.get('amount', 0)):,.2f}")
        pc3.metric("Payment Date",   payment.get("payment_date", "\u2014"))

    # Ã¢ÂÂÃ¢ÂÂ Timeline Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
    st.divider()
    with st.expander("\U0001f4c5 Claim Timeline", expanded=True):
        _render_timeline(events)

    # Ã¢ÂÂÃ¢ÂÂ Refresh Ã¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂÃ¢ÂÂ
    col_r, col_cap = st.columns([1, 5])
    if col_r.button("\U0001f504 Refresh", key="tracker_refresh"):
        _fetch_claim.clear()        # type: ignore[attr-defined]
        _fetch_assignments.clear()  # type: ignore[attr-defined]
        _fetch_timeline.clear()     # type: ignore[attr-defined]
        core_api.invalidate_claim_cache(ref)
        st.rerun()
    col_cap.caption("Data refreshes automatically every 30 seconds.")


# ---------------------------------------------------------------------------
# My Documents
# ---------------------------------------------------------------------------

def _my_documents() -> None:
    st.subheader("My Documents")
    st.info("Documents submitted with your claim. Enter a claim reference to view them.")
    claim_ref_input = st.text_input(
        "Claim Reference", placeholder="e.g. CLM-20250715123456", key="doc_claim_ref_input",
    )
    if claim_ref_input:
        with st.spinner("Fetching documents from core system\u2026"):
            docs = core_api.get_documents(claim_ref_input)
        if not docs:
            st.info("No documents found for this claim. If you just uploaded them, refresh in a moment.")
        else:
            display = [
                {
                    "Claim Ref":   d.get("claim_ref",   claim_ref_input),
                    "Document":    d.get("doc_type",    d.get("filename", "\u2014")),
                    "File Name":   d.get("filename",    "\u2014"),
                    "Uploaded":    (d.get("uploaded_at") or "\u2014")[:10],
                    "Status":      d.get("status",      "Received"),
                    "Verified By": d.get("verified_by", "\u2014"),
                }
                for d in docs
            ]
            st.dataframe(display, use_container_width=True, hide_index=True)
        if st.button("\U0001f504 Refresh Documents", key="docs_refresh_btn"):
            core_api.invalidate_claim_cache(claim_ref_input)
            st.rerun()
