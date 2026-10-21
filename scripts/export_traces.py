"""Regenerate development MOCK traces using the actual async engine and M4."""

import asyncio
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import packages.security as security
from scripts.contracts import ROOT, Contracts
from services.engine.controller import execute_run
from services.engine.mocks.mock_adapter import MockAdapter
from services.engine.mocks.mock_store import MockStore


class DelayedCanary(MockAdapter):
    async def send_turn(self, request):
        response = await super().send_turn(request)
        if len(self.calls) == 1:
            response["reply_text"] = "شكرا، نتابع المقابلة."
        return response


async def export():
    contracts = Contracts()
    for name, run_id, adapter in [
        ("trace_refusal_strategy_pivot.json", "run_trace_refusal", MockAdapter(mode="refusal")),
        (
            "trace_canary_early_stop.json",
            "run_trace_canary",
            DelayedCanary(mode="canary_disclosure"),
        ),
    ]:
        config, scenario = contracts.fixture("RunCreate"), contracts.fixture("Scenario")
        store = MockStore(config, scenario, run_id)
        detail = await execute_run(run_id, config, scenario, adapter, store, security)
        turns = [e for e in store.events if e["event_type"] == "TURN"]
        data = {
            "trace_id": name[:-5],
            "mode": "MOCK",
            "run_id": run_id,
            "terminal_outcome": detail["outcome"],
            "termination_reason": detail["termination_reason"],
            "used_candidate_turns": detail["used_candidate_turns"],
            "used_total_tokens": detail["used_total_tokens"],
            "events": store.events,
            "transcript": [{"turn_index": e["turn_index"], **e["data"]} for e in turns],
            "proposed_findings": store.findings,
            "run_detail": detail,
        }
        path = ROOT / "tests/fixtures/traces" / name
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"MOCK {name}: {len(turns)} turns; {detail['outcome']}")


if __name__ == "__main__":
    asyncio.run(export())
