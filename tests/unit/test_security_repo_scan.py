from pathlib import Path

from packages.security import scan_secrets

ROOT = Path(__file__).resolve().parents[2]
SKIP = {"test_security_integrity.py"}
EXTS = {".py", ".json", ".md"}


def _files():
    for p in (ROOT / "packages" / "security").rglob("*"):
        if p.is_file() and p.suffix in EXTS and ("__pycache__" not in p.parts):
            yield p
    doc = ROOT / "docs" / "M4_threat_model.md"
    if doc.exists():
        yield doc
    for p in (ROOT / "tests" / "unit").glob("test_security_*.py"):
        if p.name not in SKIP:
            yield p


def test_no_credentials_in_m4_files():
    hits = {}
    for p in _files():
        found = scan_secrets(p.read_text(encoding="utf-8", errors="replace"))
        if found:
            hits[str(p.relative_to(ROOT))] = found
    assert hits == {}
