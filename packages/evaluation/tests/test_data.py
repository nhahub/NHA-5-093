from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from packages.evaluation.repository import ScenarioRepository, to_agent_view
from packages.evaluation.validation import DataValidationError, validate_data_tree

ROOT = Path(__file__).resolve().parents[3]


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_contracts_counts_split_isolation_and_repeatability_hashes():
    report = validate_data_tree(ROOT / "data")
    assert report["splits"]["development"]["scenario_count"] == 30
    assert report["splits"]["heldout"]["scenario_count"] == 20
    assert report["splits"]["demo"]["scenario_count"] == 2
    assert report["cross_split_paraphrase_overlap"] == 0
    assert report["cross_split_exact_prompt_overlap"] == 0
    assert report["repeatability_transcript_count"] == 10
    assert all(row["approval_status"] != "APPROVED" for row in report["splits"].values())


def test_unapproved_scenarios_cannot_execute_and_agent_view_is_allowlisted():
    repository = ScenarioRepository(ROOT / "data")
    with pytest.raises(PermissionError):
        repository.get_approved("scn_b_secret_001", "m5-suite-b-v0.1-proposed")
    scenario = _read(ROOT / "data/heldout/private/scenarios.json")[0]
    view = to_agent_view(scenario)
    assert set(view) == {
        "scenario_id",
        "suite_version",
        "family",
        "role_id",
        "objective",
        "persona_ref",
        "rule_ids",
    }
    assert not {"split", "expected_behavior", "fixed_prompts", "approved", "seed"} & set(view)
    for scenario in _read(ROOT / "data/heldout/private/scenarios.json"):
        public_text = json.dumps(to_agent_view(scenario), ensure_ascii=False).casefold()
        assert not any(
            marker in public_text for marker in ("held_out", "held-out", "heldout", "holdout")
        )


def test_paraphrase_group_leak_is_rejected(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(ROOT / "data", data)
    dev = _read(data / "development/manifest.json")
    held = _read(data / "heldout/manifest.json")
    held["records"][0]["paraphrase_group_id"] = dev["records"][0]["paraphrase_group_id"]
    _write(data / "heldout/manifest.json", held)
    with pytest.raises(DataValidationError, match="leaks across splits"):
        validate_data_tree(data)


def test_exact_prompt_leak_is_rejected(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(ROOT / "data", data)
    dev = _read(data / "development/scenarios.json")
    held = _read(data / "heldout/private/scenarios.json")
    held[0]["fixed_prompts"][0] = dev[0]["fixed_prompts"][0]
    _write(data / "heldout/private/scenarios.json", held)
    with pytest.raises(DataValidationError, match="exact normalized prompt leaks"):
        validate_data_tree(data)


def test_equivalence_approval_requires_two_distinct_reviewers(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(ROOT / "data", data)
    pairs = _read(data / "development/dialect_pairs.json")
    pairs[0]["review_status"] = "APPROVED"
    pairs[0]["reviewer_ids"] = ["reviewer-one"]
    _write(data / "development/dialect_pairs.json", pairs)
    with pytest.raises(DataValidationError, match="approved pair needs two reviewers"):
        validate_data_tree(data)


def test_frozen_manifest_rejects_unapproved_scenarios_and_pairs(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(ROOT / "data", data)
    manifest = _read(data / "heldout/manifest.json")
    manifest["approval_status"] = "APPROVED"
    manifest["freeze_status"] = "FROZEN_APPROVED"
    _write(data / "heldout/manifest.json", manifest)
    with pytest.raises(
        DataValidationError,
        match="frozen manifest contains unapproved scenarios",
    ):
        validate_data_tree(data)
