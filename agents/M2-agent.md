# M2 - Agent orchestration / adaptive & fixed runners
**Member name:** TO_BE_ASSIGNED_BY_LEAD. **Owned files:** `services/engine/**` and agent-focused tests. Others' schemas, persistence and target logic are read-only.

## Inputs
- `RunCreate`, `AgentScenarioView`, `NextProbe`, `PolicyRulePublic`, `CheckResult`, `AdapterStart*`, `AdapterTurn*` from `contracts/schemas/`.
- M3's `InterviewerAdapter` Protocol with deterministic mock responses; M4 `check_evidence()` checker; M5 scenario selector; M1 frozen token/timeout semantics.
## Outputs
- `run_fixed(config, scenario, adapter, store)` and `run_adaptive(...)` entry points with same budgets, state graph, bounded calls, structured NextProbe, complete decision events, and terminal run outcome.
## Required internal Python interface (proposal; freeze with M1)
- `async def execute_run(run: RunCreate, *, run_id: str, adapter: InterviewerAdapter, store: EvidenceStore, checker: EvidenceChecker, scenario: Scenario) -> RunOutcome`
- `async def load_policy(rule_ids: list[str]) -> list[PolicyRulePublic]`
- `async def send_turn(session_id: str, message: str, run_id: str, turn_index: int) -> AdapterTurnResponse` (controller-internal wrapper; model-visible `send_turn` accepts only `message` + `strategy_id` per `contracts/agent_tools.json`)
- `async def check_evidence(run_id: str, turn_index: int, rule_ids: list[str]) -> list[CheckResult]`
- Only these three names may be exposed to LLM as tools. Persistence/review routing is controller-only. The controller generates session ID and idempotency key, never takes from freeform LLM text.
## Tool argument ownership
The LLM may supply only `message` and `strategy_id` to the `send_turn` tool. Controller injects run_id, session_id, turn_index and idempotency_key. Mandatory checks run automatically even when the model does not request check_evidence. Agent sees sanitized PolicyRulePublic and AgentScenarioView only.

## Tasks and tests
1. W1: Fixed runner with M3 mock; `AgentState` with per-run fresh transcript/strategy history/budgets; state transition tests and `NextProbe` schema parser.
2. W2: LangGraph initialize -> choose probe -> validate -> send -> observe/append -> verify -> budget/termination -> repeat. Real model wrapper plus clearly marked MOCK stub.
3. W2: Output strict `NextProbe` with allowed strategy IDs. Reject malformed output, unknown tools, over-limit candidate messages, out-of-order turns, budget exhaustion BEFORE any adapter call, and target text as instructions.
4. W3: Genuine observation-dependent branch on at least two final traces; fixed runner not adaptive; compare same scenario, target, prompt objective and turn/token budgets.
5. W4: Failure/cancellation tests, no cross-run memory, trace completeness, replay support, final owner acceptance.
## Required unit cases
`test_refusal_causes_strategy_change`, `test_no_calls_after_turn_limit`, `test_no_calls_after_token_limit`, `test_target_prompt_injection_is_data`, `test_invalid_tool_name_rejected`, `test_no_state_leak`, `test_fixed_repeatable_fixture`, `test_hard_timeout_no_blind_retry`.
## Coding assistant prompt
Implement only M2-owned `services/engine/` and M2 tests. Use approved contract schemas; never invent tool names or call unrestricted URLs. Begin with deterministic M3 fixtures. Persist concise observed fact/action reason, never hidden chain of thought. Show exactly two distinct observation-driven trace fixtures. Report unresolved provider/tokenizer assumptions as blockers, not guessed behavior.
