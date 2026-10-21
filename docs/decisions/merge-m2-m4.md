# M2/M4 integration increment — 21 October 2026

This is a repair and review increment, not a contract freeze or application release.
The project lead authorized preparation of both owner branches and integration
repairs in this chat. This does not stand in for the owners' review acknowledgments.
The canonical payloads and Protocol signatures remain unchanged.

Merge order is foundation PR #10, security PR #17, then engine PR #16. Use merge
commits; never bypass main protection. Every new head needs an independent human
review. Bot comments and this coding assistant are not human approvals.

Verified PR authors identify M2 as `Iabdallllah` and M4 as `Mohamedislam42`.
Backups and other missing assignments remain pending. Register owner test commands
when their package manifests arrive; missing application modules remain pending.

## Integration choices for affected-owner review

- Follow the central async AgentRunner/InterviewerAdapter/EvidenceStore contracts.
  The adapter returns the session ID. The store allocates event IDs and sequences.
- Use the same controller pipeline for FIXED and ADAPTIVE; only probe selection
  changes. Both methods require real checks and append-only persisted proposals.
- Resolve private rules from M4's catalog and the scenario allowlist. Only public
  projections reach the provider. Invalid/missing checks cannot mean NO_FINDING.
- Use the persisted run's configuration, resolved versions and creation metadata;
  M3 remains responsible for worker lifecycle persistence. The engine returns a
  canonical RunDetail and records state events, without inventing store methods.
- Count every attempted model call. Provider and target usage must be complete,
  nonnegative and internally consistent. Bound calls by the remaining deadline
  and reserve output tokens before calls; no blind conversational retries.
- The delivery supports deterministic mock and loopback-only Ollama. No Groq or
  arbitrary network provider is enabled. Approved local model collection is a
  later gate; CI never runs live inference.
- ADR-07 remains unsigned. Inconclusive mitigation verdict generation raises a
  visible error until actual approval; it never reports confirmed persistence.
- Strategy allowlists, text length bounds and span code-point interpretation are
  implementation controls for owner review, not new public enums or fields.

## Required evidence and remaining approvals

Run locked installation, contracts, Ruff, all tests, security-pack validation and
registered owner suites on Windows and Linux. Integration tests must use the
actual M4 checker with async adapter/store doubles, inspect persisted records and
cover both methods, budgets, cancellation, usage failures and Unicode spans.

M2/M4 boundary acknowledgment and M3 async/lifecycle acknowledgment remain pending.
ADR signatures are not inferred. Main merge is blocked until actual current-head
human reviews and required checks pass. After #10 lands, require the trusted
ownership status and verify the settings through the GitHub API. Missing M3/M5/M6
modules, browser/HTTP/SQLite/Compose integration and the full application golden
scenario remain pending; in-memory engine/checker tests do not satisfy them.

## Repair evidence

- Foundation `fcd8ba2`: all five hosted checks passed, including Windows/Linux.
- Security `3b59324`: 91 security tests plus 42 foundation tests passed locally;
  all five hosted checks passed, including Windows/Linux and secret scanning.
- Engine code `a207cd9`: 233 combined tests passed locally; 100 engine tests and
  91 security tests also passed independently. Canonical schemas/examples remain
  unchanged. A subsequent regression additionally verifies that a checker needs
  only the documented method, not an undocumented version attribute.
- Locked installation, npm clean install, Ruff and security-pack validation passed.
  Whole-repository secret scanning uses the unchanged exact-canary allowance.
  Fixture constants were refactored to avoid scanner false positives, without
  adding exemptions or concealing credentials. No real credential was involved.
- Both existing trace exports were regenerated through the actual async runner
  and M4 checker, explicitly marked MOCK. Their second decisions differ after
  different first observations. Persisted lifecycle events precede engine events.

The engine's local-only model seam has no automatic retry or fallback. A reliable
tokenizer must be supplied before live Ollama inference. Its tracing dependency
is declared directly and tracing is explicitly disabled around execution.

M3 must not perform inference in start_session, whose response cannot carry usage.
Its target adapter must enforce generation reservations using the persisted run
budget. The central Protocol currently supplies no pre-call usage/reservation
method; the controller uses a conservative 300-token reservation, records actual
usage and terminates explicitly on an overrun. This does not prove a hard upper
bound on target output. No completed local-model evaluation is claimed.

M3 also owns persistence of the returned RunDetail counters/times/outcome along
with its worker lifecycle. The engine appends canonical evidence and a terminal
STATE event; the in-memory test double does not establish database transactions,
restart recovery or asynchronous HTTP creation behavior.

All three PRs remain dependent on actual independent human reviews. After the
foundation lands, enable the trusted ownership status with the documented
provisioning command and refresh it after current-head approvals. Do not weaken
protection, manufacture owner acknowledgments, or merge around missing reviews.
