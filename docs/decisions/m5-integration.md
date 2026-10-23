# M5 preparation integration — 24 October 2026

The project lead authorized repairs to PR #18 and registration of verified M5
owner `RanaSakr` (repository write permission checked). This is implementation
authorization, not an owner review, mentor decision, dataset approval or freeze.
PR #19 registers ownership on the trusted base and needs independent review.

The canonical ScenarioRepository and MetricsService signatures and every shared
schema remain unchanged. MetricsService receives a deep-copied mapping of batch
IDs to private analysis context at construction. Context contains the planned
ledger, events, scores and protocol metadata already consumed by M5 analysis;
aggregate_batch supplies only its canonical run/finding/review arguments.
Missing batch context fails explicitly. No plan is inferred from observations.

Additional analysis fields are private sidecar data, not HTTP ReportSummary
fields. `repeatability.planned_entries`, when supplied, contains the existing
repeatability planner's entries, including transcript hashes, target and repeat
indices. Without a complete planned scoring inventory, coverage is explicitly
limited. Score session IDs and transcript hashes remain in detailed provenance.

Price tables alone are not provenance. Until M3 supplies an approved immutable
pricing snapshot and the affected owners agree its representation, cost remains
null. The old illustrative zero-price table is not evidence of approved pricing.
Target TURN latency is reported as target latency, not total execution time.

Preserve the currently proposed finding-based discovery formula. If multiple
confirmed findings make its numerator exceed completed intended attempts, reject
the aggregate with an explicit methodology error. Do not clamp or silently count
runs instead. M1/M4/M5/mentor must resolve this before protocol approval.

Freeze validation verifies existing protocol/manifest states, canonical hashes,
the protocol's required approvals, and two distinct nonempty reviewers per pair.
Both security and scoring subprotocols must be approved/frozen before held-out
access; dialect manifest review records must agree with the reviewed pairs.
No runtime final collection is implemented here. This preparation release keeps
all existing datasets and protocol proposed/unfrozen and rejects held-out access
until their freeze requirements are satisfied. Frozen held-out content includes
the canonical scenarios, personas, pairs and manifest records; protocol and
repeatability transcript hashes must also be recorded in the held-out manifest
as `protocol_sha256` and `repeatability_sha256` before held-out access is allowed.
These are M5-private manifest integrity fields, not shared transport changes.
Each private protocol approval row identifies `owner`, `reviewer_id`, `decision`,
`protocol_version`, and UTC-offset `approved_at`. Required owners remain exactly
M1/M4/M5/mentor. Empty or mismatched records cannot establish approval; recording
real human decisions is still required. No rows are added by this repair.

M2/M4 implementations are reused unchanged. M3 score/session persistence, hard
target token limits, approved models, human linguistic reviews, ADR-08/09 and the
complete application workflow remain pending. Human signatures are never inferred.

## Verification evidence

Windows local verification on 2026-10-24:

- Locked uv workspace sync and `npm ci --ignore-scripts`: passed.
- Contracts: 30 schemas, 35 examples and 12 API paths passed; shared files unchanged.
- Full suite `python -m pytest tests packages/evaluation/tests -q`: 289 passed.
- Registered suites after final validation edits: M2 101, M4 91, M5 55 passed.
  M3/M6 remain absent/pending rather than successful coverage.
- Ruff lint and format check: passed (85 files).
- Dataset validator and security pack: passed. Actual scenario/persona/pair,
  transcript, manifest and protocol JSON are unchanged from Rana's original head.
- Ledgers reproduce 120 security entries and 100 separate scoring entries, both
  non-comparable; hashes match the original proposal exactly.
- Gitleaks 8.24.2 clean source snapshot: no leaks. Scanner configuration unchanged.
- Runtime: Python 3.11.14, pytest 8.4.2, Ruff 0.11.13, jsonschema 4.26.0,
  Pydantic 2.14.1, LangGraph 1.2.16. Root lockfile records the installed graph.

Only isolated tests construct synthetic approval records. No human approval,
protocol freeze, real evaluation result or application integration is asserted.
Hosted verification and required current-head reviews are tracked on PR #18;
PR #19 remains the trusted-base ownership prerequisite until independently reviewed.
