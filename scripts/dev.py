"""Cross-platform developer entrypoint. Unavailable handoffs fail explicitly."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command, *, cwd=ROOT):
    executable = shutil.which(command[0])
    if not executable:
        raise RuntimeError(f"Required executable is unavailable: {command[0]}")
    return subprocess.call([executable, *command[1:]], cwd=cwd)


def handoff(role, action):
    config = json.loads((ROOT / "infra/handoffs.json").read_text(encoding="utf-8"))[role]
    command = config.get(action)
    if not (ROOT / config["path"]).is_dir() or not command:
        raise RuntimeError(f"PENDING: {role} must deliver {config['path']} and register {action}")
    if not isinstance(command, list) or not all(isinstance(arg, str) for arg in command):
        raise RuntimeError("Handoff commands must be argument arrays, never shell strings")
    return run(command)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "task",
        choices=[
            "setup",
            "contracts",
            "lint",
            "test",
            "backend",
            "frontend",
            "readiness",
            "integration",
            "containers",
            "modules",
        ],
    )
    args = parser.parse_args(argv)
    python = sys.executable
    if args.task == "setup":
        code = run(["uv", "sync", "--locked", "--all-packages"])
        return code or run(["npm.cmd" if os.name == "nt" else "npm", "ci", "--ignore-scripts"])
    tasks = {
        "contracts": [python, "scripts/validate_contracts.py"],
        "lint": [python, "-m", "ruff", "check", "."],
        "test": [python, "-m", "pytest", "tests", "-q"],
        "readiness": [python, "scripts/readiness.py"],
        "integration": [python, "scripts/integration_smoke.py", "--workflow"],
        "containers": ["docker", "compose", "-f", "infra/compose.yaml", "up", "--build", "--wait"],
    }
    if args.task in tasks:
        return run(tasks[args.task])
    if args.task == "modules":
        return run([python, "scripts/check_modules.py"])
    return handoff("M3" if args.task == "backend" else "M6", "start")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
