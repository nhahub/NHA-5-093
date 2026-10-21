"""Canonical async store double. No DB/application lifecycle coverage is claimed."""

import copy
import uuid

from scripts.contracts import Contracts
from services.engine.controller import canonical_hash, utc_now


class MockStore:
    def __init__(self, config, scenario, run_id="run_012345abcdef", *, preexisting=True):
        self.contracts = Contracts()
        self.events, self.checks, self.findings = [], [], []
        self.detail = {
            "run_id": run_id,
            "status": "RUNNING",
            "outcome": None,
            "config": copy.deepcopy(config),
            "config_hash": canonical_hash(config),
            "resolved_versions": {
                "role_version": "role-v1",
                "policy_version": "policy-v1",
                "scenario_hash": canonical_hash(scenario),
                "checker_version": "m4-checks-1.0.0",
                "target_model_id": "mock-target-v1",
            },
            "used_candidate_turns": 0,
            "used_total_tokens": 0,
            "created_at": utc_now(),
            "started_at": utc_now(),
            "finished_at": None,
            "termination_reason": None,
        }
        if preexisting:
            self._append(
                run_id,
                "STATE",
                "CONTROLLER",
                0,
                {"old_status": None, "new_status": "QUEUED", "cause": "Created"},
            )
            self._append(
                run_id,
                "STATE",
                "CONTROLLER",
                0,
                {"old_status": "QUEUED", "new_status": "RUNNING", "cause": "Worker claimed"},
            )

    def _append(self, run_id, kind, actor, turn, data):
        event = {
            "event_id": "evt_" + uuid.uuid4().hex[:12],
            "run_id": run_id,
            "seq": len(self.events) + 1,
            "event_type": kind,
            "actor": actor,
            "turn_index": turn,
            "occurred_at": utc_now(),
            "data": copy.deepcopy(data),
        }
        self.contracts.validate("AuditEvent", event)
        self.events.append(event)
        return copy.deepcopy(event)

    async def append_event(self, run_id, event_type, actor, turn_index, data):
        return self._append(run_id, event_type, actor, turn_index, data)

    async def get_run(self, run_id):
        assert run_id == self.detail["run_id"]
        return copy.deepcopy(self.detail)

    async def list_events(self, run_id, after_seq, limit):
        rows = [e for e in self.events if e["seq"] > (after_seq or 0) and e["run_id"] == run_id]
        items = rows[:limit]
        return {
            "items": copy.deepcopy(items),
            "next_cursor": str(items[-1]["seq"]) if len(rows) > limit else None,
        }

    async def save_check(self, check):
        self.contracts.validate("CheckResult", check)
        self.checks.append(copy.deepcopy(check))
        return copy.deepcopy(check)

    async def save_finding(self, finding):
        self.contracts.validate("Finding", finding)
        self.findings.append(copy.deepcopy(finding))
        return copy.deepcopy(finding)
