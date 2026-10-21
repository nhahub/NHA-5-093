"""Transport-fixture tests of the M1 harness, explicitly not application E2E evidence."""

import copy

import httpx
import pytest

from scripts.contracts import ContractError, Contracts
from scripts.integration_smoke import Smoke


def transport_fixture(*, corrupt_span=False):
    contracts = Contracts()
    f = contracts.fixture
    state = {"reviewed": False, "reviews": 0, "retest_posts": 0}
    original = f("RunDetail")
    original["config"]["method"] = "FIXED"
    followup = copy.deepcopy(original)
    followup["run_id"] = f("RetestReceipt")["retest_run_id"]
    followup["config"]["target_version"] = "hardened-v1"
    followup["outcome"] = "NO_FINDING"
    first = f("AuditEvent_STATE")
    first.update(seq=1, event_id="evt_000000000001")
    check = f("AuditEvent_CHECK")
    check.update(seq=3, event_id="evt_000000000003")
    events = [first, f("AuditEvent"), check]

    def handler(request):
        path, method = request.url.path, request.method
        code = 200
        if path == "/api/v1/batches" and method == "POST":
            value, code = f("BatchReceipt"), 202
        elif path.endswith("/events"):
            value = {"items": events, "next_cursor": None}
        elif path.endswith("/findings"):
            finding = f("Finding")
            if state["reviewed"]:
                finding["reviewer_status"] = "CONFIRMED"
            if corrupt_span:
                finding["proposal"]["evidence_spans"] = ["target_response[1:2]"]
            value = {"items": [finding], "next_cursor": None}
        elif path.endswith("/reviews") and method == "POST":
            state["reviewed"] = True
            state["reviews"] += 1
            value, code = f("ReviewReceipt"), 201
        elif path == "/api/v1/retests" and method == "POST":
            state["retest_posts"] += 1
            if not state["reviewed"]:
                value, code = f("ErrorResponse"), 409
            else:
                value, code = f("RetestReceipt"), 202
        elif path.startswith("/api/v1/retests/"):
            value = f("RetestView")
            value.update(status="COMPLETED", result=f("RetestResult"))
        elif path.startswith("/api/v1/reports/"):
            fmt = request.url.params.get("format")
            if fmt:
                return httpx.Response(
                    200,
                    content="synthetic export",
                    headers={"content-type": "text/csv" if fmt == "csv" else "text/markdown"},
                )
            value = f("ReportSummary")
        elif path == f"/api/v1/runs/{original['run_id']}":
            value = original
        elif path == f"/api/v1/runs/{followup['run_id']}":
            value = followup
        else:
            raise AssertionError(f"Unexpected fixture route: {method} {path}")
        return httpx.Response(code, json=value)

    return httpx.MockTransport(handler), state


def test_full_harness_with_existing_contract_fixtures(monkeypatch):
    monkeypatch.setenv("HG_ALLOW_TEST_REVIEWS", "1")
    transport, state = transport_fixture()
    with httpx.Client(transport=transport, base_url="http://localhost") as client:
        result = Smoke(client).workflow()
    assert result["mode"] == "MOCK"
    assert state["reviews"] == 2  # Same idempotent review fixture submitted twice.
    assert state["retest_posts"] == 2  # Rejected before confirmation, accepted afterwards.


def test_full_harness_rejects_false_evidence_before_any_review(monkeypatch):
    monkeypatch.setenv("HG_ALLOW_TEST_REVIEWS", "1")
    transport, state = transport_fixture(corrupt_span=True)
    with httpx.Client(transport=transport, base_url="http://localhost") as client:
        with pytest.raises(ContractError, match="span"):
            Smoke(client).workflow()
    assert state["reviews"] == state["retest_posts"] == 0


def test_workflow_requires_isolated_fixture_opt_in_before_mutating(monkeypatch):
    monkeypatch.delenv("HG_ALLOW_TEST_REVIEWS", raising=False)
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: pytest.fail("No requests allowed")),
        base_url="http://localhost",
    ) as client:
        with pytest.raises(ContractError, match="explicitly isolated"):
            Smoke(client).workflow()
