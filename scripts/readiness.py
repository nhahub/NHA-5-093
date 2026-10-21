"""Report pending integration prerequisites without treating them as passed tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def missing_handoffs(root=ROOT):
    result = []
    handoffs = json.loads((root / "infra/handoffs.json").read_text(encoding="utf-8"))
    for role, item in handoffs.items():
        if not (root / item["path"]).is_dir():
            result.append(f"{role}: {item['path']} absent")
        if not item["test"]:
            result.append(f"{role}: test command unregistered")
        if role in {"M3", "M6"} and not item["start"]:
            result.append(f"{role}: startup command unregistered")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-only", action="store_true", help="Inventory only; never release evidence"
    )
    args = parser.parse_args()
    missing = missing_handoffs()
    for item in missing:
        print(f"PENDING: {item}")
    print("PENDING: human approvals and release evidence must be checked separately")
    return 0 if args.report_only or not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
