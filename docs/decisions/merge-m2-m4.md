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
