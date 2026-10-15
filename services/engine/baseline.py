"""Fixed-script baseline runner (non-adaptive) for M2.

run_fixed(config, scenario, adapter, store) consumes
scenario.fixed_prompts strictly in order with the same RunLimits /
token reservation / timeout semantics as the adaptive agent, but NEVER
adapts: message selection never reads last_observation or target
replies. Skipped prompts (budget exhaustion / early stop) are logged in
unused_prompts for an interpretable method comparison. Turns are
1-based (contract range 1..6); event seq begins at 1 per run.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Protocol

from .budgets import RunLimits, can_send_turn, record_turn_consumption
from .findings import build_proposal
from .state import AgentState, create_initial_state, to_agent_view
from .tools import sanitize_target_text
from .trace import build_decision_event, build_turn_event


class EventStore(Protocol):
    def append_event(self, event: dict[str, Any]) -> None: ...


class ListStore:
    """Minimal in-memory EventStore used by tests and Mock-first runs."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def append_event(self, event: dict[str, Any]) -> None:
        self.events.append(event)


FixedChecker = Optional[Callable[[str, int], dict[str, Any]]]


def _default_check(reply_text: str, turn_index: int) -> dict[str, Any]:
    return {"result": "PASS", "rule_id": "POL-BEN-01-GENERIC", "turn_index": turn_index}


def run_fixed(
    config: dict[str, Any],
    scenario: dict[str, Any],
    adapter: Any,
    store: EventStore,
    *,
    run_id: str,
    checker: FixedChecker = None,
    target_version: str = "vulnerable-v1",
    policy_version: str = "policy-v1",
    now: float | None = None,
) -> dict[str, Any]:
    """Execute the fixed-script baseline synchronously (deterministic).

    Returns a result dict with transcript, counters, terminal_outcome,
    termination_reason, unused_prompts, versioned score, machine finding
    proposals, and the final state snapshot.
    """
    from .controller import validate_target_version

    validate_target_version(target_version)
    limits_raw = (config.get("limits", {}) if isinstance(config, dict) else {}) or {}
    limits = limits_raw if isinstance(limits_raw, RunLimits) else RunLimits(**limits_raw)
    check = checker or _default_check
    prompts: list[str] = list(scenario.get("fixed_prompts", []))
    agent_view = to_agent_view(scenario)
    state: AgentState = create_initial_state(
        run_id=run_id,
        scenario_id=agent_view["scenario_id"],
        target_version=target_version,
        policy_version=policy_version,
        persona_ref=agent_view["persona_ref"],
        timeout_seconds=float(limits.timeout_seconds),
    )

    session = adapter.start_session(
        {
            "run_id": run_id,
            "target_version": target_version,
            "role_id": agent_view["role_id"],
            "persona_ref": agent_view["persona_ref"],
        }
    )
    session_id = session["session_id"]

    seq = 1
    termination_reason: str | None = None
    terminal_outcome = "NO_FINDING"
    proposed_findings: list[dict[str, Any]] = []
    executed = 0

    try:
        for position, prompt in enumerate(prompts, start=1):
            allowed, reason = can_send_turn(state, limits, now=now)
            if not allowed:
                termination_reason = reason
                terminal_outcome = "FAILURE" if reason == "TIMEOUT" else "INCONCLUSIVE"
                break
            try:
                response = adapter.send_turn(
                    {
                        "run_id": run_id,
                        "session_id": session_id,
                        "turn_index": position,
                        "message": prompt,
                        "idempotency_key": f"{run_id}:{position}",
                    }
                )
            except TimeoutError:
                termination_reason = "TIMEOUT"
                terminal_outcome = "FAILURE"
                break

            # Defensive: canonical malformed payload -> honest INCONCLUSIVE.
            reply_raw = response.get("reply_text") if isinstance(response, dict) else None
            usage = response.get("usage") if isinstance(response, dict) else None
            if not isinstance(reply_raw, str) or not isinstance(usage, dict):
                termination_reason = "MALFORMED_RESPONSE"
                terminal_outcome = "INCONCLUSIVE"
                break

            reply_text = sanitize_target_text(reply_raw)
            agent_tokens = int(usage.get("input_tokens", 0))
            target_tokens = int(usage.get("output_tokens", 0))

            state["transcript"].append(
                {
                    "turn_index": position,
                    "candidate_message": prompt,  # fixed script: never derived from observation
                    "target_response": reply_text,
                    "agent_tokens": agent_tokens,
                    "target_tokens": target_tokens,
                }
            )
            record_turn_consumption(state, agent_tokens=agent_tokens, target_tokens=target_tokens)
            executed += 1

            turn_event = build_turn_event(
                run_id=run_id,
                seq=seq,
                turn_index=position,
                candidate_message=prompt,
                target_response=reply_text,
                model_id=str(response.get("model_id", "mock-target-v1")),
                usage=usage if isinstance(usage, dict) else {},
                latency_ms=int(response.get("latency_ms", 0)),
            )
            store.append_event(turn_event)
            seq += 1

            # Mandatory check after EVERY response (machine-only verdict).
            check_result = check(reply_text, position)
            check_id = f"chk_{run_id}_{position}"
            state["check_results"].append(
                {
                    "check_id": check_id,
                    "rule_id": str(check_result.get("rule_id", "POL-BEN-01-GENERIC")),
                    "result": str(check_result.get("result", "PASS")),
                    "turn_index": position,
                }
            )
            if str(check_result.get("result")) == "FAIL":
                terminal_outcome = "PROPOSED_FINDING"
                proposed_findings.append(
                    build_proposal(
                        run_id=run_id,
                        scenario_id=agent_view["scenario_id"],
                        rule_id=str(check_result.get("rule_id", "POL-SEC-01-CANARY")),
                        turn_index=position,
                        evidence_event_ids=[turn_event["event_id"]],
                        evidence_spans=list(check_result.get("evidence_spans", [])),
                        reason=str(check_result.get("reason", "fixed baseline FAIL")),
                        verdict="FAIL",
                    )
                )

            event = build_decision_event(
                run_id=run_id,
                seq=seq,
                turn_index=position,
                observed_fact=f"Fixed prompt {position}/{len(prompts)} executed; no adaptation",
                strategy_id="fixed_script",
                decision_reason="Baseline follows pre-reviewed order within budget",
                usage={"input_tokens": agent_tokens, "output_tokens": 0, "total_tokens": agent_tokens},
            )
            store.append_event(event)
            seq += 1

        # Versioned scoring on the same session before close (safe read;
        # retried per limits.max_retries). Never blind-resends turns.
        score: dict[str, Any] | None = None
        score_error: str | None = None
        for _ in range(1 + int(limits.max_retries)):
            try:
                score = dict(adapter.get_score(session_id))
                break
            except Exception as exc:
                score_error = f"{type(exc).__name__}: {exc}"
                score = None
    finally:
        try:
            adapter.close_session(session_id)
        except Exception:
            pass

    unused_prompts = prompts[executed:]
    state["terminal_outcome"] = terminal_outcome  # type: ignore[typeddict-item]

    return {
        "run_id": run_id,
        "scenario_id": state.get("scenario_id", ""),
        "agent_view": agent_view,
        "transcript": list(state.get("transcript", [])),
        "check_results": list(state.get("check_results", [])),
        "proposed_findings": proposed_findings,
        "used_candidate_turns": state.get("used_candidate_turns", 0),
        "used_total_tokens": state.get("used_total_tokens", 0),
        "terminal_outcome": terminal_outcome,
        "termination_reason": termination_reason,
        "unused_prompts": list(unused_prompts),
        "score": score,
        "score_error": score_error,
        "state": state,
    }


__all__ = ["EventStore", "ListStore", "run_fixed"]
