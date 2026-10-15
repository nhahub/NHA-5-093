import json

from scripts import check_modules


def test_foundation_lists_absent_modules_but_strict_gate_fails(tmp_path, monkeypatch, capsys):
    (tmp_path / "infra").mkdir()
    (tmp_path / "infra/handoffs.json").write_text(
        json.dumps({"M2": {"path": "services/engine", "test": None}}), encoding="utf-8"
    )
    monkeypatch.setattr(check_modules, "ROOT", tmp_path)
    assert check_modules.check_modules(available=True) == 0
    assert "PENDING" in capsys.readouterr().out
    assert check_modules.check_modules() == 2


def test_present_module_cannot_skip_registration(tmp_path, monkeypatch):
    (tmp_path / "infra").mkdir()
    (tmp_path / "services/engine").mkdir(parents=True)
    (tmp_path / "infra/handoffs.json").write_text(
        json.dumps({"M2": {"path": "services/engine", "test": None}}), encoding="utf-8"
    )
    monkeypatch.setattr(check_modules, "ROOT", tmp_path)

    def pending(*args):
        raise RuntimeError("PENDING")

    monkeypatch.setattr(check_modules, "handoff", pending)
    assert check_modules.check_modules(available=True) == 1
