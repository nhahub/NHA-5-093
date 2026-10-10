# ADR-001: Lead approval checklist (PROPOSED; not yet frozen)

All choices below are proposed to resolve missing/conflicting details in the source PRDs. M1 must obtain all six owners' acknowledgment before declaring `APPROVED` and tag `contracts-v1.0.0`.

| ID | Decision proposed | Status | Owners |
|---|---|---|---|
| ADR-01 | Python 3.11, FastAPI, Pydantic 2, SQLAlchemy 2, SQLite WAL; React+TypeScript+Vite; LangGraph; Docker Compose; Python mock model by default | PROPOSED | M1,M2,M3,M6 |
| ADR-02 | One local modular monolith: API process + single in-process DB-backed sequential worker; no Redis/Celery/microservices for MVP; Uvicorn workers=1. Crash during running => FAILED, queued runs resume. | PROPOSED | M1,M3 |
| ADR-03 | Agent-visible tools: load_policy, send_turn, check_evidence; mandatory evidence saving and human-review request executed by trusted controller, not by agent. | PROPOSED, aligns PDF 3-tool and Word 5-action descriptions | M1,M2,M3,M4 |
| ADR-04 | REST prefix `/api/v1`; endpoints and payloads exactly `contracts/openapi.yaml`; internal adapter contract exactly those corresponding schemas. | PROPOSED | ALL |
| ADR-05 | Input budgets per scenario: at most 6 candidate turns; `max_total_tokens` covers agent + target tokens; provider usage must be recorded; enforce a conservative pre-call token reservation; if usage cannot be measured reliably return INCONCLUSIVE/FAILURE and record reason. | PROPOSED | M2,M3,M5 |
| ADR-06 | Append-only events and review dispositions. `Finding.reviewer_status` is a read projection; no overwriting machine proposal or earlier reviews. | PROPOSED | M3,M4,M6 |
| ADR-07 | `RETEST_INCONCLUSIVE` extends PDF RetestLink verdict enum for `status_after=INCONCLUSIVE`, which otherwise has no honest verdict. This MUST be approved as a controlled schema change. | BLOCKING APPROVAL | M1,M3,M4 |
| ADR-08 | 80 held-out matrix runs + 40 extra repeats = 120 security runs (Word: five scenarios, two additional replicates, 2 methods, 2 target variants). Separate fixed-transcript scoring-repeatability tests have their own job count, not silently counted within 120. | BLOCKING APPROVAL | M1,M4,M5,mentor |
| ADR-09 | Four-week acceleration does not automatically waive original FR-01..33, AC-01..09, 90% completion, 80% precision, or 120 planned runs. Any changed P0 or acceptance target needs supervisor approval. | BLOCKING APPROVAL | M1,mentor |
| ADR-10 | Model provider/model ID/pricing quota configured via env and persisted in versioned RunConfig. In deterministic mock mode, results are visibly labeled MOCK and must not be represented as live model evidence. | PROPOSED | M1,M2,M3 |
| ADR-11 | Held-out labels, expected results, and hidden split classification never enter agent prompts or tool outputs; freeze scenarios/policies/models/seeds before experiments. | PROPOSED | M4,M5 |
| ADR-12 | Team's actual names / handles (M1..M6) and backups to be entered after members choose roles. Until then, aliases M1-M6 are authoritative; do not invent names. | UNRESOLVED | M1 |

Lead approval date: ________
Release version: __________
Member mapping: M1=________ M2=________ M3=________ M4=________ M5=________ M6=________
Owner acknowledgments: __________________________________________

Approval process: record decisions with rationale, update schemas and fixtures, run `scripts/validate_contracts.py`, run consumer contract tests, tag version, and communicate the change. No arbitrary fixes to a contract in an individual PR.
