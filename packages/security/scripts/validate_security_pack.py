"""Run: python packages/security/scripts/validate_security_pack.py  (exit 1 on any problem)."""

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from packages.security.integrity import scan_secrets
from packages.security.models import Scenario
from packages.security.policy import load_rules

ROOT = Path(__file__).resolve().parents[3]

FIX = ROOT / "packages" / "security" / "fixtures"


def validate() -> list[str]:
    errs = []
    rules = load_rules()
    ids = [r.rule_id for r in rules]
    if len(ids) != len(set(ids)):
        errs.append("duplicate rule_id")
    canaries = [r.forbidden_value for r in rules if r.checker_type == "EXACT_CANARY"]
    scen = json.loads((FIX / "scenarios_m4_templates.json").read_text(encoding="utf-8"))
    sids = [s["scenario_id"] for s in scen]
    if len(sids) != len(set(sids)):
        errs.append("duplicate scenario_id")
    for s in scen:
        sid = s["scenario_id"]
        try:
            Scenario.model_validate(s)
        except Exception as exc:
            errs.append(f"{sid}: schema violation - {exc}")
        if s["split"] != "DEVELOPMENT":
            errs.append(f"{sid}: M4 fixtures must be DEVELOPMENT only (held-out belongs to M5)")
        if not (1 <= len(s["fixed_prompts"]) <= 6):
            errs.append(f"{sid}: fixed_prompts must be 1..6")
        for rid in s["rule_ids"]:
            if rid not in ids:
                errs.append(f"{sid}: unknown rule {rid}")
        for p in s["fixed_prompts"]:
            if any(c and c in p for c in canaries):
                errs.append(f"{sid}: attacker prompt contains the canary")
            if scan_secrets(p):
                errs.append(f"{sid}: secret-like string in prompt")
    for f in (ROOT / "packages" / "security").rglob("*"):
        if (
            f.suffix in {".py", ".json", ".md"}
            and f.is_file()
            and scan_secrets(f.read_text(encoding="utf-8"))
        ):
            errs.append(f"{f.relative_to(ROOT)}: secret-like string")
    return errs


if __name__ == "__main__":
    e = validate()
    print("\n".join(e) or "security pack OK")
    sys.exit(1 if e else 0)
