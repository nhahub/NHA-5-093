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

The root uv workspace and registered owner suite include M5. Root test commands
and Windows/Linux CI collect both `tests/` and `packages/evaluation/tests/`.
The trusted-base owner registration is tracked separately in prerequisite PR #19.

`MetricsService(batch_contexts).aggregate_batch(batch_id, run_records, findings,
review_events)` implements the canonical internal interface. Context is a
deep-copied mapping of batch IDs to the existing analysis bundle's private plan,
event, score and protocol fields. Missing context is an error. The method returns
only schema-valid ReportSummary; `analyze_evaluation` retains detailed sidecars.

## Metric semantics

- Confirmed discovery counts confirmed findings linked to completed intended
  violation attempts. Failed runs are excluded from that denominator and listed.
- Precision and false-positive rate use all finally reviewed flags; reviewer
  `INCONCLUSIVE` remains in the denominator.
- Zero denominators produce `null`/`NA`.
- Dialect delta is `score(MSA) - score(EGY)`.
- Repeatability uses population standard deviation over repeated scoring of the
  identical frozen transcript. This methodological choice remains proposed.
- Every result lists the contributing run, finding, review-event, audit-event and
  score-session IDs, plus transcript hashes. Cost remains `null` until M3 provides
  an approved immutable pricing-provenance handoff. A zero-rate table is not proof.
- Detailed sidecar output preserves run-status IDs and finding review-status
  counts, including `FAILED`, `CANCELLED`, `PENDING`, and `INCONCLUSIVE`, even
  where the shared `ReportSummary` has no corresponding field.

Inputs and outputs are checked against canonical schemas. Planned entries must
match the stored configuration; findings must cite matching target evidence.
Repeatability samples must share transcript hash and scoring role/rubric, use
distinct sessions and unique in-range repetitions. Supply the existing scoring
ledger entries as `repeatability.planned_entries` to detect entirely missing
transcripts/cells. Incomplete coverage remains explicit in limitations.

The proposed finding-based discovery formula is preserved. If multiple confirmed
flags would make a rate exceed one, analysis raises an explicit methodology error
instead of silently clamping or changing the denominator. This decision remains
open in the approval packet.

Held-out execution requires validated frozen content, both approved/frozen
protocols, recorded M1/M4/M5/mentor approvals, and two-reviewer pair evidence.
Private integrity-field and approval-record formats are documented in
`docs/decisions/m5-integration.md`. No production approval or freeze was added.
