import copy
import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from brain_import.brain import Brain
from brain_import.local_ui import Wizard, inventory, make_server
from brain_import.model import ImportProblem
from brain_import.plans import build_config
from brain_import.preview import preview_plan


class FakeBrain:
    calls = []
    changed = False
    fail_at = None

    def __init__(self, target):
        self.target = target

    def identity(self):
        return {
            "firm_id": "firm_test",
            "user_id": "usr_test",
            "firm_name": "Synthetic firm",
            "name": "Alice",
        }

    def check_identity(self):
        assert self.target["firm_id"] == "firm_test"

    def require_preview(self, **kwargs):
        pass

    def call(self, tool, payload):
        self.calls.append(copy.deepcopy(payload))
        if payload.get("dry_run"):
            return {
                "dry_run": True,
                "writes": False,
                "disposition": "new",
                "scope": payload["scope"],
                "items": [{"status": "pending" if self.changed else "automatic", "candidates": []}],
            }
        if self.fail_at == len([p for p in self.calls if not p.get("dry_run")]):
            raise ImportProblem("Synthetic failure")
        return {"source_id": "src_test", "created": True, "scope": payload["scope"]}


def wait(wizard):
    deadline = time.monotonic() + 5
    while wizard.public()["phase"] in {"connecting", "previewing", "reviewing", "importing"}:
        assert time.monotonic() < deadline
        time.sleep(0.01)
    return wizard.public()


@pytest.fixture
def setup(tmp_path):
    FakeBrain.calls, FakeBrain.changed, FakeBrain.fail_at = [], False, None
    vault = tmp_path / "vault"
    (vault / "Companies").mkdir(parents=True)
    (vault / "Companies/Aster.md").write_text("# Aster\nOriginal.")
    wizard = Wizard("https://brain.example/mcp", tmp_path / "plans", FakeBrain)
    wizard.connect()
    assert wait(wizard)["phase"] == "connected"
    options = {
        "scope": "private",
        "source": {
            "type": "obsidian",
            "vault": str(vault),
            "namespace": "example",
            "include": ["Companies/*"],
            "folder_rules": [{"folder": "Companies", "profile": "organization"}],
        },
    }
    return wizard, options, vault


def test_snapshot_confirmation_recheck_and_no_duplicate_apply(setup):
    wizard, options, vault = setup
    wizard.dry_run(options)
    state = wait(wizard)
    assert state["phase"] == "ready"
    assert all(p["dry_run"] for p in FakeBrain.calls)
    assert state["plan"]["records"][0]["matching"]["subjects"][0]["name"] == "Aster"
    assert "text" not in state["plan"]["records"][0]
    assert Path(state["plan_path"]).stat().st_mode & 0o777 == 0o600
    with pytest.raises(ImportProblem):
        wizard.import_plan("wrong")
    (vault / "Companies/Aster.md").write_text("Edited after preview")
    wizard.import_plan(wizard.sha)
    assert wait(wizard)["phase"] == "complete"
    assert FakeBrain.calls[-1]["text"] == "# Aster\nOriginal."
    with pytest.raises(ImportProblem):
        wizard.import_plan(wizard.sha)


def test_changed_matches_need_reconfirmation(setup):
    wizard, options, _ = setup
    wizard.dry_run(options)
    assert wait(wizard)["phase"] == "ready"
    FakeBrain.changed = True
    wizard.import_plan(wizard.sha)
    state = wait(wizard)
    assert state["phase"] == "ready"
    assert "changed" in state["message"]
    assert all(p["dry_run"] for p in FakeBrain.calls)
    wizard.import_plan(wizard.sha)
    assert wait(wizard)["phase"] == "complete"


def test_partial_failure_keeps_receipts(setup):
    wizard, options, vault = setup
    (vault / "Companies/Birch.md").write_text("# Birch\nSecond.")
    wizard.dry_run(options)
    assert wait(wizard)["phase"] == "ready"
    FakeBrain.fail_at = 2
    wizard.import_plan(wizard.sha)
    state = wait(wizard)
    assert state["phase"] == "error"
    assert len(state["receipts"]) == 1
    assert len(Path(state["receipt_path"]).read_text().splitlines()) == 1


def test_preview_older_server_is_blocked_before_capture(monkeypatch, setup):
    wizard, options, _ = setup
    plan = build_config(
        {**options, "target": {"server": wizard.server, **wizard.account}}, Path.cwd()
    )
    monkeypatch.setattr(Brain, "check_identity", lambda self: None)
    calls = []
    monkeypatch.setattr(Brain, "call", lambda *args: calls.append(args))
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kw: SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"tools": [{"name": "capture", "inputSchema": {"properties": {}}}]}),
        ),
    )
    with pytest.raises(ImportProblem, match="Nothing was imported"):
        preview_plan(plan)
    assert not calls
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kw: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "tools": [
                        {
                            "name": "capture",
                            "inputSchema": {
                                "properties": {"dry_run": {"type": "boolean"}, "matching": {}}
                            },
                        }
                    ]
                }
            ),
        ),
    )
    Brain(plan["target"]).require_preview()


def test_http_capability_origin_host_and_private_content(setup, tmp_path):
    wizard, _, _ = setup
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "index.html").write_text("<h1>Wizard</h1>")
    http = make_server(wizard, 0, assets)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{http.server_port}"
    try:
        with httpx.Client(base_url=url) as client:
            assert client.get("/").status_code == 200
            assert client.get("/api/state").status_code == 401
            headers = {"X-Import-Key": wizard.key}
            assert client.get("/api/state", headers=headers).status_code == 200
            assert (
                client.get(
                    "/api/state", headers={**headers, "Origin": "https://evil.test"}
                ).status_code
                == 403
            )
            assert (
                client.get("/api/state", headers={**headers, "Host": "evil.test"}).status_code
                == 403
            )
            assert (
                client.post("/api/import", headers=headers, json={"sha256": "wrong"}).status_code
                == 400
            )
            assert client.get("/../plans/config.json", headers=headers).status_code == 404
            assert "frame-ancestors 'none'" in client.get("/").headers["content-security-policy"]
    finally:
        http.shutdown()
        http.server_close()
        thread.join()


def test_inventory_never_follows_symlinks_or_reads_bodies(tmp_path):
    (tmp_path / "Notes").mkdir()
    (tmp_path / "Notes/a.md").write_bytes(b"\xff")
    (tmp_path / "link.md").symlink_to(tmp_path / "Notes/a.md")
    (tmp_path / "alias").symlink_to(tmp_path / "Notes", target_is_directory=True)
    result = inventory(str(tmp_path))
    assert result["count"] == 1
    assert result["folders"] == [{"path": "Notes", "count": 1}]


def test_local_token_context_exception_never_applies_to_hosted(monkeypatch):
    monkeypatch.setenv("BRAIN_ACCESS_TOKEN", "synthetic-dev-token")
    monkeypatch.setattr(Brain, "call", lambda *args: {"account": {"firm_id": "f", "user_id": "u"}})
    assert Brain({"server": "http://127.0.0.1:8765/mcp"}).identity()["firm_id"] == "f"
    with pytest.raises(ImportProblem, match="workspace context"):
        Brain({"server": "https://brain.example/mcp"}).identity()
    monkeypatch.delenv("BRAIN_ACCESS_TOKEN")
    with pytest.raises(ImportProblem, match="workspace context"):
        Brain({"server": "http://127.0.0.1:8765/mcp"}).identity()


def test_choices_saved_to_digest_reset_and_forwarded_atomically(setup):
    wizard, options, _ = setup

    class ReviewBrain(FakeBrain):
        def call(self, tool, payload):
            result = super().call(tool, payload)
            if payload.get("dry_run"):
                result["snapshot"] = "a" * 64
                result["items"] = [{"fingerprint": "b" * 64, "status": "pending", "candidates": []}]
                result["search_results"] = [{"id": "acme", "name": "Acme", "type": "organization"}]
                for choice in payload.get("import_review", {}).get("choices", []):
                    result["items"][0].update(status=choice["action"], reviewed=True)
            return result

    wizard.brain_factory = ReviewBrain
    wizard.dry_run(options)
    assert wait(wizard)["phase"] == "ready"
    old = wizard.sha
    search = wizard.review_item({"sha256": old, "record": 0, "query": "Acme"}, search=True)
    assert search["candidates"][0]["id"] == "acme"
    assert wizard.sha == old
    for action, entity in [("approve", "acme"), ("reset", None), ("reject", None), ("defer", None)]:
        wizard.review_item(
            {
                "sha256": wizard.sha,
                "record": 0,
                "fingerprint": "b" * 64,
                "action": action,
                "entity_id": entity,
            }
        )
        state = wait(wizard)
        assert state["phase"] == "ready", state
        assert Path(state["plan_path"]).stat().st_mode & 0o777 == 0o600
        if action == "reset":
            assert wizard.sha == old
        else:
            assert wizard.sha != old
            assert wizard.plan["records"][0]["import_review"]["choices"][0]["action"] == action
    with pytest.raises(ImportProblem):
        wizard.review_item({"sha256": old, "record": 0, "action": "reject"})
    assert all(p.get("dry_run") for p in FakeBrain.calls)
    wizard.import_plan(wizard.sha)
    assert wait(wizard)["phase"] == "complete"
    assert FakeBrain.calls[-1]["import_review"]["choices"][0]["action"] == "defer"


def test_review_capability_is_required_before_capture(monkeypatch):
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **kw: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "tools": [
                        {
                            "name": "capture",
                            "inputSchema": {
                                "properties": {"dry_run": {"type": "boolean"}, "matching": {}}
                            },
                        }
                    ]
                }
            ),
        ),
    )
    with pytest.raises(ImportProblem, match="Nothing was imported"):
        Brain({}).require_preview(with_review=True)


def test_inventory_includes_parents_without_direct_notes(tmp_path):
    (tmp_path / "Companies/Nested").mkdir(parents=True)
    (tmp_path / "Companies/Nested/a.md").write_text("Synthetic note")
    result = inventory(str(tmp_path))
    assert result["count"] == 1
    assert result["folders"] == [
        {"path": "Companies", "count": 0},
        {"path": "Companies/Nested", "count": 1},
    ]
