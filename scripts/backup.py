"""Create a consistent SQLite snapshot or restore into a NEW database file."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def snapshot(source: Path, destination: Path):
    source = source.resolve(strict=True)
    destination = destination.resolve()
    if source == destination or destination.exists():
        raise ValueError("Destination must be a new file; existing evidence is never overwritten")
    if not destination.parent.is_dir():
        raise ValueError("Destination parent directory must already exist")
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as original:
        if original.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise ValueError("Source database failed integrity check")
        # Exclusive creation closes the time-of-check/time-of-use overwrite race.
        with destination.open("xb"):
            pass
        with sqlite3.connect(destination) as target:
            original.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise ValueError("Snapshot failed integrity check")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "restore"])
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    snapshot(args.source, args.destination)
    print("PASS: integrity-checked SQLite snapshot created; no existing file overwritten")


if __name__ == "__main__":
    main()
