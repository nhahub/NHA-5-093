"""Canonical async AgentRunner. M3 owns lifecycle persistence and allocated events."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import re
from datetime import UTC, datetime
from time import monotonic

from langsmith import tracing_context

from packages.security import CheckRequest, PolicyRulePublic, load_rules, to_finding, to_public
from scripts.contracts import ContractError, Contracts

from .graph import build_graph
from .providers import get_provider, validate_usage
from .state import build_agent_view, create_initial_state, to_agent_view
from .tools import NextProbe, build_send_turn_request, parse_next_probe
from .trace import build_decision_event, build_turn_event

ALLOWED_TARGET_VERSIONS = ("vulnerable-v1", "hardened-v1")
ALLOWED_METHODS = ("ADAPTIVE", "FIXED")


def canonical_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def utc_now():
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class RunStopped(Exception):
    def __init__(self, reason, outcome="INCONCLUSIVE"):
        self.reason, self.outcome = reason, outcome
        super().__init__(reason)


def validate_target_version(value):
    if value not in ALLOWED_TARGET_VERSIONS:
        raise ValueError("unknown target_version")
    return value


def validate_method(value):
    if value not in ALLOWED_METHODS:
        raise ValueError("unknown method")
    return value


def default_policies():
    return [PolicyRulePublic.model_validate(p.model_dump()) for p in to_public(load_rules())]


def payload(value):
    return value.model_dump(mode="json", by_alias=True) if hasattr(value, "model_dump") else value


class _Execution:
    def __init__(self, run_id, config, scenario, adapter, store, checker, provider, cancel):
        self.run_id, self.config, self.scenario = (
            run_id,
            copy.deepcopy(config),
            copy.deepcopy(scenario),
        )
        self.adapter, self.store, self.checker = adapter, store, checker
        self.provider, self.cancel = provider, cancel
        self.contracts = Contracts()
        self.session_id = None
        self.last_seq = 0
        self.seen_ids = set()
        self.uncertain = False
        self.outcome, self.reason = "NO_FINDING", "PROBE_STOP"
        self.state = create_initial_state(
            run_id=run_id,
            scenario_id=scenario["scenario_id"],
            target_version=config["target_version"],
        )
        self.deadline = monotonic() + config["limits"]["timeout_seconds"]

    async def io(self, operation):
        # Evidence writes remain possible after inference timeout, but cannot hang forever.
        async with asyncio.timeout(5):
            return await operation()

    async def event(self, kind, actor, turn, data):
        event = payload(
            await self.io(lambda: self.store.append_event(self.run_id, kind, actor, turn, data))
        )
        self.contracts.validate("AuditEvent", event)
        if (
            event["run_id"] != self.run_id
            or event["seq"] != self.last_seq + 1
            or event["event_id"] in self.seen_ids
            or event["event_type"] != kind
            or event["actor"] != actor
            or event["turn_index"] != turn
            or event["data"] != data
        ):
            raise ContractError("Store did not preserve the allocated event")
        self.last_seq = event["seq"]
        self.seen_ids.add(event["event_id"])
        return event

    async def guard(self, reserve=0, *, check_turn=True):
        if type(reserve) is not int or reserve < 0:
            raise RunStopped("TOKEN_LIMIT")
        if self.cancel is not None:
            cancelled = self.cancel()
            if hasattr(cancelled, "__await__"):
                cancelled = await cancelled
            if cancelled:
                raise RunStopped("CANCELLED")
        if monotonic() >= self.deadline:
            raise RunStopped("TIMEOUT", "FAILURE")
        limits = self.config["limits"]
        if check_turn and self.state["used_candidate_turns"] >= limits["max_candidate_turns"]:
            raise RunStopped("TURN_LIMIT")
        if self.state["used_total_tokens"] + reserve > limits["max_total_tokens"]:
            raise RunStopped("TOKEN_LIMIT")

    async def model_call(self, operation, *, reserve=0):
        await self.guard(reserve)
        try:
            async with asyncio.timeout(max(0.001, self.deadline - monotonic())):
                return await operation()
        except TimeoutError as exc:
            raise RunStopped("TIMEOUT", "FAILURE") from exc

    async def initialize(self):
        detail = payload(await self.io(lambda: self.store.get_run(self.run_id)))
        self.contracts.validate("RunDetail", detail)
        self.detail = copy.deepcopy(detail)
        cursor = None
        while True:
            page = await self.io(
                lambda cursor=cursor: self.store.list_events(self.run_id, cursor, 100)
            )
            for event in page["items"]:
                self.contracts.validate("AuditEvent", payload(event))
                event = payload(event)
                if (
                    event["seq"] != self.last_seq + 1
                    or event["run_id"] != self.run_id
                    or event["event_id"] in self.seen_ids
                ):
                    raise ContractError("Invalid pre-existing evidence sequence")
                self.last_seq = event["seq"]
                self.seen_ids.add(event["event_id"])
            next_cursor = page["next_cursor"]
            if next_cursor is None:
                break
            if not page["items"] or int(next_cursor) != self.last_seq:
                raise ContractError("Invalid evidence cursor")
            cursor = int(next_cursor)
        self.contracts.validate("RunCreate", self.config)
        self.contracts.validate("Scenario", self.scenario)
        self.provider = self.provider or get_provider(self.config["model_settings"])
        if self.provider.model_id != self.config["model_settings"]["model_id"]:
            raise RunStopped("INVALID_CONFIGURATION")
        if (
            detail["run_id"] != self.run_id
            or detail["config"] != self.config
            or detail["status"] != "RUNNING"
            or detail["used_candidate_turns"] != 0
            or detail["used_total_tokens"] != 0
            or detail["config_hash"] != canonical_hash(self.config)
            or not self.scenario["approved"]
            or self.scenario["scenario_id"] != self.config["scenario_id"]
            or self.scenario["suite_version"] != self.config["suite_version"]
            or detail["resolved_versions"]["scenario_hash"] != canonical_hash(self.scenario)
        ):
            raise RunStopped("INVALID_CONFIGURATION", "FAILURE")
        self.view = to_agent_view(self.scenario)
        catalog = {r.rule_id: r for r in load_rules()}
        ids = self.scenario["rule_ids"]
        if len(set(ids)) != len(ids) or any(i not in catalog for i in ids):
            raise RunStopped("INVALID_CONFIGURATION")
        self.rules = [catalog[i] for i in ids]
        self.public = to_public(self.rules)
        versions = detail["resolved_versions"]
        if (
            any(r.version != versions["policy_version"] for r in self.rules)
            or getattr(self.checker, "CHECKER_VERSION", None) != versions["checker_version"]
        ):
            raise RunStopped("INVALID_CONFIGURATION")
        await self.guard()
        request = {
            "run_id": self.run_id,
            "target_version": self.config["target_version"],
            "role_id": self.scenario["role_id"],
            "persona_ref": self.scenario["persona_ref"],
        }
        self.contracts.validate("AdapterStartRequest", request)
        response = payload(await self.model_call(lambda: self.adapter.start_session(request)))
        # Preserve a returned identifier for cleanup even when the rest is malformed.
        if isinstance(response, dict) and isinstance(response.get("session_id"), str):
            self.session_id = response["session_id"]
        self.contracts.validate("AdapterStartResponse", response)
        if response["target_version"] != self.config["target_version"]:
            raise RunStopped("MALFORMED_RESPONSE")

    async def select(self):
        index = self.state["used_candidate_turns"]
        if self.config["method"] == "FIXED":
            if index >= len(self.scenario["fixed_prompts"]):
                return None
            return NextProbe(
                action="SEND_TURN",
                strategy_id="fixed_script",
                message=self.scenario["fixed_prompts"][index],
                observed_fact=f"Fixed prompt {index + 1}; approved order",
                decision_reason="Replay approved prompt without adaptation",
                hypothesis="Fixed baseline",
            )
        view = build_agent_view(self.state)
        reserve = self.provider.reserve_tokens(view, self.public, self.view)
        await self.guard(reserve)
        raw, failure = None, None
        try:
            raw = await self.model_call(
                lambda: self.provider.choose_probe(view, self.public, self.view), reserve=reserve
            )
        except Exception as exc:
            failure = exc
        usage = validate_usage(self.provider.last_usage)
        self.state["used_total_tokens"] += usage["total_tokens"]
        raw = payload(raw)
        # Persist concise usage evidence even for an invalid model selection.
        data = build_decision_event(
            run_id=self.run_id,
            seq=1,
            turn_index=index + 1,
            observed_fact=str(raw.get("observed_fact", "Invalid probe"))
            if isinstance(raw, dict)
            else "Invalid probe",
            strategy_id=str(raw.get("strategy_id", "end_of_budget"))
            if isinstance(raw, dict)
            else "end_of_budget",
            decision_reason=str(raw.get("decision_reason", "Invalid probe"))
            if isinstance(raw, dict)
            else "Invalid probe",
            usage=usage,
        )["data"]
        await self.event("DECISION", "AGENT", index + 1, data)
        if failure is not None:
            raise failure
        await self.guard()  # provider time/tokens/cancellation cannot authorize a target call
        self.contracts.validate("NextProbe", raw)
        probe = parse_next_probe(raw)
        if usage["output_tokens"] > self.config["model_settings"]["max_output_tokens"]:
            raise RunStopped("TOKEN_LIMIT")
        return probe

    async def step(self):
        await self.guard()
        probe = await self.select()
        if probe is None or probe.action == "STOP":
            self.outcome = "INCONCLUSIVE" if self.uncertain else "NO_FINDING"
            return True
        turn = self.state["used_candidate_turns"] + 1
        if self.config["method"] == "FIXED":
            data = build_decision_event(
                run_id=self.run_id,
                seq=1,
                turn_index=turn,
                observed_fact=probe.observed_fact,
                strategy_id=probe.strategy_id,
                decision_reason=probe.decision_reason,
            )["data"]
            await self.event("DECISION", "AGENT", turn, data)
        self.state["strategy_history"].append(probe.strategy_id)
        self.state["hypothesis"] = probe.hypothesis
        request = build_send_turn_request(
            message=probe.message,
            strategy_id=probe.strategy_id,
            run_id=self.run_id,
            session_id=self.session_id,
            turn_index=turn,
        )
        self.contracts.validate("AdapterTurnRequest", request)
        response = payload(
            await self.model_call(lambda: self.adapter.send_turn(request), reserve=300)
        )
        self.contracts.validate("AdapterTurnResponse", response)
        if (
            response["session_id"] != self.session_id
            or response["turn_index"] != turn
            or response["model_id"] != self.detail["resolved_versions"]["target_model_id"]
        ):
            raise RunStopped("MALFORMED_RESPONSE")
        usage = validate_usage(response["usage"])
        self.state["used_total_tokens"] += usage["total_tokens"]
        self.state["used_candidate_turns"] += 1
        reply = response["reply_text"]  # preserve exact text, including Unicode/nulls
        self.state["transcript"].append(
            {
                "turn_index": turn,
                "candidate_message": probe.message,
                "target_response": reply,
                "agent_tokens": usage["input_tokens"],
                "target_tokens": usage["output_tokens"],
            }
        )
        self.state["last_observation"] = f"Target replied: {reply[:200]}"
        data = build_turn_event(
            run_id=self.run_id,
            seq=1,
            turn_index=turn,
            candidate_message=probe.message,
            target_response=reply,
            model_id=response["model_id"],
            usage=usage,
            latency_ms=response["latency_ms"],
        )["data"]
        event = await self.event("TURN", "TARGET", turn, data)
        req = CheckRequest(
            run_id=self.run_id, turn_index=turn, rule_ids=[r.rule_id for r in self.rules]
        )
        results = self.checker.check_evidence(req, [event], self.rules)
        if not isinstance(results, list) or len(results) != len(self.rules):
            raise RunStopped("INVALID_CHECK_RESULT")
        rows = [payload(r) for r in results]
        if {r.get("rule_id") for r in rows if isinstance(r, dict)} != set(req.rule_ids):
            raise RunStopped("INVALID_CHECK_RESULT")
        for row in rows:
            self.contracts.validate("CheckResult", row)
            if (
                row["run_id"] != self.run_id
                or row["turn_index"] != turn
                or row["checker_version"] != self.detail["resolved_versions"]["checker_version"]
            ):
                raise RunStopped("INVALID_CHECK_RESULT")
            if row["result"] == "FAIL":
                if row["evidence_event_ids"] != [event["event_id"]] or not row["evidence_spans"]:
                    raise RunStopped("INVALID_CHECK_RESULT")
                for span in row["evidence_spans"]:
                    match = re.fullmatch(r"target_response\[(\d+):(\d+)\]", span)
                    if not match or not 0 <= int(match[1]) < int(match[2]) <= len(reply):
                        raise RunStopped("INVALID_CHECK_RESULT")
            saved = payload(await self.io(lambda row=row: self.store.save_check(row)))
            self.contracts.validate("CheckResult", saved)
            if saved != row:
                raise ContractError("Store changed a check")
            await self.event(
                "CHECK",
                "CHECKER",
                turn,
                {k: v for k, v in row.items() if k not in {"run_id", "turn_index"}},
            )
            self.state["check_results"].append(row)
            self.uncertain |= row["result"] == "INCONCLUSIVE"
        await self.guard(check_turn=False)
        failed = [row for row in rows if row["result"] == "FAIL"]
        for row in failed:
            from packages.security import CheckResult

            rule = next(r for r in self.rules if r.rule_id == row["rule_id"])
            finding = to_finding(
                CheckResult.model_validate(row), rule, self.scenario["scenario_id"]
            )
            self.contracts.validate("Finding", finding)
            saved = payload(await self.io(lambda finding=finding: self.store.save_finding(finding)))
            self.contracts.validate("Finding", saved)
            if saved != finding or saved["reviewer_status"] != "PENDING":
                raise ContractError("Store changed a machine proposal")
        if failed:
            self.outcome, self.reason = "PROPOSED_FINDING", "CHECK_FAIL"
            return True
        if self.config["method"] == "FIXED" and turn >= len(self.scenario["fixed_prompts"]):
            self.outcome = "INCONCLUSIVE" if self.uncertain else "NO_FINDING"
            return True
        return False

    async def run(self):
        try:
            await self.initialize()
            await build_graph(self).ainvoke({"done": False}, config={"recursion_limit": 32})
        except asyncio.CancelledError:
            self.outcome, self.reason = "INCONCLUSIVE", "CANCELLED"
        except RunStopped as exc:
            self.outcome, self.reason = exc.outcome, exc.reason
        except Exception:
            self.outcome, self.reason = "INCONCLUSIVE", "EXECUTION_FAILURE"
        finally:
            if self.session_id:
                try:
                    await self.io(lambda: self.adapter.close_session(self.session_id))
                except Exception:
                    self.outcome, self.reason = "INCONCLUSIVE", "EXECUTION_FAILURE"
        if not hasattr(self, "detail"):
            raise ContractError("Cannot return RunDetail without valid persisted metadata")
        result = copy.deepcopy(self.detail)
        result.update(
            status="CANCELLED"
            if self.reason == "CANCELLED"
            else "FAILED"
            if self.outcome == "FAILURE"
            else "COMPLETED",
            outcome=self.outcome,
            used_candidate_turns=self.state["used_candidate_turns"],
            used_total_tokens=self.state["used_total_tokens"],
            finished_at=utc_now(),
            termination_reason=self.reason,
        )
        self.contracts.validate("RunDetail", result)
        if self.outcome in {"INCONCLUSIVE", "FAILURE"} and self.reason != "CANCELLED":
            await self.event(
                "ERROR",
                "CONTROLLER",
                self.state["used_candidate_turns"],
                {
                    "code": self.reason,
                    "message": "Execution stopped; no successful finding is inferred",
                },
            )
        await self.event(
            "STATE",
            "CONTROLLER",
            self.state["used_candidate_turns"],
            {"old_status": "RUNNING", "new_status": result["status"], "cause": self.reason},
        )
        return result


async def execute_run(
    run_id, config, scenario, adapter, store, checker, *, provider=None, cancel=None
):
    # Public positional order is the central AgentRunner Protocol. Extra hooks
    # are controller-owned test seams, never user/LLM fields.
    config, scenario = payload(config), payload(scenario)
    with tracing_context(enabled=False):
        return await _Execution(
            run_id, config, scenario, adapter, store, checker, provider, cancel
        ).run()


execute_run_async = execute_run


async def run_adaptive(run_id, config, scenario, adapter, store, checker, **kwargs):
    if config["method"] != "ADAPTIVE":
        raise ValueError("ADAPTIVE configuration required")
    return await execute_run(run_id, config, scenario, adapter, store, checker, **kwargs)


run_adaptive_async = run_adaptive
