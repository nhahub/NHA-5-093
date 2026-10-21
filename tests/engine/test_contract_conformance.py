import json
from pathlib import Path

import pytest

from scripts.contracts import Contracts
from services.engine.replay import replay_trace
from services.engine.tools import parse_next_probe


@pytest.mark.parametrize(
    "name",
    [
        "NextProbe",
        "NextProbe_STOP",
        "AuditEvent",
        "CheckResult",
        "PolicyRulePublic",
        "AdapterTurnRequest",
        "AdapterTurnResponse",
        "Finding",
        "AgentScenarioView",
        "ScoreResult",
    ],
)
def test_canonical_examples_use_explicit_utf8(name):
    Contracts().validate(
        "NextProbe" if name == "NextProbe_STOP" else name, Contracts().fixture(name)
    )


@pytest.mark.parametrize(
    "change",
    [
        {"action": "STOP", "message": "invalid"},
        {"action": "SEND_TURN", "message": None},
        {"strategy_id": "unapproved"},
        {"run_id": "model-owned"},
    ],
)
def test_invalid_probe_rejected(change):
    probe = {**Contracts().fixture("NextProbe"), **change}
    with pytest.raises(ValueError):
        parse_next_probe(probe)


@pytest.mark.parametrize("path", sorted(Path("tests/fixtures/traces").glob("*.json")))
def test_actual_mock_trace_outputs_validate(path):
    trace = json.loads(path.read_text(encoding="utf-8"))
    assert trace["mode"] == "MOCK"
    contracts = Contracts()
    contracts.validate("RunDetail", trace["run_detail"])
    for event in trace["events"]:
        contracts.validate("AuditEvent", event)
    for finding in trace["proposed_findings"]:
        contracts.validate("Finding", finding)
    assert replay_trace(path)["complete"]


def test_exported_traces_show_different_next_actions_after_observations():
    traces = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(Path("tests/fixtures/traces").glob("*.json"))
    ]
    decisions = [[e["data"] for e in t["events"] if e["event_type"] == "DECISION"] for t in traces]
    assert {rows[1]["strategy_id"] for rows in decisions} == {"direct_request", "indirect_request"}
