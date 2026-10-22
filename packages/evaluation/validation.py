"""M5 data checks: contracts, split isolation, and reviewer/freeze gates."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_COUNTS = {"development": 30, "heldout": 20}
SPLIT_ENUM = {"development": "DEVELOPMENT", "heldout": "HELD_OUT", "demo": "DEMO"}
FORBIDDEN_AGENT_FIELDS = {"split", "expected_behavior", "fixed_prompts", "approved", "seed"}
AGENT_VIEW_FIELDS = (
    "scenario_id",
    "suite_version",
    "family",
    "role_id",
    "objective",
    "persona_ref",
    "rule_ids",
)
HELDOUT_LABEL_MARKERS = ("held_out", "held-out", "heldout", "holdout")


class DataValidationError(ValueError):
    pass


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalized_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^\w\u0600-\u06ff]+", " ", value).strip()


def validate_data_tree(data_root: str | Path | None = None) -> dict[str, Any]:
    from scripts.contracts import Contracts

    root = Path(data_root) if data_root else PROJECT_ROOT / "data"
    contracts = Contracts(PROJECT_ROOT)
    errors: list[str] = []
    split_reports: dict[str, Any] = {}
    all_ids: set[str] = set()
    group_owners: dict[str, str] = {}
    prompt_owners: dict[str, str] = {}

    for split_name, split_value in SPLIT_ENUM.items():
        split_root = root / split_name
        manifest = _read(split_root / "manifest.json")
        scenarios = _read(split_root / manifest["scenario_file"])
        personas = _read(split_root / manifest["persona_file"])
        records = manifest["records"]
        record_map = {row["scenario_id"]: row for row in records}
        persona_map = {row["persona_ref"]: row for row in personas}

        expected = EXPECTED_COUNTS.get(split_name)
        if expected is not None and len(scenarios) != expected:
            errors.append(f"{split_name}: expected {expected} scenarios, found {len(scenarios)}")
        ids = [row["scenario_id"] for row in scenarios]
        if len(ids) != len(set(ids)) or set(ids) != set(record_map):
            errors.append(f"{split_name}: scenario IDs are duplicate or differ from manifest")
        if int(manifest["scenario_count"]) != len(scenarios):
            errors.append(f"{split_name}: scenario_count differs from file")
        if set(ids) & all_ids:
            errors.append(f"{split_name}: scenario IDs overlap another split")
        all_ids.update(ids)

        if split_name == "heldout" and not manifest["scenario_file"].startswith("private/"):
            errors.append("heldout: full scenarios must remain under private/")
        if split_name == "heldout" and manifest.get("agent_direct_access") is not False:
            errors.append("heldout: agent_direct_access must be false")

        for persona in personas:
            try:
                contracts.validate("Persona", persona)
            except Exception as exc:
                errors.append(f"{split_name}:{persona.get('persona_ref')}: Persona invalid: {exc}")
            if persona.get("is_synthetic") is not True:
                errors.append(
                    f"{split_name}:{persona.get('persona_ref')}: persona is not synthetic"
                )

        for scenario in scenarios:
            sid = scenario.get("scenario_id", "<missing>")
            try:
                contracts.validate("Scenario", scenario)
            except Exception as exc:
                errors.append(f"{split_name}:{sid}: Scenario invalid: {exc}")
                continue
            if scenario["split"] != split_value:
                errors.append(f"{split_name}:{sid}: wrong split enum")
            if scenario["persona_ref"] not in persona_map:
                errors.append(f"{split_name}:{sid}: unknown persona_ref")
            view = {field: scenario[field] for field in AGENT_VIEW_FIELDS}
            try:
                contracts.validate("AgentScenarioView", view)
            except Exception as exc:
                errors.append(f"{split_name}:{sid}: AgentScenarioView invalid: {exc}")
            if split_name == "heldout":
                public_text = json.dumps(view, ensure_ascii=False).casefold()
                if any(marker in public_text for marker in HELDOUT_LABEL_MARKERS):
                    errors.append(f"{split_name}:{sid}: public agent view reveals split label")
            if manifest["approval_status"] != "APPROVED" and scenario["approved"]:
                errors.append(f"{split_name}:{sid}: unapproved manifest contains approved scenario")
            record = record_map.get(sid, {})
            group = record.get("paraphrase_group_id")
            if not group:
                errors.append(f"{split_name}:{sid}: missing paraphrase_group_id")
            elif group in group_owners and group_owners[group] != split_name:
                errors.append(f"paraphrase group {group!r} leaks across splits")
            else:
                group_owners[group] = split_name
            reviewers = list(record.get("reviewer_ids", []))
            if (
                record.get("dialect_pair_id")
                and record.get("review_status") == "APPROVED"
                and len(set(reviewers)) < 2
            ):
                errors.append(f"{split_name}:{sid}: approved equivalence needs two reviewers")
            for prompt in scenario["fixed_prompts"]:
                normalized = _normalized_text(prompt)
                owner = prompt_owners.get(normalized)
                if owner and owner != split_name:
                    errors.append(
                        f"exact normalized prompt leaks across {owner}/{split_name}: {sid}"
                    )
                prompt_owners[normalized] = split_name

        pairs_path = split_root / manifest["dialect_pairs_file"]
        pairs = _read(pairs_path)
        for pair in pairs:
            pair_ids = pair["scenario_ids"]
            if len(pair_ids) != 2 or not set(pair_ids) <= set(ids):
                errors.append(f"{split_name}:{pair.get('pair_id')}: invalid scenario pair")
                continue
            languages = {
                persona_map[scenario_map["persona_ref"]]["language"]
                for scenario_map in scenarios
                if scenario_map["scenario_id"] in pair_ids
            }
            if languages != {"MSA", "EGY"}:
                errors.append(f"{split_name}:{pair.get('pair_id')}: pair must contain MSA and EGY")
            if (
                pair.get("review_status") == "APPROVED"
                and len(set(pair.get("reviewer_ids", []))) < 2
            ):
                errors.append(
                    f"{split_name}:{pair.get('pair_id')}: approved pair needs two reviewers"
                )

        if manifest.get("freeze_status") == "FROZEN_APPROVED":
            if manifest.get("approval_status") != "APPROVED":
                errors.append(f"{split_name}: frozen manifest lacks approval")
            unapproved_scenarios = sorted(
                scenario["scenario_id"] for scenario in scenarios if not scenario["approved"]
            )
            if unapproved_scenarios:
                errors.append(
                    f"{split_name}: frozen manifest contains unapproved scenarios: "
                    + ", ".join(unapproved_scenarios)
                )
            unapproved_pairs = sorted(
                pair["pair_id"]
                for pair in pairs
                if pair.get("review_status") != "APPROVED"
                or len(set(pair.get("reviewer_ids", []))) < 2
            )
            if unapproved_pairs:
                errors.append(
                    f"{split_name}: frozen manifest contains unapproved dialect pairs: "
                    + ", ".join(unapproved_pairs)
                )
            if manifest.get("content_sha256") != _sha(
                {
                    "scenarios": scenarios,
                    "personas": personas,
                    "dialect_pairs": pairs,
                    "records": records,
                }
            ):
                errors.append(f"{split_name}: frozen content hash mismatch")

        split_reports[split_name] = {
            "scenario_count": len(scenarios),
            "persona_count": len(personas),
            "dialect_pair_count": len(pairs),
            "approval_status": manifest["approval_status"],
            "freeze_status": manifest["freeze_status"],
        }

    if errors:
        raise DataValidationError("; ".join(errors))
    repeat_path = root / "heldout" / "private" / "repeatability_transcripts.json"
    transcripts = _read(repeat_path)
    transcript_ids = [row["transcript_id"] for row in transcripts]
    if len(transcripts) != 10 or len(set(transcript_ids)) != 10:
        raise DataValidationError("heldout repeatability set must contain ten unique transcripts")
    for row in transcripts:
        if row["transcript_sha256"] != _sha(row["messages"]):
            raise DataValidationError(
                f"repeatability transcript hash mismatch: {row['transcript_id']}"
            )
    return {
        "valid": True,
        "splits": split_reports,
        "total_scenarios": len(all_ids),
        "cross_split_paraphrase_overlap": 0,
        "cross_split_exact_prompt_overlap": 0,
        "repeatability_transcript_count": len(transcripts),
    }
