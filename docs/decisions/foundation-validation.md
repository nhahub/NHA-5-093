# M1 foundation validation record

Validated on Windows, 2026-10-15, Python 3.11.14 / uv 0.10.10 /
Node 24.15.0 / npm 11.12.1. This record covers M1 tooling only.

| Command | Actual result |
|---|---|
| `uv sync --locked --all-packages` | Locked environment installed |
| `npm ci --ignore-scripts` | Clean root workspace install; no application package yet |
| `uv run --locked python scripts/validate_contracts.py` | PASS: 30 schemas, all 35 examples, 12 paths; references/tool outputs/negative cases/golden fixture chain |
| `uv run --locked python -m pytest tests -q` | 39 passed |
| `uv run --locked python -m ruff check .` | Passed |
| `uv run --locked python -m ruff format --check .` | Passed |
| `actionlint 1.7.7` | All three workflow files passed static validation |
| `gitleaks 8.24.2 protect --staged --config .gitleaks.toml --redact` | No leaks found |
| `python scripts/provision_github.py --backlog --protect` | Eight milestones/issues created; main protection applied and read back |
| `python scripts/dev.py readiness` | PENDING, exit 2: M2-M6 modules and commands missing |
| `python scripts/dev.py backend` | PENDING, exit 2: M3 handoff missing |

Actionlint and Gitleaks executables were downloaded from their official release
assets, checked against published SHA-256 checksums and stored in ignored .tools.
Tests of the API smoke use existing contract fixtures and HTTPX MockTransport;
they are harness tests, not evidence of a real application, real model or human
adjudication. SQLite tests exercise an actual local WAL database and verify that
snapshots preserve committed data and refuse overwriting existing files.

## Not verified here

- Runtime/UI golden scenario, browser accessibility/RTL, application budgets,
  target-only checker implementation, worker restart and DB append-only semantics:
  owner modules do not exist yet.
- Docker build/runtime: Docker is not installed on the current host and the
  images intentionally require the real owner modules.
- Linux execution: delegated to the PR's hosted CI, not inferred from Windows.
- Source FR/AC coverage, contract freeze, final model/evaluation evidence, second
  laptop and two rehearsals: pending real inputs and recorded human evidence.
- Independent cross-owner review: required on the PR; no approval fabricated.

No canonical transport schema, endpoint, enum, internal Protocol or original
fixture was altered. No M2-M6 implementation directory was created or modified.
