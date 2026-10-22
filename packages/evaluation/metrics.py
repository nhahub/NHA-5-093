"""Deterministic, ID-backed M5 metric recomputation."""

from __future__ import annotations

import copy
import statistics
from collections import Counter, defaultdict
from typing import Any


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _latest_reviews(reviews: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    seen_event_ids: set[str] = set()
    for row in reviews:
        event_id = row["review_event_id"]
        if event_id in seen_event_ids:
            raise ValueError(f"duplicate review_event_id: {event_id}")
        seen_event_ids.add(event_id)
        current = latest.get(row["finding_id"])
        if current is None or (row["reviewed_at"], event_id) > (
            current["reviewed_at"],
            current["review_event_id"],
        ):
            latest[row["finding_id"]] = row
    return latest


def _dialect_metrics(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    pair_ids = [row["pair_id"] for row in rows]
    if len(pair_ids) != len(set(pair_ids)):
        raise ValueError("duplicate dialect pair_id")
    session_ids = [
        score["session_id"]
        for row in rows
        for score in (row["msa_score"], row["egy_score"])
    ]
    if len(session_ids) != len(set(session_ids)):
        raise ValueError("dialect scores reuse a session_id")
    details = []
    for row in sorted(rows, key=lambda item: item["pair_id"]):
        msa = float(row["msa_score"]["score_total"])
        egy = float(row["egy_score"]["score_total"])
        details.append(
            {
                "pair_id": row["pair_id"],
                "msa_session_id": row["msa_score"]["session_id"],
                "egy_session_id": row["egy_score"]["session_id"],
                "msa_score": msa,
                "egy_score": egy,
                "score_delta_msa_minus_egy": msa - egy,
            }
        )
    mean = (
        statistics.fmean(row["score_delta_msa_minus_egy"] for row in details) if details else None
    )
    summary = {
        "pairs_evaluated": len(details),
        "mean_score_delta": mean,
        "limitations": [
            "Paired dialect analysis is exploratory and requires two-reviewer semantic-equivalence approval."
        ],
    }
    return summary, details


def _repeatability_metrics(value: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    samples = value.get("samples", [])
    expected = int(value.get("expected_repeats_per_target", 0))
    session_ids = [row["score"]["session_id"] for row in samples]
    if len(session_ids) != len(set(session_ids)):
        raise ValueError("repeatability scores reuse a session_id")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in samples:
        grouped[(row["transcript_id"], row["target_version"])].append(row)
    details = []
    for (transcript_id, target), rows in sorted(grouped.items()):
        indices = [int(row["repetition_index"]) for row in rows]
        if len(indices) != len(set(indices)):
            raise ValueError(f"duplicate repeat index: {transcript_id}/{target}")
        scores = [float(row["score"]["score_total"]) for row in rows]
        passes = [bool(row["score"]["pass"]) for row in rows]
        details.append(
            {
                "transcript_id": transcript_id,
                "target_version": target,
                "observed_repeats": len(rows),
                "expected_repeats": expected,
                "mean": statistics.fmean(scores),
                "stddev_population": statistics.pstdev(scores),
                "minimum": min(scores),
                "maximum": max(scores),
                "pass_fail_flip": len(set(passes)) > 1,
                "session_ids": sorted(row["score"]["session_id"] for row in rows),
            }
        )
    incomplete = [
        f"{row['transcript_id']}/{row['target_version']} has {row['observed_repeats']} of {expected} repeats"
        for row in details
        if row["observed_repeats"] != expected
    ]
    summary = {
        "transcripts_evaluated": len({row["transcript_id"] for row in details}),
        "repeats_per_target": expected,
        "mean_stddev": statistics.fmean(row["stddev_population"] for row in details)
        if details
        else None,
        "pass_fail_flips": sum(row["pass_fail_flip"] for row in details),
        "limitations": incomplete
        or ["Population standard deviation is used; final protocol approval remains required."],
    }
    return summary, details


def _event_metrics(
    runs: list[dict[str, Any]], events: list[dict[str, Any]], pricing: dict[str, Any]
) -> tuple[float | None, float | None, dict[str, Any]]:
    run_ids = {row["run_id"] for row in runs}
    latency_by_run: dict[str, int] = defaultdict(int)
    cost_total = 0.0
    cost_events = 0
    unpriced_events = 0
    seen_events: set[str] = set()
    for event in events:
        if event["event_id"] in seen_events:
            raise ValueError(f"duplicate event_id: {event['event_id']}")
        seen_events.add(event["event_id"])
        if event["run_id"] not in run_ids:
            raise ValueError(f"event references unanalyzed run: {event['run_id']}")
        data = event.get("data", {})
        usage = data.get("usage")
        if event["event_type"] == "TURN":
            latency_by_run[event["run_id"]] += int(data["latency_ms"])
            model_id = data.get("model_id")
        elif event["event_type"] == "DECISION":
            run = next(row for row in runs if row["run_id"] == event["run_id"])
            model_id = run["config"]["model_settings"]["model_id"]
        else:
            continue
        if not isinstance(usage, dict):
            continue
        rate = pricing.get(model_id)
        if rate is None:
            unpriced_events += 1
            continue
        cost_total += (
            usage["input_tokens"] * float(rate["input_per_million"])
            + usage["output_tokens"] * float(rate["output_per_million"])
        ) / 1_000_000
        cost_events += 1
    mean_latency = statistics.fmean(latency_by_run.values()) if latency_by_run else None
    cost = cost_total if cost_events and not unpriced_events else None
    return (
        mean_latency,
        cost,
        {
            "latency_run_count": len(latency_by_run),
            "priced_usage_events": cost_events,
            "unpriced_usage_events": unpriced_events,
        },
    )


def analyze_evaluation(bundle: dict[str, Any]) -> dict[str, Any]:
    """Recompute report and detailed tables entirely from linked stored IDs."""
    planned = copy.deepcopy(bundle["planned_runs"])
    runs = copy.deepcopy(bundle["runs"])
    findings = copy.deepcopy(bundle["findings"])
    reviews = copy.deepcopy(bundle["reviews"])
    events = copy.deepcopy(bundle.get("events", []))
    run_map = {row["run_id"]: row for row in runs}
    if len(run_map) != len(runs):
        raise ValueError("duplicate run_id")
    finding_map = {row["finding_id"]: row for row in findings}
    if len(finding_map) != len(findings):
        raise ValueError("duplicate finding_id")
    for finding in findings:
        if finding["run_id"] not in run_map:
            raise ValueError(f"finding references unanalyzed run: {finding['finding_id']}")

    linked_run_ids = [row["run_id"] for row in planned if row.get("run_id")]
    if len(linked_run_ids) != len(set(linked_run_ids)):
        raise ValueError("a stored run_id is linked to multiple planned entries")
    if set(linked_run_ids) != set(run_map):
        raise ValueError("planned run links and analyzed RunDetail IDs differ")
    latest = _latest_reviews(reviews)
    for finding_id, review in latest.items():
        finding = finding_map.get(finding_id)
        if finding is None:
            raise ValueError(f"review references unknown finding: {finding_id}")
        if finding["reviewer_status"] != review["decision"]:
            raise ValueError(f"finding review projection mismatch: {finding_id}")
    for finding in findings:
        if finding["finding_id"] not in latest and finding["reviewer_status"] != "PENDING":
            raise ValueError(f"non-pending finding has no review event: {finding['finding_id']}")

    completed_ids = {row["run_id"] for row in runs if row["status"] == "COMPLETED"}
    failed_ids = sorted(row["run_id"] for row in runs if row["status"] == "FAILED")
    status_counts = dict(sorted(Counter(row["status"] for row in runs).items()))
    run_status_ids = {
        status: sorted(row["run_id"] for row in runs if row["status"] == status)
        for status in sorted(status_counts)
    }
    intended_completed = [
        row for row in planned if row["intended_violation"] and row.get("run_id") in completed_ids
    ]
    reviewed_ids = set(latest)
    confirmed_ids = {fid for fid, row in latest.items() if row["decision"] == "CONFIRMED"}
    rejected_ids = {fid for fid, row in latest.items() if row["decision"] == "REJECTED"}
    inconclusive_ids = {fid for fid, row in latest.items() if row["decision"] == "INCONCLUSIVE"}
    finding_status_counts = dict(
        sorted(Counter(row["reviewer_status"] for row in findings).items())
    )
    confirmed_discovery_ids = {
        fid
        for fid in confirmed_ids
        if finding_map[fid]["run_id"] in {row["run_id"] for row in intended_completed}
    }

    breakdowns = []
    keys = sorted({(row["method"], row["target_version"], row["family"]) for row in planned})
    for method, target, family in keys:
        cells = [
            row
            for row in planned
            if row["method"] == method
            and row["target_version"] == target
            and row["family"] == family
        ]
        denominator_ids = {
            row["run_id"]
            for row in cells
            if row["intended_violation"] and row.get("run_id") in completed_ids
        }
        numerator_ids = {
            fid for fid in confirmed_ids if finding_map[fid]["run_id"] in denominator_ids
        }
        breakdowns.append(
            {
                "method": method,
                "target_version": target,
                "family": family,
                "confirmed_findings": len(numerator_ids),
                "completed_intended_violation_attempts": len(denominator_ids),
                "confirmed_discovery_rate": _ratio(len(numerator_ids), len(denominator_ids)),
                "scheduled_runs": len(cells),
                "failed_runs": sum(
                    bool(row.get("run_id") and run_map[row["run_id"]]["status"] == "FAILED")
                    for row in cells
                ),
            }
        )

    per_method = []
    for method in ("ADAPTIVE", "FIXED"):
        for target in ("vulnerable-v1", "hardened-v1"):
            group_ids = {
                row["run_id"]
                for row in planned
                if row["method"] == method and row["target_version"] == target and row.get("run_id")
            }
            group_runs = [run_map[run_id] for run_id in sorted(group_ids)]
            per_method.append(
                {
                    "method": method,
                    "target_version": target,
                    "completed_runs": sum(row["status"] == "COMPLETED" for row in group_runs),
                    "confirmed_findings": sum(
                        finding_map[fid]["run_id"] in group_ids for fid in confirmed_ids
                    ),
                    "reviewed_flags": sum(
                        finding_map[fid]["run_id"] in group_ids for fid in reviewed_ids
                    ),
                    "tokens_total": sum(int(row["used_total_tokens"]) for row in group_runs),
                }
            )

    dialect_summary, dialect_details = _dialect_metrics(bundle.get("dialect_scores", []))
    repeat_summary, repeat_details = _repeatability_metrics(bundle.get("repeatability", {}))
    mean_latency, cost, efficiency_evidence = _event_metrics(
        runs, events, bundle.get("pricing_usd_per_million_tokens", {})
    )
    limitations = list(bundle.get("limitations", []))
    if bundle.get("protocol_approval_status") != "APPROVED":
        limitations.append("Evaluation protocol is not approved; outputs are illustrative only.")
    unlinked = len(planned) - len(linked_run_ids)
    if unlinked:
        limitations.append(f"{unlinked} planned runs do not yet have stored run IDs.")

    summary = {
        "batch_id": bundle["batch_id"],
        "run_ids": sorted(run_map),
        "failed_run_ids": failed_ids,
        "planned_runs": len(planned),
        "completed_runs": len(completed_ids),
        "failed_runs": len(failed_ids),
        "confirmed_findings": len(confirmed_ids),
        "reviewed_flags": len(reviewed_ids),
        "rejected_flags": len(rejected_ids),
        "inconclusive_reviews": len(inconclusive_ids),
        "metric_denominators": {
            "completed_intended_violation_attempts": len(intended_completed),
            "all_reviewed_flags": len(reviewed_ids),
            "all_scheduled_runs": len(planned),
        },
        "per_method": per_method,
        "confirmed_discovery_rate": _ratio(len(confirmed_discovery_ids), len(intended_completed)),
        "finding_precision": _ratio(len(confirmed_ids), len(reviewed_ids)),
        "false_positive_rate": _ratio(len(rejected_ids), len(reviewed_ids)),
        "tokens_total": sum(int(row["used_total_tokens"]) for row in runs),
        "completion_rate": _ratio(len(completed_ids), len(planned)),
        "estimated_api_cost_usd": cost,
        "mean_latency_ms": mean_latency,
        "dialect_evaluation": dialect_summary,
        "repeatability_evaluation": repeat_summary,
        "limitations": sorted(set(limitations)),
    }
    return {
        "report_summary": summary,
        "metric_numerators": {
            "confirmed_discovery_findings": len(confirmed_discovery_ids),
            "confirmed_reviewed_flags": len(confirmed_ids),
            "rejected_reviewed_flags": len(rejected_ids),
        },
        "confirmed_discovery_breakdowns": breakdowns,
        "dialect_pairs": dialect_details,
        "repeatability_groups": repeat_details,
        "status_counts": status_counts,
        "run_status_ids": run_status_ids,
        "finding_status_counts": finding_status_counts,
        "efficiency_evidence": efficiency_evidence,
        "source_ids": {
            "run_ids": sorted(run_map),
            "finding_ids": sorted(finding_map),
            "review_event_ids": sorted(row["review_event_id"] for row in reviews),
            "event_ids": sorted(row["event_id"] for row in events),
        },
    }
