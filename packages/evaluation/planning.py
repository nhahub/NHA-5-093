"""Deterministic M5 ledgers for the proposed security and scoring protocols."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

METHODS = ("ADAPTIVE", "FIXED")
TARGETS = ("vulnerable-v1", "hardened-v1")


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _plan_id(*parts: object) -> str:
    return "plan_" + hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12]


def build_security_run_plan(
    protocol: dict[str, Any], scenarios: list[dict[str, Any]]
) -> dict[str, Any]:
    """Expand the proposed 80 + 40 held-out security-run ledger.

    This function does not approve or execute the protocol.  It rejects any
    accounting other than the current proposal so deviations must be recorded
    through an approved protocol revision rather than silently accepted.
    """
    scenario_map = {row["scenario_id"]: row for row in scenarios}
    scenario_ids = list(protocol["heldout_scenario_ids"])
    repeats = list(protocol["extra_repeat_scenario_ids"])
    intended_ids = set(protocol["intended_violation_scenario_ids"])
    if len(scenario_ids) != 20 or len(set(scenario_ids)) != 20:
        raise ValueError("security protocol requires exactly 20 unique held-out scenarios")
    if set(scenario_ids) != set(scenario_map):
        raise ValueError("protocol and held-out scenario inventory differ")
    if len(repeats) != 5 or len(set(repeats)) != 5 or not set(repeats) <= set(scenario_ids):
        raise ValueError("extra-repeat selection must contain five unique held-out scenarios")
    if not intended_ids <= set(scenario_ids):
        raise ValueError("intended-violation inventory contains an unknown scenario")
    if protocol["methods"] != list(METHODS) or protocol["target_versions"] != list(TARGETS):
        raise ValueError("methods or targets differ from the proposed evaluation matrix")
    if protocol["extra_repeats_per_cell"] != 2:
        raise ValueError("the proposed ledger has exactly two extra repeats per selected cell")

    entries: list[dict[str, Any]] = []
    for scenario_id in scenario_ids:
        scenario = scenario_map[scenario_id]
        if scenario["split"] != "HELD_OUT":
            raise ValueError(f"non-held-out scenario in security ledger: {scenario_id}")
        replicate_indices = [0]
        if scenario_id in repeats:
            replicate_indices.extend(range(1, protocol["extra_repeats_per_cell"] + 1))
        for replicate_index in replicate_indices:
            for method in METHODS:
                for target in TARGETS:
                    run_create = {
                        "scenario_id": scenario_id,
                        "suite_version": scenario["suite_version"],
                        "method": method,
                        "target_version": target,
                        "limits": copy.deepcopy(protocol["limits"]),
                        "model_settings": copy.deepcopy(protocol["model_settings"]),
                    }
                    run_create["model_settings"]["seed"] = scenario["seed"]
                    entries.append(
                        {
                            "plan_id": _plan_id(
                                protocol["protocol_version"],
                                scenario_id,
                                method,
                                target,
                                replicate_index,
                            ),
                            "scenario_id": scenario_id,
                            "family": scenario["family"],
                            "intended_violation": scenario_id in intended_ids,
                            "method": method,
                            "target_version": target,
                            "replicate_index": replicate_index,
                            "run_id": None,
                            "run_create": run_create,
                        }
                    )
    if len(entries) != 120 or len({row["plan_id"] for row in entries}) != 120:
        raise AssertionError("security-run accounting must expand to 120 unique entries")
    _validate_matched_cells(entries)
    return {
        "protocol_version": protocol["protocol_version"],
        "approval_status": protocol["approval_status"],
        "comparable": False,
        "planned_runs": 120,
        "matrix_runs": 80,
        "extra_repeat_runs": 40,
        "entries": entries,
        "ledger_sha256": _canonical_hash(entries),
    }


def _validate_matched_cells(entries: list[dict[str, Any]]) -> None:
    groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for entry in entries:
        key = (entry["scenario_id"], entry["replicate_index"])
        groups.setdefault(key, []).append(entry)
    for key, rows in groups.items():
        if len(rows) != 4:
            raise ValueError(f"unmatched method/target cell: {key}")
        baseline = rows[0]["run_create"]
        for row in rows[1:]:
            candidate = row["run_create"]
            for field in ("scenario_id", "suite_version", "limits", "model_settings"):
                if candidate[field] != baseline[field]:
                    raise ValueError(f"unmatched {field} in cell {key}")


def build_repeatability_plan(
    protocol: dict[str, Any], transcripts: list[dict[str, Any]]
) -> dict[str, Any]:
    """Build the separate 10 transcripts × 5 repeats × 2 targets ledger."""
    if len(transcripts) != 10 or len({row["transcript_id"] for row in transcripts}) != 10:
        raise ValueError("repeatability protocol requires ten unique transcripts")
    repeats = int(protocol["repeats_per_target"])
    if repeats != 5:
        raise ValueError("source obligation requires five scoring repetitions per target")
    if protocol.get("targets") != list(TARGETS):
        raise ValueError("repeatability targets differ from the proposed two-target ledger")
    if protocol.get("scoring_invocations_are_separate") is not True:
        raise ValueError("repeatability scoring invocations must remain a separate ledger")
    entries = []
    for transcript in transcripts:
        for target in TARGETS:
            for repetition_index in range(1, repeats + 1):
                entries.append(
                    {
                        "score_plan_id": _plan_id(
                            protocol["protocol_version"],
                            transcript["transcript_id"],
                            target,
                            repetition_index,
                        ),
                        "transcript_id": transcript["transcript_id"],
                        "transcript_sha256": transcript["transcript_sha256"],
                        "target_version": target,
                        "repetition_index": repetition_index,
                        "session_id": None,
                    }
                )
    if len(entries) != 100:
        raise AssertionError("repeatability ledger must contain 100 scoring invocations")
    return {
        "protocol_version": protocol["protocol_version"],
        "approval_status": protocol["approval_status"],
        "comparable": False,
        "planned_scoring_invocations": 100,
        "entries": entries,
        "ledger_sha256": _canonical_hash(entries),
    }
