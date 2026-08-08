"""helpers.py — Date utilities, TAT formatters, claim ref generators"""

from datetime import datetime, timezone
from typing import Optional

def now_ms() -> float:
    return datetime.now(timezone.utc).timestamp() * 1000

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def tat_display(elapsed_ms: int) -> str:
    if elapsed_ms < 1000: return f"{elapsed_ms}ms"
    total = int(elapsed_ms)
    d, r = divmod(total, 86400000)
    h, r2 = divmod(r, 3600000)
    m, s = divmod(r2, 60000)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s and not d: parts.append(f"{s}s")
    return " ".join(parts) if parts else "0s"

def is_overdue(elapsed_ms: int, sla_hours: int) -> bool:
    return elapsed_ms > sla_hours * 3600000

def format_kes(amount: float) -> str:
    return f"KES {amount:,.0f}"

def generate_claim_ref(claim_class: str, branch_code: str = "NRB") -> str:
    import uuid, datetime
    year = datetime.datetime.now().year
    seq = uuid.uuid4().hex[:6].upper()
    prefix_map = {"motor":"MOT","motor_tp":"MOT","motor_tp_bi":"MOT","medical":"MED","property":"PRO","travel":"TRV"}
    prefix = prefix_map.get(claim_class, "CLA")
    return f"CLM/{prefix}/{branch_code}/{year}/{seq}"

def status_color(status: str) -> str:
    map_ = {"Draft":"gray","Reported":"blue","Triage":"yellow","Investigation":"orange","Assessment":"purple","Approval":"cyan","Approved":"green","Pending Payment":"lime","Paid":"green","Closed":"gray","Closed_Approved":"green","Closed_Repudiated":"red","Total_Loss_Settlement":"orange","Closed_Total_Loss":"gray"}
    return map_.get(status, "gray")
