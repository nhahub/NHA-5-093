"""Budget guards for the HireGuard red-team engine (M2).

Contract rules enforced here (ADR-05 + Chapter 07):
- max_candidate_turns <= 6; controller MUST stop BEFORE a new adapter call.
- max_total_tokens covers agent + target tokens with a conservative
  pre-call reservation (minimum 300 tokens).
- timeout_deadline is a hard wall-clock deadline.
- On exhaustion no send_turn may execute; a termination reason is recorded:
  TURN_LIMIT | TOKEN_LIMIT | TIMEOUT.

This module is pure (no I/O, no LLM calls) so it is fully unit-testable
offline in Mock mode.
"""

from __future__ import annotations

import time
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .state import AgentState

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_CANDIDATE_TURNS_HARD_CAP = 6
DEFAULT_TOKEN_RESERVATION = 300

TerminationReason = Literal["TURN_LIMIT", "TOKEN_LIMIT", "TIMEOUT"]

TURN_LIMIT: TerminationReason = "TURN_LIMIT"
TOKEN_LIMIT: TerminationReason = "TOKEN_LIMIT"
TIMEOUT: TerminationReason = "TIMEOUT"


# ---------------------------------------------------------------------------
# Limits model (mirrors RunCreate.limits subset owned by contract)
# ---------------------------------------------------------------------------


class RunLimits(BaseModel):
    """Frozen execution budgets for one scenario run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_candidate_turns: int = Field(default=6, ge=1, le=MAX_CANDIDATE_TURNS_HARD_CAP)
    max_total_tokens: int = Field(default=4000, gt=0)
    timeout_seconds: float = Field(default=120.0, gt=0)
    max_retries: int = Field(default=0, ge=0)

    @field_validator("max_candidate_turns")
    @classmethod
    def _enforce_turn_cap(cls, value: int) -> int:
        if value > MAX_CANDIDATE_TURNS_HARD_CAP:
            raise ValueError(
                f"max_candidate_turns={value} exceeds contract cap "
                f"{MAX_CANDIDATE_TURNS_HARD_CAP}"
            )
        return value


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def _now(now: float | None) -> float:
    return float(now) if now is not None else time.time()


def can_send_turn(
    state: AgentState,
    limits: RunLimits,
    *,
    now: float | None = None,
    token_reservation: int = DEFAULT_TOKEN_RESERVATION,
) -> tuple[bool, Optional[TerminationReason]]:
    """Decide whether another adapter call is allowed.

    Must be called BEFORE every send_turn. Returns (True, None) when the
    call may proceed, else (False, reason) where reason is one of
    TURN_LIMIT | TOKEN_LIMIT | TIMEOUT.

    Checks (in hard-stop order):
    1. Wall-clock deadline exceeded -> TIMEOUT.
    2. Candidate turns exhausted -> TURN_LIMIT.
    3. Token budget (including conservative reservation) exhausted -> TOKEN_LIMIT.
    """
    current = _now(now)
    reservation = max(int(token_reservation), DEFAULT_TOKEN_RESERVATION)

    deadline = float(state.get("timeout_deadline", current))
    if current >= deadline:
        return False, TIMEOUT

    used_turns = int(state.get("used_candidate_turns", 0))
    if used_turns >= int(limits.max_candidate_turns):
        return False, TURN_LIMIT

    used_tokens = int(state.get("used_total_tokens", 0))
    if used_tokens + reservation > int(limits.max_total_tokens):
        return False, TOKEN_LIMIT

    return True, None


def record_turn_consumption(
    state: AgentState,
    *,
    agent_tokens: int = 0,
    target_tokens: int = 0,
) -> AgentState:
    """Charge one completed candidate turn against the state budgets.

    Increments used_candidate_turns by exactly 1 and used_total_tokens by
    agent_tokens + target_tokens. Mutates and returns the same state dict
    for LangGraph-style in-place updates.

    Raises ValueError on negative token counts to catch provider bugs early.
    """
    if agent_tokens < 0 or target_tokens < 0:
        raise ValueError(
            f"token counts must be non-negative "
            f"(agent={agent_tokens}, target={target_tokens})"
        )
    state["used_candidate_turns"] = int(state.get("used_candidate_turns", 0)) + 1
    state["used_total_tokens"] = (
        int(state.get("used_total_tokens", 0)) + int(agent_tokens) + int(target_tokens)
    )
    return state


def remaining_turns(state: AgentState, limits: RunLimits) -> int:
    """Turns still available (never negative)."""
    return max(0, int(limits.max_candidate_turns) - int(state.get("used_candidate_turns", 0)))


def remaining_tokens(state: AgentState, limits: RunLimits) -> int:
    """Tokens still available (never negative)."""
    return max(0, int(limits.max_total_tokens) - int(state.get("used_total_tokens", 0)))


def can_retry(used_retries: int, limits: RunLimits) -> bool:
    """Whether another SAFE retry is allowed.

    Retries cover idempotent reads only (e.g. get_score, provider JSON
    repair — already capped at one). Ambiguous conversational turns are
    NEVER blind-retried regardless of this budget; a timeout there ends
    the run as FAILURE/TIMEOUT.
    """
    return int(used_retries) < int(limits.max_retries)


__all__ = [
    "DEFAULT_TOKEN_RESERVATION",
    "MAX_CANDIDATE_TURNS_HARD_CAP",
    "TIMEOUT",
    "TOKEN_LIMIT",
    "TURN_LIMIT",
    "RunLimits",
    "TerminationReason",
    "can_retry",
    "can_send_turn",
    "record_turn_consumption",
    "remaining_tokens",
    "remaining_turns",
]
