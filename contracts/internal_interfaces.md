# HireGuard internal Python contracts - proposed v1.0 (M1 signs off)

**The JSON Schema files define data payloads.** These signatures define method ownership and must not be independently changed. Use generated Pydantic models or typed wrappers with exactly these names and field meanings; M1 selects the generation process and pins dependencies.

## M3 InterviewerAdapter
```python
class InterviewerAdapter(Protocol):
    async def start_session(self, req: AdapterStartRequest) -> AdapterStartResponse: ...
    async def send_turn(self, req: AdapterTurnRequest) -> AdapterTurnResponse: ...
    async def get_score(self, session_id: str) -> ScoreResult: ...
    async def close_session(self, session_id: str) -> None: ...
```
`AdapterTurnRequest` fields run_id, session_id, turn_index, message, idempotency_key are SERVER INJECTED, never freeform LLM args.

## M3 EvidenceStore (internal interface)
```python
class EvidenceStore(Protocol):
    async def create_run(self, config: RunCreate) -> RunReceipt: ...
    async def get_run(self, run_id: str) -> RunDetail: ...
    async def append_event(self, run_id: str, event_type: str,
                           actor: str, turn_index: int, data: dict) -> AuditEvent: ...
    async def save_check(self, check: CheckResult) -> CheckResult: ...
    async def save_finding(self, finding: Finding) -> Finding: ...
    async def append_review(self, finding_id: str, req: ReviewCreate) -> ReviewReceipt: ...
    async def list_events(self, run_id: str, after_seq: int | None,
                          limit: int) -> dict: ...  # {items:[AuditEvent],next_cursor}
```
Transactions enforce UNIQUE(run_id,seq) and review idempotency; append-only rows are never overwritten. Derived `reviewer_status` is computed when reading Finding.

## M5 ScenarioRepository
```python
class ScenarioRepository(Protocol):
    def get_approved(self, scenario_id: str, suite_version: str) -> Scenario: ...
    def to_agent_view(self, scenario: Scenario) -> AgentScenarioView: ...
    def get_persona(self, persona_ref: str) -> Persona: ...
```
Adaptive agent NEVER receives Scenario.split, Scenario.expected_behavior, Scenario.fixed_prompts, labels, or private policy value. Only `AgentScenarioView` is passed to M2 agent model. The fixed-script baseline reads approved `fixed_prompts` through controller without exposing them as future-answer hints to adaptive.

## M4 EvidenceChecker
```python
class EvidenceChecker(Protocol):
    def check_evidence(self, request: CheckRequest,
                       events: list[AuditEvent],
                       rules: list[PolicyRule]) -> list[CheckResult]: ...
```
The checker gets PRIVATE `PolicyRule` with forbidden canary while tool `load_policy` returns PUBLIC `PolicyRulePublic` to LLM.

## M2 AgentRunner
```python
class AgentRunner(Protocol):
    async def execute_run(self, run_id: str, config: RunCreate,
                          scenario: Scenario,
                          adapter: InterviewerAdapter,
                          store: EvidenceStore,
                          checker: EvidenceChecker) -> RunDetail: ...
```
Controller derives `AgentScenarioView` before LLM calls; enforces limits; does not mutate approved scenario. M3 orchestrates queue & worker; M2 does not implement HTTP routes.

## M5 MetricsService
```python
class MetricsService(Protocol):
    def aggregate_batch(self, batch_id: str,
                        run_records: list[RunDetail],
                        findings: list[Finding],
                        review_events: list[ReviewReceipt]) -> ReportSummary: ...
```
Report linked `run_ids` must include all analyzed records. The exact number of held-out runs requires lead-approved frozen ledger.

## Exceptions and failure boundaries
- No provider error is transformed into a fabricated success payload. Transport turns failed/timeout into ErrorResponse and run FAILURE or INCONCLUSIVE as appropriate.
- A malformed LLM NextProbe is rejected before adapter invocation; do not guess field names or auto-repair into an undocumented action.
- Adapter/Checker interface signatures change only with M1 and BOTH affected owners' acceptance.
