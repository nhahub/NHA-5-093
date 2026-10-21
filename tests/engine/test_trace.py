"""Tests for canonical DECISION / TURN / CHECK trace events."""

from __future__ import annotations

import pytest

from services.engine.trace import (
    MAX_DECISION_FIELD_LEN,
    build_check_event,
    build_decision_event,
    build_turn_event,
    validate_decision_data,
)


def test_decision_event_has_required_contract_fields() -> None:
    event = build_decision_event(
        run_id="run_1",
        seq=1,
        turn_index=1,
        observed_fact="Interview started; no previous reply",
        strategy_id="direct_request",
        decision_reason="Test direct disclosure behavior",
    )
    assert event["event_type"] == "DECISION"
    assert event["actor"] == "AGENT"
    for key in ("event_id", "run_id", "seq", "turn_index", "occurred_at", "data"):
        assert key in event
    assert set(event["data"]) == {"observed_fact", "strategy_id", "decision_reason", "usage"}
    assert set(event["data"]["usage"]) == {"input_tokens", "output_tokens", "total_tokens"}


def test_decision_fields_are_concise_and_usage_recorded() -> None:
    event = build_decision_event(
        run_id="r",
        seq=1,
        turn_index=1,
        observed_fact="x" * 1000,
        strategy_id="direct_request",
        decision_reason="y" * 1000,
        usage={"input_tokens": 10, "output_tokens": 3, "total_tokens": 13},
    )
    assert len(event["data"]["observed_fact"]) <= MAX_DECISION_FIELD_LEN
    assert len(event["data"]["decision_reason"]) <= MAX_DECISION_FIELD_LEN
    assert event["data"]["usage"] == {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13}


def test_decision_rejects_empty_required_fields() -> None:
    with pytest.raises(ValueError):
        validate_decision_data(
            {"observed_fact": "", "strategy_id": "s", "decision_reason": "r", "usage": {}}
        )
    with pytest.raises(ValueError):
        validate_decision_data(
            {"observed_fact": "o", "strategy_id": "", "decision_reason": "r", "usage": {}}
        )


def test_turn_event_matches_canonical_payload() -> None:
    event = build_turn_event(
        run_id="run_1",
        seq=2,
        turn_index=1,
        candidate_message="hi",
        target_response="hello",
        model_id="mock-target-v1",
        usage={"input_tokens": 70, "output_tokens": 13, "total_tokens": 83},
        latency_ms=120,
    )
    assert event["event_type"] == "TURN"
    assert event["actor"] == "TARGET"
    assert set(event["data"]) == {
        "candidate_message",
        "target_response",
        "model_id",
        "usage",
        "latency_ms",
    }


def test_check_event_carries_flat_check_payload() -> None:
    from services.engine.tools import CheckResult

    check = CheckResult(
        check_id="chk_1",
        run_id="run_1",
        turn_index=1,
        rule_id="POL-SEC-01-CANARY",
        result="FAIL",
        evidence_event_ids=("e1",),
        evidence_spans=("s",),
        checker_version="checker-v1",
        reason="r",
    )
    event = build_check_event(run_id="run_1", seq=3, turn_index=1, check=check)
    assert event["event_type"] == "CHECK"
    assert event["actor"] == "CHECKER"
    assert event["data"]["check_id"] == "chk_1"
    assert "check" not in event["data"]
