"""Rubric-drift verifier: scoring output must follow the frozen RoleConfig rubric (POL-RUB-01-DRIFT).
Supports both schema-conforming arrays (criterion_id, max_points/points) and legacy dictionary formats."""

import hashlib

from .checks import CHECKER_VERSION
from .models import CheckResult

RULE_ID = "POL-RUB-01-DRIFT"


def _rubric_map(rubric):
    if (
        isinstance(rubric, dict)
        and rubric
        and all(isinstance(v, int | float) for v in rubric.values())
    ):
        return dict(rubric)
    if isinstance(rubric, list) and rubric:
        out = {}
        for c in rubric:
            if isinstance(c, dict):
                name = c.get("criterion_id", c.get("criterion", c.get("id")))
                mx = c.get("max_points", c.get("max_score"))
                if isinstance(name, str) and isinstance(mx, int | float):
                    out[name] = mx
                else:
                    return None
            else:
                return None
        return out
    return None


def _criterion_scores_map(cs):
    if isinstance(cs, dict) and cs and all(isinstance(v, int | float) for v in cs.values()):
        return dict(cs)
    if isinstance(cs, list) and cs:
        out = {}
        for item in cs:
            if isinstance(item, dict):
                cid = item.get("criterion_id", item.get("criterion", item.get("id")))
                pts = item.get("points", item.get("score"))
                if isinstance(cid, str) and isinstance(pts, int | float):
                    out[cid] = pts
                else:
                    return None
            else:
                return None
        return out
    return None


def check_rubric_drift(
    run_id: str, turn_index: int, event_id: str, score: dict, role: dict
) -> CheckResult:
    def res(result, reason):
        cid = (
            "chk_"
            + hashlib.sha256(
                f"{run_id}|{turn_index}|{RULE_ID}|{CHECKER_VERSION}".encode()
            ).hexdigest()[:8]
        )
        return CheckResult(
            check_id=cid,
            run_id=run_id,
            turn_index=turn_index,
            rule_id=RULE_ID,
            result=result,
            evidence_event_ids=[event_id],
            evidence_spans=[],
            checker_version=CHECKER_VERSION,
            reason=reason,
        )

    rub = _rubric_map(role.get("rubric"))
    cs = _criterion_scores_map(score.get("criterion_scores"))
    if (
        rub is None
        or cs is None
        or not isinstance(score.get("score_total"), int | float)
        or not isinstance(role.get("pass_threshold"), int | float)
        or "pass" not in score
    ):
        return res("INCONCLUSIVE", "score or rubric not in a checkable shape")
    if score.get("rubric_version") != role.get("version"):
        return res("FAIL", "rubric_version differs from the frozen role version")
    if set(cs) != set(rub):
        return res("FAIL", f"criteria differ from rubric: {sorted(set(cs) ^ set(rub))}")
    for k, v in cs.items():
        if not isinstance(v, int | float) or v < 0 or v > rub[k]:
            return res("FAIL", f"criterion {k!r} score {v!r} outside 0..{rub[k]}")
    if abs(sum(cs.values()) - score["score_total"]) > 1e-9:
        return res("FAIL", "score_total is not the sum of criterion_scores")
    if bool(score["pass"]) != (score["score_total"] >= role["pass_threshold"]):
        return res("FAIL", "pass flag inconsistent with pass_threshold")
    return res("PASS", "score follows the frozen rubric")
