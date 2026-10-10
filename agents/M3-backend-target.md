# M3 - API, target interviewer, persistence and job worker
**Member name:** TO_BE_ASSIGNED_BY_LEAD. **Owned paths:** `services/api/**`, `services/api/target/**`, `services/api/storage/**`, M3 transport/DB tests.

## Inputs
- Canonical `contracts/openapi.yaml`; all schemas; M2 runner callable; M4 checker callable; role/rubric/policy/scenario versions; M6 frontend client requirements.
## Outputs
- FastAPI routes EXACTLY matching OpenAPI, locally controlled vulnerable/hardened interviewer, synthetic mock adapter, data access/persistence, queued run worker, append-only evidence store, session lifecycle, and retest links.
## Adapter Protocol to implement
- `start_session(AdapterStartRequest) -> AdapterStartResponse`
- `send_turn(AdapterTurnRequest) -> AdapterTurnResponse`
- `get_score(session_id) -> ScoreResult` (versioned scorer fields strictly from ScoreResult.schema.json)
- `close_session(session_id) -> None`

## Priority milestones
1. Days 1-2: Python package and FastAPI app; `/health`, `/api/v1/config`; deterministic target fixture modes refusal, disclosure, malformed, timeout, scoring; API errors follow `ErrorResponse`.
2. Days 3-5: DB tables, migrations, `POST /api/v1/runs` 202 QUEUED, GET status/events/findings, with M2 fake callback; no blocking HTTP model calls.
3. W2: real owned target model selection; separate v1 prompts vulnerable vs hardened; record target model/version/cost tokens; SQLite WAL and one worker (if approved). Allowlist target versions; no arbitrary URL from API.
4. W2: SQLite append-only events and review records; `POST /findings/{id}/reviews` only accepts human-authored operation, deduplicates idempotency key, preserves proposal.
5. W3: `POST /retests` only for reviewer-confirmed findings, controlled clone with changed target, `GET /retests/{id}` returns RetestView with result=null while QUEUED/RUNNING; eventual RetestResult only on completion; batch isolation, cancellation behavior.
6. W4: second-machine startup, corrupt/timeout/provider-failure/DB rollback tests, API docs and data export.
## Database invariants
- `runs` holds frozen config, SHA256, status, outcome and counters; `audit_events` append-only with UNIQUE(run_id,seq); `findings` immutable proposal; `review_events` appended (derive current disposition); `retest_links` reference original/new runs; scenarios/roles/rules versioned. No PII, no keys, no actual credentials.
## Tests
Run-create validation, unauthorized target reject, GET side-effect-free, persisted queue, 1 failed case does not stop batch, event ordering, invalid state 409, append-only review, cancellation, timeout failure, rerun with same limits/seed, replay links immutable.
## Coding assistant prompt
Implement only services/api and owned tests. Read OpenAPI, schemas, examples and ADR. Never rename routes, fields or error codes. Use mock adapter immediately. Every endpoint must have schema, status-code and example-based contract tests. Explain any assumption instead of changing shared contracts, and identify necessary M2/M4 interfaces before implementation.
