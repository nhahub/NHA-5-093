import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_no_corrupted_characters_in_m4_files():
    """Scans all M4 source, test, doc, and fixture files to guarantee zero ?? or U+FFFD corruption."""
    m4_paths = [
        ROOT / "packages" / "security",
        ROOT / "docs" / "M4_threat_model.md",
    ]

    for p in ROOT.glob("tests/unit/test_security_*.py"):
        m4_paths.append(p)

    target_files = []
    for item in m4_paths:
        if item.is_file():
            if item.name != "test_security_encoding.py":
                target_files.append(item)
        elif item.is_dir():
            for p in item.rglob("*"):
                if p.is_file() and p.suffix in (".py", ".json", ".md", ".yaml", ".yml"):
                    if p.name != "test_security_encoding.py":
                        target_files.append(p)

    violations = []
    for fpath in target_files:
        content = fpath.read_text(encoding="utf-8")
        for lineno, line in enumerate(content.splitlines(), 1):
            if "??" in line or "\ufffd" in line:
                violations.append(f"{fpath.relative_to(ROOT)}:{lineno}: {line.strip()[:80]}")

    msg = "Found corrupted character sequences (?? or U+FFFD): " + "; ".join(violations)
    assert not violations, msg


def test_no_literal_unicode_escapes_in_m4_markdown():
    """Fails if any M4 .md file matches \\u0[0-9a-fA-F]{3}. Skips itself when scanning."""
    m4_md_files = [
        ROOT / "docs" / "M4_threat_model.md",
        ROOT / "packages" / "security" / "README.md",
    ]
    for p in (ROOT / "packages" / "security").rglob("*.md"):
        if p not in m4_md_files:
            m4_md_files.append(p)

    # Regex targeting literal unicode escapes like \u0639
    pattern = re.compile(r"\\u0[0-9a-fA-F]{3}")
    violations = []
    for fpath in m4_md_files:
        if fpath.name == "test_security_encoding.py":
            continue
        if not fpath.exists():
            continue
        content = fpath.read_text(encoding="utf-8")
        for lineno, line in enumerate(content.splitlines(), 1):
            if pattern.search(line):
                violations.append(f"{fpath.relative_to(ROOT)}:{lineno}: {line.strip()[:80]}")

    assert not violations, "Found literal \\u0xxx unicode escapes in markdown files: " + "; ".join(violations)


def test_arabic_characters_present_in_security_checks():
    """Asserts that at least one Arabic character (U+0600-U+06FF) exists in test_security_checks.py."""
    checks_file = ROOT / "tests" / "unit" / "test_security_checks.py"
    assert checks_file.exists(), f"Missing file: {checks_file}"
    content = checks_file.read_text(encoding="utf-8")

    arabic_matches = re.findall(r"[؀-ۿ]", content)
    assert len(arabic_matches) > 0, "No Arabic characters (U+0600-U+06FF) found in test_security_checks.py!"
