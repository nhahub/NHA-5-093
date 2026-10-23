# M5 decisions and dependencies requiring approval

No item below is treated as approved by this implementation.

1. **ADR-08 run accounting (blocking):** approve or revise the proposed 80 base
   matrix runs plus 40 extra security repeats. The generated ledger is marked
   non-comparable and cannot be used for final collection.
2. **Separate scoring ledger:** confirm that 10 frozen transcripts × 5 scoring
   repetitions × 2 targets remains a separate 100-invocation obligation.
3. **Scenario composition:** approve the proposed 20-case held-out composition
   (10 intended-violation cases, 2 benign controls, and 8 MSA/EGY dialect cases)
   and the five scenarios selected for extra repeats.
4. **Arabic equivalence review:** two independent human reviewers must approve
   every MSA/EGY pair. All current reviewer lists are empty and all pair statuses
   remain `PENDING`.
5. **Freeze:** M1/mentor must approve the protocol, split membership, scenario
   contents, role/policy/checker/target/model versions, seeds, budgets, pricing
   snapshot, and reviewer protocol before hashes become `FROZEN_APPROVED`.
6. **Repeatability statistic:** this implementation proposes population standard
   deviation because each five-repeat cell is the full planned cell. Confirm this
   choice before final reporting.
7. **Shared report gaps:** `ReportSummary` cannot carry family-level breakdowns,
   individual pair/repeat rows, cancelled/pending counts, or source score/event
   IDs. M5 emits these in its detailed sidecar result. M1/M3/M6 must decide whether
   a versioned shared-contract update is required for the API/UI.
8. **Cost provenance:** current run/event contracts do not persist a pricing
   snapshot. M3 must provide approved, versioned pricing evidence or final cost
   remains `null`; M5 will not infer a price from current public internet data.
9. **Held-out access boundary:** Git repository paths are not access control. M3
   must ensure only the controller-side `ScenarioRepository` reads full held-out
   records and the agent receives only `AgentScenarioView`.
10. **Rubric/scoring integration:** M3 must persist `ScoreResult` records and M2/M3
    must connect `get_score`; current controller runs do not produce scoring data.
11. **M4 dependencies:** semantic checking needs an approved judge, and the
    `HG-INJECT-OK-7731` marker is still explicitly an M4 proposal.
12. **Owner mapping and review:** verified M5 handle `RanaSakr` is registered in
    prerequisite PR #19 and this branch. #19 must land on trusted main and actual
    current-head owner/independent human reviews remain required before merge.
13. **M2 scenario-view integration:** `services/engine/state.py` currently contains
    a second `to_agent_view` projection that supplies defaults for missing fields
    instead of using M5's contract-validating repository projection. M1/M2/M5
    must approve an integration change in the M2-owned path; this PR does not
    alter it.
14. **M3 score boundary:** the mock adapter implements `get_score`, but there is
    no controller call or immutable persistence path for the returned
    `ScoreResult`. M2/M3 must agree the stored session/score handoff before the
    dialect or repeatability ledgers can be executed.
15. **Discovery unit ambiguity:** multiple confirmed rule findings from one run
    can exceed the completed-attempt denominator and violate ReportSummary's
    bounded rate. M1/M4/M5/mentor must choose the final unit. Until then analysis
    rejects such an aggregate; it does not clamp, drop flags or redefine the rate.

The original duplicate M2 projection remains unchanged in this repair. Contract
tests establish identical safe views for valid scenarios, and the engine already
validates full scenarios before projecting. Consolidation is a later M2/M5 choice.
