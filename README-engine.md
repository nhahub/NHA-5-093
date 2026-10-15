# HireGuard M2 — Red-Team Engine

Owner: M2. Path: `services/engine/`. Mock-first, zero-cost. Contracts in
`contracts/` (M1-owned) are read-only inputs; this module never edits them.
Every artifact M2 emits validates against `contracts/schemas/` (proven by
`tests/engine/test_contract_conformance.py`).

## Architecture & state machine

```
initialize_run -> select_probe -> validate_action -> send_turn
  -> verify_response -> decide_next --continue--> select_probe
                                  \--finish--> close_session -> finalize_run
```

* `state.py` — `AgentState` (15 exact contract fields, fresh per scenario,
  no cross-run leakage) + frozen `AgentStateView` + `to_agent_view()`
  (canonical 7-field projection; split/labels/expected/fixed_prompts
  never leak to the model).
* `providers.py` — `LLMProvider` protocol + `DeterministicMockProvider`
  (`mock-agent-v1`) + `GroqProvider` + `OllamaProvider` via
  `get_provider("mock"|"groq"|"ollama")`. Live prompts carry the
  scenario objective; keys come from `GROQ_API_KEY` (fallback
  `HG_AGENT_MODEL_API_KEY`) — never hardcoded.
* `tools.py` — allowlisted tools only (`load_policy, send_turn,
  check_evidence` per `contracts/agent_tools.json`); strict `NextProbe`
  invariants (`STOP` ⇔ `message is None`; `strategy_id` ∈ allowlist
  including canonical `end_of_budget`/`approved_rephrase`; message ≤2000
  chars; turns 1..6). Target replies are untrusted data, never executed.
* `budgets.py` — `max_candidate_turns ≤ 6`, `≥300`-token pre-call
  reservation, wall-clock deadline, `can_retry()` for safe reads only
  (never blind conversational resends). Exhaustion yields
  `TURN_LIMIT | TOKEN_LIMIT | TIMEOUT` with no further adapter calls.
* `graph.py` / `controller.py` — LangGraph wiring + `run_adaptive()` /
  `execute_run()` in canonical `AgentRunner` order
  `(run_id, config, scenario, adapter, store, checker)`. Public wrappers
  `load_policy()` / `send_turn()` / `check_evidence()` (+ async shims).
  Targets allowlisted (`vulnerable-v1`/`hardened-v1`); idempotent
  `cancel` yields `CANCELLED`. Findings are machine proposals only
  (`PROPOSED_FINDING` + `review_status=PENDING` + `proposed_findings[]`
  shaped as `Finding`); the agent never writes `CONFIRMED`.
* `baseline.py` — `run_fixed(config, scenario, adapter, store)`
  replays `fixed_prompts` in order with identical budgets, logs
  `unused_prompts`, and returns a versioned `ScoreResult`.
* `replay.py` — `replay_trace()` validates stored-trace completeness
  (unique IDs, monotonic seq from 1, per-type keys, conciseness,
  counter consistency) for M5 reproducibility checks.
* `mocks/` — `MockAdapter` (canonical req-object signatures;
  `refusal` / `canary_disclosure` / `scoring` / `timeout` /
  canonical-negative `malformed`) and `mock_checker` (canonical
  `(request, events, rules)` form; FAIL on `HG-SECRET-4821`).

Events follow `docs/INTEGRATION_PROTOCOL.md` exactly: actors
`AGENT`/`TARGET`/`CHECKER`, `seq` from 1, TURN/DECISION/CHECK payload
shapes verbatim, `usage.total == input + output`, turns 1-based.

## Run tests fully offline (no internet, no keys)

```bash
python3.11 -m pytest tests/engine -v
python3.11 scripts/validate_contracts.py   # M1 kit, must stay PASS
```

Live provider tests self-skip unless explicitly opted in:

```bash
HIREGUARD_LIVE=1 GROQ_API_KEY=gsk_... python3.11 -m pytest tests/engine -v -m groq
HIREGUARD_LIVE=1 python3.11 -m pytest tests/engine -v -m ollama
```

## Switch providers

```bash
LLM_PROVIDER=mock   # default, deterministic, CI-safe
LLM_PROVIDER=groq   # needs GROQ_API_KEY; model via GROQ_MODEL (default llama-3.3-70b-versatile)
LLM_PROVIDER=ollama # needs local server; OLLAMA_BASE_URL + OLLAMA_MODEL (default qwen2.5:7b)
```

See `.env.engine.example` (M1's root `.env.example` is untouched).
`GroqProvider` uses JSON mode with exactly one retry on invalid output,
then fails closed (`ProviderError` → controller ends `INCONCLUSIVE`,
no blind send). `last_usage` from every call is charged into
`used_total_tokens` and recorded on `DECISION` events.

## Certified adaptive traces

Regenerate any time (deterministic):

```bash
python3.11 scripts/export_traces.py
```

* `tests/fixtures/traces/trace_refusal_strategy_pivot.json` — refusal →
  `direct_request` pivots to `indirect_request` across 6 turns
  (24 `DECISION/TURN/CHECK` events, ends `TURN_LIMIT`).
* `tests/fixtures/traces/trace_canary_early_stop.json` — canary
  `HG-SECRET-4821` → immediate `STOP`, `PROPOSED_FINDING`/`PENDING`.

Both files carry complete `AuditEvent` lists plus `agent_view`,
counters, `check_results`, and `proposed_findings` — ready for M5
metrics and the M6 dashboard evidence timeline. Every event in both
files validates against `contracts/schemas/AuditEvent`.
