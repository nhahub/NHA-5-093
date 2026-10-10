# M1 - Team lead, contracts, integration and infrastructure
**Member name:** TO_BE_ASSIGNED_BY_LEAD. **Approved scope:** `contracts/`, `infra/`, `.github/`, CI, `docs/decisions/`, shared versioning, release. Do NOT implement other members' internals.

## Inputs
- Source PRDs, `AGENTS.md`, approved ADR, all schema and JSON examples, each producer's public interface and fixture.
## Outputs
- Canonical contract release `contracts-v1.0.0`; Python/TypeScript model generation or validation process; CI and Docker Compose; release tags; integration gate results; troubleshooting runbook; second-laptop launch checklist.
## Ordered implementation tickets
1. Day 1: Ask team to sign ADR, select exact dependency lock files, assign names/backups, commit repository tree and `.env.example`. Confirm approved external provider and cost budget. **Do not claim approved before votes.**
2. Day 2: Verify all 30 schemas/examples, OpenAPI paths, tool names, enums and idempotency behavior. Add schema checks to CI. Create `docs/decisions/ADR-002-interfaces.md` only if approved changes occur.
3. Day 3: Provide `make test-contracts`, backend API startup, frontend startup and mock-mode commands; health and run-route contract smoke; sample test harness.
4. Days 4-7: Get M2/M3/M4/M5/M6 mock-first vertical slice working and protected `main`. Daily PR reviews and full suite after merge.
5. Week 2: Docker reproducibility, CI, secret scanning, path ownership enforcement, smoke test on local container.
6. Week 3: Confirm run/review/retest/report integrated and strict P0 gates; feature freeze on Day 21.
7. Week 4: Hold final model/policy/fixture versions immutable, ensure 120 security run ledger or supervisor-approved deviation, rehearse twice, verify clean install on second laptop.
## Acceptance checklist
- Unknown/changed fields fail contract validation; source diagrams and code contracts agree; no direct main pushes; CI required; every member's mocked consumer test passes; a fresh machine can start local app; recorded demo honestly indicates mock/live mode.
## Coding assistant prompt
Implement ONLY the M1 tickets from this document. Read root AGENTS.md, all contract files, approved ADR first. First output an inventory of existing files, identified unresolved decisions, proposed touched paths, and exact acceptance tests. Do not modify M2-M6 directories; open cross-owner issues. Produce small PR-ready changes with commands and outputs.
