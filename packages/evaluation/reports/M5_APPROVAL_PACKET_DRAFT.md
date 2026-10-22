# M5 evaluation approval packet — draft for M1, M4, and mentor

**Draft date:** 2026-10-22
**Status:** REVIEW DRAFT ONLY — no decision in this packet is approved, and no
dataset or protocol is frozen.
**Prepared from:** the current repository state; no final evaluation results are
claimed.

## Repository state checked before drafting

- Git root: `HireGuard/repo`
- Branch: `main` tracking `origin/main`
- HEAD: `bc71def` (`Merge pull request #16 from WalidAbdelmeguid/feat/m2-adaptive-agent-traces`)
- Working tree at the start of this review: `data/` and `packages/evaluation/`
  were untracked. Existing work in those paths was not overwritten or deleted.

## Source documents

- [M5 approval register](../APPROVALS_REQUIRED.md)
- [Proposed held-out protocol](../../../data/heldout/protocol.json)
- [Held-out freeze checklist](../../../data/heldout/FREEZE_CHECKLIST.md)
- [M5 package README](../README.md)
- [ADR approval checklist, especially ADR-08](../../../docs/ADR-001-approvals.md)
- [Source reconciliation and unresolved differences](../../../docs/decisions/source-reconciliation.md)
- [M5 role rubric](../../../agents/M5-evaluation.md)
- [Held-out manifest](../../../data/heldout/manifest.json)

## Current approval posture

All relevant records are proposals. ADR-08 is `BLOCKING APPROVAL`; the security
protocol is `BLOCKED_ADR_08`; the split and protocol are
`PROPOSED_NOT_FROZEN`; all 20 held-out scenarios have `approved: false`; all
four Arabic-pair reviews are `PENDING` with empty reviewer lists; and the
protocol approval list is empty. The generated ledgers are deterministic plans,
not executed runs or final evidence.

## Proposed dataset composition and accounting

| Item | Proposed composition | Accounting | Current state |
|---|---|---:|---|
| Development set | 30 synthetic Arabic scenarios | 30 scenarios | Manifest is `PENDING_M1_MENTOR` and `PROPOSED_NOT_FROZEN` |
| Held-out set | 10 intended-violation cases: 4 secret leak, 4 injection, 2 rubric drift; 2 benign controls; 8 dialect cases forming 4 MSA/EGY pairs | 20 scenarios | Not approved or frozen |
| Base security matrix | 20 held-out scenarios × 2 methods (`ADAPTIVE`, `FIXED`) × 2 targets (`vulnerable-v1`, `hardened-v1`) | 80 runs | Proposed by ADR-08 |
| Extra security repeats | 5 selected scenarios × 2 additional repeats × 2 methods × 2 targets | 40 runs | Proposed by ADR-08 |
| Total security ledger | Base matrix + extra repeats | **120 runs** | `BLOCKED_ADR_08`, non-comparable |
| Fixed-transcript repeatability | 10 frozen transcripts × 5 scoring repetitions × 2 targets | **100 scoring invocations** | Separate proposed ledger; not part of the 120 |

The five selected extra-repeat scenarios are one secret-leak case, one injection
case, one rubric-drift case, one benign control, and the MSA half of one dialect
pair. The resulting 120 planned runs break down as 24 secret-leak, 24 injection,
16 rubric-drift, 16 benign-control, and 40 dialect-pair runs. Only 64 of the 120
are marked intended-violation attempts; 56 are benign or dialect runs. Reviewers
must approve whether this is the intended meaning of “120 security runs.”

The deterministic planning code currently expands to 120 unique security plan
IDs and 100 unique scoring plan IDs. Its current hashes are:

- Security plan: `99c6ef4808c3fda3d10da5481f10c73d6d3eaf9b333c7dcb8a2e29465395415d`
- Repeatability plan: `d67af2cea6af20a7d92dbdf0e1076eee1630e3b88b2b11dd583c5ad6ac9f718c`

These are review aids only. They are not approved freeze hashes, and their
entries have null run/session IDs because no final collection has occurred.

## Decisions requested from M1

1. **ADR-08 governance:** approve or revise the 80 + 40 = 120 accounting and
   record M1's acknowledgment together with M4, M5, and mentor acknowledgments.
2. **Dataset/protocol scope:** approve or request revision of the proposed
   30-development/20-held-out composition and the five extra-repeat selections;
   ADR-08 alone does not explicitly approve those contents.
3. **Freeze authority:** approve the freeze process and evidence required by the
   checklist—split membership, scenario content, role/policy/checker/target/model
   versions, seeds, budgets, pricing, reviewers, and immutable hashes—without
   marking the current proposal frozen prematurely.
4. **Runtime ownership:** assign M3 integration for controller-only held-out
   access, immutable run/event/score persistence, and the `get_score` path.
5. **Contract/report decision:** decide whether family breakdowns, individual
   dialect/repeat rows, pending/cancelled counts, and source IDs remain in the M5
   sidecar report or require a versioned shared `ReportSummary` change. No field
   should be added informally.
6. **Identity and review:** record the actual M5 handle under ADR-12 and arrange
   cross-owner review. The repository still lists M5 as unassigned.
7. **Model and pricing provenance:** decide the final evaluation model setup and
   require a versioned pricing snapshot. The protocol currently names
   `mock-agent-v1`; ADR-10 forbids presenting mock results as live evidence.

## Decisions requested from M4

1. **ADR-08 acknowledgment:** approve or revise the 120-run accounting from a
   security-evaluation perspective.
2. **Security coverage:** approve or revise the held-out family mix and confirm
   whether benign and dialect cases belong inside the 120-run “security” ledger.
3. **Extra-repeat selection:** approve or revise the five selected scenarios,
   including the asymmetric choice of only the MSA member of one dialect pair.
4. **Checker readiness:** provide or approve the semantic judge and checker
   versions needed for final runs.
5. **Injection marker:** approve, replace, or reject the proposed planted marker
   `HG-INJECT-OK-7731` and its checking semantics before freeze.
6. **Review denominator:** agree with M1/M5/mentor on whether precision and false
   positive rate use reviewed flags only, and how pending flags are reported.

## Decisions requested from the mentor/supervisor

1. **Experiment accounting:** approve or revise 80 base + 40 extra = 120 security
   runs and confirm that the 100 fixed-transcript scoring invocations remain a
   separate obligation.
2. **Experimental composition:** approve or revise the 20-case mix and the five
   extra-repeat selections, including whether dialect/control cases count within
   the security matrix.
3. **Protocol configuration:** approve or require changes to matched budgets and
   information, maximum 6 candidate turns, 4,000-token cap, 120-second timeout,
   zero retries, target versions, model identity, temperature, and seed handling.
4. **Statistical method:** approve or revise population standard deviation for
   each complete five-repeat scoring cell.
5. **Acceptance semantics:** settle the reviewed-flag versus all-flagged-proposal
   denominator conflict before final precision/FPR claims.
6. **ADR-09:** confirm that schedule acceleration does not waive the original P0
   requirements, 90% completion target, 80% precision target, or planned run
   obligations unless an explicit supervisor-approved change is recorded.
7. **Freeze authorization:** approve final data collection only after the full
   freeze checklist, Arabic reviews, runtime evidence, and owner acknowledgments
   are complete.

## Unresolved dependencies and risks

- **Arabic equivalence review:** all four held-out MSA/EGY pairs still need two
  independent human reviewers; there are no reviewer IDs or approvals yet.
- **M3 persistence/runtime:** final evidence needs immutable run, event, finding,
  review, audit, score, and session IDs. The controller must enforce the private
  held-out boundary; repository directories alone are not access control.
- **`get_score` integration:** M2/M3 have not connected the tool/runtime path and
  M3 does not yet persist `ScoreResult`, blocking dialect and repeatability data.
- **Pricing provenance:** no approved, versioned pricing snapshot is persisted.
  Cost must remain `null` rather than using a current web price or an inferred
  value.
- **M4 judge and marker:** the semantic judge is not approved and the planted
  injection marker remains a proposal.
- **Model provenance:** `mock-agent-v1` is frozen into the proposed protocol
  draft, but mock output cannot support live-model claims under ADR-10.
- **Contract capacity:** the shared report cannot carry all required detailed
  rows, statuses, and provenance IDs; an owner decision is needed before any
  shared-schema modification.
- **Human review protocol:** reviewer identities, assignment rules, conflict
  handling, and final dispositions are not approved.
- **No final evidence:** there are plans and illustrative fixtures, but no
  approved protocol, completed final runs, or human-review ledger.

## Inconsistencies and ambiguities requiring reviewer resolution

1. **“Three times” versus “two additional repeats”:** the recovered PDF says five
   scenarios are repeated three times while also calling the increment 40 runs;
   the DOCX and ADR-08 use two additional repeats. The implementation follows the
   latter proposal, but ADR-08 is not approved.
2. **Run name versus run contents:** ADR-08 calls all 120 entries “security runs,”
   but the implemented ledger includes 16 benign-control runs and 40 dialect
   runs; only 64 entries are intended-violation attempts.
3. **Dialect placement:** the 8 dialect cases are included inside the 20 held-out
   matrix, although dialect sensitivity is a distinct metric requiring
   `get_score`. The approved documents do not yet state whether those cases
   should consume 8 of the 20 security slots.
4. **Repeat selection balance:** one MSA dialect scenario receives two extra
   repeats while its EGY pair does not, which can unbalance paired dialect
   comparisons. Neither ADR-08 nor the role rubric names the five cases.
5. **Approval labels differ:** the protocol says `BLOCKED_ADR_08`; the split and
   repeatability records say `PENDING_M1_MENTOR`; the protocol itself requires
   `M1`, `M4`, `M5`, and `mentor`. The labels do not consistently identify every
   required approver, and the approvals array is empty.
6. **Mock model versus final-evaluation intent:** the protocol fixes
   `mock-agent-v1`, while ADR-10 says mock results must not be represented as live
   evidence. The packet needs a decision on dry-run versus final model config.
7. **Seed representation:** `protocol.json` stores a null model seed, but the
   planner replaces it with each scenario's seed. The freeze record must make
   this resolution rule explicit and approved.
8. **Precision/FPR denominator:** source documents conflict between all flagged
   proposals and reviewed flags. The current README/analysis uses reviewed flags
   with inconclusive reviews in the denominator.
9. **Repeatability statistic:** population standard deviation is implemented and
   documented as proposed, but it is not approved in an ADR or protocol field.
10. **Pricing freeze gap:** the freeze checklist requires pricing evidence, but
    `protocol.json` has no pricing snapshot or reference and the shared runtime
    contracts do not currently persist one.
11. **Arabic-review evidence gap:** the checklist requires two reviewers per
    pair, but the protocol does not define their identities or acceptance rule;
    all pair records remain pending.
12. **Report contract gap:** required family/pair/repeat/source-ID detail exists
    only in an M5 sidecar design because the shared `ReportSummary` cannot encode
    it. Whether this is acceptable is unresolved.

## Draft reviewer messages — not sent

### M1

> Please review the M5 evaluation proposal in
> [APPROVALS_REQUIRED.md](../APPROVALS_REQUIRED.md),
> [protocol.json](../../../data/heldout/protocol.json), and
> [ADR-001](../../../docs/ADR-001-approvals.md), especially ADR-08. I need your
> recorded decision to approve or revise (a) the 80 + 40 = 120 run accounting,
> (b) the 20-case composition and five repeat selections, (c) the freeze and
> model/pricing requirements, and (d) the M3/shared-contract integration owners.
> Please do not mark the protocol frozen yet; the
> [freeze checklist](../../../data/heldout/FREEZE_CHECKLIST.md) is still open.

### M4

> Please review the security design in
> [protocol.json](../../../data/heldout/protocol.json), the open decisions in
> [APPROVALS_REQUIRED.md](../APPROVALS_REQUIRED.md), and ADR-08 in
> [ADR-001](../../../docs/ADR-001-approvals.md). I need your decision on the
> security-family mix, whether benign/dialect cases belong in the 120-run ledger,
> the five extra-repeat selections, the semantic judge/checker version, and the
> proposed `HG-INJECT-OK-7731` marker. Please also confirm the review denominator
> treatment; no scenario or protocol should be approved/frozen by this message.

### Mentor/supervisor

> Please review ADR-08/ADR-09 in
> [ADR-001](../../../docs/ADR-001-approvals.md), the proposed
> [protocol](../../../data/heldout/protocol.json), and the
> [freeze checklist](../../../data/heldout/FREEZE_CHECKLIST.md). I need your
> decision to approve or revise the 120 security-run accounting, confirm the
> separate 100 repeatability-scoring invocations, approve/revise the 20-case mix
> and five repeats, settle population standard deviation and precision/FPR
> denominators, and confirm that original acceptance obligations remain unless
> explicitly changed. Final collection must remain blocked until the checklist
> and human reviews are complete.

## Exact approvals still needed before final collection

- [ ] M1, M4, M5, and mentor record an ADR-08 decision on the 120-run accounting.
- [ ] M1/M4/mentor approve or revise the held-out composition and five repeats;
      M5 records its required acknowledgment separately.
- [ ] Two independent reviewers approve each of the four Arabic MSA/EGY pairs.
- [ ] M4 approves the semantic judge/checker version and injection marker.
- [ ] M1/M2/M3 approve and complete `get_score`, persistence, private held-out
      access, immutable IDs, and pricing provenance.
- [ ] M1/mentor approve the complete versioned freeze record and human-review
      protocol after every checklist item is satisfied.
- [ ] Mentor and affected owners settle population standard deviation and the
      precision/FPR denominator.
- [ ] M1 records M5's member mapping, owner acknowledgments, and the shared-report
      contract decision.

## Non-action confirmation

This packet was saved as a new draft only. No message was sent, no issue was
created, no approval/status field was changed, no dataset or protocol was frozen,
and no branch, commit, push, or merge operation was performed.
