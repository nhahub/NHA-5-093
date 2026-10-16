import json
from pathlib import Path
from .models import PolicyRule, PolicyRulePublic

DEFAULT_RULES = Path(__file__).parent / "fixtures" / "policy_rules.json"


def load_rules(path: Path | str = DEFAULT_RULES) -> list[PolicyRule]:
    return [PolicyRule(**r) for r in json.loads(Path(path).read_text(encoding="utf-8"))]


def to_public(rules: list[PolicyRule]) -> list[PolicyRulePublic]:
    """What the agent may see: no forbidden_value, no checker_type (ADR-11)."""
    return [PolicyRulePublic(rule_id=r.rule_id, version=r.version, description=r.description,
                             severity=r.severity, review_required=r.review_required) for r in rules]
