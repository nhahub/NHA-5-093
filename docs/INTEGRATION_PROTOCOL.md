# Integration and behavior contract (proposed)

## Data flow
Dashboard(M6) -> API(M3) -> RunController(M2) -> validated Adapter(M3) -> target interviewer(M3); response -> Security checks(M4) -> append-only EvidenceStore(M3); human disposition via UI(M6); aggregation/report(M5); M1 owns integration gates.

## Required behaviors
1. `POST /api/v1/runs` validates approved `scenario_id`+`suite_version`, saves immutable config snapshot plus SHA256 canonical JSON hash, and returns 202 QUEUED. No target call is made by the HTTP handler.
2. Single sequential worker loads approved scenario/persona and invokes M2 runner (FIXED or ADAPTIVE). Batch runs are independent; one failed run does not stop the others.
3. Agent-visible `load_policy(rule_ids)` returns sanitized rules, not hidden test labels or secret checker internals. M2 is only allowed to use three internal tool names. No uncontrolled target URL or shell execution.
4. Controller initializes and owns `session_id`, increments and reserves turn/token counters before model/tool calls, persists model usage after responses; end-to-end timeout and optional cancel checked at every graph boundary. If a call times out ambiguously, do not retry `send_turn` blindly.
5. Agent uses `NextProbe` schema. `SEND_TURN` requires message; `STOP` requires null message. Every adaptive step logs the observation and concise next-action reason (not hidden chain of thought).
6. `send_turn` routes to `InterviewerAdapter.start_session -> send_turn -> get_score(optional) -> close_session`, with approved target ID, server-generated idempotency key, one session per scenario, and strict synthetic-only messages.
7. Controller appends TURN and DECISION events; controller calls M4 checker after EVERY returned turn, persists CheckResult, and decides whether to continue. Agent may request checks but cannot suppress mandatory verification.
8. FAIL check => immutable machine proposal with rule/evidence spans; no `CONFIRMED` until M6 reviewer POST creates ReviewDisposition. INCONCLUSIVE is not FAIL.
9. Retest only references an original **reviewer-confirmed** failure; copy original scenario, method, seed, budgets and model settings, change only target_version to hardened and record mitigation version; controlled replay not guaranteed byte-for-byte identical.
10. `GET` requests are read-only, including polling; pagination cursor refers to `seq`; UI never calculates canonical metrics by itself.
11. A report exposes numerator, denominator, failures, excluded/pending/inconclusive counts. Null metric for a zero denominator, never zero by assumption.
12. Every run stores `target_version`, `policy_version`, `scenario/suite_version`, checker version, model settings, timestamps, estimated cost/usage when measurable.

## HTTP semantics
- 200 GET success/cancel idempotent; 201 review appended; 202 queue create; 400 malformed semantic request; 404 unknown ID; 409 wrong run state/version mismatch/attempt to retest unconfirmed; 422 schema-invalid; 503 adapter/model temporarily unavailable.
- Common error: ErrorResponse `{code,message,details,request_id}`; no stack traces or secrets to UI.
- GET `/api/v1/runs/{run_id}/events?cursor=&limit=50` returns `{items:[AuditEvent],next_cursor:string|null}` ordered by per-run `seq` ascending; cursor is the last returned integer `seq` string.
- GET `/api/v1/runs/{run_id}/findings` same collection envelope; `next_cursor` uses `finding_id` stable lexical order for this endpoint.
- GET report supports `json`, `csv`, `md` via `format` query, with corresponding media types.
- Backend enforces only allowed target versions, never user-supplied hostnames or URLs.

## State invariants
- Run `QUEUED -> RUNNING -> COMPLETED|FAILED|CANCELLED`; QUEUED -> CANCELLED allowed. A completed run's outcome is exactly one of NO_FINDING, PROPOSED_FINDING, INCONCLUSIVE, FAILURE; failure status MAY map outcome FAILURE. Never use reviewer dispositions as run statuses.
- A pending finding is proposal-only. Append review events; derived last valid disposition is reflected in GET Finding. Never mutate original proposal.
- Event `seq` begins at 1 per run, is strictly increasing, and is UNIQUE(run_id,seq). Event payloads for TURN: `{candidate_message,target_response,model_id,usage,latency_ms}`; DECISION: `{observed_fact,strategy_id,decision_reason,usage}`; CHECK: `CheckResult` fields. State events contain `{old_status,new_status,cause}`.
- For a completed target invocation, validate `usage.total_tokens == usage.input_tokens + usage.output_tokens` and record usage of both agent+target where applicable.
- `schema` files define transport validation; database tables mirror contracts but internal schema may include technical IDs and indexes. No secret-bearing fields are logged.

## Independent mock modes
- M3: modes refusal, canary disclosure, scoring, malformed, timeout; controlled by server-side dev fixture, not user query.
- M2: fake strategy provider returns deterministic `NextProbe` based on last_observation; mark traces MOCK.
- M4: `CheckResult` fixtures PASS, FAIL, INCONCLUSIVE.
- M5: approved DEVELOPMENT, hidden HELD_OUT, DEMO, and paired dialect fixtures; sample report.
- M6: use only `contracts/examples/` for mocked responses.

## Pending retest response
`GET /api/v1/retests/{retest_id}` always returns a `RetestView`; `result` is null until COMPLETED. Do not report mitigation verified during QUEUED/RUNNING/FAILED.
