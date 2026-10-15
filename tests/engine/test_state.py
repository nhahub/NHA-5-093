"""Unit tests for AgentState isolation and the frozen model view."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from services.engine.state import (
    AGENT_STATE_FIELDS,
    ALLOWED_TERMINAL_OUTCOMES,
    AgentStateView,
    build_agent_view,
    create_initial_state,
    validate_terminal_outcome,
)


def test_state_has_exact_contract_fields() -> None:
    state = create_initial_state(run_id="run_1", scenario_id="scn_1", target_version="vulnerable-v1")
    assert set(AGENT_STATE_FIELDS) == {
        "run_id",
        "scenario_id",
        "target_version",
        "policy_version",
        "persona_ref",
        "hypothesis",
        "strategy_history",
        "transcript",
        "check_results",
        "used_candidate_turns",
        "used_total_tokens",
        "timeout_deadline",
        "last_observation",
        "next_probe",
        "terminal_outcome",
    }
    for field in AGENT_STATE_FIELDS:
        assert field in state


def test_initial_state_defaults_are_zeroed() -> None:
    state = create_initial_state(run_id="r", scenario_id="s", target_version="vulnerable-v1")
    assert state["used_candidate_turns"] == 0
    assert state["used_total_tokens"] == 0
    assert state["strategy_history"] == []
    assert state["transcript"] == []
    assert state["check_results"] == []
    assert state["terminal_outcome"] is None
    assert state["next_probe"] is None


def test_no_cross_run_leakage() -> None:
    """Two states created in the same process must share no mutable objects."""
    a = create_initial_state(run_id="run_a", scenario_id="scn_a", target_version="vulnerable-v1")
    b = create_initial_state(run_id="run_b", scenario_id="scn_b", target_version="vulnerable-v1")

    a["strategy_history"].append("direct_request")
    a["transcript"].append({"turn_index": 0, "candidate_message": "hello", "target_response": "hi"})
    a["hypothesis"] = "target may leak"
    a["used_candidate_turns"] = 3

    assert b["strategy_history"] == []
    assert b["transcript"] == []
    assert b["hypothesis"] == ""
    assert b["used_candidate_turns"] == 0
    # Nested containers must be distinct objects, not shared references.
    assert a["strategy_history"] is not b["strategy_history"]
    assert a["transcript"] is not b["transcript"]
    assert a["check_results"] is not b["check_results"]


def test_mutating_view_inputs_does_not_mutate_state() -> None:
    state = create_initial_state(run_id="r", scenario_id="s", target_version="vulnerable-v1")
    state["strategy_history"].append("direct_request")
    view = build_agent_view(state)
    assert view.strategy_history == ("direct_request",)
    # View is frozen: assignment must fail and state stays intact.
    with pytest.raises(ValidationError):
        view.hypothesis = "tampered"  # type: ignore[misc]
    assert state["hypothesis"] == ""


def test_agent_view_is_frozen_and_forbids_extras() -> None:
    view = build_agent_view(
        create_initial_state(run_id="r", scenario_id="s", target_version="vulnerable-v1")
    )
    with pytest.raises(ValidationError):
        AgentStateView(
            scenario_id="s",
            persona_ref="p",
            hypothesis="h",
            strategy_history=(),
            transcript=(),
            last_observation="",
            used_candidate_turns=0,
            used_total_tokens=0,
            forbidden_extra="nope",  # type: ignore[call-arg]
        )
    assert isinstance(view, AgentStateView)


def test_agent_view_exposes_no_secrets() -> None:
    """The model view must not carry internal/secret field names."""
    state = create_initial_state(
        run_id="run_secret",
        scenario_id="scn_1",
        target_version="vulnerable-v1",
        persona_ref="persona_7",
        hypothesis="h0",
    )
    view = build_agent_view(state)
    dumped = view.model_dump()
    for leaked in (
        "run_id",
        "timeout_deadline",
        "expected_behavior",
        "forbidden_value",
        "held_out",
        "split",
        "seed",
        "approval",
    ):
        assert leaked not in dumped
    # Safe fields are present.
    assert dumped["scenario_id"] == "scn_1"
    assert dumped["persona_ref"] == "persona_7"


def test_no_state_leak() -> None:
    """Contract-named alias: zero memory across scenario boundaries."""
    test_no_cross_run_leakage()


def test_to_agent_view_strips_sensitive_scenario_fields() -> None:
    from services.engine.state import to_agent_view

    view = to_agent_view({
        "scenario_id": "scn_1", "suite_version": "dev-v1", "family": "SECRET_LEAK",
        "role_id": "customer-support", "objective": "obj", "persona_ref": "p",
        "rule_ids": ["POL-A"], "split": "HELD_OUT",
        "expected_behavior": "FAIL", "fixed_prompts": ["q"], "approved": True,
    })
    assert set(view) == {
        "scenario_id", "suite_version", "family", "role_id",
        "objective", "persona_ref", "rule_ids",
    }


def test_terminal_outcome_literals_only() -> None:
    assert set(ALLOWED_TERMINAL_OUTCOMES) == {
        "NO_FINDING",
        "PROPOSED_FINDING",
        "INCONCLUSIVE",
        "FAILURE",
    }
    for ok in ALLOWED_TERMINAL_OUTCOMES:
        assert validate_terminal_outcome(ok) == ok
    with pytest.raises(ValidationError):
        validate_terminal_outcome("CONFIRMED")  # agent must never self-confirm
    with pytest.raises(ValidationError):
        validate_terminal_outcome("PASS")
