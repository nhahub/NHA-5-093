"""Validate stored inputs and their links before computing any aggregate."""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from scripts.contracts import Contracts


@lru_cache(maxsize=1)
def contracts() -> Contracts:
    return Contracts()


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("review timestamp must include a UTC offset")
    return parsed.astimezone(UTC)


def unique(rows: list[dict], field: str) -> None:
    values = [row[field] for row in rows]
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"empty or invalid {field}")
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {field}")


def _finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite analysis value")
    if isinstance(value, dict):
        for item in value.values():
            _finite(item)
    elif isinstance(value, list):
        for item in value:
            _finite(item)


def validate_bundle(bundle: dict[str, Any]) -> None:
    _finite(bundle)
    schemas = contracts()
    for name, key, identifier in (
        ("RunDetail", "runs", "run_id"),
        ("Finding", "findings", "finding_id"),
        ("ReviewReceipt", "reviews", "review_event_id"),
        ("AuditEvent", "events", "event_id"),
    ):
        rows = bundle.get(key, [])
        if not isinstance(rows, list):
            raise ValueError(f"{key} must be a list")
        for row in rows:
            schemas.validate(name, row)
        unique(rows, identifier)
    planned = bundle["planned_runs"]
    unique(planned, "plan_id")
    runs = {row["run_id"]: row for row in bundle["runs"]}
    plans = {}
    for entry in planned:
        if type(entry["intended_violation"]) is not bool:
            raise ValueError("intended_violation must be a boolean")
        if entry["family"] not in schemas.schemas["Scenario"]["properties"]["family"]["enum"]:
            raise ValueError("unknown planned family")
        if entry["method"] not in {"ADAPTIVE", "FIXED"} or entry["target_version"] not in {
            "vulnerable-v1",
            "hardened-v1",
        }:
            raise ValueError("unknown planned method or target")
        if "run_create" in entry:
            schemas.validate("RunCreate", entry["run_create"])
            if any(
                entry[field] != entry["run_create"][field]
                for field in ("scenario_id", "method", "target_version")
            ):
                raise ValueError("planned immutable configuration differs from entry")
        run_id = entry.get("run_id")
        if run_id is None:
            continue
        if run_id in plans:
            raise ValueError("a stored run_id is linked to multiple planned entries")
        plans[run_id] = entry
        if run_id not in runs:
            raise ValueError("planned run references missing RunDetail")
        config = runs[run_id]["config"]
        if any(
            entry[field] != config[field] for field in ("scenario_id", "method", "target_version")
        ):
            raise ValueError("planned entry differs from stored run configuration")
        if "run_create" in entry and entry["run_create"] != config:
            raise ValueError("planned immutable configuration differs from stored run")
    if set(plans) != set(runs):
        raise ValueError("planned run links and analyzed RunDetail IDs differ")

    events = {row["event_id"]: row for row in bundle.get("events", [])}
    sequences = set()
    for event in events.values():
        if event["run_id"] not in runs:
            raise ValueError("event references unanalyzed run")
        key = (event["run_id"], event["seq"])
        if key in sequences:
            raise ValueError("duplicate event sequence within run")
        sequences.add(key)
        usage = event["data"].get("usage")
        if (
            usage is not None
            and usage["total_tokens"] != usage["input_tokens"] + usage["output_tokens"]
        ):
            raise ValueError("inconsistent event usage")
    for finding in bundle["findings"]:
        run_id = finding["run_id"]
        if run_id not in runs or finding["scenario_id"] != runs[run_id]["config"]["scenario_id"]:
            raise ValueError("finding references a different run/scenario")
        proposal = finding["proposal"]
        linked = []
        if len(set(proposal["evidence_event_ids"])) != len(proposal["evidence_event_ids"]):
            raise ValueError("duplicate finding evidence link")
        for identifier in proposal["evidence_event_ids"]:
            event = events.get(identifier)
            if (
                event is None
                or event["run_id"] != run_id
                or event["event_type"] != "TURN"
                or event["actor"] != "TARGET"
                or event["turn_index"] != proposal["turn_index"]
            ):
                raise ValueError(
                    "finding evidence is missing, foreign, or not a matching target TURN"
                )
            linked.append(event)
        if proposal["verdict"] == "FAIL" and not proposal["evidence_spans"]:
            raise ValueError("failed proposal needs target evidence spans")
        for span in proposal["evidence_spans"]:
            match = re.fullmatch(r"target_response\[(\d+):(\d+)\]", span)
            if not match or not all(
                0 <= int(match[1]) < int(match[2]) <= len(event["data"]["target_response"])
                for event in linked
            ):
                raise ValueError("invalid target evidence span")
    finding_ids = {row["finding_id"] for row in bundle["findings"]}
    for review in bundle["reviews"]:
        if review["finding_id"] not in finding_ids:
            raise ValueError("review references unknown finding")
        timestamp(review["reviewed_at"])
        if not review["reviewer_id"].strip():
            raise ValueError("reviewer identity is missing")
    _validate_scores(bundle)


def _validate_scores(bundle: dict[str, Any]) -> None:
    schemas = contracts()
    sessions = set()
    identities = {}
    pairs = bundle.get("dialect_scores", [])
    unique(pairs, "pair_id")
    repeatability = bundle.get("repeatability", {})
    samples = repeatability.get("samples", [])
    expected = repeatability.get("expected_repeats_per_target", 0)
    if type(expected) is not int or expected < 0 or (samples and expected == 0):
        raise ValueError("invalid expected repeat count")
    scores = []
    for pair in pairs:
        msa, egy = pair["msa_score"], pair["egy_score"]
        schemas.validate("ScoreResult", msa)
        schemas.validate("ScoreResult", egy)
        if any(msa[field] != egy[field] for field in ("role_id", "rubric_version")):
            raise ValueError("incompatible dialect scoring role/rubric")
        scores.extend([msa, egy])
    for row in samples:
        schemas.validate("ScoreResult", row["score"])
        if row["target_version"] not in {"vulnerable-v1", "hardened-v1"}:
            raise ValueError("unknown scoring target")
        index = row["repetition_index"]
        if type(index) is not int or not 1 <= index <= expected:
            raise ValueError("repeat index outside planned range")
        score = row["score"]
        identity = tuple(
            score[field] for field in ("evaluated_transcript_hash", "role_id", "rubric_version")
        )
        previous = identities.setdefault(row["transcript_id"], identity)
        if identity != previous:
            raise ValueError("inconsistent repeatability transcript hash or scoring role/rubric")
        scores.append(score)
    for score in scores:
        schemas.validate("ScoreResult", score)
        if score["session_id"] in sessions:
            raise ValueError("score records reuse a session_id")
        sessions.add(score["session_id"])
    planned = repeatability.get("planned_entries")
    if planned is not None:
        unique(planned, "score_plan_id")
        cells = {}
        transcript_hashes = {}
        for row in planned:
            key = (row["transcript_id"], row["target_version"], row["repetition_index"])
            if (
                key in cells
                or row["target_version"] not in {"vulnerable-v1", "hardened-v1"}
                or type(row["repetition_index"]) is not int
                or not 1 <= row["repetition_index"] <= expected
            ):
                raise ValueError("invalid or duplicate planned scoring cell")
            if not re.fullmatch(r"[a-f0-9]{64}", row["transcript_sha256"]):
                raise ValueError("invalid planned transcript hash")
            previous = transcript_hashes.setdefault(row["transcript_id"], row["transcript_sha256"])
            if previous != row["transcript_sha256"]:
                raise ValueError("inconsistent planned transcript hash")
            cells[key] = row
        for row in samples:
            key = (row["transcript_id"], row["target_version"], row["repetition_index"])
            cell = cells.get(key)
            if (
                cell is None
                or row["score"]["evaluated_transcript_hash"] != cell["transcript_sha256"]
            ):
                raise ValueError("score differs from planned transcript/cell")
            if (
                cell.get("session_id") is not None
                and cell["session_id"] != row["score"]["session_id"]
            ):
                raise ValueError("score differs from planned session")
