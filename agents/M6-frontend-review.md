# M6 - Frontend dashboard and human evidence review
**Member name:** TO_BE_ASSIGNED_BY_LEAD. **Owned paths:** `apps/dashboard/**` and UI/component tests. Do NOT edit API backend or contracts without accepted ADR.

## Inputs
- `contracts/openapi.yaml` and schemas RunCreate, RunReceipt, RunDetail, AuditEvent, Finding, ReviewCreate/Receipt, RetestCreate/Receipt/View/Result, ReportSummary; M3 mock responses and M5 sample reports.
## Outputs
- Accessible React/TypeScript local dashboard, run creation, batch selection, readonly status monitor, evidence timeline with Arabic RTL, human disposition action+note, comparative report, JSON/CSV/Markdown export and explicit MOCK-mode watermark.
## Page contract
1. `/` overview + target/version/method/scenario selection: POST `/api/v1/runs` or `/batches`, show returned run_id and status.
2. `/runs/:runId`: GET run status and events every 1-2s (read-only), show budgets, exact event order, observed fact and decision reason. Stop polling at terminal state.
3. `/runs/:runId/findings`: list machine proposals and reviewer status, link transcript spans, never display 'confirmed' for pending proposal.
4. `/findings/:findingId`: POST review decision with reviewer ID, required note, idempotency key; show persisted timestamp and append-only history when API supports it.
5. `/retests`: POST retest for approved confirmed original; GET RetestView. While QUEUED/RUNNING, result is null; never invent mitigation success. Display before/after run IDs and target version.
6. `/reports/:batchId`: GET report and display numerator/denominator, completion and failures, dialect/repeatability limitations, exports.
## Implementation constraints
- Use generated TypeScript client/types from OpenAPI or JSON schemas; do not manually invent backend fields.
- GET polling MUST be side-effect free. No fake success toast before server confirms. No inferred OPEN/current statuses, secrets or API keys in client.
- Arabic content uses `dir=rtl` for transcript panes only; mixed JSON/code stays ltr. All controls have labels; status text never relies only on color.
- Model calls are asynchronous: show queued/running, error, cancel; UI never calls target model itself.
- Mock example data comes from `contracts/examples/` until M3 real responses are available.
## Tasks
W1 skeleton mock views; W2 live monitor/review; W3 reports/retest/export/RTL tests; W4 smoke on clean laptop and demo recording. Include tests for run creation, unchanged GET data, review submissions, Arabic RTL, missing evidence graceful handling, and mock watermark.
## Coding assistant prompt
Implement only frontend and UI tests. Treat OpenAPI as sole network truth. Build against fixtures first; never add unapproved endpoints or hard-coded backend response keys. Show actual `PENDING` until human review succeeds; never convert an uncertain result into a success badge. Return screenshots, tests and PR summary.
