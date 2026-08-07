"""api_client.py — Phase 1: 6 API Exchanges with Idempotency, Retry Queue
================================================================

Exchanges:
  1. GET  /policies?identity          — live policy pull
  2. POST /claims/notification        — register loss + initial reserve
  3. PUSH /portal/claims/{ref}/triage — routing / manual fallback
  4. PUSH /claims/{ref}/reports      — assessment + investigation packet
  5. PUSH /portal/claims/{ref}/decision — approved payout or repudiation
  6. PUSH /claims/{ref}/settlement   — adjust policy limit
"""

from __future__ import annotations

import json
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import requests

# ---------------------------------------------------------------------------
# Config — hardcoded for Phase 1; will come from config_db in Phase 2
# ---------------------------------------------------------------------------
BASE_URL = "https://api.definiteassurance.co.ke"   # placeholder — update when core system URL is known
API_KEY  = ""                                         # placeholder — update when auth is ready
TIMEOUT  = 30          # seconds

# ---------------------------------------------------------------------------
# Idempotency key store (in-memory for Phase 1; Redis in production)
# ---------------------------------------------------------------------------
_SEEN: dict[str, str] = {}   # idempotency_key -> response_sha
_SEEN_LOCK = threading.Lock()


def make_idempotency_key(claim_ref: str, exchange: str, attempt: int = 1) -> str:
    """Generate a deterministic GUID per claim+exchange+attempt."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{claim_ref}-{exchange}-{attempt}"))


def is_duplicate(idempotency_key: str) -> bool:
    with _SEEN_LOCK:
        return idempotency_key in _SEEN


def mark_seen(idempotency_key: str, response_hash: str) -> None:
    with _SEEN_LOCK:
        _SEEN[idempotency_key] = response_hash


# ---------------------------------------------------------------------------
# Exponential backoff
# ---------------------------------------------------------------------------
MAX_RETRIES   = 5
BASE_DELAY    = 2.0     # seconds
BACKOFF_MAX   = 60.0    # seconds


def backoff_delay(attempt: int) -> float:
    delay = BASE_DELAY * (2 ** (attempt - 1))
    return min(delay, BACKOFF_MAX)


# ---------------------------------------------------------------------------
# Persistent outbound queue (single-threaded dispatcher for Phase 1)
# ---------------------------------------------------------------------------

@dataclass
class QueuedRequest:
    claim_ref: str
    exchange: str          # e.g. "exchange_3_triage"
    method: str
    url: str
    headers: dict
    payload: dict | None
    idempotency_key: str
    retries: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OutboundQueue:
    """
    Thread-safe FIFO queue for outbound API calls.
    Phase 1: single dispatch thread. Phase 2: persistent queue with persistence.
    """
    def __init__(self):
        self._q: queue.Queue[QueuedRequest | None] = queue.Queue()
        self._running = False
        self._thread: threading.Thread | None = None

    def enqueue(self, req: QueuedRequest) -> None:
        self._q.put(req)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._q.put(None)   # sentinel
        if self._thread:
            self._thread.join(timeout=5)

    def _dispatch_loop(self) -> None:
        while self._running:
            req = self._q.get()
            if req is None:
                continue
            self._dispatch(req)

    def _dispatch(self, req: QueuedRequest) -> None:
        # Skip if already sent successfully (idempotency)
        if is_duplicate(req.idempotency_key):
            print(f"[api_client] Skipping duplicate: {req.idempotency_key}")
            return

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._send(req, attempt)
                if response is not None:
                    # Mark idempotency key as seen
                    mark_seen(req.idempotency_key, str(hash(str(response))))
                    print(f"[api_client] {req.exchange} succeeded on attempt {attempt}")
                    return
            except Exception as e:
                print(f"[api_client] {req.exchange} attempt {attempt} failed: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(backoff_delay(attempt))
        print(f"[api_client] {req.exchange} exhausted retries after {MAX_RETRIES} attempts")

    def _send(self, req: QueuedRequest, attempt: int) -> dict | None:
        """Execute a single HTTP request. Returns parsed JSON on success, None on 4xx/5xx."""
        headers = dict(req.headers)
        headers["Idempotency-Key"] = req.idempotency_key
        headers["X-Attempt"] = str(attempt)

        try:
            if req.method == "GET":
                r = requests.get(req.url, headers=headers, timeout=TIMEOUT)
            elif req.method == "POST":
                r = requests.post(req.url, json=req.payload, headers=headers, timeout=TIMEOUT)
            elif req.method == "PUT":
                r = requests.put(req.url, json=req.payload, headers=headers, timeout=TIMEOUT)
            elif req.method == "PATCH":
                r = requests.patch(req.url, json=req.payload, headers=headers, timeout=TIMEOUT)
            else:
                print(f"[api_client] Unknown method: {req.method}")
                return None

            if r.status_code >= 400:
                print(f"[api_client] HTTP {r.status_code}: {r.text[:200]}")
                return None

            return r.json() if r.content else None

        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request timed out after {TIMEOUT}s")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Connection failed: {e}")


# Global queue instance
_OUTBOUND_QUEUE: OutboundQueue | None = None
_QUEUE_LOCK = threading.Lock()


def get_queue() -> OutboundQueue:
    global _OUTBOUND_QUEUE
    if _OUTBOUND_QUEUE is None:
        with _QUEUE_LOCK:
            if _OUTBOUND_QUEUE is None:
                _OUTBOUND_QUEUE = OutboundQueue()
                _OUTBOUND_QUEUE.start()
    return _OUTBOUND_QUEUE


# ---------------------------------------------------------------------------
# API Client — 6 exchanges
# ---------------------------------------------------------------------------

class APIClient:
    """
    Thin wrapper around the 6 API exchanges.
    All methods return (success: bool, data: dict | None, error: str | None).
    """
    def __init__(self, base_url: str = BASE_URL, api_key: str = API_KEY):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self, extra: dict | None = None) -> dict:
        h = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ClaimsPortal/1.0",
        }
        if extra:
            h.update(extra)
        return h

    def _queue(self, exchange: str, method: str, url: str, payload: dict | None, claim_ref: str) -> None:
        key = make_idempotency_key(claim_ref, exchange)
        req = QueuedRequest(
            claim_ref=claim_ref,
            exchange=exchange,
            method=method,
            url=url,
            headers=self._headers(),
            payload=payload,
            idempotency_key=key,
        )
        get_queue().enqueue(req)

    # Exchange 1: GET /policies?identity= — live policy pull
    def get_policy(self, identity: str, claim_ref: str) -> tuple[bool, dict | None, str | None]:
        """Pull active policy by ID number or policy reference."""
        url = f"{self.base_url}/policies?identity={identity}"
        key = make_idempotency_key(claim_ref, "exchange_1_policy")
        try:
            r = requests.get(url, headers=self._headers({"Idempotency-Key": key}), timeout=TIMEOUT)
            if r.status_code >= 400:
                return False, None, f"HTTP {r.status_code}: {r.text[:200]}"
            return True, r.json() if r.content else {}, None
        except Exception as e:
            return False, None, str(e)

    # Exchange 2: POST /claims/notification — register loss + initial reserve
    def notify_claim(self, claim_ref: str, policy_ref: str, payload: dict) -> tuple[bool, str | None]:
        """
        Submit FNOL to core system.
        Returns (enqueued, error_message).
        """
        url = f"{self.base_url}/claims/notification"
        self._queue("exchange_2_fnol", "POST", url, {**payload, "claim_ref": claim_ref, "policy_ref": policy_ref}, claim_ref)
        return True, None

    # Exchange 3: PUSH /portal/claims/{ref}/triage — routing / manual fallback
    def push_triage(self, claim_ref: str, triage_decision: str, officer_id: str, notes: str = "") -> tuple[bool, str | None]:
        url = f"{self.base_url}/portal/claims/{claim_ref}/triage"
        payload = {"triage_decision": triage_decision, "officer_id": officer_id, "notes": notes}
        self._queue("exchange_3_triage", "POST", url, payload, claim_ref)
        return True, None

    # Exchange 4: PUSH /claims/{ref}/reports — combined assessment + investigation
    def push_reports(self, claim_ref: str, assessment: dict, investigation: dict) -> tuple[bool, str | None]:
        url = f"{self.base_url}/claims/{claim_ref}/reports"
        payload = {"assessment": assessment, "investigation": investigation}
        self._queue("exchange_4_reports", "POST", url, payload, claim_ref)
        return True, None

    # Exchange 5: PUSH /portal/claims/{ref}/decision — approved payout or repudiation
    def push_decision(self, claim_ref: str, decision: str, amount: float | None, currency: str = "KES", reason: str = "") -> tuple[bool, str | None]:
        """
        Submit final claim decision to core system.
        decision: "approved" | "repudiated"
        Must be idempotent — core system guards against duplicate decisions.
        """
        url = f"{self.base_url}/portal/claims/{claim_ref}/decision"
        payload = {"decision": decision, "amount": amount, "currency": currency, "reason": reason}
        self._queue("exchange_5_decision", "POST", url, payload, claim_ref)
        return True, None

    # Exchange 6: PUSH /claims/{ref}/settlement — adjust policy limit
    def push_settlement(self, claim_ref: str, payout_amount: float, currency: str = "KES", remaining_reserve: float = 0) -> tuple[bool, str | None]:
        """
        Notify core system of settlement. Triggers remaining coverage reduction.
        """
        url = f"{self.base_url}/claims/{claim_ref}/settlement"
        payload = {"payout_amount": payout_amount, "currency": currency, "remaining_reserve": remaining_reserve}
        self._queue("exchange_6_settlement", "POST", url, payload, claim_ref)
        return True, None


# Singleton
_client: APIClient | None = None


def get_client() -> APIClient:
    global _client
    if _client is None:
        _client = APIClient()
    return _client
