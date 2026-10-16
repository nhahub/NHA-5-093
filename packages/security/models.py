# Local mirrors of contracts/schemas/*.schema.json (M1 owns the truth).
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

Result = Literal["PASS", "FAIL", "INCONCLUSIVE"]

class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

class CheckRequest(_Strict):
    run_id: str
    turn_index: int = Field(..., ge=1, le=6)
    rule_ids: list[str] = Field(..., min_length=1)

class AuditEvent(_Strict):
    event_id: str = Field(..., pattern=r"^evt_[a-f0-9]{12}$")
    run_id: str
    seq: int = Field(..., ge=1)
    event_type: Literal["STATE", "DECISION", "TURN", "CHECK", "ERROR"]
    actor: Literal["CONTROLLER", "AGENT", "TARGET", "CHECKER"]
    turn_index: int = Field(..., ge=0)
    occurred_at: str
    data: dict[str, Any]

class PolicyRule(_Strict):
    rule_id: str = Field(..., pattern=r"^POL-[A-Z]+-[0-9]{2}-[A-Z0-9-]+$")
    version: str
    description: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    checker_type: Literal[
        "EXACT_CANARY",
        "SCHEMA",
        "SEMANTIC",
        "SCORING_DRIFT",
        "BENIGN_CONTROL",
        "CANARY_EXACT",
        "REGEX",
    ]
    forbidden_value: str | None = None
    review_required: bool = True

class PolicyRulePublic(_Strict):
    rule_id: str = Field(..., pattern=r"^POL-[A-Z]+-[0-9]{2}-[A-Z0-9-]+$")
    version: str
    description: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    review_required: bool = True

class CheckResult(_Strict):
    check_id: str
    run_id: str
    turn_index: int = Field(..., ge=1, le=6)
    rule_id: str
    result: Result
    evidence_event_ids: list[str] = Field(default_factory=list)
    evidence_spans: list[str] = Field(default_factory=list)
    checker_version: str
    reason: str

class FindingProposal(_Strict):
    verdict: Literal["FAIL", "INCONCLUSIVE"]
    turn_index: int = Field(..., ge=1, le=6)
    evidence_event_ids: list[str] = Field(..., min_length=1)
    evidence_spans: list[str] = Field(default_factory=list)
    reason: str

class Finding(_Strict):
    finding_id: str = Field(..., pattern=r"^fnd_[a-f0-9]{8}$")
    run_id: str
    scenario_id: str
    rule_id: str
    category: Literal["INJECTION", "SECRET_LEAK", "RUBRIC_DRIFT", "POLICY_VIOLATION"]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    proposal: FindingProposal
    reviewer_status: Literal["PENDING", "CONFIRMED", "REJECTED", "INCONCLUSIVE"]

class Scenario(_Strict):
    scenario_id: str = Field(..., pattern=r"^scn_[a-z0-9_]+$")
    suite_version: str
    split: Literal["DEVELOPMENT", "HELD_OUT", "DEMO"]
    family: Literal[
        "INJECTION",
        "SECRET_LEAK",
        "RUBRIC_DRIFT",
        "POLICY_VIOLATION",
        "BENIGN_CONTROL",
        "DIALECT_PAIR",
        "REPEATABILITY",
    ]
    role_id: str
    objective: str
    persona_ref: str
    rule_ids: list[str] = Field(..., min_length=1)
    expected_behavior: str
    fixed_prompts: list[str] = Field(..., min_length=1)
    approved: bool
    seed: int = Field(..., ge=0)

class RetestResult(_Strict):
    retest_id: str
    original_run_id: str
    retest_run_id: str
    mitigation_version: str
    status_before: Literal["CONFIRMED_FAIL"]
    status_after: Literal["PASS", "FAIL", "INCONCLUSIVE"]
    verdict: Literal["MITIGATION_VERIFIED", "VULNERABILITY_PERSISTS", "RETEST_INCONCLUSIVE"]

class NextProbeModel(_Strict):
    action: Literal["SEND_TURN", "STOP"]
    strategy_id: str
    message: str | None
    observed_fact: str
    decision_reason: str
    hypothesis: str

class ScoreResultCriterion(_Strict):
    criterion_id: str
    points: float = Field(..., ge=0)

class ScoreResult(_Strict):
    session_id: str
    role_id: str
    rubric_version: str
    criterion_scores: list[ScoreResultCriterion] = Field(..., min_length=1)
    score_total: float = Field(..., ge=0, le=100)
    pass_: bool = Field(..., alias="pass")
    evaluated_transcript_hash: str = Field(..., pattern=r"^[a-f0-9]{64}$")

class RubricCriterion(_Strict):
    criterion_id: str
    description: str
    max_points: int = Field(..., ge=1, le=100)

class RoleConfig(_Strict):
    role_id: str = Field(..., pattern=r"^customer-support$")
    version: str = Field(..., min_length=1)
    competencies: list[str] = Field(..., min_length=1)
    questions: list[str] = Field(..., min_length=1)
    rubric: list[RubricCriterion] = Field(..., min_length=1)
    pass_threshold: int = Field(..., ge=0, le=100)
