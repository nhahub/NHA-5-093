"""Trace replay validator for the HireGuard red-team engine (M2).

Replays an exported trace file structurally (no model calls): checks
event-id uniqueness, per-run seq monotonicity, required per-type data
keys, DECISION conciseness, and counter/transcript consistency. Used by
M2 acceptance (trace completeness) and M5 reproducibility checks.

Replay never claims byte-identical regeneration across providers; it
validates that a stored trace is complete and self-consistent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .trace import MAX_DECISION_FIELD_LEN

_REQUIRED_TOP_KEYS = (
    "event_id",
    "run_id",
    "seq",
    "event_type",
    "actor",
    "turn_index",
    "occurred_at",
    "data",
)

_REQUIRED_DATA_KEYS: dict[str, tuple[str, ...]] = {
    "DECISION": ("observed_fact", "strategy_id", "decision_reason", "usage"),
    "TURN": ("candidate_message", "target_response", "model_id", "usage", "latency_ms"),
    "CHECK": ("check_id", "rule_id", "result", "evidence_event_ids",
              "evidence_spans", "checker_version", "reason"),
}


def replay_trace(trace_path: str | Path) -> dict[str, Any]:
    """Validate a stored trace file and return a completeness report."""
    path = Path(trace_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    events = payload.get("events", [])
    errors: list[str] = []

    if not isinstance(events, list) or not events:
        errors.append("trace has no events list")
        return _report(payload, events=[], errors=errors)

    seen_ids: set[str] = set()
    last_seq = -1
    for pos, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"event[{pos}] is not an object")
            continue
        for key in _REQUIRED_TOP_KEYS:
            if key not in event:
                errors.append(f"event[{pos}] missing top key '{key}'")
        eid = event.get("event_id")
        if eid in seen_ids:
            errors.append(f"duplicate event_id '{eid}'")
        seen_ids.add(eid)
        seq = event.get("seq")
        if not isinstance(seq, int) or seq <= last_seq:
            errors.append(f"event[{pos}] seq not strictly increasing: {seq}")
        last_seq = seq if isinstance(seq, int) else last_seq
        etype = event.get("event_type")
        for dkey in _REQUIRED_DATA_KEYS.get(str(etype), ()):
            data = event.get("data", {})
            if not isinstance(data, dict) or dkey not in data:
                errors.append(f"event[{pos}] ({etype}) missing data key '{dkey}'")
        if etype == "DECISION" and isinstance(event.get("data"), dict):
            for fkey in ("observed_fact", "decision_reason", "hypothesis"):
                val = event["data"].get(fkey, "")
                if isinstance(val, str) and len(val) > MAX_DECISION_FIELD_LEN:
                    errors.append(f"event[{pos}] DECISION field '{fkey}' exceeds concise limit")

    transcript = payload.get("transcript", [])
    turns = [e for e in events if isinstance(e, dict) and e.get("event_type") == "TURN"]
    if isinstance(transcript, list) and len(turns) != len(transcript):
        errors.append(
            f"TURN event count ({len(turns)}) != transcript length ({len(transcript)})"
        )
    used_turns = payload.get("used_candidate_turns")
    if isinstance(used_turns, int) and isinstance(transcript, list) and used_turns != len(transcript):
        errors.append(
            f"used_candidate_turns ({used_turns}) != transcript length ({len(transcript)})"
        )
    outcome = payload.get("terminal_outcome")
    if outcome not in ("NO_FINDING", "PROPOSED_FINDING", "INCONCLUSIVE", "FAILURE"):
        errors.append(f"unknown terminal_outcome '{outcome}'")

    return _report(payload, events=events, errors=errors)


def _report(
    payload: dict[str, Any], *, events: list, errors: list[str]
) -> dict[str, Any]:
    return {
        "trace_id": payload.get("trace_id", ""),
        "run_id": payload.get("run_id", ""),
        "terminal_outcome": payload.get("terminal_outcome"),
        "event_count": len(events),
        "complete": not errors,
        "errors": errors,
    }


__all__ = ["replay_trace"]
