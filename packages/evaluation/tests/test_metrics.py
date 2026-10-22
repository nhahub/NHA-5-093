from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from packages.evaluation.metrics import analyze_evaluation
from packages.evaluation.reporting import render_markdown
from scripts.contracts import Contracts

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "packages/evaluation/fixtures/sample_evaluation_input.json"


def _bundle():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_contracts_and_metric_denominators():
    bundle = _bundle()
    contracts = Contracts(ROOT)
    for name, rows in (
        ("RunDetail", bundle["runs"]),
        ("Finding", bundle["findings"]),
        ("ReviewReceipt", bundle["reviews"]),
        ("AuditEvent", bundle["events"]),
    ):
        for row in rows:
            contracts.validate(name, row)
    for row in bundle["dialect_scores"]:
        contracts.validate("ScoreResult", row["msa_score"])
        contracts.validate("ScoreResult", row["egy_score"])
    for row in bundle["repeatability"]["samples"]:
        contracts.validate("ScoreResult", row["score"])

    result = analyze_evaluation(bundle)
    summary = result["report_summary"]
    contracts.validate("ReportSummary", summary)
    assert summary["metric_denominators"] == {
        "completed_intended_violation_attempts": 3,
        "all_reviewed_flags": 3,
        "all_scheduled_runs": 4,
    }
    assert summary["confirmed_discovery_rate"] == pytest.approx(1 / 3)
    assert summary["finding_precision"] == pytest.approx(1 / 3)
    assert summary["false_positive_rate"] == pytest.approx(1 / 3)
    assert summary["completion_rate"] == pytest.approx(3 / 4)
    assert summary["failed_run_ids"] == ["run_eval_004"]
    assert summary["inconclusive_reviews"] == 1
    assert summary["tokens_total"] == 320
    assert summary["mean_latency_ms"] == 125
    assert summary["estimated_api_cost_usd"] == 0
    assert summary["dialect_evaluation"]["mean_score_delta"] == 0
    assert summary["repeatability_evaluation"]["pass_fail_flips"] == 1
    markdown = render_markdown(result)
    assert "Numerator" in markdown and "run_eval_004" in markdown


def test_zero_denominators_are_null_never_zero():
    bundle = {
        "batch_id": "batch_zero",
        "protocol_approval_status": "PROPOSED",
        "planned_runs": [
            {
                "plan_id": "plan_zero",
                "scenario_id": "scn_hold_secret_001",
                "family": "SECRET_LEAK",
                "intended_violation": True,
                "method": "ADAPTIVE",
                "target_version": "vulnerable-v1",
                "run_id": None,
            }
        ],
        "runs": [],
        "findings": [],
        "reviews": [],
        "events": [],
        "dialect_scores": [],
        "repeatability": {"expected_repeats_per_target": 5, "samples": []},
    }
    summary = analyze_evaluation(bundle)["report_summary"]
    assert summary["confirmed_discovery_rate"] is None
    assert summary["finding_precision"] is None
    assert summary["false_positive_rate"] is None
    assert summary["completion_rate"] == 0
    assert summary["mean_latency_ms"] is None
    assert summary["estimated_api_cost_usd"] is None


def test_failed_and_inconclusive_records_do_not_disappear():
    result = analyze_evaluation(_bundle())
    assert result["status_counts"] == {"COMPLETED": 3, "FAILED": 1}
    assert result["run_status_ids"]["FAILED"] == ["run_eval_004"]
    assert result["finding_status_counts"] == {
        "CONFIRMED": 1,
        "INCONCLUSIVE": 1,
        "REJECTED": 1,
    }
    assert result["report_summary"]["failed_runs"] == 1
    assert result["report_summary"]["inconclusive_reviews"] == 1
    assert result["report_summary"]["reviewed_flags"] == 3


def test_recomputation_is_deterministic_under_input_order_changes():
    original = _bundle()
    reordered = copy.deepcopy(original)
    for key in ("planned_runs", "runs", "findings", "reviews", "events", "dialect_scores"):
        reordered[key].reverse()
    reordered["repeatability"]["samples"].reverse()
    assert analyze_evaluation(original) == analyze_evaluation(reordered)


def test_duplicate_repeat_index_is_rejected():
    bundle = _bundle()
    duplicate = copy.deepcopy(bundle["repeatability"]["samples"][0])
    duplicate["score"]["session_id"] = "sess_duplicate"
    bundle["repeatability"]["samples"].append(duplicate)
    with pytest.raises(ValueError, match="duplicate repeat index"):
        analyze_evaluation(bundle)


def test_missing_price_makes_cost_null_and_reports_evidence_gap():
    bundle = _bundle()
    bundle["pricing_usd_per_million_tokens"] = {}
    result = analyze_evaluation(bundle)
    assert result["report_summary"]["estimated_api_cost_usd"] is None
    assert result["efficiency_evidence"]["unpriced_usage_events"] == 4


def test_pending_findings_and_cancelled_runs_are_reported_but_not_reviewed():
    bundle = _bundle()
    cancelled = copy.deepcopy(bundle["runs"][3])
    cancelled["run_id"] = "run_eval_005"
    cancelled["status"] = "CANCELLED"
    cancelled["outcome"] = None
    cancelled["finished_at"] = "2026-10-20T10:04:02Z"
    cancelled["termination_reason"] = "USER_CANCELLED"
    bundle["runs"].append(cancelled)
    bundle["planned_runs"].append(
        {
            "plan_id": "plan_sample_005",
            "scenario_id": "scn_b_secret_003",
            "family": "SECRET_LEAK",
            "intended_violation": True,
            "method": "ADAPTIVE",
            "target_version": "vulnerable-v1",
            "run_id": "run_eval_005",
        }
    )
    pending = copy.deepcopy(bundle["findings"][0])
    pending["finding_id"] = "fnd_00000004"
    pending["run_id"] = "run_eval_005"
    pending["scenario_id"] = "scn_b_secret_003"
    pending["reviewer_status"] = "PENDING"
    bundle["findings"].append(pending)

    result = analyze_evaluation(bundle)
    assert result["status_counts"]["CANCELLED"] == 1
    assert result["run_status_ids"]["CANCELLED"] == ["run_eval_005"]
    assert result["finding_status_counts"]["PENDING"] == 1
    assert result["report_summary"]["reviewed_flags"] == 3


def test_duplicate_dialect_pair_and_reused_score_sessions_are_rejected():
    duplicate_pair = _bundle()
    duplicate_pair["dialect_scores"].append(copy.deepcopy(duplicate_pair["dialect_scores"][0]))
    with pytest.raises(ValueError, match="duplicate dialect pair_id"):
        analyze_evaluation(duplicate_pair)

    reused_session = _bundle()
    reused_session["repeatability"]["samples"][1]["score"]["session_id"] = "sess_rv_01"
    with pytest.raises(ValueError, match="reuse a session_id"):
        analyze_evaluation(reused_session)
