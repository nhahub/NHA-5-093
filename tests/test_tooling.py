import json
import tomllib

import pytest
import yaml

from scripts import dev
from scripts.contracts import ROOT
from scripts.dev import handoff
from scripts.readiness import missing_handoffs


def test_missing_modules_are_pending_not_successful(tmp_path, monkeypatch):
    (tmp_path / "infra").mkdir()
    (tmp_path / "infra/handoffs.json").write_text(
        json.dumps({"M3": {"path": "services/api", "test": None, "start": None}}), encoding="utf-8"
    )
    monkeypatch.setattr(dev, "ROOT", tmp_path)
    assert missing_handoffs(tmp_path)
    with pytest.raises(RuntimeError, match="PENDING"):
        handoff("M3", "start")


def test_container_ports_are_loopback_and_database_is_persistent():
    compose = yaml.safe_load((ROOT / "infra/compose.yaml").read_text(encoding="utf-8"))
    assert compose["services"]["api"]["volumes"] == ["evidence:/data"]
    for service in compose["services"].values():
        for port in service.get("ports", []):
            assert port.startswith("127.0.0.1:")
    assert compose["services"]["dashboard"]["depends_on"]["api"]["condition"] == "service_healthy"


def test_secret_allowlist_only_matches_exact_synthetic_canary():
    import re

    config = tomllib.loads((ROOT / ".gitleaks.toml").read_text(encoding="utf-8"))
    allow = config["allowlists"][0]
    assert allow["regexTarget"] == "secret"
    assert not allow.get("paths")
    pattern = allow["regexes"][0]
    assert re.fullmatch(pattern, "HG-SECRET-4821")
    assert not re.fullmatch(pattern, "prefix-HG-SECRET-4821-suffix")


def test_ownership_workflow_checks_out_only_trusted_base():
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/ownership.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["ownership"]["steps"]
    checkout = steps[0]
    assert (
        checkout["with"]["ref"]
        == "${{ github.event.pull_request.base.sha || github.event.repository.default_branch }}"
    )
    assert checkout["with"]["persist-credentials"] is False
    document = (ROOT / ".github/workflows/ownership.yml").read_text(encoding="utf-8")
    assert "pull_request_review:" not in document
    assert "issue_comment:" in document


def test_handoff_paths_remain_owned_by_their_teams():
    config = json.loads((ROOT / "infra/handoffs.json").read_text(encoding="utf-8"))
    assert config["M2"]["path"] == "services/engine"
    assert config["M3"]["path"] == "services/api"
    assert config["M4"]["path"] == "packages/security"
    assert config["M5"]["path"] == "packages/evaluation"
    assert config["M6"]["path"] == "apps/dashboard"
