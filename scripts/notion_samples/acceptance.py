"""Opt-in CLI/Brain persistence check. Run with the Brain eval environment on PYTHONPATH."""

import argparse
import asyncio
import json
import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

from brain_import.adapters.notion import page_record
from brain_import.main import apply
from brain_import.plans import build_config, save
from brain_import.preview import preview_plan

from .live_probe import convert


async def run(root, output):
    from evals.fixture import Fixture
    from evals.stack import Stack, StackConfig
    from evals.ui_stack import ports

    output.mkdir(parents=True, exist_ok=False)
    fixture = Fixture("northwind")
    api, temporal = ports(2)
    config = StackConfig(
        database="vcbrain_notion_" + uuid.uuid4().hex[:8],
        bucket="notion-" + uuid.uuid4().hex[:8],
        port=api,
        temporal_port=temporal,
    )
    for endpoint in (config.admin_dsn, config.s3_endpoint):
        if urlparse(endpoint).hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Synthetic acceptance requires local database and storage services.")
    async with Stack(config, fixture) as stack:
        target = {
            "server": f"http://127.0.0.1:{api}/mcp",
            "firm_id": fixture.firm_id,
            "user_id": fixture.user_id(fixture.admin),
        }
        previous = os.environ.get("BRAIN_ACCESS_TOKEN")
        os.environ["BRAIN_ACCESS_TOKEN"] = stack.tokens[target["user_id"]]
        try:

            def execute():
                pages = json.loads((root / "pages.json").read_text())
                plan = build_config(
                    {
                        "scope": "private",
                        "target": target,
                        "source": {
                            "type": "notion",
                            "namespace": "notion-live-lab",
                            "fixture": "pages.json",
                            "page_ids": list(pages),
                        },
                    },
                    root,
                )
                report = {
                    "evidence": "live MCP snapshots -> actual importer -> CLI -> isolated Brain"
                }
                with stack.sql() as sql:

                    def counts():
                        return [
                            sql.execute("SELECT count(*) FROM " + table).fetchone()[0]
                            for table in (
                                "sources",
                                "source_links",
                                "source_associations",
                                "source_association_events",
                                "entities",
                            )
                        ]

                    def apply_check(data, name):
                        sha = save(data, output / f"{name}.plan.json")
                        receipts = []
                        apply(
                            data,
                            sha,
                            sha,
                            output / f"{name}.receipts.jsonl",
                            on_receipt=receipts.append,
                        )
                        for record, receipt in zip(data["records"], receipts, strict=True):
                            stored = sql.execute(
                                "SELECT text,scope_principal_id,external_id,url "
                                "FROM sources WHERE id=%s",
                                (receipt["source_id"],),
                            ).fetchone()
                            assert stored == (
                                record["text"],
                                target["user_id"],
                                record["external_id"],
                                record["url"],
                            )
                        return receipts

                    before = counts()
                    preview = preview_plan(plan)
                    assert counts() == before
                    assert len(preview) == 38
                    first = apply_check(plan, "initial")
                    assert all(r["created"] for r in first)
                    print("38 source snapshots stored and read back exactly.", flush=True)
                    before = counts()
                    repeat = preview_plan(plan)
                    assert counts() == before
                    assert all(r["disposition"] == "unchanged" for r in repeat)
                    second = apply_check(plan, "repeat")
                    assert not any(r["created"] for r in second)
                    assert counts() == before
                    assert [r["source_id"] for r in first] == [r["source_id"] for r in second]
                    print(
                        "Unchanged repeat reused all 38 sources without table growth.", flush=True
                    )
                    baseline = json.loads((root / "baseline.json").read_text())
                    edits = json.loads((root / "mutations.json").read_text())
                    records = []
                    for key, db in [("C001", "companies"), ("L001", "leads")]:
                        schema = json.loads(
                            re.search(
                                r"<data-source-state>\n(.*?)\n</data-source-state>",
                                baseline["schemas"][db]["text"],
                                re.S,
                            )[1]
                        )["schema"]
                        item, _ = convert(edits[key], schema)
                        r = page_record(
                            item["page"], item["markdown"], "notion-live-lab", item["page"]["id"]
                        ).payload("private")
                        r["preserve_audience"] = True
                        records.append(r)
                    revision = {**plan, "records": records}
                    before = counts()
                    preview = preview_plan(revision)
                    assert counts() == before
                    assert all(r["disposition"] == "revision" for r in preview)
                    revised = apply_check(revision, "revised")
                    original_ids = {r["external_id"]: r["source_id"] for r in first}
                    assert all(
                        r["created"] and r["revision_of"] == original_ids[r["external_id"]]
                        for r in revised
                    )
                    report.update(
                        records=38,
                        no_write_preview=True,
                        exact_persistence=True,
                        private_scope=True,
                        unchanged_repeat_no_growth=True,
                        metadata_only_revisions=2,
                        isolated_local_brain=True,
                    )
                    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
                    print(json.dumps(report), flush=True)

            await asyncio.to_thread(execute)
        finally:
            if previous is None:
                os.environ.pop("BRAIN_ACCESS_TOKEN", None)
            else:
                os.environ["BRAIN_ACCESS_TOKEN"] = previous
    (output / "cleanup.ok").write_text("Isolated database and bucket removed.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--apply-local", action="store_true", required=True)
    args = parser.parse_args()
    asyncio.run(run(args.root.resolve(), args.out.resolve()))
