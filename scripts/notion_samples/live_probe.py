"""Verify captured live MCP reads of this synthetic lab; not a REST authentication test."""

import argparse
import json
import re
from pathlib import Path
from uuid import UUID

from brain_import.adapters.notion import page_record
from brain_import.plans import build_config, save

from .catalog import catalog


def page_uuid(url):
    return str(UUID(url.split("?")[0].rstrip("/").split("/")[-1]))


def convert(fetched, schema):
    text = fetched["text"]
    assert not any(
        fetched.get(k)
        for k in ("truncated", "unknown_block_count", "unknown_block_ids", "warnings")
    )
    assert "<unknown" not in text
    raw = json.loads(re.search(r"<properties>\n(.*?)\n</properties>", text, re.S)[1])
    content = re.search(r"<content>\n(.*?)\n</content>\n</page>", text, re.S)
    if content:
        body = content[1]
    else:
        assert "<blank-page>This page is blank and has no content.</blank-page>" in text
        body = ""
    properties = {}
    assert set(raw) - set(schema) <= {"url"}
    for name, value in raw.items():
        if name == "url" and name not in schema:
            continue
        kind = schema[name]["type"]
        kind = "rich_text" if kind == "text" else kind
        if kind in {"title", "rich_text"}:
            value = [{"plain_text": value, "type": "text", "text": {"content": value}}]
        elif kind in {"select", "status"}:
            value = {"name": value} if value else None
        elif kind == "relation":
            value = [{"id": page_uuid(url)} for url in value]
        else:
            assert kind in {"number", "email", "url"}, "Unsupported lab schema"
        properties[name] = {"type": kind, kind: value}
    # No fabricated REST property IDs. Omitted values remain explicitly omitted.
    page = {
        "id": fetched["id"],
        "url": raw["url"],
        "properties": properties,
        "provenance": {
            "transport": "notion-mcp-rendered-export",
            "property_ids_available": False,
            "omitted_properties": sorted(set(schema) - set(raw)),
        },
    }
    markdown = {"id": fetched["id"], "markdown": body, "truncated": False, "unknown_block_ids": []}
    return {"page": page, "markdown": markdown}, raw


def run(root):
    baseline = json.loads((root / "baseline.json").read_text())
    mutations = json.loads((root / "mutations.json").read_text())
    schemas = {
        db: json.loads(
            re.search(r"<data-source-state>\n(.*?)\n</data-source-state>", value["text"], re.S)[1]
        )["schema"]
        for db, value in baseline["schemas"].items()
    }
    rows = catalog()["rows"]
    assert len(baseline["fetches"]) == len(rows) == 38
    fixture, originals = {}, {}
    for row in rows:
        item, raw = convert(baseline["fetches"][row["key"]], schemas[row["database"]])
        for name, expected in row["properties"].items():
            actual = raw.get(name)
            assert actual == expected or (expected is None and actual == ""), (row["key"], name)
        for name, targets in row["relations"].items():
            assert {page_uuid(u) for u in raw.get(name, [])} == {
                baseline["pages"][k]["id"] for k in targets
            }, (row["key"], name)
        pid = item["page"]["id"]
        fixture[pid] = item
        originals[row["key"]] = page_record(item["page"], item["markdown"], "notion-live-lab", pid)
    (root / "pages.json").write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n")
    plan = build_config(
        {
            "scope": "private",
            "target": {
                "server": "http://127.0.0.1:1/mcp",
                "firm_id": "synthetic",
                "user_id": "synthetic",
            },
            "source": {
                "type": "notion",
                "namespace": "notion-live-lab",
                "fixture": "pages.json",
                "page_ids": list(fixture),
            },
        },
        root,
    )
    digest = save(plan, root / "live.plan.json")
    for key, db in [("C001", "companies"), ("L001", "leads")]:
        item, raw = convert(mutations[key], schemas[db])
        changed = page_record(item["page"], item["markdown"], "notion-live-lab", item["page"]["id"])
        assert changed.external_id == originals[key].external_id
        assert changed.text != originals[key].text
        assert json.loads(changed.text)["markdown"] == json.loads(originals[key].text)["markdown"]
        if key == "C001":
            assert raw["Deal Fit"] == 91 and raw["Status"] == "Shortlisted"
        else:
            assert [page_uuid(u) for u in raw["Theses"]] == [baseline["pages"]["T003"]["id"]]
    for key in ("C011", "L012"):
        assert json.loads(originals[key].text)["markdown"] == ""
    report = {
        "live_mcp_rows_verified": 38,
        "plan_records": len(plan["records"]),
        "property_only_pages": 2,
        "live_property_and_relation_edits_detected": True,
        "original_markdown_preserved": True,
        "plan_sha256": digest,
        "rest_authentication_tested": False,
        "brain_apply_tested": False,
    }
    (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    print(json.dumps(run(parser.parse_args().root), indent=2))
