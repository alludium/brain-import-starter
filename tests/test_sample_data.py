"""Generated samples are reproducible, bounded and isolated from normal CI writes."""

import sys
import tomllib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts/sample_data"))
from generate import generate  # noqa: E402
from verify import config  # noqa: E402

from brain_import import plans  # noqa: E402
from brain_import.model import ImportProblem  # noqa: E402

TARGET = {"server": "http://127.0.0.1:1/mcp", "firm_id": "synthetic", "user_id": "synthetic"}


@pytest.fixture(scope="module")
def samples(tmp_path_factory):
    root = tmp_path_factory.mktemp("samples") / "vaults"
    return root, generate(root)


def test_sample_selection_and_originals(samples):
    root, manifest = samples
    assert len(manifest["entities"]) == 157
    for key, count in [("curated", 78), ("volume", 1000)]:
        spec = manifest["sets"][key]
        plan = plans.build_config(config(root, spec, TARGET), root)
        editable = tomllib.loads((root / f"{key}.toml").read_text())
        editable["target"] = TARGET
        assert plans.build_config(editable, root) == plan
        cases = {c["id"]: c for c in spec["cases"]}
        assert len(plan["records"]) == count
        for row in plan["records"]:
            cid = row["external_id"].split(":id:")[1]
            assert row["text"].encode() == (root / spec["vault"] / cases[cid]["path"]).read_bytes()
            assert row["scope"] == "private" and row["preserve_audience"]
        assert all("excluded" not in r["title"] and r["title"] != "link" for r in plan["records"])


def test_failure_selections_stop_before_brain(samples):
    root, manifest = samples
    for case in manifest["failures"]:
        with pytest.raises(ImportProblem, match=case["error"]):
            plans.build_config(config(root, case, TARGET), root)


def test_generator_refuses_existing_directory(samples):
    root, _ = samples
    sentinel = root / "keep.txt"
    sentinel.write_text("user work")
    with pytest.raises(FileExistsError):
        generate(root)
    assert sentinel.read_text() == "user work"
