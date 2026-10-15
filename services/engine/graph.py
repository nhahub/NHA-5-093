"""LangGraph adaptive loop for the HireGuard red-team engine (M2).

Node order (approved):
  initialize_run -> select_probe -> validate_action -> send_turn
  -> verify_response -> decide_next (+ close_session -> finalize_run)

Routing:
- STOP action, exhausted budgets, or a decided terminal outcome go to
  close_session -> finalize_run.
- Otherwise decide_next loops back to select_probe.

Side effects (adapter/store) are injected via GraphDeps so tests build a
fresh compiled graph per case with deterministic mocks. Target text is
always treated as untrusted data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from .budgets import RunLimits, can_send_turn, record_turn_consumption
from .providers import DeterministicMockProvider
from .state import AgentState, build_agent_view
from .tools import PolicyRulePublic, parse_next_probe, validate_tool_name
from .trace import build_check_event, build_decision_event, build_turn_event


@dataclass
class GraphDeps:
    provider: Any = field(default_factory=DeterministicMockProvider)
    adapter: Any = None
    checker: Any = None  # callable or module with check_evidence()
    store: Any = None  # object with append_event(event)
    limits: RunLimits = field(default_factory=RunLimits)
    policies: list[PolicyRulePublic] = field(default_factory=list)
    run_id: str = "run_graph"
    session_id: str = ""
    scenario_view: dict[str, Any] | None = None


def node_initialize_run(state: AgentState) -> dict:
    updates: dict[str, Any] = {}
    updates.setdefault("strategy_history", state.get("strategy_history", []) or [])
    if "used_candidate_turns" not in state:
        updates["used_candidate_turns"] = 0
    if "used_total_tokens" not in state:
        updates["used_total_tokens"] = 0
    if "transcript" not in state:
        updates["transcript"] = []
    if "check_results" not in state:
        updates["check_results"] = []
    return updates


def make_nodes(deps: GraphDeps) -> dict[str, Any]:
    seq = {"n": 0}
    last_turn_event: dict[str, Any] = {}

    def _next_seq() -> int:
        seq["n"] += 1
        return seq["n"]

    def _choose(view: Any) -> Any:
        try:
            return deps.provider.choose_probe(view, deps.policies, deps.scenario_view)
        except TypeError:
            return deps.provider.choose_probe(view, deps.policies)

    def select_probe(state: AgentState) -> dict:
        view = build_agent_view(state)
        try:
            probe = _choose(view)
            validated = parse_next_probe(
                probe.model_dump() if hasattr(probe, "model_dump") else dict(probe)
            )
        except Exception as exc:  # invalid provider output -> honest stop
            return {
                "terminal_outcome": "INCONCLUSIVE",
                "last_observation": f"Invalid provider probe blocked: {exc}"[:280],
                "next_probe": None,
            }
        history = list(state.get("strategy_history", [])) + [validated.strategy_id]
        provider_usage = getattr(deps.provider, "last_usage", None) or {}
        provider_tokens = max(0, int(provider_usage.get("total_tokens", 0)))
        new_total = int(state.get("used_total_tokens", 0)) + provider_tokens
        state["used_total_tokens"] = new_total
        turn_number = int(state.get("used_candidate_turns", 0)) + 1
        event = build_decision_event(
            run_id=deps.run_id,
            seq=_next_seq(),
            turn_index=turn_number,
            observed_fact=validated.observed_fact,
            strategy_id=validated.strategy_id,
            decision_reason=validated.decision_reason,
            usage={
                "input_tokens": max(0, int(provider_usage.get("input_tokens", 0))),
                "output_tokens": max(0, int(provider_usage.get("output_tokens", 0))),
                "total_tokens": provider_tokens,
            },
        )
        if deps.store is not None:
            deps.store.append_event(event)
        return {
            "next_probe": validated.model_dump(),
            "hypothesis": validated.hypothesis,
            "strategy_history": history,
            "last_observation": validated.observed_fact,
            "used_total_tokens": new_total,
        }

    def validate_action(state: AgentState) -> dict:
        # Schema already enforced in select_probe. Stamp budget exhaustion
        # here so finalize semantics match controller.run_adaptive exactly:
        # TIMEOUT -> FAILURE, other exhaustion -> INCONCLUSIVE.
        from .budgets import TIMEOUT as _TIMEOUT

        if state.get("terminal_outcome"):
            return {}
        validate_tool_name("send_turn")
        probe = state.get("next_probe") or {}
        if probe.get("action") == "STOP":
            return {}
        allowed, reason = can_send_turn(state, deps.limits)
        if allowed:
            return {}
        return {"terminal_outcome": "FAILURE" if reason == _TIMEOUT else "INCONCLUSIVE"}

    def send_turn(state: AgentState) -> dict:
        # Delegates to the shared controller wrapper so graph and
        # run_adaptive can never diverge (parity invariant).
        from .controller import send_turn as controller_send_turn

        probe_raw = state.get("next_probe") or {}
        message = str(probe_raw.get("message", ""))
        strategy_id = str(probe_raw.get("strategy_id", "direct_request"))
        turn_number = int(state.get("used_candidate_turns", 0)) + 1
        try:
            response = controller_send_turn(
                adapter=deps.adapter,
                session_id=deps.session_id,
                message=message,
                run_id=deps.run_id,
                turn_index=turn_number,
                strategy_id=strategy_id,
            )
        except TimeoutError:
            return {"terminal_outcome": "FAILURE", "last_observation": "Target timeout; no blind retry"}
        except ValueError:
            return {"terminal_outcome": "INCONCLUSIVE", "last_observation": "Malformed target reply; abstaining"}
        reply = str(response["reply_text"])
        usage = response.get("usage", {})
        if not isinstance(usage, dict):
            usage = {}
        agent_tokens = int(usage.get("input_tokens", 0))
        target_tokens = int(usage.get("output_tokens", 0))
        transcript = list(state.get("transcript", [])) + [
            {
                "turn_index": turn_number,
                "candidate_message": message,
                "target_response": reply,
                "agent_tokens": agent_tokens,
                "target_tokens": target_tokens,
            }
        ]
        record_turn_consumption(state, agent_tokens=agent_tokens, target_tokens=target_tokens)
        turn_event = build_turn_event(
            run_id=deps.run_id,
            seq=_next_seq(),
            turn_index=turn_number,
            candidate_message=message,
            target_response=reply,
            model_id=str(response.get("model_id", "mock-target-v1")),
            usage=usage,
            latency_ms=int(response.get("latency_ms", 0)),
        )
        last_turn_event.clear()
        last_turn_event.update(turn_event)
        if deps.store is not None:
            deps.store.append_event(turn_event)
        return {
            "transcript": transcript,
            "used_candidate_turns": state.get("used_candidate_turns", 0),
            "used_total_tokens": state.get("used_total_tokens", 0),
            "last_observation": f"Turn {turn_number}: target replied: {reply[:200]}",
        }

    def verify_response(state: AgentState) -> dict:
        from .controller import check_evidence as controller_check_evidence

        transcript = state.get("transcript", [])
        if not transcript:
            return {}
        last = transcript[-1]
        turn_number = int(last.get("turn_index", 1))
        rule_ids = [p.rule_id for p in deps.policies] or ["POL-SEC-01-CANARY"]
        rule_dicts = [p.model_dump(mode="json") for p in deps.policies]
        events = [dict(last_turn_event)] if last_turn_event else []
        results = controller_check_evidence(
            checker=deps.checker,
            run_id=deps.run_id,
            turn_index=turn_number,
            rule_ids=rule_ids,
            events=events,
            rules=rule_dicts,
        )
        cached = list(state.get("check_results", []))
        for res in results:
            cached.append(
                {
                    "check_id": res.check_id,
                    "rule_id": res.rule_id,
                    "result": res.result,
                    "turn_index": int(res.turn_index),
                }
            )
            if deps.store is not None:
                deps.store.append_event(
                    build_check_event(
                        run_id=deps.run_id, seq=_next_seq(),
                        turn_index=turn_number, check=res,
                    )
                )
        updates: dict[str, Any] = {"check_results": cached}
        if any(r.result == "FAIL" for r in results):
            updates["terminal_outcome"] = "PROPOSED_FINDING"
        return updates

    def decide_next(state: AgentState) -> dict:
        # Stamp exact budget exhaustion so a fully-consumed budget ends
        # INCONCLUSIVE here, identical to the controller's next gate check.
        if state.get("terminal_outcome"):
            return {}
        allowed, reason = can_send_turn(state, deps.limits)
        if allowed:
            return {}
        from .budgets import TIMEOUT as _TIMEOUT

        return {"terminal_outcome": "FAILURE" if reason == _TIMEOUT else "INCONCLUSIVE"}

    def close_session(state: AgentState) -> dict:
        _ = state
        try:
            if deps.adapter is not None and deps.session_id:
                deps.adapter.close_session(deps.session_id)
        except Exception:
            pass
        return {}

    def finalize_run(state: AgentState) -> dict:
        if state.get("terminal_outcome"):
            return {}
        checks = state.get("check_results", [])
        if any(c.get("result") == "FAIL" for c in checks):
            return {"terminal_outcome": "PROPOSED_FINDING"}
        return {"terminal_outcome": "NO_FINDING"}

    return {
        "initialize_run": node_initialize_run,
        "select_probe": select_probe,
        "validate_action": validate_action,
        "send_turn": send_turn,
        "verify_response": verify_response,
        "decide_next": decide_next,
        "close_session": close_session,
        "finalize_run": finalize_run,
    }


def _route_after_validate(state: AgentState, deps: GraphDeps) -> str:
    if state.get("terminal_outcome"):
        return "finish"
    probe = state.get("next_probe") or {}
    if probe.get("action") == "STOP":
        return "finish"
    allowed, _ = can_send_turn(state, deps.limits)
    return "send" if allowed else "finish"


def _route_after_decide(state: AgentState, deps: GraphDeps) -> str:
    if state.get("terminal_outcome") == "PROPOSED_FINDING":
        return "finish"
    if state.get("terminal_outcome") in ("FAILURE", "INCONCLUSIVE"):
        return "finish"
    allowed, _ = can_send_turn(state, deps.limits)
    return "continue" if allowed else "finish"


def build_graph(deps: GraphDeps):
    """Compile the adaptive StateGraph with injected mock-backed deps."""
    nodes = make_nodes(deps)
    builder: StateGraph = StateGraph(AgentState)
    for name, fn in nodes.items():
        builder.add_node(name, fn)
    builder.add_edge(START, "initialize_run")
    builder.add_edge("initialize_run", "select_probe")
    builder.add_edge("select_probe", "validate_action")
    builder.add_conditional_edges(
        "validate_action",
        lambda s: _route_after_validate(s, deps),
        {"send": "send_turn", "finish": "close_session"},
    )
    builder.add_edge("send_turn", "verify_response")
    builder.add_edge("verify_response", "decide_next")
    builder.add_conditional_edges(
        "decide_next",
        lambda s: _route_after_decide(s, deps),
        {"continue": "select_probe", "finish": "close_session"},
    )
    builder.add_edge("close_session", "finalize_run")
    builder.add_edge("finalize_run", END)
    return builder.compile()


RouteDecision = Literal["send", "finish", "continue"]

__all__ = [
    "GraphDeps",
    "build_graph",
    "make_nodes",
    "node_initialize_run",
]
