from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from packages.evaluation.planning import build_repeatability_plan, build_security_run_plan
from scripts.contracts import Contracts

ROOT = Path(__file__).resolve().parents[3]


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _inputs():
    protocol = _read(ROOT / "data/heldout/protocol.json")
    scenarios = _read(ROOT / "data/heldout/private/scenarios.json")
    transcripts = _read(ROOT / "data/heldout/private/repeatability_transcripts.json")
    return protocol, scenarios, transcripts


def test_security_plan_has_80_matrix_plus_40_extra_and_matched_cells():
    protocol, scenarios, _ = _inputs()
    plan = build_security_run_plan(protocol, scenarios)
    assert plan["planned_runs"] == 120
    assert plan["matrix_runs"] == 80
    assert plan["extra_repeat_runs"] == 40
    assert len(plan["entries"]) == len({row["plan_id"] for row in plan["entries"]}) == 120
    assert sum(row["replicate_index"] == 0 for row in plan["entries"]) == 80
    assert sum(row["replicate_index"] > 0 for row in plan["entries"]) == 40
    contracts = Contracts(ROOT)
    for row in plan["entries"]:
        contracts.validate("RunCreate", row["run_create"])
    grouped = {}
    for row in plan["entries"]:
        grouped.setdefault((row["scenario_id"], row["replicate_index"]), []).append(row)
    for rows in grouped.values():
        assert {(r["method"], r["target_version"]) for r in rows} == {
            ("ADAPTIVE", "vulnerable-v1"),
            ("ADAPTIVE", "hardened-v1"),
            ("FIXED", "vulnerable-v1"),
            ("FIXED", "hardened-v1"),
        }
        assert len({json.dumps(r["run_create"]["limits"], sort_keys=True) for r in rows}) == 1
        assert (
            len({json.dumps(r["run_create"]["model_settings"], sort_keys=True) for r in rows}) == 1
        )


def test_repeatability_is_separate_100_invocation_ledger():
    protocol, _, transcripts = _inputs()
    plan = build_repeatability_plan(protocol["repeatability"], transcripts)
    assert plan["planned_scoring_invocations"] == 100
    assert len(plan["entries"]) == len({row["score_plan_id"] for row in plan["entries"]}) == 100
    assert all(row["session_id"] is None for row in plan["entries"])


def test_repeatability_protocol_must_keep_targets_and_ledger_separate():
    protocol, _, transcripts = _inputs()
    changed_targets = copy.deepcopy(protocol["repeatability"])
    changed_targets["targets"] = ["vulnerable-v1"]
    with pytest.raises(ValueError, match="targets differ"):
        build_repeatability_plan(changed_targets, transcripts)
    combined = copy.deepcopy(protocol["repeatability"])
    combined["scoring_invocations_are_separate"] = False
    with pytest.raises(ValueError, match="separate ledger"):
        build_repeatability_plan(combined, transcripts)


def test_security_count_and_repeat_accounting_fail_closed():
    protocol, scenarios, _ = _inputs()
    missing = copy.deepcopy(protocol)
    missing["heldout_scenario_ids"] = missing["heldout_scenario_ids"][:-1]
    with pytest.raises(ValueError, match="exactly 20"):
        build_security_run_plan(missing, scenarios[:-1])
    changed = copy.deepcopy(protocol)
    changed["extra_repeats_per_cell"] = 3
    with pytest.raises(ValueError, match="exactly two"):
        build_security_run_plan(changed, scenarios)


def test_plan_is_deterministic():
    protocol, scenarios, transcripts = _inputs()
    assert build_security_run_plan(protocol, scenarios) == build_security_run_plan(
        copy.deepcopy(protocol), copy.deepcopy(scenarios)
    )
    assert build_repeatability_plan(
        protocol["repeatability"], transcripts
    ) == build_repeatability_plan(
        copy.deepcopy(protocol["repeatability"]), copy.deepcopy(transcripts)
    )
