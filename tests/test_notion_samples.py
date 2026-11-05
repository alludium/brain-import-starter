"""Research-shaped samples expose page-adapter gaps without treating them as acceptance."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]


@pytest.fixture(scope="module")
def notion_lab(tmp_path_factory):
    root = tmp_path_factory.mktemp("notion") / "lab"
    subprocess.run(
        [sys.executable, "-m", "scripts.notion_samples.generate", "--out", str(root)],
        cwd=REPO,
        check=True,
        capture_output=True,
    )
    return root, json.loads((root / "catalog.json").read_text())


def test_graph_and_research_shapes(notion_lab):
    _, data = notion_lab
    rows = {row["key"]: row for row in data["rows"]}
    assert len(rows) == len(data["rows"]) == 38
    assert rows["C015"]["properties"]["Deal Fit"] is None
    assert rows["C016"]["properties"]["Deal Fit"] == 0
    assert "Score Unknown" in rows["C015"]["content"]
    assert "Score 0;" in rows["C016"]["content"]
    assert rows["L007"]["relations"]["Company"] == []
    assert rows["L009"]["relations"]["Company"] == ["C001"]
    assert rows["L003"]["properties"]["Lead"] == rows["L004"]["properties"]["Lead"]
    assert rows["L003"]["properties"]["Email"] != rows["L004"]["properties"]["Email"]
    assert rows["C017"]["relations"]["Theses"] == ["T001", "T002"]
    for row in rows.values():
        assert "{{page:" not in row["content"]
        for relation, targets in row["relations"].items():
            assert all(t in rows for t in targets)
            assert all(
                rows[t]["database"] == ("companies" if relation == "Company" else "theses")
                for t in targets
            )
    thesis = rows["T001"]["content"]
    assert '<mention url="https://www.notion.so/' in thesis
    assert "Every question and its evidence" in thesis
    assert "What would change our mind" in thesis


def test_actual_importer_probe_exposes_current_gaps(notion_lab):
    root, _ = notion_lab
    result = subprocess.run(
        [sys.executable, "-m", "scripts.notion_samples.probe", str(root)],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    assert report["plans"] == {"companies": 19, "theses": 6, "leads": 11}
    assert report["original_text_and_private_scope_preserved"]
    assert set(report["refused_rows"]) == {"C011", "L012"}
    assert not report["property_only_change_visible"]
    assert not report["relation_change_visible"]
    assert "must be text" in report["mapped_company_relation"]
    assert report["page_rename_keeps_source_id"]


def test_sample_directory_is_never_overwritten(notion_lab):
    root, _ = notion_lab
    original = (root / "catalog.json").read_bytes()
    result = subprocess.run(
        [sys.executable, "-m", "scripts.notion_samples.generate", "--out", str(root)],
        cwd=REPO,
        capture_output=True,
    )
    assert result.returncode != 0
    assert (root / "catalog.json").read_bytes() == original
