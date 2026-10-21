import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile

from scripts.contracts import ROOT


def normalize(value):
    return " ".join(value.split())


def test_recovered_sources_match_recorded_hashes():
    manifest = json.loads(
        (ROOT / "docs/decisions/source-manifest.json").read_text(encoding="utf-8")
    )
    assert {entry["id"] for entry in manifest} == {"PRD-DOCX", "PRD-PDF", "MASTER-PDF"}
    for entry in manifest:
        path = (ROOT / entry["path"]).resolve()
        assert path.is_relative_to(ROOT / "docs/decisions/sources")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]


def test_all_traceability_rows_match_original_docx_requirements():
    path = ROOT / "docs/decisions/sources/HireGuard_PRD_and_Team_Plan_EN.docx"
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
    expected = {}
    for table_index, table in enumerate(document.findall(".//w:tbl", ns), 1):
        for row_index, row in enumerate(table.findall("w:tr", ns), 1):
            cells = [
                "".join(t.text or "" for t in cell.findall(".//w:t", ns))
                for cell in row.findall("w:tc", ns)
            ]
            if not cells or not re.fullmatch(r"(?:FR|NFR|AC)-\d{2}", cells[0]):
                continue
            identifier = cells[0]
            requirement = cells[2] if identifier.startswith(("FR-", "NFR-")) else cells[1]
            acceptance = cells[3] if identifier.startswith("FR-") else cells[2]
            expected[identifier] = (
                normalize(requirement),
                normalize(acceptance),
                f"table {table_index} row {row_index}",
            )
    with (ROOT / "docs/decisions/requirements-traceability.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    required = {
        f"{kind}-{i:02}"
        for kind, count in (("FR", 33), ("NFR", 12), ("AC", 9))
        for i in range(1, count + 1)
    }
    assert len(rows) == len(required)
    assert {row["requirement_id"] for row in rows} == required == set(expected)
    for row in rows:
        assert row["source"] == "PRD-DOCX"
        assert (
            normalize(row["requirement_text"]),
            normalize(row["acceptance_test_planned"]),
            row["source_location"],
        ) == expected[row["requirement_id"]]
        assert row["primary_owner_proposed"] in {f"M{i}" for i in range(1, 7)}
