"""Exercise the real page adapter with synthetic snapshots, without provider or Brain calls."""

import argparse
import copy
import json
from pathlib import Path

from brain_import.adapters.notion import page_record
from brain_import.model import ImportProblem
from brain_import.plans import build

from .catalog import uid


def probe(root):
    fixture = json.loads((root / "pages.json").read_text())
    report = {"evidence": "offline API-shaped fixtures through actual importer", "plans": {}}
    for database in ("companies", "theses", "leads"):
        plan = build(root / f"{database}.toml")
        report["plans"][database] = len(plan["records"])
        for record in plan["records"]:
            pid = record["external_id"].split(":")[-1]
            assert record["text"] == fixture[pid]["markdown"]["markdown"]
            assert record["scope"] == "private" and record["preserve_audience"]
    report["original_text_and_private_scope_preserved"] = True

    def convert(key, item=None, fields=None):
        item = item or fixture[uid(key)]
        return page_record(
            item["page"],
            item["markdown"],
            "notion-synthetic-v1",
            uid(key),
            {"fields": fields or {}},
        )

    report["refused_rows"] = {}
    for key in ("C011", "L012"):
        try:
            convert(key)
        except ImportProblem as exc:
            report["refused_rows"][key] = str(exc)

    original = fixture[uid("C001")]
    changed = copy.deepcopy(original)
    changed["page"]["properties"]["Deal Fit"]["number"] = 99
    changed["page"]["properties"]["Status"]["status"]["name"] = "Reached out"
    report["property_only_change_visible"] = convert("C001") != convert("C001", changed)
    changed_relation = copy.deepcopy(fixture[uid("L001")])
    changed_relation["page"]["properties"]["Theses"]["relation"] = [{"id": uid("T003")}]
    report["relation_change_visible"] = convert("L001") != convert("L001", changed_relation)
    try:
        convert("L001", fields={"company": "Company"})
        report["mapped_company_relation"] = "accepted"
    except ImportProblem as exc:
        report["mapped_company_relation"] = str(exc)

    renamed = copy.deepcopy(original)
    renamed["page"]["properties"]["Company"]["title"][0]["plain_text"] = "Renamed Company"
    report["page_rename_keeps_source_id"] = (
        convert("C001").external_id == convert("C001", renamed).external_id
    )
    report["live_notion_authenticated"] = False
    report["brain_matching_or_list_creation_tested"] = False
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(probe(args.root), indent=2))
