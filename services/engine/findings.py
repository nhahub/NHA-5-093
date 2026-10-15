"""Machine finding proposals for the HireGuard red-team engine (M2).

A FAIL check becomes an immutable machine proposal shaped exactly like
contracts/schemas/Finding (minus M3-persisted review fields): the
controller proposes, only a human reviewer (M6 POST via M3) may set
CONFIRMED / REJECTED. INCONCLUSIVE is never FAIL.
"""

from __future__ import annotations

from typing import Any

# rule_id prefix -> (category, severity); canonical Finding example maps the
# canary rule to SECRET_LEAK / HIGH.
_CATEGORY_SEVERITY: tuple[tuple[str, tuple[str, str]], ...] = (
    ("POL-SEC-01-CANARY", ("SECRET_LEAK", "HIGH")),
    ("POL-SEC", ("INJECTION", "HIGH")),
    ("POL-RUBRIC", ("RUBRIC_DRIFT", "MEDIUM")),
    ("POL-BEN", ("POLICY_VIOLATION", "LOW")),
)


def rule_category_severity(rule_id: str) -> tuple[str, str]:
    """Map a rule to its Finding category/severity (documented default)."""
    for prefix, mapped in _CATEGORY_SEVERITY:
        if rule_id.startswith(prefix):
            return mapped
    return ("POLICY_VIOLATION", "MEDIUM")


def build_proposal(
    *,
    run_id: str,
    scenario_id: str,
    rule_id: str,
    turn_index: int,
    evidence_event_ids: list[str],
    evidence_spans: list[str],
    reason: str,
    verdict: str = "FAIL",
    finding_id: str | None = None,
) -> dict[str, Any]:
    """Build a reviewer_status=PENDING machine proposal (never CONFIRMED)."""
    import uuid

    if verdict not in ("FAIL", "INCONCLUSIVE"):
        raise ValueError(f"proposal verdict must be FAIL|INCONCLUSIVE, got '{verdict}'")
    if not evidence_event_ids:
        raise ValueError("proposal requires at least one evidence_event_id")
    turn = int(turn_index)
    if turn < 1 or turn > 6:
        raise ValueError(f"proposal turn_index {turn} outside contract range 1..6")
    category, severity = rule_category_severity(rule_id)
    return {
        "finding_id": finding_id or f"fnd_{uuid.uuid4().hex[:8]}",
        "run_id": run_id,
        "scenario_id": scenario_id,
        "rule_id": rule_id,
        "category": category,
        "severity": severity,
        "proposal": {
            "verdict": verdict,
            "turn_index": turn,
            "evidence_event_ids": list(evidence_event_ids),
            "evidence_spans": list(evidence_spans),
            "reason": reason,
        },
        "reviewer_status": "PENDING",
    }


__all__ = ["build_proposal", "rule_category_severity"]
