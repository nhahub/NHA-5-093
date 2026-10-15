# HireGuard Coding-Agent Contract Pack - proposed v1.0

## M1 foundation

The repository now includes locked uv/npm tooling, expanded contract validation,
CI and trusted approval policy, local container scaffolding, an API smoke harness,
and operational documentation. M2-M6 application modules are still pending;
the contract proposals have not been frozen or approved by this implementation.

Start with `python scripts/dev.py setup`, then
`uv run --locked python scripts/dev.py test` and
`uv run --locked python scripts/dev.py contracts`.
`uv run --locked python scripts/dev.py readiness` reports missing handoffs with
a nonzero exit; it does not pretend an absent application passed integration.

See [team handoffs](docs/decisions/handoffs.md),
[installation and operations](docs/decisions/operations.md),
[decisions and contract audit](docs/decisions/M1-foundation.md), and
[acceptance ledger](docs/decisions/acceptance.md).
The original PRDs and master specification are now retained unchanged in
[the source manifest](docs/decisions/source-manifest.json), with a
[54-row requirement map](docs/decisions/requirements-traceability.csv) and
[source reconciliation](docs/decisions/source-reconciliation.md).

**Purpose:** This package accompanies `HireGuard_Master_Coding_Specification.pdf`. It contains machine-checkable schemas, canonical mock payloads, the API specification, precise task ownership, and assistant instructions. This is a build contract proposal, NOT implementation code and NOT a guarantee of error-free AI coding.

**First-time usage:**
1. Read `docs/ADR-001-approvals.md`. M1 must approve unresolved architecture and requirement changes with the team/mentor.
2. Run the locked setup and validator commands above. Expect PASS with 30 schemas, 35 examples and 12 API paths.
3. Owners add their modules using the paths in `AGENTS.md` and the team handoff protocol. Review the recovered original sources and unresolved differences before claiming FR/AC acceptance.
4. M1 protects `main`, creates branches and publishes contract tag `contracts-v1.0.0` only once ADR is approved.
5. Every member gives their coding assistant: `AGENTS.md` + relevant `agents/MN-*.md` + approved ADR + relevant contract schemas + relevant fixture examples + assigned GitHub Issue.
6. Every coding assistant writes and runs unit/contract tests and opens a short-lived feature PR; another member reviews. Never merge solely because generated code looks plausible.

## Contents
- `AGENTS.md` - global mandatory coding-agent rules and directory ownership.
- `docs/ADR-001-approvals.md` - unresolved decisions with names to fill; approve before code freeze.
- `docs/INTEGRATION_PROTOCOL.md` - state, lifecycle, HTTP, evidence and safety invariants.
- `contracts/openapi.yaml` - proposed REST 3.1 contract (12 paths).
- `contracts/agent_tools.json` - exact agent-visible tool input and output contracts.
- `contracts/internal_interfaces.md` - Python Protocol signatures for producer/consumer boundaries.
- `contracts/mock_target_modes.json` - refusal, canary, scoring, timeout and malformed mocks.
- `contracts/schemas/*.schema.json` - 30 Draft-2020-12 JSON schemas (source of truth).
- `contracts/examples/*.json` - 30 matching example payloads.
- `agents/M1-..M6-*.md` - per-member coding assistant instructions.
- `plans/30_day_plan.csv` - parallel delivery schedule and checkpoint evidence.
- `scripts/validate_contracts.py` - proof fixtures and references are internally consistent.
- `.env.example` - safe placeholders for local integration.

## Critical warning
The two original PRDs describe overlapping but not identical agent tool sets, and an ambiguous repeatability plan. This pack selects a documented proposal, but lead approval of ADR-03, ADR-07, ADR-08, ADR-09 is compulsory. Names are M1..M6 until assigned. Never change source requirements silently to satisfy a deadline.

## What this pack does not provide
Fully implemented application, provider API keys, secured external deployment, real applicant dataset, guaranteed perfect LLM behavior, empirical results, or automatic review confirmation.
