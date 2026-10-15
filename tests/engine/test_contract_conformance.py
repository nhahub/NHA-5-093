"""Contract conformance: M2 artifacts vs M1 canonical schemas (read-only).

Validates that everything M2 produces/consumes matches
contracts/schemas/*.schema.json and contracts/examples/*.json exactly:
NextProbe payloads, AuditEvent streams, CheckResults, Finding proposals,
PolicyRulePublic views, AdapterTurnRequests, and ScoreResults.

These tests read M1-owned files only; they never modify contracts.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).parents[2]
SCHEMAS = ROOT / "contracts" / "schemas"
EXAMPLES = ROOT / "contracts" / "examples"


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))


def _check(instance: dict, schema_name: str) -> None:
    jsonschema.validate(instance=instance, schema=_schema(schema_name))


def test_canonical_examples_still_validate() -> None:
    for name in ("NextProbe", "AuditEvent", "CheckResult", "PolicyRulePublic",
                 "AdapterTurnRequest", "AdapterTurnResponse", "Finding",
                 "AgentScenarioView", "ScoreResult"):
        example = json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))
        _check(example, name)


def test_mock_adapter_responses_validate() -> None:
    from services.engine.mocks.mock_adapter import MockAdapter

    turn_schema = _schema("AdapterTurnResponse")
    score_schema = _schema("ScoreResult")
    for mode in ("refusal", "canary_disclosure", "scoring"):
        adapter = MockAdapter(mode=mode)  # type: ignore[arg-type]
        session = adapter.start_session(
            {"run_id": "run_k", "target_version": "vulnerable-v1",
             "role_id": "customer-support", "persona_ref": "p"}
        )
        _check(session, "AdapterStartResponse")
        response = adapter.send_turn(
            {"run_id": "run_k", "session_id": session["session_id"],
             "turn_index": 1, "message": "hi", "idempotency_key": "run_k:1"}
        )
        _check(response, "AdapterTurnResponse")
        assert response["usage"]["total_tokens"] == (
            response["usage"]["input_tokens"] + response["usage"]["output_tokens"]
        )
        _check(adapter.get_score(session["session_id"]), "ScoreResult")
    assert turn_schema and score_schema


def test_engine_nextprobe_and_requests_validate() -> None:
    from services.engine.tools import build_send_turn_request, parse_next_probe

    probe = parse_next_probe(json.loads((EXAMPLES / "NextProbe.json").read_text()))
    _check(probe.model_dump(mode="json"), "NextProbe")
    stop = parse_next_probe(json.loads((EXAMPLES / "NextProbe_STOP.json").read_text()))
    _check(stop.model_dump(mode="json"), "NextProbe")
    req = build_send_turn_request(
        message="hi", strategy_id="direct_request",
        run_id="run_k", session_id="sess_k", turn_index=1,
    )
    _check(req, "AdapterTurnRequest")


def test_engine_events_and_checks_validate() -> None:
    from services.engine.baseline import ListStore
    from services.engine.controller import run_adaptive
    from services.engine.mocks import mock_checker
    from services.engine.mocks.mock_adapter import MockAdapter
    from services.engine.providers import DeterministicMockProvider
    from services.engine.budgets import RunLimits

    store = ListStore()
    result = run_adaptive(
        "run_conf",
        {"method": "ADAPTIVE", "target_version": "vulnerable-v1",
         "limits": {"max_candidate_turns": 2, "max_total_tokens": 4000, "timeout_seconds": 60},
         "model_settings": {"model_id": "mock-agent-v1", "seed": 1}},
        {"scenario_id": "scn_conf", "suite_version": "dev-v1", "family": "SECRET_LEAK",
         "role_id": "customer-support", "objective": "o", "persona_ref": "p",
         "rule_ids": ["POL-SEC-01-CANARY"]},
        MockAdapter(mode="refusal"), store, mock_checker,
        provider=DeterministicMockProvider(),
        limits=RunLimits(max_candidate_turns=2, max_total_tokens=4000, timeout_seconds=60),
    )
    event_schema = _schema("AuditEvent")
    assert len(store.events) > 0
    seqs = [e["seq"] for e in store.events]
    assert seqs[0] == 1 and seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    for event in store.events:
        _check(event, "AuditEvent")
    assert event_schema is not None
    for record in result["check_results"]:
        _check({
            "check_id": record["check_id"], "run_id": "run_conf",
            "turn_index": record["turn_index"], "rule_id": record["rule_id"],
            "result": record["result"], "evidence_event_ids": [],
            "evidence_spans": [], "checker_version": "mock-checker-v1",
            "reason": "conformance",
        }, "CheckResult")


def test_finding_proposals_validate() -> None:
    from services.engine.findings import build_proposal

    proposal = build_proposal(
        run_id="run_k", scenario_id="scn_1", rule_id="POL-SEC-01-CANARY",
        turn_index=1, evidence_event_ids=["evt_1"],
        evidence_spans=["target_response[0:14]"], reason="r",
    )
    _check(proposal, "Finding")
    assert proposal["reviewer_status"] == "PENDING"


def test_agent_view_matches_canonical_shape() -> None:
    from services.engine.state import to_agent_view

    canonical = json.loads((EXAMPLES / "AgentScenarioView.json").read_text())
    derived = to_agent_view({**canonical, "split": "HELD_OUT",
                             "expected_behavior": "X", "fixed_prompts": []})
    _check(derived, "AgentScenarioView")
    assert derived == canonical


def test_policy_views_validate() -> None:
    from services.engine.controller import default_policies

    for policy in default_policies():
        _check(policy.model_dump(mode="json"), "PolicyRulePublic")


@pytest.mark.parametrize("path", sorted((ROOT / "tests" / "fixtures" / "traces").glob("*.json")))
def test_certified_trace_events_validate(path: Path) -> None:
    trace = json.loads(path.read_text(encoding="utf-8"))
    assert len(trace["events"]) > 0
    for event in trace["events"]:
        _check(event, "AuditEvent")
    for proposal in trace.get("proposed_findings", []):
        _check(proposal, "Finding")
