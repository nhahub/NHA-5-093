# Local installation, operations and release runbook

## Installation

Install Git, uv 0.10.10, Node 24.15.0 with npm 11.12.1, and Docker with Compose
when container gates become ready. The foundation was tested on Windows with
Python 3.11.14 downloaded by uv. Docker is not installed on the current host.

From PowerShell at repository root:

```powershell
python scripts/dev.py setup
uv run --locked python scripts/dev.py contracts
uv run --locked python scripts/dev.py lint
uv run --locked python scripts/dev.py test
uv run --locked python scripts/dev.py readiness
```

The last command currently reports PENDING and returns 2. This is expected until
M2-M6 provide modules and approved commands. The application is not implemented
by this foundation. `make test-contracts` and other Make targets wrap the same
Python entrypoint on machines with Make.

Once owner handoffs are ready, `uv run --locked python scripts/dev.py backend`
and `... frontend` start their registered commands. Copy `.env.example` to a
local `.env` as needed; never put real keys in tracked files or the dashboard.
Keep mock mode enabled for deterministic CI.

## Containers and integration

```powershell
uv run --locked python scripts/dev.py readiness
docker compose -f infra/compose.yaml config
uv run --locked python scripts/dev.py containers
uv run --locked python scripts/integration_smoke.py
```

The API is exposed on loopback port 8000 and dashboard on loopback 5173. SQLite
lives in a named evidence volume; the API process owns the sequential worker.
Images require the actual owner modules; they cannot build/run the application
today. The smoke defaults to health/config only and labels that limited scope.

For a fresh, isolated mock instance ONLY, the full synthetic review workflow is:

```powershell
$env:HG_ALLOW_TEST_REVIEWS='1'
uv run --locked python scripts/integration_smoke.py --workflow
Remove-Item Env:HG_ALLOW_TEST_REVIEWS
```

This simulates a human fixture through the API to test the transport. It is never
a model-visible tool, a production review, or final evaluation confirmation. The
workflow produces `artifacts/mock-smoke.json` with actual IDs, commit, dirty-worktree
flag, timestamp and contract digest; it never
invents replies. Browser, pre-call budget, worker-paused GET, restart and DB
immutability tests remain mandatory owner/runtime gates. The manual GitHub runtime
workflow fails until handoffs are complete. Foundation CI runs each present
module's registered suite and records absent modules explicitly as pending in
its coverage summary. Once real runtime gates are proven,
M1 must add them to required PR CI before feature freeze.

## Backup and restore

For a native SQLite database, create an integrity-checked snapshot:

```powershell
uv run --locked python scripts/backup.py backup data/hireguard.db artifacts/backup.sqlite
```

Create `artifacts` first if absent. The script uses SQLite's online backup API,
which includes committed WAL data. It refuses an existing destination. For a
container volume, stop services and use the same script inside the API container
with both source and destination on its volume, then `docker compose cp` the
snapshot out. Do not copy only the main .db file while WAL writers are active.

To restore, stop writers and restore into a new filename, then configure M3's
database location to that file and run integrity and application smoke checks:

```powershell
uv run --locked python scripts/backup.py restore artifacts/backup.sqlite data/restored.sqlite
```

Never remove the original evidence to make room for a restore. `docker compose
down` preserves the volume; `down -v` destroys it and is not part of this runbook.

## Troubleshooting

| Symptom | Action |
|---|---|
| PENDING handoff | Owner supplies package, startup/test commands and fixtures; M1 reviews registration |
| Lock mismatch | Owner proposes dependency change; M1 regenerates and reviews the shared lock, then reruns all consumers |
| Contract failure | Fix producer/consumer against canonical contract; use an approved ADR for real changes |
| Queue stalls | M3 checks single-worker lifecycle and DB; never make GET advance jobs |
| Timeout/unknown usage | Fail or mark inconclusive per approved rules; do not fabricate a reply or blindly retry a turn |
| Container unhealthy | Check registered M3 binding and `/health`; use sanitized logs; preserve evidence volume |
| Ownership pending | Assign actual owner or obtain current-head human review, then refresh status |
| Golden regression | Stop dependent merges; owner fix PR or independently reviewed revert PR; never rewrite published history |

## Release and second laptop checklist

- Review the recovered source manifest and FR/NFR/AC mapping; obtain owner and
  mentor decisions on differences in source-reconciliation.md.
- Record actual owner/mentor decisions; freeze approved contract tag.
- Pass module, contract, runtime, browser, reliability and Compose suites.
- Freeze local model versions/settings, policies, split manifests and seeds before
  final collection; record hardware and measured usage availability.
- Reproduce M5 metrics from actual run/review IDs. Verify 80 matrix + 40 extra
  security runs or approved deviation. Keep scoring-repeatability jobs separate.
- Record completion/precision against original acceptance thresholds, with every
  failed, excluded, pending and inconclusive case disclosed.
- On an independent laptop: clean clone release candidate, locked install,
  startup, golden workflow, review/retest/report/export, backup/restore. Record
  operator, OS/runtime versions, commit and actual results.
- Rehearse twice; distinguish mock fallback recordings from live-model evidence.
- Publish release notes with exact versions, validation evidence, known limitations
  and genuine reviewers. Tag only after these gates pass; never sign for others.
