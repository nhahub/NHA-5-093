"""Print deterministic proposed security and repeatability ledgers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    from packages.evaluation.planning import build_repeatability_plan, build_security_run_plan

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    heldout = ROOT / "data" / "heldout"
    protocol = _read(heldout / "protocol.json")
    manifest = _read(heldout / "manifest.json")
    scenarios = _read(heldout / manifest["scenario_file"])
    transcripts = _read(heldout / "private" / "repeatability_transcripts.json")
    result = {
        "security": build_security_run_plan(protocol, scenarios),
        "repeatability": build_repeatability_plan(protocol["repeatability"], transcripts),
    }
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
