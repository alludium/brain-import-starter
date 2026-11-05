"""Generate reproducible Notion samples locally; never authenticate or write remotely."""

import argparse
import csv
import json
from pathlib import Path

from .catalog import catalog, uid

TITLES = {"companies": "Company", "theses": "Thesis", "leads": "Lead"}
NUMBERS = {"Deal Fit", "Conviction", "Conviction v2", "Lead Score", "Unknown answers"}
SELECTS = {
    "Action",
    "Track",
    "Engine Status",
    "Lead Type",
    "Tier",
    "Starting something",
    "Reachable",
}


def api_property(name, value, title):
    kind = (
        "title"
        if name == title
        else "number"
        if name in NUMBERS
        else (
            "select"
            if name in SELECTS
            else "status"
            if name == "Status"
            else "email"
            if name == "Email"
            else "url"
            if name == "Website"
            else "rich_text"
        )
    )
    if kind in {"title", "rich_text"}:
        value = [{"plain_text": value or "", "type": "text", "text": {"content": value or ""}}]
    elif kind in {"select", "status"}:
        value = {"name": value} if value else None
    return {"id": uid("property:" + name), "type": kind, kind: value}


def generate(root):
    root.mkdir(parents=True, exist_ok=False)
    data = catalog()
    for row in data["rows"]:
        for target in data["rows"]:
            title = target["properties"][TITLES[target["database"]]]
            row["content"] = row["content"].replace(
                "{{page:" + target["key"] + "}}",
                f'<mention url="https://www.notion.so/{uid(target["key"])}">{title}</mention>',
            )
    fixture = {}
    for row in data["rows"]:
        pid = uid(row["key"])
        props = {
            k: api_property(k, v, TITLES[row["database"]]) for k, v in row["properties"].items()
        }
        props.update(
            {
                k: {
                    "id": uid("property:" + k),
                    "type": "relation",
                    "relation": [{"id": uid(v)} for v in values],
                    "has_more": False,
                }
                for k, values in row["relations"].items()
            }
        )
        fixture[pid] = {
            "page": {
                "object": "page",
                "id": pid,
                "url": "https://www.notion.so/" + pid.replace("-", ""),
                "archived": False,
                "properties": props,
                "parent": {"type": "data_source_id", "data_source_id": uid(row["database"])},
            },
            "markdown": {
                "id": pid,
                "markdown": row["content"],
                "truncated": False,
                "unknown_block_ids": [],
            },
        }
    (root / "catalog.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    (root / "pages.json").write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n")
    for database in TITLES:
        rows = [r for r in data["rows"] if r["database"] == database]
        with (root / f"{database}.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]["properties"]))
            writer.writeheader()
            writer.writerows(r["properties"] for r in rows)
        ids = [uid(r["key"]) for r in rows if r["content"]]
        fields = (
            {"company": "Company", "website": "Website"}
            if database == "companies"
            else (
                {
                    "company": "Company name",
                    "website": "Website",
                    "person": "Person",
                    "email": "Email",
                }
                if database == "leads"
                else {}
            )
        )
        config = (
            'scope = "private"\nmax_records = 100\n[target]\n'
            'server = "http://127.0.0.1:1/mcp"\nfirm_id = "synthetic"\nuser_id = "synthetic"\n'
            '[source]\ntype = "notion"\nnamespace = "notion-synthetic-v1"\n'
            'fixture = "pages.json"\npage_ids = ' + json.dumps(ids) + "\n[source.fields]\n"
        )
        config += "".join(f'{k} = "{v}"\n' for k, v in fields.items())
        (root / f"{database}.toml").write_text(config)
    guide = """# Notion synthetic import lab

38 fictional records: 20 companies, 12 mixed person/company leads and 6 theses.
Inspired by demonstrated research layouts, not copied customer records. All evidence URLs are
non-working .test placeholders. Fake local Notion IDs are deterministic and do not name live pages.

## Start here

- C001/C002: exact company identifiers; C003: conflicting company name and website.
- C005/C006: shared alias; C007/C008: parent/subsidiary shared domain.
- C011/L012: empty body with useful properties; deliberately excluded from compatible TOMLs.
- C015/C016: unknown versus zero score. C017/L001: memberships in multiple theses.
- L003/L004: two people with the same name. L007: person without a company.
- L009/L010: company leads referencing pipeline companies; do not create duplicates.
- L011: person name and email disagree. T001: versioned scores and detailed evidence tables.
- C019: long text. C020: quoted instructions must remain inert source data.

The generated CSVs are for inspection. They do not carry page bodies or relations. catalog.json
contains properties, relations and original content; pages.json is an offline API-shaped fixture.
The three TOMLs exercise the current page adapter only, with an inert Brain target. They do not
populate origination lists or establish live Notion authentication. Run probe.py for current gaps.

## Preserving meaning

Keep imported scores and status source-reported. A high lead score is not high identity confidence.
Domain on a thesis describes a research area, not a company website. Unknown is not false or zero.
Do not execute outreach controls, promote Deals, auto-create companies for people, or infer sharing.
Relations and page links are separate cases. A selected view is not a permission boundary.

## Mutation checks for a later live importer

1. Change only C001 Deal Fit and Status; expect a new property snapshot with unchanged body.
2. Rename C002; retain the same source ID. Rename a property; use its stable property ID.
3. Link C017 to another thesis; retain one company and all memberships.
4. Remove a row from a view; do not delete the company or widen access.
5. Simulate an inaccessible relation, paging interruption and retry; report incomplete input.
6. Repeat unchanged input; create no duplicate sources, people, companies or list entries.

These are acceptance expectations, not claims that the current importer supports these operations.
The original screenshot set contains UI buttons and unknown underlying schema. This lab models
the observed data shapes; it does not reproduce hidden formulas, workflows or Jay's exact schema.
"""
    (root / "README.md").write_text(guide)
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    data = generate(args.out.expanduser().resolve())
    print(json.dumps({"rows": len(data["rows"]), "output": str(args.out)}))
