"""Decision trace builder for the HireGuard red-team engine (M2).

Builds AuditEvent dicts with event_type="DECISION" per the canonical
contract (docs/INTEGRATION_PROTOCOL.md + contracts/schemas/AuditEvent):
actor is "AGENT" (uppercase enum), and data carries exactly
{observed_fact, strategy_id, decision_reason, usage{input,output,total}}.

Rules:
- All text fields are concise (<= 280 chars); longer input is truncated.
- No hidden chain-of-thought is ever stored: only the concise
  observed fact / reason strings are persisted (hypothesis lives in
  AgentState + NextProbe, never in the event payload).
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any, Optional

MAX_DECISION_FIELD_LEN = 280


def truncate_concise(text: str, limit: int = MAX_DECISION_FIELD_LEN) -> str:
    """Strip and hard-truncate a decision field to a concise length."""
    cleaned = " ".join(str(text).split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit]


def validate_decision_data(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure DECISION data carries the mandatory canonical keys."""
    for key in ("observed_fact", "strategy_id", "decision_reason", "usage"):
        if key not in data:
            raise ValueError(f"DECISION data requires '{key}'")
    for key in ("observed_fact", "strategy_id", "decision_reason"):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"DECISION data requires non-empty '{key}'")
        if len(value) > MAX_DECISION_FIELD_LEN:
            raise ValueError(f"DECISION field '{key}' exceeds {MAX_DECISION_FIELD_LEN} chars")
    usage = data.get("usage", {})
    if not isinstance(usage, dict):
        raise ValueError("DECISION data requires usage object")
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        if key not in usage:
            raise ValueError(f"DECISION usage requires '{key}'")
    return data


def build_decision_event(
    *,
    run_id: str,
    seq: int,
    turn_index: int,
    observed_fact: str,
    strategy_id: str,
    decision_reason: str,
    usage: dict[str, int] | None = None,
    event_id: Optional[str] = None,
    occurred_at: Optional[str] = None,
) -> dict[str, Any]:
    """Build a canonical DECISION AuditEvent dict.

    `seq` begins at 1 per run and is strictly increasing
    (UNIQUE(run_id,seq) enforced by M3's EvidenceStore).
    """
    safe_usage = dict(usage) if usage else {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    data = {
        "observed_fact": truncate_concise(observed_fact),
        "strategy_id": truncate_concise(strategy_id),
        "decision_reason": truncate_concise(decision_reason),
        "usage": {
            "input_tokens": max(0, int(safe_usage.get("input_tokens", 0))),
            "output_tokens": max(0, int(safe_usage.get("output_tokens", 0))),
            "total_tokens": max(0, int(safe_usage.get("total_tokens", 0))),
        },
    }
    validate_decision_data(data)
    return {
        "event_id": event_id or f"evt_{uuid.uuid4().hex[:12]}",
        "run_id": run_id,
        "seq": int(seq),
        "event_type": "DECISION",
        "actor": "AGENT",
        "turn_index": int(turn_index),
        "occurred_at": occurred_at
        or _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "data": data,
    }


__all__ = [
    "MAX_DECISION_FIELD_LEN",
    "build_check_event",
    "build_decision_event",
    "build_turn_event",
    "truncate_concise",
    "validate_decision_data",
]


def build_turn_event(
    *,
    run_id: str,
    seq: int,
    turn_index: int,
    candidate_message: str,
    target_response: str,
    model_id: str,
    usage: dict[str, int],
    latency_ms: int,
    event_id: Optional[str] = None,
    occurred_at: Optional[str] = None,
) -> dict[str, Any]:
    """Build a canonical TURN AuditEvent (actor TARGET, exact payload keys)."""
    safe = dict(usage) if isinstance(usage, dict) else {}
    return {
        "event_id": event_id or f"evt_{uuid.uuid4().hex[:12]}",
        "run_id": run_id,
        "seq": int(seq),
        "event_type": "TURN",
        "actor": "TARGET",
        "turn_index": int(turn_index),
        "occurred_at": occurred_at
        or _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "data": {
            "candidate_message": candidate_message,
            "target_response": target_response,
            "model_id": model_id,
            "usage": {
                "input_tokens": max(0, int(safe.get("input_tokens", 0))),
                "output_tokens": max(0, int(safe.get("output_tokens", 0))),
                "total_tokens": max(0, int(safe.get("total_tokens", 0))),
            },
            "latency_ms": max(0, int(latency_ms)),
        },
    }


def build_check_event(
    *,
    run_id: str,
    seq: int,
    turn_index: int,
    check: dict[str, Any],
    event_id: Optional[str] = None,
    occurred_at: Optional[str] = None,
) -> dict[str, Any]:
    """Build a canonical CHECK AuditEvent (exact CheckResult payload keys).

    The contract fixes CHECK data to exactly {check_id, rule_id, result,
    evidence_event_ids, evidence_spans, checker_version, reason} — run_id
    and turn_index travel on the event envelope, never inside data.
    """
    payload = check.model_dump(mode="json") if hasattr(check, "model_dump") else dict(check)
    data = {
        "check_id": str(payload.get("check_id", "")),
        "rule_id": str(payload.get("rule_id", "")),
        "result": str(payload.get("result", "INCONCLUSIVE")),
        "evidence_event_ids": list(payload.get("evidence_event_ids", [])),
        "evidence_spans": list(payload.get("evidence_spans", [])),
        "checker_version": str(payload.get("checker_version", "")),
        "reason": str(payload.get("reason", "")),
    }
    return {
        "event_id": event_id or f"evt_{uuid.uuid4().hex[:12]}",
        "run_id": run_id,
        "seq": int(seq),
        "event_type": "CHECK",
        "actor": "CHECKER",
        "turn_index": int(turn_index),
        "occurred_at": occurred_at
        or _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "data": data,
    }
