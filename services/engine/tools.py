"""Tool contracts and strict NextProbe validation for M2 (ADR-03).

Only three tool names are ever visible to the LLM:
  load_policy, send_turn, check_evidence.
Anything else is rejected BEFORE any adapter call.

Security invariants:
- NextProbe.action is SEND_TURN | STOP.
- STOP requires message is None; SEND_TURN requires a non-empty message.
- strategy_id must belong to ALLOWED_STRATEGIES.
- The model supplies only (message + strategy_id); the controller injects
  run_id / session_id / turn_index / idempotency_key.
- Target replies are ALWAYS untrusted data: text that looks like a tool
  call or injection is stored as plain text and never executed.
"""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

# ---------------------------------------------------------------------------
# Allowlisted names (frozen; changes require M1 ADR)
# ---------------------------------------------------------------------------

ALLOWED_TOOLS: tuple[str, str, str] = ("load_policy", "send_turn", "check_evidence")

ALLOWED_STRATEGIES: tuple[str, ...] = (
    "direct_request",
    "indirect_request",
    "multi_turn",
    "benign_control",
    "fixed_script",
    # Canonical-example strategies (contracts/examples/): STOP probes use
    # end_of_budget; decision traces may cite approved_rephrase.
    "end_of_budget",
    "approved_rephrase",
)

ToolName = Literal["load_policy", "send_turn", "check_evidence"]


class UnknownToolError(ValueError):
    """Raised when the model requests a tool outside the allowlist."""


def validate_tool_name(name: str) -> ToolName:
    """Allowlist gate: reject unknown tools before any side effect."""
    if name not in ALLOWED_TOOLS:
        raise UnknownToolError(
            f"unknown tool '{name}'; allowed={list(ALLOWED_TOOLS)}"
        )
    return name  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Sanitized public models (no secrets cross this boundary)
# ---------------------------------------------------------------------------


class PolicyRulePublic(BaseModel):
    """Sanitized rule view for the agent. No forbidden values or labels."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    review_required: bool = True


class CheckResult(BaseModel):
    """Machine-only verification verdict (never a human confirmation)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    check_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    turn_index: int = Field(ge=0)
    rule_id: str = Field(min_length=1)
    result: Literal["PASS", "FAIL", "INCONCLUSIVE"]
    evidence_event_ids: tuple[str, ...] = ()
    evidence_spans: tuple[str, ...] = ()
    checker_version: str = Field(min_length=1)
    reason: str = ""


# ---------------------------------------------------------------------------
# Strict NextProbe parsing (action/strategy/message invariants)
# ---------------------------------------------------------------------------


class NextProbe(BaseModel):
    """Validated structured agent choice."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["SEND_TURN", "STOP"]
    strategy_id: str = Field(min_length=1)
    message: Optional[str] = Field(default=None, max_length=2000)
    observed_fact: str = Field(min_length=1, max_length=2000)
    decision_reason: str = Field(min_length=1, max_length=2000)
    hypothesis: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def _check_invariants(self) -> "NextProbe":
        if self.strategy_id not in ALLOWED_STRATEGIES:
            raise ValueError(
                f"strategy_id '{self.strategy_id}' not in {list(ALLOWED_STRATEGIES)}"
            )
        if self.action == "STOP":
            if self.message is not None:
                raise ValueError("STOP requires message is None")
        else:  # SEND_TURN
            if not isinstance(self.message, str) or not self.message.strip():
                raise ValueError("SEND_TURN requires a non-empty message")
        return self


def parse_next_probe(payload: dict[str, Any]) -> NextProbe:
    """Parse and strictly validate a raw LLM NextProbe dict.

    Raises pydantic.ValidationError on any schema or invariant violation.
    """
    if not isinstance(payload, dict):
        raise ValidationError.from_exception_data(
            "NextProbe",
            [{"type": "dict_type", "loc": (), "input": payload}],
        )
    return NextProbe.model_validate(payload)


# ---------------------------------------------------------------------------
# load_policy: read-only sanitized policy access (ADR-03 tool #1)
# ---------------------------------------------------------------------------

MAX_MESSAGE_CHARS = 2000


def load_policy(
    rule_ids: list[str],
    policies: list[PolicyRulePublic] | None = None,
) -> list[PolicyRulePublic]:
    """Return sanitized public views for the requested rule IDs.

    Read-only: never exposes forbidden values, labels, or checker
    internals (callers only ever hold PolicyRulePublic). Unknown IDs are
    ignored so a stale model request cannot crash the controller loop.
    """
    catalog = list(policies) if policies is not None else []
    wanted = [r for r in rule_ids if isinstance(r, str)]
    return [p for p in catalog if p.rule_id in wanted]


def build_send_turn_request(
    *,
    message: str,
    strategy_id: str,
    run_id: str,
    session_id: str,
    turn_index: int,
) -> dict[str, Any]:
    """Build a controller-owned AdapterTurnRequest.

    Exactly the canonical keys (run_id, session_id, turn_index, message,
    idempotency_key) — no extras, since M3 validates strict schemas.
    The LLM supplies only message + strategy_id; IDs and the idempotency
    key are injected here so freeform model text can never hijack routing.
    Turn index is 1-based per contract (minimum 1, maximum 6).
    """
    if not message or not message.strip():
        raise ValueError("send_turn requires a non-empty message")
    if len(message) > MAX_MESSAGE_CHARS:
        raise ValueError(
            f"send_turn message exceeds {MAX_MESSAGE_CHARS} chars "
            f"(got {len(message)})"
        )
    if strategy_id not in ALLOWED_STRATEGIES:
        raise ValueError(f"strategy_id '{strategy_id}' not in {list(ALLOWED_STRATEGIES)}")
    turn = int(turn_index)
    if turn < 1 or turn > 6:
        raise ValueError(f"turn_index {turn} outside contract range 1..6")
    return {
        "run_id": run_id,
        "session_id": session_id,
        "turn_index": turn,
        "message": message,
        "idempotency_key": f"{run_id}:{turn}",
    }


# ---------------------------------------------------------------------------
# Untrusted-target handling (never execute target text as a tool call)
# ---------------------------------------------------------------------------

_TOOL_CALL_PATTERN = re.compile(
    r"(call\s+tool|send_turn\s*\(|load_policy\s*\(|check_evidence\s*\(|"
    r"ignore\s+(previous|prior)\s+instructions|system\s*:\s*)",
    re.IGNORECASE,
)


def target_text_requests_tool(reply_text: str) -> bool:
    """Detect tool-like / injection phrasing in target output (for logging).

    A True result does NOT authorize execution; the text must still be
    stored as plain data via sanitize_target_text().
    """
    return bool(_TOOL_CALL_PATTERN.search(reply_text or ""))


def sanitize_target_text(reply_text: str) -> str:
    """Treat target output strictly as data: strip null bytes, keep text."""
    if not isinstance(reply_text, str):
        raise ValueError("target reply must be a string")
    return reply_text.replace("\x00", "")


__all__ = [
    "ALLOWED_STRATEGIES",
    "ALLOWED_TOOLS",
    "CheckResult",
    "MAX_MESSAGE_CHARS",
    "NextProbe",
    "PolicyRulePublic",
    "ToolName",
    "UnknownToolError",
    "build_send_turn_request",
    "load_policy",
    "parse_next_probe",
    "sanitize_target_text",
    "target_text_requests_tool",
    "validate_tool_name",
]
