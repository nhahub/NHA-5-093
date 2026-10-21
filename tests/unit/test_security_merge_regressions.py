import copy
import json
from pathlib import Path

import pytest

from packages.security import CheckRequest, PolicyRule, check_evidence, load_rules
from packages.security.scripts import validate_security_pack as pack
from scripts.contracts import Contracts


def test_dictionary_boundary_has_one_result_per_rule_and_codepoint_spans():
    contracts = Contracts()
    event = contracts.fixture("AuditEvent")
    text = "😀 عربي HG-SECRET-4821"
    event["data"]["target_response"] = text
    request = {
        "run_id": event["run_id"],
        "turn_index": event["turn_index"],
        "rule_ids": ["POL-SEC-01-CANARY", "unknown"],
    }
    results = check_evidence(request, [event], [r.model_dump() for r in load_rules()])
    assert [r.result for r in results] == ["FAIL", "INCONCLUSIVE"]
    start = text.index("HG-SECRET-4821")
    assert results[0].evidence_spans == [f"target_response[{start}:{start + 14}]"]
    assert results[0].evidence_event_ids == [event["event_id"]]
    for result in results:
        contracts.validate("CheckResult", result.model_dump(mode="json"))


def test_malformed_request_never_disappears_as_empty_checks():
    with pytest.raises(ValueError):
        check_evidence({"run_id": "r", "turn_index": 0, "rule_ids": []}, [], [])


@pytest.mark.parametrize("alias", ["REGEX", "CANARY_EXACT"])
def test_noncanonical_policy_aliases_rejected(alias):
    rule = load_rules()[0].model_dump()
    rule["checker_type"] = alias
    with pytest.raises(ValueError):
        PolicyRule.model_validate(rule)


def test_invalid_turn_payload_is_inconclusive():
    event = Contracts().fixture("AuditEvent")
    event["data"]["usage"] = {}
    request = CheckRequest(
        run_id=event["run_id"], turn_index=event["turn_index"], rule_ids=["POL-SEC-01-CANARY"]
    )
    assert check_evidence(request, [event], load_rules())[0].result == "INCONCLUSIVE"


def test_pack_rejects_canary_in_candidate_fixture(tmp_path, monkeypatch):
    source = Path("packages/security/fixtures/scenarios_m4_templates.json")
    scenarios = copy.deepcopy(json.loads(source.read_text(encoding="utf-8")))
    scenarios[0]["fixed_prompts"][0] = "HG-SECRET-4821"
    (tmp_path / source.name).write_text(json.dumps(scenarios), encoding="utf-8")
    monkeypatch.setattr(pack, "FIX", tmp_path)
    assert any("attacker prompt contains the canary" in error for error in pack.validate())


def test_callers_cannot_enable_unsigned_retest_verdict():
    from packages.security import evaluate_mitigation
    from packages.security.models import CheckResult

    before = CheckResult(
        check_id="c",
        run_id="r",
        rule_id="POL-SEC-01-CANARY",
        turn_index=1,
        result="FAIL",
        checker_version="v",
        reason="synthetic",
        evidence_event_ids=["evt_012345abcdef"],
    )
    with pytest.raises(ValueError, match="ADR-07"):
        evaluate_mitigation(
            [before], [], before.rule_id, reviewer_confirmed=True, allow_retest_inconclusive=True
        )
