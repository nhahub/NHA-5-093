# PR — M2: Adaptive Red-Team Agent, Baseline Runner & Trace Exports

**Owner:** M2 (Agentic AI Engineer) · **Branch:** `feat/m2-adaptive-agent-traces`
**Reviewer:** M1 (Team Lead) · **Status:** Ready for review (mock-first, zero-cost, offline-green, contract-conformant)

## 1. Module Ownership

This PR touches **only** M2-owned paths plus M2-scoped project files:

* `services/engine/**` — `state, budgets, trace, tools, providers, graph,
  controller, baseline` + `services/engine/mocks/` (test-doubles only,
  never the real `services/api/` backend)
* `tests/engine/**` — 10 test modules (66 collected: 64 pass, 2 live-skip)
* `tests/fixtures/traces/` — 2 certified adaptive trace fixtures
* `scripts/export_traces.py`, `requirements-engine.txt`, `.env.example`,
  `pytest.ini` (marker registration only), `README-engine.md`

No changes to `contracts/`, `agents/`, `docs/`, `services/api/`,
`packages/*`, `apps/dashboard/`, `infra/`, `plans/`, root `README.md`,
`.env.example`, or any other member's directory. No shared schema,
endpoint, or enum was renamed or added. The only dummy key in the
tree is the non-functional `gsk_test` placeholder inside mocked HTTP
tests (no network, no real credentials anywhere; verified by grep sweep).
Local reference PDFs under `docs/` stay untracked (not part of this PR).

## 1b. Canonical contract conformance (verified against origin/main)

After fetching the contract pack, every M2 artifact was aligned and is
now proven by `tests/engine/test_contract_conformance.py` (jsonschema
against `contracts/schemas/*.schema.json` + `contracts/examples/*.json`):

* Turns are **1-based** (contract range 1..6); event **seq starts at 1**;
  actors are the uppercase enum (`AGENT`/`TARGET`/`CHECKER`).
* TURN/DECISION/CHECK payloads match `INTEGRATION_PROTOCOL.md` verbatim
  (exact key sets incl. `model_id`/`latency_ms` on TURN, flat CheckResult
  on CHECK, canonical `usage` triple everywhere).
* Adapter speaks request-object form (`AdapterTurnRequest` 5 keys, no
  extras); `start_session` returns `sess_[0-9a-f]{12}`; malformed mode
  replays the canonical negative payload; `ScoreResult` uses the
  criteria-array shape with a 64-hex transcript hash.
* `execute_run(run_id, config, scenario, adapter, store, checker)` follows
  the `AgentRunner` protocol order; `run_fixed(config, scenario, adapter,
  store)` follows the brief; checker follows `EvidenceChecker`
  `(request, events, rules)`; unknown `method`/`target_version` rejected
  pre-call; `rule_id`s satisfy the canonical 4-segment pattern.
* `to_agent_view()` derives the 7-field `AgentScenarioView` (leak-proof);
  Finding proposals (incl. both certified traces) validate as `Finding`
  with `reviewer_status=PENDING`.

## 2. Deliverables Summary

**Architecture.** LangGraph `StateGraph` executing
`initialize_run → select_probe → validate_action → send_turn →
verify_response → decide_next`, with `close_session → finalize_run` on
`STOP` / budget exhaustion / terminal verdict. `controller.execute_run()`
dispatches `ADAPTIVE` vs `FIXED` under matched budgets from a single entry
point.

**Protected state.** `AgentState` carries the 15 exact contract fields with
fresh per-scenario isolation (proven by leakage tests). The LLM observes
only the frozen `AgentStateView` — no run internals, held-out labels,
`expected_behavior`, or forbidden secret values ever enter prompts
(asserted by `test_agent_view_exposes_no_secrets`).

**Strict budgets.** `max_candidate_turns ≤ 6` (schema-rejected above),
`≥300`-token pre-call reservation against `max_total_tokens`, hard
wall-clock deadline. Every gate is checked **before** each adapter call;
exhaustion records `TURN_LIMIT | TOKEN_LIMIT | TIMEOUT` with zero further
calls.

**Invariants (all test-enforced).**
* The agent/controller can **never** write `CONFIRMED` — violations become
  `PROPOSED_FINDING` + `review_status=PENDING` only.
* Target replies are **untrusted data**: tool-like text
  (`call tool`, `ignore previous instructions`, …) is detected for logging
  but stored as plain text and never executed.
* Only `load_policy | send_turn | check_evidence` are callable; anything
  else is rejected pre-call. The model supplies `message + strategy_id`
  only — `run_id / session_id / turn_index / idempotency_key`
  (`f"{run_id}:{turn_index}"`) are controller-injected.
* `STOP ⇔ message is None`; `SEND_TURN` requires a non-empty message and
  an allowlisted `strategy_id`. Invalid provider JSON gets exactly one
  retry, then the run ends `INCONCLUSIVE` — never a blind send.

**Triple free runtime.** `DeterministicMockProvider` (offline, seeded,
CI-safe) · `GroqProvider` (`GROQ_API_KEY` env-only, default
`llama-3.3-70b-versatile` → fallback `llama-3.1-8b-instant`, JSON mode,
precise `usage` charged into the token budget and `DECISION` events) ·
`OllamaProvider` (default `http://localhost:11434`, `qwen2.5:7b`) — all
behind `get_provider("mock"|"groq"|"ollama")` with zero graph/controller
changes.

**Baseline.** `run_fixed()` replays `scenario.fixed_prompts` in order with
identical budgets, zero adaptation (never reads `last_observation`), and
logs `unused_prompts` lost to budget/early-stop for fair
adaptive-vs-fixed comparison. Ends with a versioned `ScoreResult` via
`adapter.get_score()` (safe read, retried per `max_retries`, surfaced as
`score`/`score_error` — never invented).

**Public tool surface (Ch.20 interface).** `tools.load_policy()` (sanitized
subset, unknown IDs ignored), `controller.send_turn()` (injects IDs +
idempotency key, asserts turn-echo order, sanitizes reply),
`controller.check_evidence()` (typed `CheckResult` list, mandatory
post-turn). Sync mock-first engine ships `execute_run_async` /
`run_adaptive_async` / `load_policy_async` shims for the proposed async
signature. Target versions allowlisted (`vulnerable-v1`/`hardened-v1`,
rejected pre-call); `max_retries` gates safe-read retries only (never
blind conversational resends); `cancel` callable yields idempotent
`CANCELLED`; `replay.replay_trace()` validates stored-trace completeness
for M5. Receipts carry `resolved_versions` (`model_id`, `target_version`,
`policy_version`, `seed`). Graph nodes delegate to the same controller
wrappers — `test_graph_controller_parity` proves identical outcomes.

## 3. Test Results Matrix — 81 passed, 2 live-skipped, 0 failed

| Module | File | Tests | Result |
|---|---|---|---|
| State isolation, view, agent-view projection (+`test_no_state_leak` alias) | `test_state.py` | 9 | ✅ pass |
| Budgets (turn/token/timeout/retry) | `test_budgets.py` | 9 | ✅ pass |
| Decision traces (canonical DECISION/TURN/CHECK) | `test_trace.py` | 5 | ✅ pass |
| NextProbe + allowlist + injection + load_policy + msg-cap + STOP strategy | `test_tools.py` | 7 | ✅ pass |
| Mock adapter modes (canonical signatures) | `test_mocks.py` | 5 | ✅ pass |
| Fixed baseline (+ScoreResult, positional brief signature) | `test_baseline.py` | 7 | ✅ pass |
| Graph compile + budget gates | `test_graph.py` | 5 | ✅ pass |
| Adaptivity branches + never-confirm | `test_adaptivity.py` | 3 | ✅ pass |
| Providers (mocked HTTP, retry, usage, HG fallback) | `test_providers.py` | 11 | ✅ pass |
| Hardening (wrappers, method/target guards, cancel, replay, parity, receipt, async) | `test_hardening.py` | 11 | ✅ pass |
| Schema conformance vs `contracts/` (events, probes, findings, traces) | `test_contract_conformance.py` | 9 | ✅ pass |
| Live provider probes | `test_providers.py` | 2 | ⏭️ skip (need `HIREGUARD_LIVE=1` + key/server) |

Key proofs: `test_refusal_causes_strategy_change` (direct → indirect
pivot), `test_second_branch_trace` (canary → early `STOP`,
adaptive turns < baseline turns), `test_controller_never_self_confirms…`,
`test_no_calls_after_turn/token_limit`, `test_hard_timeout_no_blind_retry`,
`test_graph_controller_parity`, `test_replay_trace_completeness…`,
`test_unknown_target_version_rejected…`, `test_cancellation_stops…`,
`test_agent_view_matches_canonical_shape`,
`test_certified_trace_events_validate`.

Reproduce offline (no keys, no network):

```bash
python3.11 -m pytest tests/engine -v   # 81 passed, 2 skipped
python3.11 scripts/validate_contracts.py  # M1 kit PASS (unchanged)
ruff check services/engine tests/engine scripts/export_traces.py   # clean
flake8 services/engine tests/engine scripts/export_traces.py --max-line-length=120  # clean
```

## 4. Integration Guide for Teammates

**M1 (Lead) — worker hook.** Import one symbol; inject your store/adapter:

```python
from services.engine.controller import execute_run
receipt = execute_run(
    run_id,
    {"method": "ADAPTIVE",  # or "FIXED"
     "target_version": "vulnerable-v1",
     "limits": {"max_candidate_turns": 6, "max_total_tokens": 4000,
                "timeout_seconds": 120, "max_retries": 0},
     "model_settings": {"model_id": "mock-agent-v1", "seed": 17}},
    scenario,        # approved Scenario (M5 derives AgentScenarioView inside)
    adapter,         # InterviewerAdapter: start_session(req) / send_turn(req)
    store,          # append_event(event: AuditEvent)
    checker,        # check_evidence(request, events, rules)
)
# receipt: {run_id, status: COMPLETED|FAILED|CANCELLED, outcome,
#           termination_reason, used_candidate_turns, used_total_tokens,
#           resolved_versions: {model_id, target_version, policy_version,
#                               suite_version, checker_version, seed},
#           result}
```

`store` needs only `append_event(event)`; `adapter` needs
`start_session(req: AdapterStartRequest)` / `send_turn(req:
AdapterTurnRequest)` / `get_score(session_id)` / `close_session`;
`checker` needs `check_evidence(request: CheckRequest, events:
list[AuditEvent], rules: list[PolicyRule])`. Extra knobs:
`cancel=<callable>` for idempotent cancellation, `provider=get_provider(
"groq"|"ollama")` for live firing. No contract
changes required — field names already mirror `contracts/schemas/`.
Any drift found during wiring is a BLOCKER issue to M2, not a silent fix.

**M3 (Backend) — adapter parity.** `services/engine/mocks/mock_adapter.py`
implements your exact expected surface (`start_session → send_turn →
get_score → close_session`) across `refusal / canary_disclosure /
scoring / timeout / malformed`. Swap the mock for the real
`InterviewerAdapter` without touching engine code; `malformed` and
`timeout` cases document how honestly-handled failures look.

**M5 (Evaluation) — certified traces.** Regenerate deterministically with
`python3.11 scripts/export_traces.py`:
* `tests/fixtures/traces/trace_refusal_strategy_pivot.json` — 6-turn
  refusal→indirect adaptation (24 events, ends `TURN_LIMIT`).
* `tests/fixtures/traces/trace_canary_early_stop.json` — 1-turn canary
  capture (`PROPOSED_FINDING`/`PENDING`).
Both carry full `AuditEvent` lists plus counters/strategies/transcripts
for discovery-rate, precision, and branch-divergence analysis.
Validate any trace (including M5-produced ones) with
`services.engine.replay.replay_trace(path)` — checks ID uniqueness,
monotonic seq, per-type keys, conciseness, and counter consistency.

**M6 (Frontend) — event stream.** Every run emits ordered `AuditEvent`
dicts: `DECISION` (`observed_fact, strategy_id, decision_reason,
hypothesis, usage`), `TURN` (`candidate_message, target_response,
usage`), `CHECK` (`check` payload). Arabic transcript strings are plain
text (render `dir=rtl`); machine proposals stay `PENDING` until your
review POST resolves them.

## 5. Limitations & follow-ups (not silent downgrades)

* Live `Groq`/`Ollama` paths are implemented and mocked-tested but not
  live-fired (zero budget for keyed runs); first live firing is a
  supervised follow-up, results to be labeled `MOCK` until then per ADR-10.
* `ruff format --check` reports style drift (19 files predate formatter
  adoption); intentionally **not** mass-reformatted to keep this diff
  reviewable — formatter adoption is proposed as a separate M1-owned
  commit.
