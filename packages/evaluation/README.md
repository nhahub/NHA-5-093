# HireGuard M5 evaluation package

This package contains M5-owned synthetic Arabic datasets, split-isolation
validation, deterministic experiment ledgers, and ID-backed metric analysis.

## Approval state

All artifacts are **PROPOSED — M1/mentor approval required**. No scenario is
marked approved, no split is declared frozen, and the illustrative fixture is
not final evaluation evidence. ADR-08 (80 matrix runs + 40 extra security runs)
is blocking. The separate source obligation is 10 fixed transcripts × 5 scoring
repetitions × 2 targets = 100 scoring invocations.

The current public Scenario schema contains `split`, `expected_behavior`, and
fixed prompts. Held-out full records therefore live under `data/heldout/private/`.
Only the exact `AgentScenarioView` allowlist may reach the adaptive agent.
Repository file permissions are not an authorization boundary; M3 must enforce
the controller-only repository boundary when it implements persistence/worker
integration.

## Commands

```powershell
uv run --locked python packages/evaluation/scripts/validate_data.py
uv run --locked python packages/evaluation/scripts/build_ledgers.py
uv run --locked python -m pytest packages/evaluation/tests -q
uv run --locked python packages/evaluation/scripts/analyze.py `
  packages/evaluation/fixtures/sample_evaluation_input.json
```

The root workspace does not yet register this package or its owner test command;
those M1-owned changes require M1 approval. The scripts can still be run from the
repository root once the locked dependencies are installed.

## Metric semantics

- Confirmed discovery counts confirmed findings linked to completed intended
  violation attempts. Failed runs are excluded from that denominator and listed.
- Precision and false-positive rate use all finally reviewed flags; reviewer
  `INCONCLUSIVE` remains in the denominator.
- Zero denominators produce `null`/`NA`.
- Dialect delta is `score(MSA) - score(EGY)`.
- Repeatability uses population standard deviation over repeated scoring of the
  identical frozen transcript. This methodological choice remains proposed.
- Every result lists the contributing run, finding, review-event, and audit-event
  IDs. Cost is `null` unless every priced usage event has a frozen pricing entry.
- Detailed sidecar output preserves run-status IDs and finding review-status
  counts, including `FAILED`, `CANCELLED`, `PENDING`, and `INCONCLUSIVE`, even
  where the shared `ReportSummary` has no corresponding field.
