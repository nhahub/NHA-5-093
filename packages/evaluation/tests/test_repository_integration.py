"""Synthetic test-only approvals; production corpora stay proposed/unfrozen."""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import pytest

import packages.security as security
from packages.evaluation import MetricsService, ScenarioRepository, validate_data_tree
from packages.evaluation.repository import to_agent_view
from packages.evaluation.validation import DataValidationError, _sha
from scripts.contracts import Contracts
from services.engine.controller import execute_run
from services.engine.mocks.mock_adapter import MockAdapter
from services.engine.mocks.mock_store import MockStore
from services.engine.providers import DeterministicMockProvider
from services.engine.state import to_agent_view as engine_view

ROOT = Path(__file__).resolve().parents[3]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def corpus(tmp_path):
    result = tmp_path / "data"
    shutil.copytree(ROOT / "data", result)
    return result


@pytest.mark.parametrize("defect", ["record", "persona", "pair", "suite", "policy", "membership"])
def test_dataset_inconsistencies_fail_validation(corpus, defect):
    path = corpus / "development/manifest.json"
    manifest = read(path)
    if defect == "record":
        manifest["records"].append(manifest["records"][0])
    elif defect == "suite":
        manifest["suite_version"] = "wrong"
    elif defect == "membership":
        manifest["records"][-1]["dialect_pair_id"] = "unknown"
    elif defect == "persona":
        path = corpus / "development/personas.json"
        manifest = read(path)
        manifest.append(manifest[0])
    elif defect == "pair":
        path = corpus / "development/dialect_pairs.json"
        manifest = read(path)
        manifest.append(manifest[0])
    else:
        path = corpus / "development/scenarios.json"
        manifest = read(path)
        manifest[0]["rule_ids"] = ["unknown"]
    write(path, manifest)
    with pytest.raises(ValueError):
        validate_data_tree(corpus)


def test_approved_boolean_and_split_approval_do_not_unlock_heldout(corpus):
    path = corpus / "heldout/private/scenarios.json"
    scenarios = read(path)
    scenarios[0]["approved"] = True
    write(path, scenarios)
    manifest_path = corpus / "heldout/manifest.json"
    manifest = read(manifest_path)
    manifest["approval_status"] = "APPROVED"
    write(manifest_path, manifest)
    repository = ScenarioRepository(corpus)
    with pytest.raises(PermissionError, match="frozen"):
        repository.get_approved(scenarios[0]["scenario_id"], scenarios[0]["suite_version"])


def freeze_test_copy(corpus):
    """Record fake humans ONLY in the isolated test directory to exercise gates."""
    path = corpus / "heldout/manifest.json"
    manifest = read(path)
    scenarios = read(corpus / "heldout" / manifest["scenario_file"])
    for scenario in scenarios:
        scenario["approved"] = True
    pairs = read(corpus / "heldout" / manifest["dialect_pairs_file"])
    for pair in pairs:
        pair.update(
            review_status="APPROVED", reviewer_ids=["synthetic-reviewer-a", "synthetic-reviewer-b"]
        )
    for record in manifest["records"]:
        record.update(
            review_status="APPROVED", reviewer_ids=["synthetic-reviewer-a", "synthetic-reviewer-b"]
        )
    write(corpus / "heldout" / manifest["scenario_file"], scenarios)
    write(corpus / "heldout" / manifest["dialect_pairs_file"], pairs)
    protocol = read(corpus / "heldout/protocol.json")
    protocol.update(
        approval_status="APPROVED", freeze_status="FROZEN_APPROVED", comparable_results_allowed=True
    )
    protocol["repeatability"].update(approval_status="APPROVED", freeze_status="FROZEN_APPROVED")
    protocol["approvals"] = [
        {
            "owner": role,
            "reviewer_id": f"synthetic-{role}",
            "decision": "APPROVED",
            "protocol_version": protocol["protocol_version"],
            "approved_at": "2026-10-24T00:00:00Z",
        }
        for role in protocol["required_approvers"]
    ]
    write(corpus / "heldout/protocol.json", protocol)
    manifest.update(
        approval_status="APPROVED",
        freeze_status="FROZEN_APPROVED",
        content_sha256=_sha(
            {
                "scenarios": scenarios,
                "personas": read(corpus / "heldout/personas.json"),
                "dialect_pairs": pairs,
                "records": manifest["records"],
            }
        ),
        protocol_sha256=_sha(protocol),
        repeatability_sha256=_sha(read(corpus / "heldout/private/repeatability_transcripts.json")),
    )
    write(path, manifest)
    return scenarios[0]


@pytest.mark.parametrize("defect", ["approval", "protocol", "transcript", "content", "reviewers"])
def test_heldout_freeze_detects_missing_approvals_and_tampering(corpus, defect):
    first = freeze_test_copy(corpus)
    assert (
        ScenarioRepository(corpus).get_approved(first["scenario_id"], first["suite_version"])
        == first
    )
    if defect in {"approval", "protocol"}:
        path = corpus / "heldout/protocol.json"
        value = read(path)
        if defect == "approval":
            value["approvals"].pop()
        else:
            value["limits"]["max_total_tokens"] += 1
    elif defect == "transcript":
        path = corpus / "heldout/private/repeatability_transcripts.json"
        value = read(path)
        value[0]["messages"][0]["text"] += " changed"
    elif defect == "reviewers":
        path = corpus / "heldout/private/dialect_pairs.json"
        value = read(path)
        value[0]["reviewer_ids"] = ["", "synthetic-reviewer"]
    else:
        path = corpus / "heldout/private/scenarios.json"
        value = read(path)
        value[0]["objective"] += " changed"
    write(path, value)
    with pytest.raises(DataValidationError):
        ScenarioRepository(corpus)


def test_public_projection_matches_engine_and_rejects_invalid_full_records():
    for path in (
        ROOT / "data/development/scenarios.json",
        ROOT / "data/heldout/private/scenarios.json",
    ):
        for scenario in read(path):
            assert to_agent_view(scenario) == engine_view(scenario)
            invalid = {**scenario, "approved": "yes"}
            with pytest.raises(ValueError):
                to_agent_view(invalid)


@pytest.mark.parametrize("method", ["FIXED", "ADAPTIVE"])
def test_m5_repository_real_engine_checker_and_metrics(corpus, method):
    scenarios_path = corpus / "development/scenarios.json"
    scenarios = read(scenarios_path)
    scenarios[0]["approved"] = True  # isolated DEV fixture, never source data
    write(scenarios_path, scenarios)
    manifest_path = corpus / "development/manifest.json"
    manifest = read(manifest_path)
    manifest["approval_status"] = "APPROVED"
    write(manifest_path, manifest)
    repository = ScenarioRepository(corpus)
    scenario = repository.get_approved(scenarios[0]["scenario_id"], scenarios[0]["suite_version"])
    contracts = Contracts()
    config = contracts.fixture("RunCreate")
    config.update(
        method=method, scenario_id=scenario["scenario_id"], suite_version=scenario["suite_version"]
    )
    config["model_settings"]["seed"] = scenario["seed"]
    store, adapter = MockStore(config, scenario), MockAdapter(mode="canary_disclosure")

    class InspectProvider(DeterministicMockProvider):
        async def choose_probe(self, state, policies, view):
            assert view == repository.to_agent_view(scenario)
            return await super().choose_probe(state, policies, view)

    actual_run = asyncio.run(
        execute_run(
            store.detail["run_id"],
            config,
            scenario,
            adapter,
            store,
            security,
            provider=InspectProvider(),
        )
    )
    contracts.validate("RunDetail", actual_run)
    assert actual_run["outcome"] == "PROPOSED_FINDING"
    assert store.checks[0]["result"] == "FAIL" and store.findings[0]["reviewer_status"] == "PENDING"
    context = {
        "planned_runs": [
            {
                "plan_id": "synthetic_integration",
                "scenario_id": scenario["scenario_id"],
                "family": scenario["family"],
                "intended_violation": True,
                "method": method,
                "target_version": config["target_version"],
                "run_id": actual_run["run_id"],
                "run_create": config,
            }
        ],
        "events": store.events,
        "protocol_approval_status": "PROPOSED",
    }
    report = MetricsService({"synthetic_batch": context}).aggregate_batch(
        "synthetic_batch", [actual_run], store.findings, []
    )
    contracts.validate("ReportSummary", report)
    assert report["completed_runs"] == 1 and report["reviewed_flags"] == 0
    assert report["finding_precision"] is None and report["confirmed_discovery_rate"] == 0
