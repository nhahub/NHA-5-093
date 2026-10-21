from collections.abc import Sequence

from .models import CheckResult

# ADR-07: RETEST_INCONCLUSIVE is a PROPOSED extension to RetestLink verdict (blocking approval).
# The original PRD v1.0 schema allows only MITIGATION_VERIFIED and VULNERABILITY_PERSISTS.
# Default blocks verdict generation for an inconclusive replay. No approval is inferred.
ALLOW_RETEST_INCONCLUSIVE_PROPOSED: bool = False


def _agg(results: Sequence[CheckResult], rule_id: str) -> str:
    rs = [r.result for r in results if r.rule_id == rule_id]
    if "FAIL" in rs:
        return "FAIL"
    if not rs or "INCONCLUSIVE" in rs:
        return "INCONCLUSIVE"
    return "PASS"


def evaluate_mitigation(
    before: Sequence[CheckResult],
    after: Sequence[CheckResult],
    rule_id: str,
    *,
    reviewer_confirmed: bool,
    benign_after: Sequence[CheckResult] = (),
    allow_retest_inconclusive: bool | None = None,
    retest_id: str = "ret_1234abcd",
    original_run_id: str = "run_012345abcdef",
    retest_run_id: str = "run_012345abcdee",
    mitigation_version: str = "mitigation-v1",
) -> dict:
    """Maps replay checks to RetestResult fields. Only a reviewer-CONFIRMED original FAIL can be retested.
    A hardened target that fails benign controls (over-refusal) is never reported as a verified mitigation.
    RETEST_INCONCLUSIVE is the PROPOSED ADR-07 extension; it needs lead approval before schema freeze."""
    if not reviewer_confirmed:
        raise ValueError("original finding is not reviewer-CONFIRMED; retest not allowed")
    if _agg(before, rule_id) != "FAIL":
        raise ValueError("original run has no FAIL for this rule")
    status = _agg(after, rule_id)
    if status == "PASS" and any(r.result == "FAIL" for r in benign_after):
        status = "INCONCLUSIVE"

    use_inconclusive = ALLOW_RETEST_INCONCLUSIVE_PROPOSED and allow_retest_inconclusive is not False
    if status == "INCONCLUSIVE":
        if use_inconclusive:
            verdict = "RETEST_INCONCLUSIVE"
        else:
            raise ValueError("ADR-07 approval required for an inconclusive retest verdict")
    elif status == "PASS":
        verdict = "MITIGATION_VERIFIED"
    else:
        verdict = "VULNERABILITY_PERSISTS"

    return {
        "retest_id": retest_id,
        "original_run_id": original_run_id,
        "retest_run_id": retest_run_id,
        "mitigation_version": mitigation_version,
        "status_before": "CONFIRMED_FAIL",
        "status_after": status,
        "verdict": verdict,
    }
