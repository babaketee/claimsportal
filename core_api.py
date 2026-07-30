"""Insurance Core System — API client.

Reads two environment variables:
  CORE_API_BASE_URL  e.g. https://core.myinsurer.co.ke/api/v1
  CORE_API_TOKEN     Bearer token (or API key) issued by the core system

All public functions degrade gracefully when the core system is unreachable.

record_status_change() writes to a local SQLite file (claims_history.db)
so the audit trail works standalone without any external database.
"""
from __future__ import annotations

import datetime
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

import requests
import streamlit as st

logger = logging.getLogger(__name__)

_BASE_URL: str  = os.environ.get("CORE_API_BASE_URL", "").rstrip("/")
_TOKEN: str      = os.environ.get("CORE_API_TOKEN", "")
_TIMEOUT: int   = 15

_DB_PATH = os.environ.get("CLAIMS_HISTORY_DB", "claims_history.db")

def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS status_history (
            history_id TEXT PRIMARY KEY,
            claim_ref  TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            changed_by TEXT,
            from_status TEXT,
            to_status   TEXT NOT NULL,
            source      TEXT DEFAULT 'portal',
            note        TEXT
        )
    """)
    conn.commit()
    return conn


def _headers(json_body: bool = True) -> dict[str, str]:
    h: dict[str, str] = {"Accept": "application/json"}
    if json_body:
        h["Content-Type"] = "application/json"
    if _TOKEN:
        h["Authorization"] = f"Bearer {_TOKEN}"
    return h


def is_configured() -> bool:
    return bool(_BASE_URL)


def _warn_not_configured(fn: str) -> None:
    logger.debug("core_api.%s skipped — CORE_API_BASE_URL not set", fn)


def record_status_change(
    claim_ref: str,
    to_status: str,
    from_status: str = "",
    changed_by: str = "",
    source: str = "portal",
    note: str = "",
) -> bool:
    """INSERT one row into local SQLite status_history table.
    Works standalone — no Databricks, no external dependencies.
    """
    history_id = "SH-" + datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    try:
        conn = _get_db()
        conn.execute("""
            INSERT INTO status_history
                (history_id, claim_ref, changed_at, changed_by, from_status, to_status, source, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            history_id,
            claim_ref,
            datetime.datetime.utcnow().isoformat(),
            changed_by or "",
            from_status or "",
            to_status,
            source or "portal",
            note or "",
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        logger.warning("record_status_change failed: %s", exc)
        return False


def post_claim(payload: dict[str, Any]) -> dict[str, Any] | None:
    if not is_configured():
        _warn_not_configured("post_claim")
        return None
    try:
        r = requests.post(f"{_BASE_URL}/claims/", json=payload, headers=_headers(), timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.warning("post_claim failed: %s", exc)
        return None


@st.cache_data(ttl=30, show_spinner=False)
def get_claim(claim_ref: str) -> dict[str, Any] | None:
    if not is_configured():
        _warn_not_configured("get_claim")
        return None
    try:
        r = requests.get(f"{_BASE_URL}/claims/{claim_ref}", headers=_headers(), timeout=_TIMEOUT)
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.warning("get_claim failed: %s", exc)
        return None


def update_claim_status(claim_ref: str, status: str, note: str = "", actor: str = "") -> bool:
    record_status_change(
        claim_ref=claim_ref,
        to_status=status,
        changed_by=actor,
        source="portal",
        note=note,
    )
    if not is_configured():
        _warn_not_configured("update_claim_status")
        return True
    try:
        payload = {
            "status": status,
            "note": note,
            "actor": actor,
            "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        }
        r = requests.patch(f"{_BASE_URL}/claims/{claim_ref}/status", json=payload, headers=_headers(), timeout=_TIMEOUT)
        r.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("update_claim_status failed: %s", exc)
        return False


def post_document(claim_ref: str, filename: str, mime_type: str, data: bytes, doc_type: str = "") -> dict[str, Any] | None:
    if not is_configured():
        _warn_not_configured("post_document")
        return None
    try:
        h = _headers(json_body=False)
        files = {"file": (filename, data, mime_type)}
        data_fields = {"doc_type": doc_type} if doc_type else {}
        r = requests.post(f"{_BASE_URL}/claims/{claim_ref}/documents/", files=files, data=data_fields, headers=h, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.warning("post_document failed: %s", exc)
        return None


@st.cache_data(ttl=60, show_spinner=False)
def get_documents(claim_ref: str) -> list[dict[str, Any]]:
    if not is_configured():
        _warn_not_configured("get_documents")
        return []
    try:
        r = requests.get(f"{_BASE_URL}/claims/{claim_ref}/documents/", headers=_headers(), timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json().get("documents", [])
    except Exception as exc:
        logger.warning("get_documents failed: %s", exc)
        return []


@st.cache_data(ttl=30, show_spinner=False)
def get_payment_status(claim_ref: str) -> dict[str, Any] | None:
    if not is_configured():
        _warn_not_configured("get_payment_status")
        return None
    try:
        r = requests.get(f"{_BASE_URL}/claims/{claim_ref}/payment/", headers=_headers(), timeout=_TIMEOUT)
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.warning("get_payment_status failed: %s", exc)
        return None


def update_payment_status(claim_ref: str, payload: dict[str, Any]) -> bool:
    if not is_configured():
        _warn_not_configured("update_payment_status")
        return False
    try:
        r = requests.patch(f"{_BASE_URL}/claims/{claim_ref}/payment/", json=payload, headers=_headers(), timeout=_TIMEOUT)
        r.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("update_payment_status failed: %s", exc)
        return False


def invalidate_claim_cache(claim_ref: str) -> None:
    get_claim.clear()
    get_payment_status.clear()
    get_documents.clear()
