# Team handoff protocol

M1 owns integration and root settings. Every module owner keeps its implementation
and unit tests within the owned paths in AGENTS.md. Each member creates a fresh
`feat/mN-task-name` branch from current main and opens an incremental PR. No member
changes another module merely to fix an integration error.

All members read the same recovered sources listed in source-manifest.json and
the source-reconciliation record before implementing their mapped FR/NFR/AC
requirements. Unresolved source differences go to M1 and affected owners; they
do not authorize independent schema/endpoint changes.

| Owner | Deliver first | Later acceptance |
|---|---|---|
| M2 | Fixed runner using central AgentRunner Protocol; fake observation provider | Adaptive traces, budgets, injection defense, cancellation, per-run isolation |
| M3 | API health/config, mock adapter, worker and evidence store | Persistence/reviews/retests; lifecycle, rollback and restart tests |
| M4 | Exact target-only canary checker; benign and inconclusive tests | Mitigation regression and evidence-linked review samples |
| M5 | Approved DEV/DEMO scenario/persona and repository; metrics fixtures | Split-safe datasets, frozen experiment ledger and reproducible analyses |
| M6 | Dashboard fixture views; run creation and Arabic timeline | Live monitor, review/retest/report/export and browser/RTL tests |

Role-specific initial handoffs are tracked in issues #11 (M2), #12 (M3), #13 (M4),
#14 (M5) and #15 (M6). These assign responsibilities to roles; actual people and
backups still need to be entered. Feature branch prefixes must match the author's
actual member assignment before merge.

Each handoff PR provides:

1. The module manifest (`pyproject.toml` for Python or `package.json` for M6),
   with packages discoverable by root uv/npm workspaces.
2. Its own tests validating boundary models against canonical JSON schemas.
3. Exact shell-free argument arrays for startup and tests; M1 records them in
   `infra/handoffs.json` after review. Commands run from repository root. A Python
   command should use the workspace interpreter or `uv run --locked`. M6 startup
   and tests should use its npm workspace. Register tests that include typecheck,
   build and component/browser checks where relevant.
4. M3's container start must bind 0.0.0.0:8000, use exactly one Uvicorn process
   and one sequential in-process worker. Local-host startup must bind loopback.
   Put this distinction inside M3's approved startup command/configuration;
   never increase worker count to fix readiness problems.
5. M6's build produces its standard Vite dist and uses relative `/api/v1` calls
   so the same-origin container proxy works without putting model keys in JS.
6. Evidence, dependencies, unresolved decisions and version compatibility.

M1 changes only the root handoff/lock configuration, runs consumer and integration
checks, and merges after an independent review. Each owner fixes failures in
their own branch. Contract changes go through affected-owner ADR approval first.

Unknown commands remain null; a directory's existence is not proof of readiness.
No owner-visible HTTP API, extra tool or invented application entrypoint is
introduced by these root wrappers.
