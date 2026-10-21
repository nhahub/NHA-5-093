import copy
import json
import shutil

import pytest

from scripts.contracts import ROOT, ContractError, Contracts, local_url
from scripts.validate_contracts import validate_repository


def test_all_contracts_and_fixtures():
    validate_repository()


@pytest.fixture
def kit(tmp_path):
    shutil.copytree(ROOT / "contracts", tmp_path / "contracts")
    return tmp_path


def test_dangling_reference_in_an_unused_schema_is_rejected(kit):
    path = kit / "contracts/schemas/ConfigResponse.schema.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["properties"]["role_ids"]["items"] = {"$ref": "Missing.schema.json"}
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ContractError, match="Unregistered reference"):
        validate_repository(kit)


def test_external_reference_is_rejected_without_network():
    contracts = Contracts()
    with pytest.raises(ContractError, match="Unregistered reference"):
        contracts.check_references(
            {"$ref": "https://example.invalid/a.json"}, "file:///tmp/root.json"
        )


def test_broken_pointer_is_rejected():
    contracts = Contracts()
    with pytest.raises(ContractError, match="Unresolved JSON Pointer"):
        contracts.check_references(
            {"$ref": "RunCreate.schema.json#/missing"}, contracts.schemas["RunCreate"]["$id"]
        )


def test_every_extra_example_is_checked(kit):
    path = kit / "contracts/examples/NextProbe_EXTRA.json"
    path.write_text('{"action":"STOP"}', encoding="utf-8")
    with pytest.raises(ContractError):
        validate_repository(kit)


def test_validation_does_not_echo_payload():
    contracts = Contracts()
    value = contracts.fixture("RunCreate")
    value["target_version"] = "sensitive-synthetic-test-value"
    with pytest.raises(ContractError) as error:
        contracts.validate("RunCreate", value)
    assert value["target_version"] not in str(error.value)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://localhost.evil",
        "http://user:pass@localhost",
        "http://127.0.0.1/path",
        "file:///tmp/file",
        "http://localhost?target=external",
    ],
)
def test_smoke_rejects_nonlocal_origins(url):
    with pytest.raises(ContractError):
        local_url(url)


def test_events_are_typed_and_usage_is_not_silently_repaired():
    contracts = Contracts()
    event = copy.deepcopy(contracts.fixture("AuditEvent"))
    event["actor"] = "AGENT"
    with pytest.raises(ContractError):
        contracts.validate("AuditEvent", event)
