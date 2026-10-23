"""M5 merge regressions using canonical stored records, not simplified reports."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from packages.evaluation import MetricsService, analyze_evaluation
from packages.evaluation.analysis_validation import timestamp
from packages.evaluation.metrics import _latest_reviews
from scripts.contracts import Contracts

ROOT = Path(__file__).resolve().parents[3]


def bundle():
    return json.loads(
        (ROOT / "packages/evaluation/fixtures/sample_evaluation_input.json").read_text(
            encoding="utf-8"
        )
    )


@pytest.mark.parametrize(
    "field,value",
    [("method", "FIXED"), ("target_version", "hardened-v1"), ("scenario_id", "scn_other")],
)
def test_plan_must_match_stored_run(field, value):
    value_bundle = bundle()
    value_bundle["planned_runs"][0][field] = value
    with pytest.raises(ValueError, match="planned entry differs"):
        analyze_evaluation(value_bundle)


@pytest.mark.parametrize(
    "record,field,value",
    [
        ("runs", "used_total_tokens", -1),
        ("reviews", "decision", "AUTO_APPROVED"),
        ("runs", "status", "SUCCESS"),
    ],
)
def test_canonical_records_are_validated_at_analysis_boundary(record, field, value):
    data = bundle()
    data[record][0][field] = value
    with pytest.raises(ValueError):
        analyze_evaluation(data)


def test_duplicate_plan_and_immutable_configuration_are_rejected():
    data = bundle()
    data["planned_runs"][1]["plan_id"] = data["planned_runs"][0]["plan_id"]
    with pytest.raises(ValueError, match="duplicate plan_id"):
        analyze_evaluation(data)
    data = bundle()
    data["planned_runs"][0]["run_create"] = copy.deepcopy(data["runs"][0]["config"])
    data["planned_runs"][0]["run_create"]["model_settings"]["seed"] += 1
    with pytest.raises(ValueError, match="immutable configuration"):
        analyze_evaluation(data)


@pytest.mark.parametrize("kind", ["missing", "foreign", "candidate", "span", "scenario"])
def test_findings_need_matching_target_evidence(kind):
    data = bundle()
    finding = data["findings"][0]
    if kind == "missing":
        finding["proposal"]["evidence_event_ids"] = ["evt_ffffffffffff"]
    elif kind == "foreign":
        finding["proposal"]["evidence_event_ids"] = [data["events"][1]["event_id"]]
    elif kind == "candidate":
        data["events"][0]["actor"] = "AGENT"
    elif kind == "span":
        finding["proposal"]["evidence_spans"] = ["target_response[0:99999]"]
    else:
        finding["scenario_id"] = "scn_other"
    with pytest.raises(ValueError):
        analyze_evaluation(data)


def test_missing_usage_cannot_be_reported_as_complete_efficiency_evidence():
    data = bundle()
    del data["events"][0]["data"]["usage"]
    with pytest.raises(ValueError):
        analyze_evaluation(data)


def test_discovery_over_one_requires_methodology_decision():
    data = bundle()
    for index in range(3):
        finding = copy.deepcopy(data["findings"][0])
        finding["finding_id"] = f"fnd_{index + 16:08x}"
        review = copy.deepcopy(data["reviews"][0])
        review.update(finding_id=finding["finding_id"], review_event_id=f"review_extra_{index}")
        data["findings"].append(finding)
        data["reviews"].append(review)
    with pytest.raises(ValueError, match="numerator exceeds denominator"):
        analyze_evaluation(data)


def test_reviews_use_actual_utc_instants_and_reject_conflicting_ties():
    reviews = bundle()["reviews"][:1]
    earlier = copy.deepcopy(reviews[0])
    earlier.update(
        review_event_id="earlier", reviewed_at="2026-10-20T14:00:00+04:00", decision="REJECTED"
    )
    later = copy.deepcopy(reviews[0])
    later.update(review_event_id="later", reviewed_at="2026-10-20T10:01:00Z")
    assert timestamp(earlier["reviewed_at"]) < timestamp(later["reviewed_at"])
    assert _latest_reviews([later, earlier])[later["finding_id"]] == later
    tied = copy.deepcopy(later)
    tied.update(
        review_event_id="tied", decision="REJECTED", reviewed_at="2026-10-20T11:01:00+01:00"
    )
    for rows in ([tied, later], [later, tied]):
        with pytest.raises(ValueError, match="indistinguishable ordering"):
            _latest_reviews(rows)


@pytest.mark.parametrize(
    "field,value",
    [
        ("evaluated_transcript_hash", "f" * 64),
        ("rubric_version", "different"),
        ("role_id", "different"),
    ],
)
def test_repeated_scoring_requires_same_transcript_and_configuration(field, value):
    data = bundle()
    data["repeatability"]["samples"][1]["score"][field] = value
    with pytest.raises(ValueError, match="inconsistent repeatability"):
        analyze_evaluation(data)


def test_planned_scoring_inventory_detects_entirely_missing_groups():
    data = bundle()
    repeat = data["repeatability"]
    repeat["planned_entries"] = [
        {
            "score_plan_id": f"score_{row['score']['session_id']}",
            "transcript_id": row["transcript_id"],
            "target_version": row["target_version"],
            "repetition_index": row["repetition_index"],
            "transcript_sha256": row["score"]["evaluated_transcript_hash"],
            "session_id": row["score"]["session_id"],
        }
        for row in repeat["samples"]
    ]
    extra = copy.deepcopy(repeat["planned_entries"][0])
    extra.update(score_plan_id="missing_group", transcript_id="rpt_missing", session_id=None)
    repeat["planned_entries"].append(extra)
    result = analyze_evaluation(data)
    assert any(
        "rpt_missing" in item and "0 of 5" in item
        for item in result["report_summary"]["repeatability_evaluation"]["limitations"]
    )
    repeat["planned_entries"][0]["transcript_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="planned transcript"):
        analyze_evaluation(data)


def test_incomplete_repeats_and_unproven_prices_remain_visible():
    data = bundle()
    data["repeatability"]["samples"].pop()
    result = analyze_evaluation(data)
    assert result["report_summary"]["estimated_api_cost_usd"] is None
    assert any(
        "4 of 5" in item
        for item in result["report_summary"]["repeatability_evaluation"]["limitations"]
    )
    assert result["source_ids"]["score_session_ids"]
    assert result["source_ids"]["transcript_hashes"]


def test_canonical_metrics_service_uses_immutable_context():
    data = bundle()
    batch_id = data["batch_id"]
    expected = analyze_evaluation(data)["report_summary"]
    service = MetricsService({batch_id: data})
    data["planned_runs"].clear()
    actual = service.aggregate_batch(batch_id, data["runs"], data["findings"], data["reviews"])
    assert actual == expected
    Contracts().validate("ReportSummary", actual)
    actual["limitations"].clear()
    assert (
        service.aggregate_batch(batch_id, data["runs"], data["findings"], data["reviews"])
        == expected
    )
    with pytest.raises(ValueError, match="context is missing"):
        service.aggregate_batch("missing", [], [], [])
