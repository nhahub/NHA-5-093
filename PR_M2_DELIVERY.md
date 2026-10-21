# M2 async engine repair increment

Tickets: M1-05/M1-06, M2 handoff #11; FR-06, FR-09..15, FR-17..19,
FR-22..24 and AC-03/AC-05 integration preparation.

The previous synchronous loops bypassed the supplied checker in FIXED mode and
could miss disclosures with the actual M4 checker. The repaired canonical async
runner uses one LangGraph pipeline, awaits adapter/store operations, persists
allocated events and checks, and creates only evidence-linked pending findings.
Usage, cancellation and time/token gates are rechecked before target execution.
The response is validated directly as RunDetail. Private policy data remains on
the controller/checker side. Groq execution and implicit zero-usage fallbacks are
removed; malformed provider attempts are accounted without automatic retries.

Changes include M2 code/tests/traces plus M1-approved workspace manifests, shared
lock/configuration and handoff registration. Earlier sync-only runtime tests are
migrated to async boundary/persistence regression tests. Pure state, budget, tool
and trace tests are retained. No canonical schema, endpoint, enum or Protocol is
changed. The M1 version of tests/__init__.py is retained.

Validation commands are the locked commands in README-engine.md and the root CI.
Actual results and current commits are recorded in docs/decisions/merge-m2-m4.md.

Merge dependency: M1 #10 then M4 #17 before this PR #16. Independent human review,
M2/M4 boundary acknowledgment and M3 lifecycle acknowledgment remain pending.
ADR-07 remains unsigned. No API/SQLite/browser/container or final model-evaluation
success is claimed. Target-generation reservation enforcement still needs M3's
owned adapter implementation; only conservative controller preflight is present.
