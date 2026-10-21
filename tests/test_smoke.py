import httpx
import pytest

from scripts.contracts import ContractError, Contracts
from scripts.integration_smoke import Smoke


def test_smoke_validates_real_transport_shape():
    def handler(request):
        return httpx.Response(200, json={"status": "ok"})

    with httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://localhost"
    ) as client:
        assert Smoke(client).request("GET", "/health", "/health") == {"status": "ok"}


def test_smoke_rejects_malformed_response():
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"status": "invented"})),
        base_url="http://localhost",
    ) as client:
        with pytest.raises(ContractError):
            Smoke(client).request("GET", "/health", "/health")


def test_smoke_never_follows_redirect_to_external_target():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(302, headers={"location": "https://example.invalid"})
        ),
        base_url="http://localhost",
        follow_redirects=False,
    ) as client:
        with pytest.raises(ContractError, match="expected 200, got 302"):
            Smoke(client).request("GET", "/health", "/health")


def test_smoke_rejects_repeating_pagination_cursor():
    fixture = Contracts().fixture("AuditEvent")
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"items": [fixture], "next_cursor": "2"})
        ),
        base_url="http://localhost",
    ) as client:
        with pytest.raises(ContractError, match="cursor repeated"):
            Smoke(client).collection("run_012345abcdef", "events")
