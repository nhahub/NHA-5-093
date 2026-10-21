# M1 foundation: implementation record

Status: tooling selected by M1's implementation request; application ADR decisions remain PROPOSED.

M1 is WalidAbdelmeguid. M2-M6 identities and all backups are unassigned in
`infra/team.json`; no names or acknowledgments are inferred. The original PRDs
and master specification have now been recovered unchanged into `sources/` with
SHA-256 provenance. See source-reconciliation.md and the 54-row traceability map.
Source differences and owner acknowledgments still prevent contract freeze.

## Tooling

- Python 3.11.14, uv 0.10.10, Node 24.15.0, npm 11.12.1.
- One root uv workspace and lock; each Python owner supplies their own package
  manifest. One root npm workspace and lock; M6 supplies the dashboard manifest.
- JSON Schema is the source of validation truth. M1 tooling validates payloads
  directly against the shared schemas. Owners must use generated models or prove
  their boundary models with contract tests; independently drifting models fail
  acceptance. No generated application model is silently introduced here.
- Dependency resolution is committed in lockfiles; CI installs with `--locked`
  and `npm ci`. Dependency updates are reviewed PRs, never implicit CI updates.
- Root commands wrap owner-provided command arrays in `infra/handoffs.json`.
  Missing modules fail with PENDING and nonzero exit. No fake application is
  supplied to make integration green.

## Ownership and bootstrap

No M2-M6 module or brief is modified. Shared model, provider and interface decisions
still need the acknowledgments required by ADR-001. This foundation is a bootstrap
PR; the trusted-base ownership workflow becomes usable after it is merged. Native
independent-review protection must govern the bootstrap if the repository's plan
supports it. Rerun provisioning after merge to require the ownership status.

Only actual known handles enter CODEOWNERS. CODEOWNERS cannot express the required
M1 AND affected-owner review rule; `check_approvals.py` checks latest-head human
reviews, writer permissions, prior rename paths and all shared-contract consumers.
The policy executes base-branch code with read-only contents/review access and
commit-status write access, never PR-head code. Review refresh uses a trusted
issue-comment trigger, not a PR-head review workflow. Only write-authorized members
can refresh the policy using `/check-ownership`.

## Decisions still requiring affected-owner approval

| Topic | Evidence / proposed resolution | Required owners |
|---|---|---|
| Runner signature | M2 brief returns RunOutcome with a different signature; central Protocol returns RunDetail. Use the central signature after M2/M3 acknowledgment and update the brief in an owner PR. | M1,M2,M3 |
| Session identifiers | AdapterStartResponse returns session_id; controller manages lifecycle and injects it into subsequent requests. Clarify language claiming the controller creates every ID. | M1,M2,M3 |
| Message ownership | Internal interface text calls message server-injected, while agent_tools accepts message. Treat it as model-supplied but controller-validated; never trust model-supplied session/run/turn/idempotency fields. | M1,M2,M3 |
| Strategy allowlist | No canonical strategy list exists. Owners must agree on a versioned allowlist and its source before adaptive integration. | M1,M2,M4,M5 |
| Model snapshot and mode | Existing fields record agent/target model IDs but do not settle complete target settings, hardware or explicit mode transport. Propose a versioned solution before changing schemas; IDs prefixed mock- only support the current mock smoke. | M1,M2,M3,M5,M6 |
| Evidence spans | Existing examples use target_response[start:end]. Agree on Unicode code-point offsets, end-exclusive, with M4/M6 before claiming multilingual span compatibility. | M1,M3,M4,M6 |
| Retest semantics | Schema enums do not enforce all before/after/verdict combinations or pending result rules; test them at runtime. RETEST_INCONCLUSIVE remains subject to ADR-07 approval. | M1,M3,M4 |
| Evaluation accounting | 80 matrix + 40 extra runs; fixed-transcript scoring repetition remains separate. Original sources and mentor approval required. | M1,M4,M5,mentor |

No public endpoint, schema, field, enum, tool or existing fixture is changed by this
foundation. Do not tag contracts-v1.0.0 or an application release until the relevant
source reconciliation, owner approvals and runtime gates pass.
