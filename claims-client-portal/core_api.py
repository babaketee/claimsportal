"""Insurance Core System — API client.

Reads two environment variables (set them in app.yaml env_vars or as Databricks Secrets):
  CORE_API_BASE_URL  e.g. https://core.myinsurer.co.ke/api/v1
  CORE_API_TOKEN     Bearer token (or API key) issued by the core system

All public functions degrade gracefully when the core system is unreachable:
  - GET helpers return None or [] instead of raising.
  - POST/PATCH helpers return False / None and log a warning.
This lets the portal remain usable even when the core system is down.

record_status_change() writes to main.claims.status_history via the Databricks SDK
and runs regardless of whether the external core system is configured.
"""
from __future__ import annotations

import datetime
import logging
import os
from typing import Any

import requests
import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementParameterListItem, StatementState

logger = logging.getLogger(__name__)

_BASE_URL: str      = os.environ.get("CORE_API_BASE_URL", "").rstrip("/")
_TOKEN: str         = os.environ.get("CORE_API_TOKEN", "")
_TIMEOUT: int       = 15  # seconds for all calls except document upload

_WAREHOUSE_ID: str  = os.environ.get("DATABRICKS_WAREHOUSE_ID", "4489dbff81694cd8")
_STATUS_HISTORY     = "main.claims.status_history"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _headers(json_body: bool = True) -> dict[str, str]:
    h: dict[str, str] = {"Accept": "application/json"}
    if json_body:
        h["Content-Type"] = "application/json"
    if _TOKEN:
        h["Authorization"] = f"Bearer {_TOKEN}"
    return h


def is_configured() -> bool:
    """Return True when CORE_API_BASE_URL is set."""
    return bool(_BASE_URL)


def _warn_not_configured(fn: str) -> None:
    logger.debug("core_api.%s skipped — CORE_API_BASE_URL not set", fn)


# ---------------------------------------------------------------------------
# Status History  (Delta write — always runs, no core system required)
# ---------------------------------------------------------------------------

def record_status_change(
    claim_ref: str,
    to_status: str,
    from_status: str = "",
    changed_by: str = "",
    source: str = "portal",
    note: str = "",
) -> bool:
    """INSERT one row into main.claims.status_history.

    This is a Delta write via the Databricks SDK.  It runs regardless of
    whether the external core system is configured, so the audit trail is
    always populated even in standalone / disconnected deployments.

    Returns True on success, False on any error (non-fatal — callers should
    not abort their own logic if this fails).
    """
    history_id = "SH-" + datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    try:
        w = WorkspaceClient()
        resp = w.statement_execution.execute_statement(
            warehouse_id=_WAREHOUSE_ID,
            statement=f"""
                INSERT INTO {_STATUS_HISTORY} (
                    history_id, claim_ref, changed_at, changed_by,
                    from_status, to_status, source, note
                ) VALUES (
                    :hid, :cref, CURRENT_TIMESTAMP(), :cby,
                    :from_s, :to_s, :src, :note
                )
            """,
            parameters=[
                StatementParameterListItem(name="hid",    value=history_id),
                StatementParameterListItem(name="cref",   value=claim_ref),
                StatementParameterListItem(name="cby",    value=changed_by  or ""),
                StatementParameterListItem(name="from_s", value=from_status or ""),
                StatementParameterListItem(name="to_s",   value=to_status),
                StatementParameterListItem(name="src",    value=source      or "portal"),
                StatementParameterListItem(name="note",   value=note        or ""),
            ],
            wait_timeout="30s",
        )
        return resp.status.state == StatementState.SUCCEEDED
    except Exception as exc:  # noqa: BLE001
        logger.warning("core_api.record_status_change failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------

def post_claim(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Create / sync a new claim in the core system.

    Args:
        payload: dict with at minimum ``claim_ref``, ``policy_number``,
                 ``incident_type``, ``status``, and ``submitted_at``.

    Returns:
        Parsed JSON response from the core system, or ``None`` on failure.
    """
    if not is_configured():
        _warn_not_configured("post_claim")
        return None
    try:
        r = requests.post(
            f"{_BASE_URL}/claims",
            json=payload,
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("core_api.post_claim failed: %s", exc)
        return None


@st.cache_data(ttl=30, show_spinner=False)
def get_claim(claim_ref: str) -> dict[str, Any] | None:
    """Fetch a real-time claim record from the core system (TTL: 30 s).

    Returns:
        Claim dict, empty dict if claim not found (404), or ``None`` on error.
    """
    if not is_configured():
        _warn_not_configured("get_claim")
        return None
    try:
        r = requests.get(
            f"{_BASE_URL}/claims/{claim_ref}",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("core_api.get_claim failed: %s", exc)
        return None


def update_claim_status(
    claim_ref: str,
    status: str,
    note: str = "",
    actor: str = "",
) -> bool:
    """Update the claim status.

    Always records the change in main.claims.status_history (Delta).
    Also PATCHes the external core system when CORE_API_BASE_URL is configured.

    Returns:
        True when the core system PATCH succeeds (or is not configured),
        False when the PATCH fails.
    """
    # ── Always write to Delta status history ─────────────────────────────
    record_status_change(
        claim_ref=claim_ref,
        to_status=status,
        changed_by=actor,
        source="portal",
        note=note,
    )

    # ── Optionally sync to the external core system ───────────────────────
    if not is_configured():
        _warn_not_configured("update_claim_status")
        return True   # Delta write succeeded; core system not required
    try:
        payload = {
            "status":     status,
            "note":       note,
            "actor":      actor,
            "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        }
        r = requests.patch(
            f"{_BASE_URL}/claims/{claim_ref}/status",
            json=payload,
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("core_api.update_claim_status failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def post_document(
    claim_ref: str,
    filename: str,
    mime_type: str,
    data: bytes,
    doc_type: str = "",
) -> dict[str, Any] | None:
    """Upload a document to the core system under the given claim."""
    if not is_configured():
        _warn_not_configured("post_document")
        return None
    try:
        h = _headers(json_body=False)
        files = {"file": (filename, data, mime_type)}
        data_fields = {"doc_type": doc_type} if doc_type else {}
        r = requests.post(
            f"{_BASE_URL}/claims/{claim_ref}/documents",
            files=files,
            data=data_fields,
            headers=h,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("core_api.post_document failed: %s", exc)
        return None


@st.cache_data(ttl=60, show_spinner=False)
def get_documents(claim_ref: str) -> list[dict[str, Any]]:
    """List documents attached to a claim in the core system (TTL: 60 s)."""
    if not is_configured():
        _warn_not_configured("get_documents")
        return []
    try:
        r = requests.get(
            f"{_BASE_URL}/claims/{claim_ref}/documents",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("documents", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("core_api.get_documents failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

@st.cache_data(ttl=30, show_spinner=False)
def get_payment_status(claim_ref: str) -> dict[str, Any] | None:
    """Fetch real-time payment status for a claim (TTL: 30 s)."""
    if not is_configured():
        _warn_not_configured("get_payment_status")
        return None
    try:
        r = requests.get(
            f"{_BASE_URL}/claims/{claim_ref}/payment",
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("core_api.get_payment_status failed: %s", exc)
        return None


def update_payment_status(claim_ref: str, payload: dict[str, Any]) -> bool:
    """PATCH the payment record for a claim in the core system."""
    if not is_configured():
        _warn_not_configured("update_payment_status")
        return False
    try:
        r = requests.patch(
            f"{_BASE_URL}/claims/{claim_ref}/payment",
            json=payload,
            headers=_headers(),
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("core_api.update_payment_status failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------

def invalidate_claim_cache(claim_ref: str) -> None:
    """Clear the short-lived Streamlit caches after any write operation."""
    get_claim.clear()           # type: ignore[attr-defined]
    get_payment_status.clear()  # type: ignore[attr-defined]
    get_documents.clear()       # type: ignore[attr-defined]
