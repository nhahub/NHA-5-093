"""Validate all canonical examples, API structure, tools and the fixture chain."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.contracts import ROOT, ContractError, Contracts

TOOL_NAMES = ["load_policy", "send_turn", "check_evidence"]


def require(condition, message):
    if not condition:
        raise ContractError(message)


def rejected(contracts, name, value):
    try:
        contracts.validate(name, value)
    except ContractError:
        return
    raise ContractError(f"Negative case unexpectedly accepted: {name}")


def validate_repository(root=ROOT):
    contracts = Contracts(root)
    for schema in contracts.schemas.values():
        contracts.check_references(schema, schema["$id"])
    count = 0
    for path in sorted((contracts.base / "examples").glob("*.json")):
        name = path.stem
        schema_name = name.split("_", 1)[0]
        require(schema_name in contracts.schemas, f"Orphan example: {name}")
        contracts.validate(schema_name, contracts.fixture(name))
        count += 1
    for name in contracts.schemas:
        require((contracts.base / "examples" / f"{name}.json").is_file(), f"Missing {name}")
    api_path = contracts.base / "openapi.yaml"
    api = yaml.safe_load(api_path.read_text(encoding="utf-8"))
    contracts.check_references(api, api_path.as_uri())
    validate(api, base_uri=api_path.as_uri())
    require(api["openapi"] == "3.1.0", "Unexpected OpenAPI version")
    operations = [op for methods in api["paths"].values() for op in methods.values()]
    ids = [op["operationId"] for op in operations]
    require(len(ids) == len(set(ids)), "Duplicate operationId")
    for path in ("/api/v1/runs", "/api/v1/batches", "/api/v1/retests"):
        require("202" in api["paths"][path]["post"]["responses"], "Queue must return 202")
    tools = json.loads((contracts.base / "agent_tools.json").read_text(encoding="utf-8"))
    require([tool["name"] for tool in tools["tools"]] == TOOL_NAMES, "Tool allowlist drift")
    contracts.check_references(tools, (contracts.base / "agent_tools.json").as_uri())
    for tool in tools["tools"]:
        for key in ("arguments_schema", "output_schema"):
            Draft202012Validator.check_schema(tool[key])
        require(tool["arguments_schema"]["additionalProperties"] is False, "Open tool input")
        sample = {"rule_ids": ["POL-SEC-01-CANARY"]}
        if tool["name"] == "send_turn":
            sample = {"message": "اختبار اصطناعي", "strategy_id": "direct_request"}
        contracts.validate_schema(tool["arguments_schema"], sample)
        try:
            contracts.validate_schema(tool["arguments_schema"], {**sample, "run_id": "injected"})
        except ContractError:
            pass
        else:
            raise ContractError("Tool accepted controller-owned fields")
        output = {
            "load_policy": [contracts.fixture("PolicyRulePublic")],
            "send_turn": contracts.fixture("AdapterTurnResponse"),
            "check_evidence": [contracts.fixture("CheckResult")],
        }[tool["name"]]
        contracts.validate_schema(tool["output_schema"], output)
    modes = json.loads((contracts.base / "mock_target_modes.json").read_text(encoding="utf-8"))
    for mode in ("refusal", "canary_disclosure", "scoring"):
        contracts.validate("AdapterTurnResponse", modes[mode])
    contracts.validate("ErrorResponse", modes["timeout"])
    rejected(contracts, "AdapterTurnResponse", modes["malformed"])
    stop = contracts.fixture("NextProbe_STOP")
    rejected(contracts, "NextProbe", {**stop, "message": "illegal"})
    rejected(
        contracts,
        "RunCreate",
        {**contracts.fixture("RunCreate"), "target_version": "https://invalid"},
    )
    for name, schema in contracts.schemas.items():
        if schema.get("additionalProperties") is False:
            rejected(contracts, name, {**contracts.fixture(name), "unexpected_field": True})
    event = contracts.fixture("AuditEvent")
    rejected(contracts, "AuditEvent", {**event, "occurred_at": "yesterday"})
    invalid = copy.deepcopy(event)
    invalid["data"] = {"code": "INVALID", "message": "wrong payload type"}
    rejected(contracts, "AuditEvent", invalid)
    validate_golden(contracts)
    print(
        f"PASS: {len(contracts.schemas)} schemas, {count} examples, {len(api['paths'])} API paths"
    )
    print("PASS: local references, OpenAPI, tool inputs/outputs, negative cases and fixture chain")
    print("NOTE: fixture validation does not establish runtime integration or human approval")


def validate_golden(contracts):
    f = contracts.fixture
    turn, event, check, finding = (
        f(n) for n in ("AdapterTurnResponse", "AuditEvent", "CheckResult", "Finding")
    )
    run, detail, scenario, rule, review = (
        f(n) for n in ("RunCreate", "RunDetail", "Scenario", "PolicyRule", "ReviewReceipt")
    )
    require(
        run["scenario_id"] == scenario["scenario_id"] == finding["scenario_id"], "Scenario links"
    )
    require(
        finding["run_id"] == check["run_id"] == event["run_id"] == detail["run_id"], "Run links"
    )
    require(turn["reply_text"] == event["data"]["target_response"], "Reply link")
    require(event["event_type"] == "TURN", "Golden target event")
    require(
        check["turn_index"] == finding["proposal"]["turn_index"] == event["turn_index"],
        "Turn links",
    )
    require(rule["forbidden_value"] in turn["reply_text"], "Synthetic canary chain")
    require(rule["rule_id"] == check["rule_id"] == finding["rule_id"], "Rule links")
    for evidence in (check, finding["proposal"]):
        require(event["event_id"] in evidence["evidence_event_ids"], "Evidence links")
    require(check["result"] == finding["proposal"]["verdict"] == "FAIL", "Machine proposal")
    require(finding["reviewer_status"] == "PENDING", "Machine cannot confirm")
    require(
        review["finding_id"] == finding["finding_id"] and review["decision"] == "CONFIRMED",
        "Separate review fixture",
    )


if __name__ == "__main__":
    try:
        validate_repository()
    except (ContractError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
