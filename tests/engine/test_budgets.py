"""Unit tests for budget guards: turns, tokens (with reservation), timeout."""

from __future__ import annotations

import time

import pytest
from pydantic import ValidationError

from services.engine.budgets import (
    DEFAULT_TOKEN_RESERVATION,
    RunLimits,
    can_send_turn,
    record_turn_consumption,
    remaining_tokens,
    remaining_turns,
)
from services.engine.state import create_initial_state


def _state(**overrides):
    base = create_initial_state(
        run_id="run_1", scenario_id="scn_1", target_version="vulnerable-v1", timeout_seconds=120
    )
    base.update(overrides)
    return base


def test_default_reservation_is_at_least_300() -> None:
    assert DEFAULT_TOKEN_RESERVATION >= 300


def test_contract_rejects_turn_limit_above_six() -> None:
    with pytest.raises(ValidationError):
        RunLimits(max_candidate_turns=7, max_total_tokens=4000, timeout_seconds=60)


def test_allows_first_turn_with_fresh_budgets() -> None:
    state = _state()
    limits = RunLimits(max_candidate_turns=6, max_total_tokens=4000, timeout_seconds=120)
    allowed, reason = can_send_turn(state, limits)
    assert allowed is True
    assert reason is None


def test_stops_after_six_candidate_turns() -> None:
    limits = RunLimits(max_candidate_turns=6, max_total_tokens=100_000, timeout_seconds=600)
    state = _state()
    for _ in range(6):
        allowed, _ = can_send_turn(state, limits)
        assert allowed is True
        record_turn_consumption(state, agent_tokens=10, target_tokens=10)
    assert state["used_candidate_turns"] == 6
    allowed, reason = can_send_turn(state, limits)
    assert allowed is False
    assert reason == "TURN_LIMIT"
    # Must stay stopped (no further calls).
    allowed2, reason2 = can_send_turn(state, limits)
    assert (allowed2, reason2) == (False, "TURN_LIMIT")


def test_stops_before_call_when_tokens_would_exceed_with_reservation() -> None:
    limits = RunLimits(max_candidate_turns=6, max_total_tokens=1000, timeout_seconds=600)
    # 800 used + 300 reservation > 1000 => blocked BEFORE the adapter call.
    state = _state(used_total_tokens=800)
    allowed, reason = can_send_turn(state, limits, token_reservation=300)
    assert allowed is False
    assert reason == "TOKEN_LIMIT"
    # Boundary: exactly fitting reservation is still allowed.
    edge = _state(used_total_tokens=700)
    allowed_edge, _ = can_send_turn(edge, limits, token_reservation=300)
    assert allowed_edge is True
    # Counters must not move on a blocked call.
    assert state["used_candidate_turns"] == 0
    assert state["used_total_tokens"] == 800


def test_timeout_blocks_even_with_remaining_turns_and_tokens() -> None:
    limits = RunLimits(max_candidate_turns=6, max_total_tokens=100_000, timeout_seconds=120)
    past_deadline = time.time() - 1.0
    state = _state(timeout_deadline=past_deadline)
    allowed, reason = can_send_turn(state, limits, now=time.time())
    assert allowed is False
    assert reason == "TIMEOUT"


def test_consumption_charges_both_sides_and_increments_turn() -> None:
    state = _state()
    record_turn_consumption(state, agent_tokens=40, target_tokens=60)
    assert state["used_candidate_turns"] == 1
    assert state["used_total_tokens"] == 100
    assert (
        remaining_turns(
            state, RunLimits(max_candidate_turns=6, max_total_tokens=4000, timeout_seconds=60)
        )
        == 5
    )
    assert (
        remaining_tokens(
            state, RunLimits(max_candidate_turns=6, max_total_tokens=4000, timeout_seconds=60)
        )
        == 3900
    )


def test_consumption_rejects_negative_tokens() -> None:
    state = _state()
    with pytest.raises(ValueError):
        record_turn_consumption(state, agent_tokens=-1, target_tokens=0)


def test_max_retries_budget_gate() -> None:
    from services.engine.budgets import can_retry

    limits = RunLimits(
        max_candidate_turns=6, max_total_tokens=4000, timeout_seconds=60, max_retries=1
    )
    assert can_retry(0, limits) is True
    assert can_retry(1, limits) is False
    strict = RunLimits(max_candidate_turns=6, max_total_tokens=4000, timeout_seconds=60)
    assert can_retry(0, strict) is False
