import hashlib
from .models import CheckResult, PolicyRule

def _category(rule_id: str) -> str:
    return {"POL-SEC": "SECRET_LEAK", "POL-INJ": "INJECTION", "POL-RUB": "RUBRIC_DRIFT"}.get(rule_id[:7], "POLICY_VIOLATION")

def to_finding(result: CheckResult, rule: PolicyRule, scenario_id: str, *, include_inconclusive: bool = False):
    """Machine proposal only. reviewer_status is always PENDING; a human review event changes it (M3)."""
    if result.rule_id != rule.rule_id:
        raise ValueError("result/rule mismatch")
    if result.result == "PASS" or (result.result == "INCONCLUSIVE" and not include_inconclusive):
        return None
    if not result.evidence_event_ids:
        raise ValueError("a finding must cite at least one evidence event (AC-03)")
    return {
        "finding_id": "fnd_" + hashlib.sha256(result.check_id.encode()).hexdigest()[:8],
        "run_id": result.run_id,
        "scenario_id": scenario_id,
        "rule_id": rule.rule_id,
        "category": _category(rule.rule_id),
        "severity": rule.severity,
        "proposal": {
            "verdict": result.result,
            "turn_index": result.turn_index,
            "evidence_event_ids": list(result.evidence_event_ids),
            "evidence_spans": list(result.evidence_spans),
            "reason": result.reason,
        },
        "reviewer_status": "PENDING",
    }
