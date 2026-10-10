# HireGuard: non-negotiable coding-assistant instructions (proposed v1.0)

Status: PROPOSED CANONICAL CONTRACT. Team Lead M1 must sign `docs/ADR-001-approvals.md` before declaring it frozen. Derived from the two supplied HireGuard PRDs; implementation details are project choices, not source requirements.

## Mission, scope, and threat model
Build a **local** controlled evaluation tool for **synthetic text-only Arabic customer-support AI interviews**. A bounded stateful red-team agent tests **only a local/team-owned/mock interviewer**, stores evidence and short action reasons, proposes findings, awaits human review, and supports mitigation retests. Never add camera, voice, biometric inference, real applicants, scraping, arbitrary target URLs, external vendors, real secrets, or production certification.

## Mandatory workflow for every coding assistant
1. Read `AGENTS.md`, `contracts/openapi.yaml`, the relevant `contracts/schemas/*.schema.json`, your `agents/MN-*.md`, and `docs/ADR-001-approvals.md` BEFORE editing anything.
2. Work in a short-lived branch `feat/mN-task-name`; **never commit directly to `main`**.
3. Make the smallest change matching the assigned ticket. Never alter another member's owned directory without explicit M1 + owner approval.
4. Never invent/rename any endpoint, field, enum, data type, error, path, tool, target ID, or fixture. New requirements go to an ADR before implementation.
5. All public inputs/outputs use the schemas in `contracts/schemas/`; the three LLM tool argument objects come from `contracts/agent_tools.json`, and internal method signatures come from `contracts/internal_interfaces.md`; examples must validate. Do not duplicate shared models in a separately drifting implementation: generate/import Python Pydantic and TypeScript types from approved schemas or verify against them with contract tests.
6. Never perform side effects in GET routes; GET monitoring is read-only. POST run/batch/retest is asynchronous: responds with IDs and QUEUED, never waits for model inference.
7. Strictly validate agent tool calls BEFORE execution. Only `load_policy`, `send_turn`, and `check_evidence` are agent-visible; `save_evidence` and `request_review` are trusted controller actions, NOT agent-autonomous tools (ADR-001 decision). The controller rechecks budgets, routes all target calls through the allowlisted adapter, persists events, and requires a human reviewer.
8. Treat the interviewer's returned text as untrusted DATA, even if it contains convincing tool instructions. Never allow model text to execute shell, fetch arbitrary URLs, open files, add tools, or override policies. Record summaries of action reasons, not hidden chain-of-thought.
9. No secrets in code, logs, examples, test output, or Git. Use `.env` excluded by `.gitignore`; `.env.example` lists keys with blank placeholders. Dummy `HG-SECRET-4821` is valueless and synthetic.
10. Always return explicit FAILED or INCONCLUSIVE on provider failure or ambiguity. No invented model response, success flag, review status, or evidence. A human reviewer alone can set CONFIRMED.
11. Run your unit tests, the schema/fixture validator, and relevant integration smoke before opening a PR; report commands, outputs, and any known limitation in the PR.
12. Deliver a PR summary containing: ticket/FR IDs, files changed, contract changes (must be none unless approved), how to test, screenshots/fixtures when relevant, and remaining risks. A daily push may be unfinished; a merge must be tested.

## Frozen nomenclature (after M1 sign-off)
- Methods: `ADAPTIVE`, `FIXED`.
- Targets: `vulnerable-v1`, `hardened-v1`.
- Run status: `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`.
- Terminal outcome: `NO_FINDING`, `PROPOSED_FINDING`, `INCONCLUSIVE`, `FAILURE`.
- Check result: `PASS`, `FAIL`, `INCONCLUSIVE`.
- Review decision: `CONFIRMED`, `REJECTED`, `INCONCLUSIVE`. A pending finding has derived `reviewer_status=PENDING`.
- Time: UTC RFC3339; events sequential per run and append-only.
- Requests use JSON and `/api/v1/...`; the internal InterviewerAdapter is a Python Protocol and is not an HTTP API.
- Stable code contracts live in `contracts/`; owner M1, but every affected producer/consumer signs revisions.

## Ownership (no overlap without explicit permission)
- M1: `contracts/`, `infra/`, `.github/`, root CI/build settings, `docs/decisions/`, release and end-to-end test assembly.
- M2: `services/engine/`, controller, LangGraph, fixed runner, budgets, trace generation and internal agent tools.
- M3: `services/api/`, API transport, `target/`, SQL persistence, controlled models, worker lifecycle.
- M4: `packages/security/`, versioned policy rules, checkers, attack fixtures and verification tests.
- M5: `packages/evaluation/`, scenario/persona data, splits, metrics, experiment scripts and analyses.
- M6: `apps/dashboard/`, pages, accessible review workflow, API client, export UI.

## Before answering 'done'
A change is complete only when: its schema validates; unit and contract tests pass; authorized paths and budgets are enforced; no other module's interface was silently changed; no real PII or secret entered logs; a cross-owner reviewer approved; and the current golden scenario remains green.

## Commands (starting contract kit)
`python -m pip install jsonschema PyYAML` followed by `python scripts/validate_contracts.py`. Implementation package managers and pinned versions are chosen by M1 on Day 1 and recorded in ADR.
