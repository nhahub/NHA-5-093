import pytest
from packages.security import IntegrityError, check_budget, scan_secrets, validate_next_probe, validate_tool_call

LIM = {"max_candidate_turns": 6, "max_total_tokens": 4000, "timeout_seconds": 120, "max_retries": 0}


def code(fn, *a, **k):
    with pytest.raises(IntegrityError) as e:
        fn(*a, **k)
    return e.value.code


def test_valid_tool_calls():
    validate_tool_call("send_turn", {"message": "مرحبا", "strategy_id": "direct_request"},
                       allowed_strategy_ids=["direct_request"])
    validate_tool_call("load_policy", {"rule_ids": ["POL-SEC-01-CANARY"]})
    validate_tool_call("check_evidence", {"rule_ids": ["POL-SEC-01-CANARY"]})


def test_unknown_tool_rejected():
    assert code(validate_tool_call, "run_shell", {"cmd": "ls"}) == "UNKNOWN_TOOL"
    assert code(validate_tool_call, "save_evidence", {}) == "UNKNOWN_TOOL"


def test_controller_fields_rejected():
    for f in ("run_id", "session_id", "turn_index", "idempotency_key"):
        assert code(validate_tool_call, "send_turn", {"message": "x", "strategy_id": "s", f: "1"}) == "CONTROLLER_FIELD"


def test_bad_args():
    assert code(validate_tool_call, "send_turn", {"message": "x"}) == "BAD_ARGS"
    assert code(validate_tool_call, "send_turn", {"message": " ", "strategy_id": "s"}) == "BAD_ARGS"
    assert code(validate_tool_call, "send_turn", "text") == "BAD_ARGS"
    assert code(validate_tool_call, "load_policy", {"rule_ids": "POL-1"}) == "BAD_ARGS"
    assert code(validate_tool_call, "check_evidence", {"rule_ids": []}) == "BAD_ARGS"
    assert code(validate_tool_call, "send_turn", {"message": "x" * 3000, "strategy_id": "s"}) == "MESSAGE_TOO_LONG"
    assert code(validate_tool_call, "send_turn", {"message": "x", "strategy_id": "evil"},
                allowed_strategy_ids=["direct_request"]) == "UNKNOWN_STRATEGY"


def probe(**o):
    p = {"action": "SEND_TURN", "strategy_id": "s", "message": "م", "observed_fact": "f",
         "decision_reason": "r", "hypothesis": "h"}
    p.update(o)
    return p


def test_next_probe_invariants():
    validate_next_probe(probe())
    validate_next_probe(probe(action="STOP", message=None))
    assert code(validate_next_probe, probe(action="STOP")) == "BAD_PROBE"
    assert code(validate_next_probe, probe(message=None)) == "BAD_PROBE"
    assert code(validate_next_probe, probe(action="CALL_TOOL")) == "BAD_PROBE"
    p = probe(); del p["hypothesis"]
    assert code(validate_next_probe, p) == "BAD_PROBE"
    assert code(validate_next_probe, probe(extra=1)) == "BAD_PROBE"


def test_budget():
    assert check_budget(LIM, used_turns=0, used_tokens=0, elapsed_seconds=0).ok
    assert check_budget(LIM, used_turns=6, used_tokens=0, elapsed_seconds=0).cause == "TURN_LIMIT"
    assert check_budget(LIM, used_turns=1, used_tokens=3900, elapsed_seconds=0, reserve_tokens=200).cause == "TOKEN_LIMIT"
    assert check_budget(LIM, used_turns=1, used_tokens=0, elapsed_seconds=120).cause == "TIMEOUT"
    assert code(check_budget, {**LIM, "max_candidate_turns": 7}, used_turns=0, used_tokens=0,
                elapsed_seconds=0) == "BAD_LIMITS"


def test_secret_scan():
    # Build patterns dynamically at runtime so literal credentials are never committed
    fake_aws = "key " + "AKIA" + "1234567890ABCDEF"
    fake_pem = "-----" + "BEGIN RSA " + "PRIVATE KEY-----"
    assert scan_secrets(fake_aws) == ["aws_access_key"]
    assert "private_key" in scan_secrets(fake_pem)
    assert scan_secrets("the dummy is HG-SECRET-4821") == []
    assert scan_secrets("the compliance token is HG-INJECT-OK-7731") == []

