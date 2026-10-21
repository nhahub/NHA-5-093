"""Run registered owner suites; distinguish absent handoffs from passing tests."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.dev import ROOT, handoff


def check_modules(*, available=False):
    config = json.loads((ROOT / "infra/handoffs.json").read_text(encoding="utf-8"))
    rows = []
    result = 0
    for role, item in config.items():
        if not (ROOT / item["path"]).is_dir():
            rows.append(f"| {role} | PENDING: module absent; no tests executed |")
            if not available:
                result = 2
            continue
        try:
            code = handoff(role, "test")
        except RuntimeError:
            rows.append(f"| {role} | FAILED: module exists without registered test command |")
            result = 1
            continue
        rows.append(f"| {role} | {'FAILED' if code else 'PASSED registered suite'} |")
        if code:
            result = 1
    summary = "\n".join(
        [
            "## Owner module coverage",
            "",
            "| Owner | Actual coverage |",
            "|---|---|",
            *rows,
            "",
            "Absent modules remain pending integration gates; this inventory is not runtime evidence.",
            "",
        ]
    )
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as stream:
            stream.write(summary)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--available",
        action="store_true",
        help="Foundation only: run present modules, list absent modules as pending",
    )
    args = parser.parse_args()
    return check_modules(available=args.available)


if __name__ == "__main__":
    raise SystemExit(main())
