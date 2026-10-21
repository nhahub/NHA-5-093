"""Compatibility helper delegates metadata and finding construction to M4."""

from packages.security import CheckResult, load_rules, to_finding


def build_proposal(
    *,
    run_id,
    scenario_id,
    rule_id,
    turn_index,
    evidence_event_ids,
    evidence_spans,
    reason,
    verdict="FAIL",
    finding_id=None,
):
    rule = next(r for r in load_rules() if r.rule_id == rule_id)
    result = CheckResult(
        check_id=f"{run_id}:{turn_index}:{rule_id}",
        run_id=run_id,
        turn_index=turn_index,
        rule_id=rule_id,
        result=verdict,
        evidence_event_ids=evidence_event_ids,
        evidence_spans=evidence_spans,
        reason=reason,
        checker_version="m4-checks-1.0.0",
    )
    finding = to_finding(result, rule, scenario_id, include_inconclusive=True)
    if finding_id is not None:
        finding["finding_id"] = finding_id
    return finding
