import sqlite3

import pytest

from scripts.backup import snapshot


def test_wal_snapshot_preserves_committed_data_and_refuses_overwrite(tmp_path):
    source, destination = tmp_path / "source.db", tmp_path / "copy.db"
    with sqlite3.connect(source) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE test_evidence (seq INTEGER PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO test_evidence VALUES (1, 'synthetic')")
        db.commit()
        snapshot(source, destination)
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT * FROM test_evidence").fetchall() == [(1, "synthetic")]
    with pytest.raises(ValueError, match="new file"):
        snapshot(source, destination)


def test_corrupt_database_is_not_reported_as_successful(tmp_path):
    source = tmp_path / "broken.db"
    source.write_text("This is not a database", encoding="utf-8")
    with pytest.raises(sqlite3.DatabaseError):
        snapshot(source, tmp_path / "snapshot.db")
