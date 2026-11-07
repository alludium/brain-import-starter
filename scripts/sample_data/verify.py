"""Opt-in loopback acceptance using the actual importer and installed Brain CLI.

Called by an isolated Brain stack owner; SQL is used only for independent readback.
Never imported by CI tests to perform writes.
"""

import json
import time
from collections import Counter
from urllib.parse import urlsplit

from brain_import.main import apply
from brain_import.model import ImportProblem
from brain_import.plans import build_config, save
from brain_import.preview import preview_plan

TABLES = (
    "sources",
    "source_links",
    "source_associations",
    "source_association_events",
    "entities",
    "groups_meta",
    "group_members",
)


def counts(sql):
    return {t: sql.execute("SELECT count(*) FROM " + t).fetchone()[0] for t in TABLES}


def config(root, spec, target, **extra):
    return dict(
        target=target,
        scope="private",
        max_records=spec["max_records"],
        source={
            **dict(
                type="obsidian",
                vault=str(root / spec["vault"]),
                namespace=spec.get("namespace", "failure-v1"),
                identity_property=spec.get("identity_property", ""),
                folder_rules=spec.get("folder_rules", []),
            ),
            **spec.get("source", {}),
        },
        **extra,
    )


def signature(items, ids):
    inverse = {v: k for k, v in ids.items()}
    return sorted(
        (
            r["status"],
            tuple(sorted(inverse.get(c["id"], c["id"]) for c in r["candidates"])),
            inverse.get(r.get("entity_id")),
            r["evidence"]["role"],
        )
        for r in items
    )


def expected_signature(case):
    return sorted(
        (e["status"], tuple(sorted(e["candidates"])), e["entity"], e["role"])
        for e in case["expected"]
    )


def check_preview(plan, rows, spec, ids, *, repeated=False):
    cases = {c["id"]: c for c in spec["cases"]}
    failures = []
    for record, row in zip(plan["records"], rows, strict=True):
        key = record["external_id"].split(":id:", 1)[1]
        case = cases[key]
        actual = signature(row["items"], ids)
        expected = expected_signature(case)
        # Persistent review has no rows for unmatched subjects if another subject had a decision.
        if repeated and any(e[0] != "unmatched" for e in expected):
            expected = [e for e in expected if e[0] != "unmatched"]
        if actual != expected:
            failures.append(
                dict(case=key, title=case.get("title"), expected=expected, actual=actual)
            )
    return failures


def verify_stored(sql, plan, receipts, spec, ids):
    cases = {c["id"]: c for c in spec["cases"]}
    for record, receipt in zip(plan["records"], receipts, strict=True):
        sid = receipt["source_id"]
        case = cases[record["external_id"].split(":id:", 1)[1]]
        text, scope, external, url = sql.execute(
            "SELECT text,scope_principal_id,external_id,url FROM sources WHERE id=%s", (sid,)
        ).fetchone()
        assert text == record["text"], ("text", case["id"])
        assert scope == plan["target"]["user_id"], ("scope", case["id"])
        assert external == record["external_id"] and url == record["url"], (
            "provenance",
            case["id"],
        )
        links = {
            r[0]
            for r in sql.execute("SELECT entity_id FROM source_links WHERE source_id=%s", (sid,))
        }
        assert links == {ids[e["entity"]] for e in case["expected"] if e["entity"]}, (
            "links",
            case["id"],
            links,
        )
        stored = list(
            sql.execute(
                (
                    "SELECT status,entity_id,evidence,candidates FROM "
                    "source_associations WHERE source_id=%s"
                ),
                (sid,),
            )
        )
        normalized = [
            dict(
                status=status,
                entity_id=eid,
                evidence=evidence,
                candidates=[{"id": i} for i in candidates],
            )
            for status, eid, evidence, candidates in stored
        ]
        assert signature(normalized, ids) == [
            e for e in expected_signature(case) if e[0] != "unmatched"
        ], ("associations", case["id"])


def run(root, target, ids, sql, output, *, allow_apply=False, selected=("curated", "volume")):
    if not allow_apply:
        raise ValueError("Explicit opt-in is required for local acceptance writes.")
    if urlsplit(target["server"]).hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Acceptance writes require an isolated loopback Brain.")
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((root / "manifest.json").read_text())
    report = {
        "evidence": "real importer + installed CLI + isolated local Brain",
        "sets": {},
        "failures": [],
    }

    def write():
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    for failure in manifest["failures"]:
        try:
            build_config(config(root, failure, target), root)
        except ImportProblem as exc:
            passed = failure["error"] in str(exc)
            report["failures"].append(dict(case=failure["id"], passed=passed, message=str(exc)))
        else:
            report["failures"].append(
                dict(case=failure["id"], passed=False, message="Unexpected success")
            )
    write()
    assert all(r["passed"] for r in report["failures"]), report["failures"]
    for name in selected:
        spec = manifest["sets"][name]
        plan = build_config(config(root, spec, target), root)
        assert len(plan["records"]) == len(spec["cases"])
        sha = save(plan, output / f"{name}.plan.json")
        t = time.monotonic()
        before = counts(sql)

        progress_state = {"phase": "preview", "started": t}

        def progress(done, total, name=name, state=progress_state):
            if done % 50 == 0 or done == total:
                elapsed = time.monotonic() - state["started"]
                print(f"{name} {state['phase']}: {done}/{total} ({elapsed:.1f}s)", flush=True)

        rows = preview_plan(plan, progress=progress)
        result = {
            "notes": len(rows),
            "preview_seconds": round(time.monotonic() - t, 2),
            "preview_no_writes": counts(sql) == before,
            "mismatches": check_preview(plan, rows, spec, ids),
            "statuses": dict(Counter(r["status"] for p in rows for r in p["items"])),
        }
        report["sets"][name] = result
        write()
        (output / f"{name}.preview.json").write_text(json.dumps(rows, ensure_ascii=False))
        assert result["preview_no_writes"]
        assert not result["mismatches"], result["mismatches"]
        t = time.monotonic()
        progress_state.update(phase="import", started=t)
        receipts = []

        total = len(rows)

        def received(r, receipts=receipts, total=total, progress=progress):
            receipts.append(r)
            progress(len(receipts), total)

        apply(plan, sha, sha, output / f"{name}.receipts.jsonl", on_receipt=received)
        result["import_seconds"] = round(time.monotonic() - t, 2)
        assert all(r["created"] for r in receipts)
        verify_stored(sql, plan, receipts, spec, ids)
        result["exact_text_audience_provenance_links"] = True
        write()
        t = time.monotonic()
        before = counts(sql)
        progress_state.update(phase="repeat preview", started=t)
        repeat = preview_plan(plan, progress=progress)
        assert counts(sql) == before
        assert all(r["disposition"] == "unchanged" for r in repeat)
        assert not check_preview(plan, repeat, spec, ids, repeated=True)
        progress_state.update(phase="repeat import", started=time.monotonic())
        repeat_receipts = []
        apply(
            plan,
            sha,
            sha,
            output / f"{name}.repeat.receipts.jsonl",
            on_receipt=lambda r, repeat_receipts=repeat_receipts, progress=progress, total=total: (
                repeat_receipts.append(r),
                progress(len(repeat_receipts), total),
            ),
        )
        assert [r["source_id"] for r in receipts] == [r["source_id"] for r in repeat_receipts]
        assert not any(r["created"] for r in repeat_receipts)
        assert counts(sql) == before
        result.update(
            repeat_seconds=round(time.monotonic() - t, 2),
            repeat_created=0,
            repeat_unchanged=len(repeat_receipts),
            repeat_no_database_growth=True,
        )
        write()
    return report
