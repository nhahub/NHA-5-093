# Recovered source requirements and unresolved differences

The original detailed PRD, architecture blueprint and proposed master coding
specification were recovered from the project owner's Downloads on 2026-10-15.
Unchanged copies are retained under `sources/`; `source-manifest.json` records
their original filenames, SHA-256 hashes and PDF page counts. Everyone can now
use the same source bytes. No personal name, signature or approval was inferred.

`requirements-traceability.csv` contains all 33 FR, 12 NFR and 9 AC requirements
from the DOCX source, with exact requirement/acceptance wording, table/row
locators, counterpart PDF pages, proposed primary role and an integration ticket.
Planned acceptance is separate from actual evidence; actual evidence remains
empty because application implementation and owner review are pending. Role
assignments are a coordination proposal, not permission to edit another role's
owned directory. Source-integrity tests check hashes and the DOCX text against
the CSV using OOXML directly, without adding document dependencies to the app.

## Reading order and authority

1. Read AGENTS.md for this repository's explicit safety and directory boundaries.
2. Read both original PRDs for requirements, priorities and acceptance criteria.
3. Read the master PDF as an implementation PROPOSAL; it explicitly requires lead
   and mentor approval and refers to the machine-readable contract pack.
4. Implement approved interfaces from contracts, not new fields inferred from a
   PDF diagram. Record discrepancies here and obtain affected-owner decisions
   through ADR-001 before contract freeze. The PRD PDF's own frozen-spec label is
   not evidence that the implementation proposal or ADR has been signed.

## Decisions that cannot be silently reconciled

| Source difference | Current treatment / required decision |
|---|---|
| Original eight-week schedule vs four-week master proposal | This work uses undated milestones as requested. Original P0 obligations and acceptance targets remain; acceleration/waivers need mentor approval under ADR-09. |
| PDF FR-10 lists three model tools; DOCX FR-10 lists five actions | Preserve current three-tool contract. Save evidence/request review remain trusted controller actions. ADR-03 needs affected-owner acknowledgment. |
| PDF RetestLink permits INCONCLUSIVE after-state without an honest verdict for it | Keep proposed RETEST_INCONCLUSIVE visible as pending ADR-07; no freeze or fabricated mitigation success. |
| PDF says five scenarios repeated three times yet labels them 40 extra runs; DOCX explicitly says two additional repeats per method/target | Proposed 80 + 40 security-run accounting stays pending ADR-08 acknowledgment. Do not include the original run again as an extra repeat. |
| DOCX FR-20 requires ten fixed transcripts five times for each of two targets | Track 100 scoring invocations separately from the 120 security runs unless approved accounting changes it. Report mean/stddev/range/flips and all failures. |
| PDF precision/FPR formulas refer to all flagged proposals; DOCX metrics refer to reviewed flags | Existing ReportSummary uses reviewed-flag denominators. M1/M4/M5 and mentor must explicitly settle pending-flag treatment before final evaluation/acceptance claims. |
| Original team table gives M6 Docker/CI; AGENTS/master and M1's accepted task assign root infra/CI to M1 | Follow current explicit directory ownership. M1 changes root infrastructure; M6 changes apps/dashboard. Record affected-owner acknowledgment before freezing the revised ownership. |
| PDF role acceptance mentions an immutable version hash; current RoleConfig exposes a version string | M1/M3 must show how immutable content/version resolution satisfies the source without inventing a new public field. |
| PDF state transitions mention millisecond timestamps; DOCX says timestamp/reason; schema permits RFC3339 | M1/M2/M3 must settle precision and produce compatible traces; do not treat schema validity alone as proof of this acceptance detail. |
| P1 cloning, drafting, extensible families and cached demo exceed currently exposed API/schema detail | Keep P1 priority and document an approved design before adding routes, family enum values or draft states. No P0 feature is silently waived. |
| DOCX suggests possible post-core speech input; PDF and current AGENTS prohibit voice in this MVP | Preserve the explicit current text-only boundary; do not implement speech/camera/biometrics. |

Confirmed source acceptance targets include 90% completion, 80% reviewed held-out
precision, complete evidence on every confirmed finding, two observation-driven
traces, a verified mitigation retest, matched method budgets, dialect/repeatability
limitations, and a clean second-laptop launch. Reading those targets does not
establish that they have been achieved. All release evidence remains pending.
