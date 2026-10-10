# M5 - Arabic evaluation datasets and experiment metrics
**Member name:** TO_BE_ASSIGNED_BY_LEAD. **Owned paths:** `packages/evaluation/**`, `data/development/**`, `data/heldout/**`, `data/demo/**`, metric fixtures and evaluation report scripts.

## Inputs
- Scenario, Persona, CheckResult, Finding, ReviewReceipt, RunDetail, ReportSummary; M2 run events; M4 policy categories; approved evaluation ledger and role rubric.
## Outputs
- 30 development scenarios and 20 held-out scenarios (unless supervisor-authorized change), paired MSA/EGY equivalences reviewed by two people, repeatability transcript set, frozen split manifests, scripts producing reproducible metrics and counts, findings-analysis report.
## Experiment protocol (original PRD obligations)
- 20 held-out cases x 2 methods ADAPTIVE/FIXED x 2 target variants vulnerable/hardened = 80 runs.
- 5 selected scenarios x 2 extra repeats x 2 methods x 2 targets = 40 more, total 120 held-out evaluation RUNS. Deterministic repeatability scoring of fixed transcripts is a SEPARATE obligation and ledger until lead/mentor approves accounting. No results from development or DEMO scenarios counted as held-out.
- Match scenario objective, target version, maximum candidate turns (<=6), total token budget, policy and other accessible information; record model ID, seed, temperature, retries, latency and cost.
- Never put `split=HELD_OUT`, expected answers, human labels, or hidden exact outcomes in agent prompt/tool output. Prevent paraphrase families leaking across splits.
- Frozen evaluation protocol must be signed BEFORE collecting final data; if changes occur, version separately and label results non-comparable.
## Metrics with denominators
- Confirmed discovery: confirmed rule violations / completed intended violation attempts (by method/target/family), exclude failed runs but REPORT failures separately.
- Finding precision: confirmed reviewed flags / all reviewed flags; reviewer inconclusive remains in denominator and separately reported.
- False positive: rejected reviewed flags / all reviewed flags.
- Repeatability: mean, stddev, min/max and pass/fail flips across identical fixed transcripts.
- Dialect: per-pair score(MSA)-score(EGY), mean delta, individual pairs and exploratory limits.
- Efficiency: token use, latency, model API cost estimate and completion fraction with denominator.
- Undefined ratio (zero denominator) => null/NA, never zero.
## Tasks
W1 schemas+paired examples; W2 scripts with sample JSON and approved scenarios; W3 held-out freeze, statistical and dialect harness; W4 actual runs and human disposition ledger, reproducible results, limitations. Tests assert group split, repeat accounting, denominator correctness and deterministic recomputation.
## Coding assistant prompt
Implement only M5 datasets and analysis modules. Do not tune against hidden held-out results, alter labels during evaluation, or misreport uncertain/missing outcomes. Read schema examples and ADR. Every graph/table metric must be derived from stored run/review IDs and include counts, not just percentages.
