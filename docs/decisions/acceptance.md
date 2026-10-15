# Integration and release acceptance ledger

These are handoff gates, not claims of completed behavior. Record commit, contract
version, command, output artifact and human reviewer when each gate is satisfied.
Individual tooling tests do not satisfy an application milestone.

| Gate | Current state | Required evidence |
|---|---|---|
| M1-01 sources/approvals | PENDING | Original sources, complete per-FR/AC mapping, actual handles/backups, actual signatures |
| M1-02 freeze | PENDING | Contract audit, affected-owner decisions, consumer tests, approved tag |
| M1-03 tooling | Foundation implemented; review pending | Locked setup, Windows/Linux CI, fresh-clone smoke, owner manifests |
| M1-04 governance | Configuration prepared; server verification recorded separately | Protection readback, required CI, actual team assignment and independent review |
| M1-05 mock slice | PENDING M2-M6 | Real runtime plus browser golden workflow with MOCK label |
| M1-06 reliability | PENDING M2-M6 | Two adaptive branch traces, budgets, no state leak, injection defense, cancellation, restart, batch isolation, Compose |
| M1-07 full workflow | PENDING M3-M6 | Human review fixture, append-only DB checks, pending/failed retest semantics, report recomputation, RTL/browser tests |
| M1-08 release | PENDING | Frozen local models/protocol, 120-run security ledger, separate scoring-repeatability ledger, reproducible metrics, second laptop and two rehearsals |

## Required runtime coverage

- Creation returns 202 QUEUED before inference; unknown targets rejected.
- GET polling never calls models or changes state; test with the worker paused as
  well as at terminal state. Terminal snapshot smoke alone is insufficient.
- Every response receives mandatory checking; zero calls after budget exhaustion.
- Target instructions cannot invoke shell, tools, URLs or policy overrides.
- State and evidence are append-only, sequential and isolated per run. Canary
  detection matches target output only; malformed/ambiguous results are honest.
- Human authorization is enforced by M3; an integration review fixture is not a
  live human finding disposition. Confirm/reject/inconclusive reviews persist.
- Retests reject unconfirmed originals, preserve settings, show null while pending,
  and never show mitigation verified for failed or inconclusive jobs.
- Worker restart fails interrupted running jobs and resumes queued jobs; failure
  in one batch member does not stop another; DB rollback is tested by M3.
- Reports match raw stored records and exported values, disclose failures and
  pending/inconclusive cases, and use null for undefined ratios.
- Browser tests cover Arabic RTL, mixed JSON direction, keyboard labels, evidence
  navigation, terminal polling, errors and explicit MOCK identification.

Keep final evaluation immutable. Never count development/DEMO runs as held-out.
If frozen data/models change, version a separate experiment and disclose the change.
