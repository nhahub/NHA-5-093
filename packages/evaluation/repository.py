"""Split-aware M5 scenario repository.

Full Scenario records are controller-only data.  Adaptive model callers receive
only the canonical AgentScenarioView allowlist produced by ``to_agent_view``.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .analysis_validation import contracts
from .validation import split_file, validate_data_tree

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = PROJECT_ROOT / "data"

AGENT_VIEW_FIELDS = (
    "scenario_id",
    "suite_version",
    "family",
    "role_id",
    "objective",
    "persona_ref",
    "rule_ids",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_contract(name: str, value: dict[str, Any]) -> None:
    contracts().validate(name, value)


def to_agent_view(scenario: dict[str, Any]) -> dict[str, Any]:
    """Return exactly the public Scenario fields allowed by the contract."""
    _validate_contract("Scenario", scenario)
    view = {field: copy.deepcopy(scenario[field]) for field in AGENT_VIEW_FIELDS}
    _validate_contract("AgentScenarioView", view)
    return view


class ScenarioRepository:
    """Read approved scenarios while keeping split metadata and labels private."""

    def __init__(self, data_root: str | Path = DEFAULT_DATA_ROOT):
        self.data_root = Path(data_root)
        self._scenarios: dict[tuple[str, str], dict[str, Any]] = {}
        self._personas: dict[str, dict[str, Any]] = {}
        self._manifests: dict[str, dict[str, Any]] = {}
        validate_data_tree(self.data_root)
        self._load()

    def _load(self) -> None:
        for split in ("development", "heldout", "demo"):
            split_root = self.data_root / split
            manifest_path = split_root / "manifest.json"
            if not manifest_path.exists():
                continue
            manifest = _read_json(manifest_path)
            self._manifests[manifest["split"]] = manifest
            scenario_path = split_file(split_root, manifest["scenario_file"])
            persona_path = split_file(split_root, manifest["persona_file"])
            for scenario in _read_json(scenario_path):
                _validate_contract("Scenario", scenario)
                key = (scenario["scenario_id"], scenario["suite_version"])
                if key in self._scenarios:
                    raise ValueError(f"duplicate scenario key: {key}")
                self._scenarios[key] = scenario
            for persona in _read_json(persona_path):
                _validate_contract("Persona", persona)
                ref = persona["persona_ref"]
                if ref in self._personas:
                    raise ValueError(f"duplicate persona_ref: {ref}")
                self._personas[ref] = persona

    def get_approved(self, scenario_id: str, suite_version: str) -> dict[str, Any]:
        scenario = self._scenarios.get((scenario_id, suite_version))
        if scenario is None:
            raise KeyError(f"unknown scenario/version: {scenario_id}/{suite_version}")
        if not scenario["approved"]:
            raise PermissionError(f"scenario is not approved for execution: {scenario_id}")
        manifest = self._manifests[scenario["split"]]
        if manifest["approval_status"] != "APPROVED" or (
            scenario["split"] == "HELD_OUT" and manifest["freeze_status"] != "FROZEN_APPROVED"
        ):
            raise PermissionError("scenario split is not approved/frozen for execution")
        return copy.deepcopy(scenario)

    def to_agent_view(self, scenario: dict[str, Any]) -> dict[str, Any]:
        return to_agent_view(scenario)

    def get_persona(self, persona_ref: str) -> dict[str, Any]:
        persona = self._personas.get(persona_ref)
        if persona is None:
            raise KeyError(f"unknown persona: {persona_ref}")
        return copy.deepcopy(persona)
