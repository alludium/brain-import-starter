"""Real local importer lifecycle and audience acceptance; explicit opt-in only."""

import copy
import json
from urllib.parse import urlsplit

import httpx
import yaml
from verify import counts

from brain_import.brain import Brain
from brain_import.main import apply
from brain_import.model import ImportProblem
from brain_import.plans import build_config, save
from brain_import.preview import preview_plan


def run(target, ids, sql, output, *, other_email, other_token, allow_apply=False):
    if not allow_apply or urlsplit(target["server"]).hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise ValueError("Lifecycle acceptance requires explicit local-write opt-in.")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    vault = output / "vault"
    vault.mkdir()
    results = {}
    serial = 0
    brain = Brain(target)
    brain.check_identity()

    def note(key, properties, *, scope="private", **audience):
        text = (
            "---\n"
            + yaml.safe_dump({"brain_id": key, "synthetic": True, **properties})
            + "---\n# Lifecycle\nSynthetic "
            + key
            + "\n"
        )
        (vault / f"{key}.md").write_text(text)
        return build_config(
            {
                "target": target,
                "scope": scope,
                **audience,
                "source": {
                    "type": "obsidian",
                    "vault": str(vault),
                    "namespace": "sample-life-v1",
                    "include": [key + ".md"],
                    "identity_property": "brain_id",
                },
            },
            vault,
        )

    def store(plan, factory=Brain):
        nonlocal serial
        serial += 1
        sha = save(plan, output / f"{serial}.plan.json")
        receipts = []
        apply(
            plan,
            sha,
            sha,
            output / f"{serial}.receipts.jsonl",
            brain_factory=factory,
            on_receipt=receipts.append,
        )
        return receipts

    def refused(fn):
        before = counts(sql)
        try:
            fn()
        except ImportProblem:
            pass
        else:
            raise AssertionError("Expected refusal")
        assert counts(sql) == before

    # Confirm, reject and defer before import, then retain decisions on unchanged repeats.
    for action in ["approve", "reject", "defer"]:
        plan = note(action, {"company": "Acme AI"})
        before = counts(sql)
        row = preview_plan(plan)[0]
        assert counts(sql) == before
        choice = {"fingerprint": row["items"][0]["fingerprint"], "action": action}
        if action == "approve":
            choice["entity_id"] = ids["acme"]
        reviewed = copy.deepcopy(plan)
        reviewed["records"][0]["import_review"] = {"snapshot": row["snapshot"], "choices": [choice]}
        sid = store(reviewed)[0]["source_id"]
        association = sql.execute(
            "SELECT status,entity_id,id FROM source_associations WHERE source_id=%s", (sid,)
        ).fetchone()
        assert (
            association[0]
            == {"approve": "approved", "reject": "rejected", "defer": "deferred"}[action]
        )
        assert association[1] == (ids["acme"] if action == "approve" else None)
        assert (
            sql.execute(
                "SELECT count(*) FROM source_association_events "
                "WHERE association_id=%s AND actor_id=%s",
                (association[2], target["user_id"]),
            ).fetchone()[0]
            == 1
        )
        repeat = preview_plan(plan)[0]
        assert repeat["items"][0]["status"] == association[0]
        assert store(plan)[0]["created"] is False
        # A real edit is a new review, not a silently inherited approval/rejection.
        if action == "approve":
            path = vault / "approve.md"
            path.write_text(path.read_text() + "\nNew substantive observation.\n")
            updated = build_config(
                {
                    "target": target,
                    "source": {
                        "type": "obsidian",
                        "vault": str(vault),
                        "namespace": "sample-life-v1",
                        "include": ["approve.md"],
                        "identity_property": "brain_id",
                    },
                },
                vault,
            )
            fresh = preview_plan(updated)[0]
            assert fresh["disposition"] == "revision" and fresh["items"][0]["status"] == "pending"
            receipt = store(updated)[0]
            assert receipt["created"] and receipt["revision_of"] == sid
    results["approve_reject_defer_audit_repeat_revision"] = True

    # Search can resolve an initially unmatched subject to an existing visible identity.
    unknown = note("searched", {"company": "Unmapped project label"})
    before = counts(sql)
    preview = preview_plan(unknown)[0]
    assert preview["items"][0]["status"] == "unmatched"
    searched = brain.call(
        "capture", {**unknown["records"][0], "dry_run": True, "matching_search": "Kestrel"}
    )
    assert searched["writes"] is False and counts(sql) == before
    assert ids["kestrel"] in {c["id"] for c in searched["search_results"]}
    unknown["records"][0]["import_review"] = {
        "snapshot": preview["snapshot"],
        "choices": [
            {
                "fingerprint": preview["items"][0]["fingerprint"],
                "action": "approve",
                "entity_id": ids["kestrel"],
            }
        ],
    }
    chosen = store(unknown)[0]["source_id"]
    assert sql.execute(
        "SELECT status,entity_id FROM source_associations WHERE source_id=%s", (chosen,)
    ).fetchone() == ("approved", ids["kestrel"])
    results["search_resolves_unmatched_without_creating_identity"] = True

    # Stable IDs survive an actual filesystem rename; unchanged original content is reused.
    plan = note("move", {"company": "Acme AI", "website": "acme.test"})
    sid = store(plan)[0]["source_id"]
    (vault / "move.md").rename(vault / "renamed.md")
    moved = build_config(
        {
            "target": target,
            "source": {
                "type": "obsidian",
                "vault": str(vault),
                "namespace": "sample-life-v1",
                "include": ["renamed.md"],
                "identity_property": "brain_id",
            },
        },
        vault,
    )
    assert preview_plan(moved)[0]["disposition"] == "unchanged"
    assert store(moved)[0]["source_id"] == sid
    widened = copy.deepcopy(moved)
    widened["records"][0]["scope"] = "firm"
    refused(lambda: preview_plan(widened))
    refused(lambda: store(widened))
    results["rename_same_identity_and_audience_change_refused"] = True

    # Actual group/people/private/firm imports and a second member's HTTP readback.
    # Creator must be a member too; include self by the verified name.
    own = brain.identity()["name"]
    brain.call(
        "configure",
        {"groups": [{"name": "Synthetic import reviewers", "members": [own, other_email]}]},
    )
    for scope, recipient in [
        ("private", {}),
        ("firm", {}),
        ("people", {"people": [other_email]}),
        ("group", {"group": "Synthetic import reviewers"}),
    ]:
        plan = note(
            "audience-" + scope,
            {"company": "Acme AI", "website": "acme.test"},
            scope=scope,
            **recipient,
        )
        before = counts(sql)
        preview = preview_plan(plan)[0]
        assert preview["items"][0]["status"] == "automatic" and counts(sql) == before
        receipt = store(plan)[0]
        assert receipt["scope"] == scope
        response = httpx.get(
            target["server"].removesuffix("/mcp")
            + "/api/sources/"
            + receipt["source_id"]
            + "/matching",
            headers={"Authorization": "Bearer " + other_token},
        )
        assert response.status_code == (404 if scope == "private" else 200), (
            scope,
            response.status_code,
        )
    results["four_audiences_and_second_member_readback"] = True
    # Removing that member must revoke access to the already imported group note.
    brain.call("configure", {"groups": [{"name": "Synthetic import reviewers", "members": [own]}]})
    removed = httpx.get(
        target["server"].removesuffix("/mcp")
        + "/api/sources/"
        + receipt["source_id"]
        + "/matching",
        headers={"Authorization": "Bearer " + other_token},
    )
    assert removed.status_code == 404
    results["removed_group_member_loses_access"] = True
    private = note(
        "canary-private", {"company": "Private Canary Labs", "website": "private-canary.test"}
    )
    assert preview_plan(private)[0]["items"][0]["status"] == "automatic"
    firm = note(
        "canary-firm",
        {"company": "Private Canary Labs", "website": "private-canary.test"},
        scope="firm",
    )
    preview = preview_plan(firm)[0]
    assert preview["items"][0]["status"] == "unmatched"
    assert not preview["items"][0]["candidates"]
    secret = copy.deepcopy(firm)
    secret["records"][0]["import_review"] = {
        "snapshot": preview["snapshot"],
        "choices": [
            {
                "fingerprint": preview["items"][0]["fingerprint"],
                "action": "approve",
                "entity_id": ids["secret"],
            }
        ],
    }
    refused(lambda: store(secret))
    results["private_identity_cannot_be_lent_to_firm"] = True

    # A changed candidate set invalidates an earlier human choice atomically.
    anchor = brain.call(
        "capture",
        {
            "text": "Synthetic lifecycle-only identity, separate from the curated catalog.",
            "scope": "firm",
            "entities": [
                {
                    "type": "organization",
                    "name": "Lifecycle Match Anchor",
                    "external_refs": [{"system": "domain", "external_id": "lifecycle-anchor.test"}],
                }
            ],
        },
    )["entities"][0]["id"]
    plan = note("stale", {"company": "Lifecycle Match Anchor"})
    preview = preview_plan(plan)[0]
    plan["records"][0]["import_review"] = {
        "snapshot": preview["snapshot"],
        "choices": [
            {
                "fingerprint": preview["items"][0]["fingerprint"],
                "action": "approve",
                "entity_id": anchor,
            }
        ],
    }
    extra = brain.call(
        "capture",
        {
            "text": "Synthetic distinct duplicate candidate.",
            "scope": "firm",
            "entities": [
                {
                    "type": "organization",
                    "name": "Lifecycle Duplicate Anchor",
                    "external_refs": [
                        {"system": "domain", "external_id": "lifecycle-duplicate.test"}
                    ],
                }
            ],
        },
    )["entities"][0]["id"]
    brain.call(
        "capture",
        {
            "text": "Synthetic common alias evidence.",
            "scope": "firm",
            "entities": [
                {
                    "id": extra,
                    "type": "organization",
                    "name": "Lifecycle Duplicate Anchor",
                    "aliases": ["Lifecycle Match Anchor"],
                }
            ],
        },
    )
    refused(lambda: store(plan))
    results["stale_choice_no_partial_write"] = True

    # Inject interruption between real writes; normal retry reuses the first source.
    first = note("partial-one", {"company": "Kestrel Data", "website": "kestrel.test"})
    second = note("partial-two", {"company": "Kestrel Data", "website": "kestrel.test"})
    first["records"] += second["records"]

    class InterruptSecond(Brain):
        writes = 0

        def call(self, tool, payload):
            if tool == "capture" and not payload.get("dry_run"):
                self.writes += 1
                if self.writes == 2:
                    raise ImportProblem("Synthetic interruption between writes")
            return super().call(tool, payload)

    try:
        store(first, InterruptSecond)
    except ImportProblem:
        pass
    else:
        raise AssertionError("Fault was not injected")
    partial = [
        json.loads(line) for line in (output / f"{serial}.receipts.jsonl").read_text().splitlines()
    ]
    assert len(partial) == 1
    retries = store(first)
    assert (
        retries[0]["source_id"] == partial[0]["source_id"]
        and not retries[0]["created"]
        and retries[1]["created"]
    )
    results["injected_interruption_real_retry_receipts"] = True
    (output / "report.json").write_text(json.dumps(results, indent=2))
    return results
