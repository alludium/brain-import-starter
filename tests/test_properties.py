import copy
from pathlib import Path

import pytest

from brain_import import plans
from brain_import.adapters import notion, obsidian
from brain_import.model import ImportProblem
from brain_import.properties import evidence, frontmatter

ROOT = Path(__file__).parents[1]


def test_properties_are_typed_and_original_text_survives(tmp_path):
    text = (
        '---\r\ncompany: "[[Companies/Acme AI|Acme]]"\r\n'
        "website: https://WWW.acme.ai/products\r\n"
        'attendees: ["[[People/Maya Lindqvist]]"]\r\n---\r\n'
        "# Meeting\r\nKestrel is a competitor.\r\n"
    )
    (tmp_path / "note.md").write_bytes(text.encode())
    row = list(obsidian.records({"vault": str(tmp_path), "namespace": "test"}, tmp_path))[0]
    assert row.text == text
    assert row.matching["subjects"] == [
        {
            "type": "organization",
            "name": "Acme AI",
            "domain": "acme.ai",
            "location": "properties.company",
            "role": "subject",
        },
        {
            "type": "person",
            "name": "Maya Lindqvist",
            "location": "properties.attendees",
            "role": "participant",
        },
    ]
    assert row.matching["heading"] == "Meeting"


def test_custom_fields_and_person_affiliation():
    out = evidence(
        {"Company": "Acme AI", "URL": "https://acme.ai", "Person": "Maya", "Email": "maya@acme.ai"},
        "",
        {
            "fields": {
                "company": "Company",
                "company_website": "URL",
                "person": "Person",
                "email": "Email",
            }
        },
    )
    assert out["subjects"][0]["role"] == "affiliation"
    assert out["subjects"][1]["email"] == "maya@acme.ai"


@pytest.mark.parametrize(
    "raw", ["company: A\ncompany: B", "company: &x [*x]", "- item", "company: [unterminated"]
)
def test_unsafe_properties_stop_plan(raw):
    with pytest.raises(ImportProblem):
        frontmatter("---\n" + raw + "\n---\nText")


def test_stable_identity_survives_rename_and_missing_id_fails(tmp_path):
    note = tmp_path / "one.md"
    note.write_text("---\nbrain_id: stable-123\n---\nText")
    config = {"vault": str(tmp_path), "namespace": "test", "identity_property": "brain_id"}
    original = list(obsidian.records(config, tmp_path))[0]
    note.rename(tmp_path / "two.md")
    moved = list(obsidian.records(config, tmp_path))[0]
    assert original.external_id == moved.external_id == "test:id:stable-123"
    assert original.url != moved.url
    (tmp_path / "missing.md").write_text("No ID")
    with pytest.raises(ImportProblem):
        list(obsidian.records(config, tmp_path))


@pytest.mark.parametrize(
    "audience",
    [
        {"scope": "group", "group": "Research"},
        {"scope": "people", "people": ["alice@example.test"]},
        {"scope": "firm"},
        {"scope": "private"},
    ],
)
def test_all_audiences_bound_to_reviewed_plan(audience, tmp_path):
    import tomllib

    raw = (
        (ROOT / "examples/obsidian.toml")
        .read_text()
        .replace('vault = "obsidian-vault"', f'vault = "{ROOT / "examples/obsidian-vault"}"')
    )
    raw = raw.replace(
        'scope = "private"',
        "\n".join(f"{k} = {__import__('json').dumps(v)}" for k, v in audience.items()),
    )
    path = tmp_path / "config.toml"
    path.write_text(raw)
    plan = plans.build(path)
    assert all(r["preserve_audience"] for r in plan["records"])
    for k, v in audience.items():
        assert plan["records"][0][k] == v
    assert tomllib.loads(raw)["scope"] == audience["scope"]


def test_invalid_audiences_and_duplicate_ids_rejected():
    for item in [
        {"scope": "public"},
        {"scope": "group"},
        {"scope": "people", "people": []},
        {"scope": "private", "group": "Research"},
    ]:
        with pytest.raises(ImportProblem):
            plans.validate_audience(item)
    plan = plans.build(ROOT / "examples/obsidian.toml")
    plan["records"].append(copy.deepcopy(plan["records"][0]))
    with pytest.raises(ImportProblem, match="Duplicate"):
        plans.validate(plan)


def test_notion_properties_supply_evidence_without_rewriting_markdown():
    import json

    pid = "10000000-0000-4000-8000-000000000001"
    data = json.loads((ROOT / "examples/notion-pages.json").read_text())[pid]
    data["page"]["properties"]["Website"] = {"type": "url", "url": "https://www.acme.ai"}
    row = notion.page_record(
        data["page"], data["markdown"], "test", pid, {"fields": {"website": "Website"}}
    )
    assert json.loads(row.text)["markdown"] == data["markdown"]["markdown"]
    assert row.matching["subjects"][0]["domain"] == "acme.ai"


def test_bom_properties_preserve_original_and_report_bad_note_path(tmp_path):
    text = "\ufeff---\nbrain_id: bom-1\ncompany: Acme AI\nwebsite: acme.test\n---\n# Note\nText"
    (tmp_path / "bom.md").write_bytes(text.encode())
    config = {"vault": str(tmp_path), "namespace": "bom", "identity_property": "brain_id"}
    row = list(obsidian.records(config, tmp_path))[0]
    assert row.external_id == "bom:id:bom-1"
    assert row.text == text and row.matching["subjects"][0]["domain"] == "acme.test"
    (tmp_path / "broken.md").write_text("---\ncompany: [broken\n---\nPrivate payload")
    with pytest.raises(ImportProblem, match="broken.md: Invalid YAML") as error:
        list(obsidian.records(config, tmp_path))
    assert "Private payload" not in str(error.value)


@pytest.mark.parametrize(
    ("body", "wanted"),
    [
        ("```markdown\n# Acme AI\n```\nNotes", ""),
        ("~~~\n# Acme AI\n~~~\n   # Kestrel Data ###", "Kestrel Data"),
        ("````\n```\n# Acme AI\n````\n# Kestrel Data", "Kestrel Data"),
        ("<!--\n# Acme AI\n-->\n# Kestrel Data", "Kestrel Data"),
        ("    # Acme AI\n# Kestrel Data", "Kestrel Data"),
        ("#hashtag\n# Kestrel Data", "Kestrel Data"),
    ],
)
def test_heading_ignores_quoted_code_and_honours_markdown_indentation(body, wanted):
    assert evidence({}, body, {})["heading"] == wanted


def test_duplicate_stable_identity_names_both_files_without_echoing_id(tmp_path):
    for name in ("one.md", "two.md"):
        (tmp_path / name).write_text("---\nbrain_id: private-value\n---\nSynthetic note")
    with pytest.raises(ImportProblem) as error:
        list(
            obsidian.records(
                {"vault": str(tmp_path), "namespace": "test", "identity_property": "brain_id"},
                tmp_path,
            )
        )
    assert "one.md" in str(error.value) and "two.md" in str(error.value)
    assert "private-value" not in str(error.value)
