# HireGuard M2 — bounded async engine

The central interface is `await execute_run(run_id, config, scenario, adapter,
store, checker)` from `services.engine.controller`. Both FIXED and ADAPTIVE
use one LangGraph execution pipeline and the real M4 checker. Only probe
selection differs. The adapter and store implement the async Protocols in
`contracts/internal_interfaces.md`; synchronous mocks are no longer compatible.

M3 must create a RUNNING record with immutable configuration/hash, timestamps,
role/policy/checker/target versions and canonical scenario hash before invoking
the runner. The runner returns an actual schema-valid RunDetail and appends a
terminal STATE event; M3 persists worker lifecycle/counters through its owned
implementation. No new store method or HTTP field is invented. M3 acknowledgment
of this handoff remains required before runtime integration.

The store allocates event IDs and sequences. Both methods persist real checks
and policy-derived pending findings. Empty/malformed checks, unknown rules,
missing usage and provider failures stop explicitly. No model can confirm a
finding. A timeout never blindly retries a conversational turn. No automatic
provider repair/fallback retries are performed, including when max_retries=1;
this limit is an allowance rather than a mandatory retry count.

Use the root locked workspace:

```powershell
uv sync --locked --all-packages
uv run --locked python -m pytest tests/engine -q
uv run --locked python scripts/export_traces.py
```

Mock mode is selected by `model_settings.model_id=mock-agent-v1`. The test traces
are explicitly MOCK and development-only. One trace pivots after refusal; the
other continues directly after a neutral reply and stops after canary evidence.

Only loopback Ollama is an optional model seam. Frozen model, temperature, output
cap and seed are honored. Live calls require an injected, approved reliable
model tokenizer for pre-call input measurement; the default factory does not
supply one and fails visibly before live inference. No live-model evaluation is
claimed. Groq and arbitrary network providers have been removed.

A 300-token conservative reservation is rechecked before target turns. Actual
usage is validated and charged; any overrun stops subsequent inference. M3 must
bound target generation within the remaining allowance using its run-owned
configuration. The current adapter Protocol has no tokenizer/reservation method,
so this controller alone cannot prove a hard upper bound on target output.

Tests use async in-memory doubles under `services/engine/mocks`, not M3's API,
SQLite worker or a browser. Those application gates remain pending. Owner/mentor
signatures and independent current-head human review are still required.
