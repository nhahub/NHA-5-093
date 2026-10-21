from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from .models import PolicyRule


@dataclass
class SemanticVerdict:
    verdict: Literal["PASS", "FAIL", "INCONCLUSIVE"]
    quote: str | None  # exact substring of the target reply supporting FAIL
    reason: str


SemanticJudge = Callable[[PolicyRule, str], SemanticVerdict]


def run_semantic(judge: SemanticJudge | None, rule: PolicyRule, target_text: str):
    """Returns (verdict, span|None, reason). Never trusts an uncited or fabricated quote."""
    if judge is None:
        return "INCONCLUSIVE", None, "no semantic judge configured"
    try:
        v = judge(rule, target_text)
    except Exception as exc:  # judge failure is not a policy finding
        return "INCONCLUSIVE", None, f"semantic judge error: {type(exc).__name__}"
    if v.verdict == "FAIL":
        quote = v.quote
        if quote and quote in target_text:
            s = target_text.index(quote)
            return "FAIL", (s, s + len(quote)), v.reason
        if quote:
            q_strip = quote.strip()
            if q_strip and q_strip in target_text:
                s = target_text.index(q_strip)
                return "FAIL", (s, s + len(q_strip)), v.reason
            if (
                len(q_strip) >= 2
                and q_strip[0] in ('"', "'", "«", "“")
                and q_strip[-1] in ('"', "'", "»", "”")
            ):
                inner = q_strip[1:-1].strip()
                if inner and inner in target_text:
                    s = target_text.index(inner)
                    return "FAIL", (s, s + len(inner)), v.reason
        return (
            "INCONCLUSIVE",
            None,
            "semantic FAIL without a verifiable quote from the target reply",
        )
    if v.verdict == "PASS":
        return "PASS", None, v.reason
    return "INCONCLUSIVE", None, v.reason
