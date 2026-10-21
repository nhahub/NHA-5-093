"""Agent state definitions for the HireGuard red-team engine (M2).

Ownership: M2 (services/engine). Contracts are read-only inputs from M1.
This module defines the per-scenario mutable state (LangGraph-compatible
TypedDict) and the frozen, model-safe view exposed to the LLM provider.

Security notes:
- AgentState holds controller internals (run_id, deadlines, counters).
- AgentStateView exposes ONLY safe, non-secret fields. It must never carry
  held-out labels, expected_behavior, forbidden secret values, checker
  internals, or approval state.
"""

from __future__ import annotations

import copy
import time
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .tools import NextProbe as NextProbeModel

# ---------------------------------------------------------------------------
# Contract literals (frozen by spec)
# ---------------------------------------------------------------------------

TerminalOutcome = Literal["NO_FINDING", "PROPOSED_FINDING", "INCONCLUSIVE", "FAILURE"]

ALLOWED_TERMINAL_OUTCOMES: tuple[str, str, str, str] = (
    "NO_FINDING",
    "PROPOSED_FINDING",
    "INCONCLUSIVE",
    "FAILURE",
)

# Exact AgentState field names required by the contract. Do not rename
# without an approved ADR (M1 owns contracts/).
AGENT_STATE_FIELDS: tuple[str, ...] = (
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
)


# ---------------------------------------------------------------------------
# Supporting record shapes (kept generic until M1 freezes full schemas)
# ---------------------------------------------------------------------------


class TranscriptTurn(TypedDict, total=False):
    """One candidate -> target exchange stored in AgentState.transcript."""

    turn_index: int
    candidate_message: str
    target_response: str
    agent_tokens: int
    target_tokens: int


class CheckRecord(TypedDict, total=False):
    """Minimal cached copy of an M4 CheckResult for state decisions."""

    check_id: str
    rule_id: str
    result: str  # PASS | FAIL | INCONCLUSIVE (validated by M4)
    turn_index: int


# ---------------------------------------------------------------------------
# Mutable per-scenario state (LangGraph node state)
# ---------------------------------------------------------------------------


class AgentState(TypedDict, total=False):
    """Fresh, isolated state for exactly one scenario execution.

    A new dict MUST be created per scenario via create_initial_state().
    Never share nested objects (transcript / strategy_history / ...) across
    runs; see tests/engine/test_state.py::test_no_cross_run_leakage.
    """

    run_id: str
    scenario_id: str
    target_version: str
    policy_version: str
    persona_ref: str
    hypothesis: str
    strategy_history: list[str]
    transcript: list[TranscriptTurn]
    check_results: list[CheckRecord]
    used_candidate_turns: int
    used_total_tokens: int
    timeout_deadline: float  # epoch seconds (monotonic wall-clock deadline)
    last_observation: str
    next_probe: dict[str, Any] | None
    terminal_outcome: TerminalOutcome | None


# ---------------------------------------------------------------------------
# Frozen model-safe view (the ONLY thing the LLM may observe)
# ---------------------------------------------------------------------------


class AgentStateView(BaseModel):
    """Minimal observation passed to the LLM provider.

    Deliberately excludes: run_id, timeout_deadline, policy internals,
    expected_behavior, held-out labels, forbidden secret values, checker
    internals, approval flags, seeds, and cost internals.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str
    persona_ref: str
    hypothesis: str
    strategy_history: tuple[str, ...] = ()
    transcript: tuple[str, ...] = ()  # safe, truncated turn summaries
    last_observation: str = ""
    used_candidate_turns: int = Field(default=0, ge=0)
    used_total_tokens: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# Factories / converters
# ---------------------------------------------------------------------------


def create_initial_state(
    *,
    run_id: str,
    scenario_id: str,
    target_version: str,
    policy_version: str = "policy-v1",
    persona_ref: str = "",
    hypothesis: str = "",
    timeout_deadline: float | None = None,
    timeout_seconds: float = 120.0,
) -> AgentState:
    """Build a fresh, fully isolated AgentState for one scenario.

    Every mutable container is newly allocated so two states created in the
    same process share no nested objects.
    """
    deadline = (
        float(timeout_deadline)
        if timeout_deadline is not None
        else time.time() + float(timeout_seconds)
    )
    return AgentState(
        run_id=run_id,
        scenario_id=scenario_id,
        target_version=target_version,
        policy_version=policy_version,
        persona_ref=persona_ref,
        hypothesis=hypothesis,
        strategy_history=[],
        transcript=[],
        check_results=[],
        used_candidate_turns=0,
        used_total_tokens=0,
        timeout_deadline=deadline,
        last_observation="",
        next_probe=None,
        terminal_outcome=None,
    )


def build_agent_view(state: AgentState, *, max_transcript_chars: int = 4000) -> AgentStateView:
    """Project mutable controller state into a frozen model-safe view.

    Transcript turns are rendered as plain text summaries and truncated to
    bound prompt size. No secret material is copied: this function only reads
    the safe fields listed in AgentStateView.
    """
    transcript_lines: list[str] = []
    budget = max(0, int(max_transcript_chars))
    for turn in state.get("transcript", []):
        candidate = str(turn.get("candidate_message", ""))[:500]
        target = str(turn.get("target_response", ""))[:500]
        line = f"T{turn.get('turn_index', '?')}: you={candidate} | target={target}"
        if budget <= 0:
            break
        transcript_lines.append(line[:1000])
        budget -= len(line)

    return AgentStateView(
        scenario_id=state.get("scenario_id", ""),
        persona_ref=state.get("persona_ref", ""),
        hypothesis=state.get("hypothesis", ""),
        strategy_history=tuple(state.get("strategy_history", [])),
        transcript=tuple(transcript_lines),
        last_observation=state.get("last_observation", ""),
        used_candidate_turns=int(state.get("used_candidate_turns", 0)),
        used_total_tokens=int(state.get("used_total_tokens", 0)),
    )


def clone_state(state: AgentState) -> AgentState:
    """Deep-copy a state (used for replay / failure isolation tests)."""
    return copy.deepcopy(state)


def to_agent_view(scenario: dict[str, Any]) -> dict[str, Any]:
    """Derive the canonical AgentScenarioView from an approved Scenario.

    Allowlist projection only: scenario_id, suite_version, family,
    role_id, objective, persona_ref, rule_ids. NEVER forwards split,
    expected_behavior, fixed_prompts, labels, or approval state
    (M5 ScenarioRepository contract).
    """
    return {
        "scenario_id": str(scenario.get("scenario_id", "")),
        "suite_version": str(scenario.get("suite_version", "dev-v1")),
        "family": str(scenario.get("family", "POLICY_VIOLATION")),
        "role_id": str(scenario.get("role_id", "customer-support")),
        "objective": str(scenario.get("objective", "")),
        "persona_ref": str(scenario.get("persona_ref", "")),
        "rule_ids": [str(r) for r in scenario.get("rule_ids", [])],
    }


def validate_terminal_outcome(value: str) -> TerminalOutcome:
    if value not in ALLOWED_TERMINAL_OUTCOMES:
        raise ValidationError.from_exception_data(
            "TerminalOutcome",
            [
                {
                    "type": "literal_error",
                    "loc": ("terminal_outcome",),
                    "input": value,
                    "ctx": {"expected": ", ".join(ALLOWED_TERMINAL_OUTCOMES)},
                }
            ],
        )
    return value  # type: ignore[return-value]


__all__ = [
    "AGENT_STATE_FIELDS",
    "ALLOWED_TERMINAL_OUTCOMES",
    "AgentState",
    "AgentStateView",
    "CheckRecord",
    "NextProbeModel",
    "TerminalOutcome",
    "TranscriptTurn",
    "build_agent_view",
    "clone_state",
    "create_initial_state",
    "to_agent_view",
    "validate_terminal_outcome",
]
