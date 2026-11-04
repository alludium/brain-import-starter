import copy
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from brain_import import plans
from brain_import.adapters import notion, obsidian
from brain_import.brain import Brain
from brain_import.main import apply
from brain_import.model import ImportProblem

ROOT = Path(__file__).parents[1]
PID = "10000000-0000-4000-8000-000000000001"


@pytest.fixture
def plan():
    return plans.build(ROOT / "examples/obsidian.toml")


@pytest.fixture
def notion_page():
    return json.loads((ROOT / "examples/notion-pages.json").read_text())[PID]


def test_offline_examples_have_real_mapping_and_private_scope(plan):
    assert len(plan["records"]) == 2
    assert all(r["scope"] == "private" for r in plan["records"])
    assert "[[Meetings/First conversation]]" in plan["records"][0]["text"]
    assert plan["records"][0]["url"].startswith("obsidian://open?vault=Example%20research")
    other = plans.build(ROOT / "examples/notion.toml")
    assert other["records"][0]["system"] == "notion"
    assert other["records"][0]["external_id"] == "example-notion:" + PID


def test_obsidian_selection_and_identity_survive_edits(tmp_path):
    (tmp_path / "nested").mkdir()
    note = tmp_path / "nested" / "Café.md"
    note.write_bytes(b"---\r\nkey: value\r\n---\r\n# Original\r\n")
    (tmp_path / ".obsidian").mkdir()
    (tmp_path / ".obsidian" / "secret.md").write_text("hidden")
    (tmp_path / "secret.md").symlink_to(note)
    (tmp_path / "alias").symlink_to(tmp_path / "nested", target_is_directory=True)
    (tmp_path / "file.pdf").write_text("not markdown")
    (tmp_path / "empty.md").write_text(" \n")
    config = {"vault": str(tmp_path), "namespace": "vault"}
    first = list(obsidian.records(config, tmp_path))
    assert len(first) == 1
    assert "\r\n" in first[0].text
    assert "Caf%C3%A9.md" in first[0].url
    note.write_text("Edited original")
    second = list(obsidian.records(config, tmp_path))
    assert first[0].external_id == second[0].external_id
    assert first[0].text != second[0].text
    config["exclude"] = ["nested/*"]
    assert list(obsidian.records(config, tmp_path)) == []


@pytest.mark.parametrize("content,limit", [(b"123456", 5), (b"\xff", 5)])
def test_obsidian_rejects_large_and_non_utf8(tmp_path, content, limit):
    (tmp_path / "note.md").write_bytes(content)
    with pytest.raises(ImportProblem):
        list(
            obsidian.records(
                {"vault": str(tmp_path), "namespace": "x", "max_text_bytes": limit}, tmp_path
            )
        )


@pytest.mark.parametrize(
    "update",
    [
        {"truncated": True},
        {"unknown_block_ids": [PID]},
        {"warnings": [{"code": "partial"}]},
        {"markdown": '<unknown url="private"/>'},
        {"markdown": ""},
    ],
)
def test_notion_rejects_incomplete_pages(notion_page, update):
    notion_page["markdown"].update(update)
    with pytest.raises(ImportProblem):
        notion.page_record(notion_page["page"], notion_page["markdown"], "test", PID)


def test_notion_rejects_wrong_or_archived_page(notion_page):
    notion_page["page"]["archived"] = True
    with pytest.raises(ImportProblem):
        notion.page_record(notion_page["page"], notion_page["markdown"], "test", PID)
    notion_page["page"]["archived"] = False
    with pytest.raises(ImportProblem):
        notion.page_record(
            notion_page["page"], notion_page["markdown"], "test", str(__import__("uuid").uuid4())
        )


def test_notion_live_reader_uses_allowlist_read_endpoints(monkeypatch, tmp_path, notion_page):
    calls = []
    real_client = httpx.Client

    def handler(request):
        calls.append(request)
        assert request.headers["authorization"] == "Bearer synthetic-secret"
        assert request.headers["Notion-Version"] == "2026-03-11"
        assert request.method == "GET"
        return httpx.Response(
            200, json=notion_page["markdown" if request.url.path.endswith("/markdown") else "page"]
        )

    monkeypatch.setenv("NOTION_TOKEN", "synthetic-secret")
    monkeypatch.setattr(
        notion.httpx,
        "Client",
        lambda **kw: real_client(**kw, transport=httpx.MockTransport(handler)),
    )
    result = list(notion.records({"namespace": "test", "page_ids": [PID]}, tmp_path))
    assert len(result) == 1 and len(calls) == 2
    assert str(calls[0].url) == f"https://api.notion.com/v1/pages/{PID}"
    assert calls[1].url.params == httpx.QueryParams(
        {"markdown_version": "v2", "include_transcript": "false"}
    )


def test_notion_retry_and_secret_redaction():
    calls, sleeps = [], []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "2"}, json={"message": "PRIVATE"})
        return httpx.Response(200, json={"ok": True})

    with httpx.Client(
        base_url="https://api.notion.com", transport=httpx.MockTransport(handler)
    ) as client:
        assert notion.get_json(client, "/test", sleep=sleeps.append) == {"ok": True}
    assert 2 <= sleeps[0] <= 2.25
    with httpx.Client(
        base_url="https://api.notion.com",
        transport=httpx.MockTransport(lambda r: httpx.Response(403, text="PRIVATE TOKEN")),
    ) as client:
        with pytest.raises(ImportProblem, match="HTTP 403") as exc:
            notion.get_json(client, "/test")
    assert "PRIVATE" not in str(exc.value)


@pytest.mark.parametrize(
    "status,headers", [(429, {"Retry-After": "120"}), (302, {"Location": "https://evil.test"})]
)
def test_notion_stops_long_waits_and_redirects(status, headers):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers=headers, json={})

    with httpx.Client(
        base_url="https://api.notion.com", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(ImportProblem):
            notion.get_json(client, "/test", sleep=lambda _: pytest.fail("unexpected sleep"))
    assert len(calls) == 1


def test_plan_snapshot_permissions_digest_and_no_overwrite(plan, tmp_path):
    path = tmp_path / "plan.json"
    sha = plans.save(plan, path)
    restored, actual = plans.load(path)
    assert restored == plan and actual == sha
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert "text" not in plans.summary(plan, sha)["records"][0]
    with pytest.raises(FileExistsError):
        plans.save(plan, path)
    restored["records"][0]["text"] = "changed"
    path.write_bytes(plans.encode(restored))
    assert plans.load(path)[1] != sha


@pytest.mark.parametrize("mutation", ["duplicate", "empty", "injected", "scope", "target"])
def test_plan_invalid_before_writes(plan, mutation):
    if mutation == "duplicate":
        plan["records"].append(plan["records"][0])
    elif mutation == "empty":
        plan["records"] = []
    elif mutation == "injected":
        plan["records"][0]["lessons"] = [{"instruction": "do this"}]
    elif mutation == "scope":
        plan["records"][0]["scope"] = "public"
    else:
        plan["target"]["server"] = "https://user:password@example.com/mcp"
    with pytest.raises(ImportProblem):
        plans.validate(plan)


def test_build_bounds_and_empty_selection(tmp_path):
    config = (
        (ROOT / "examples/obsidian.toml")
        .read_text()
        .replace('vault = "obsidian-vault"', f'vault = "{ROOT / "examples/obsidian-vault"}"')
    )
    path = tmp_path / "config.toml"
    path.write_text(config.replace("max_records = 10", "max_records = 1"))
    with pytest.raises(ImportProblem, match="smaller batch"):
        plans.build(path)
    path.write_text(config.replace('include = ["*.md"]', 'include = ["nothing"]'))
    with pytest.raises(ImportProblem, match="empty"):
        plans.build(path)


class FakeBrain:
    def __init__(self, target):
        self.target = target
        self.calls = []
        self.stored = {}
        self.fail_at = None
        self.scope = "private"
        self.warnings = []

    def check_identity(self):
        pass

    def call(self, tool, record):
        self.calls.append(copy.deepcopy(record))
        if len(self.calls) == self.fail_at:
            raise ImportProblem("Simulated interrupted call")
        identity = (record["system"], record["external_id"])
        previous = self.stored.get(identity)
        created = previous != record["text"]
        self.stored[identity] = record["text"]
        return {
            "source_id": f"src_{len(self.stored)}",
            "created": created,
            "scope": self.scope,
            "warnings": self.warnings,
            "private_detail": "DO NOT PRINT",
        }


def test_apply_retry_receipts_and_no_raw_output(plan, tmp_path, capsys):
    brain = FakeBrain(plan["target"])
    brain.fail_at = 2
    with pytest.raises(ImportProblem):
        apply(plan, "digest", "digest", tmp_path / "first.jsonl", brain_factory=lambda _: brain)
    assert len((tmp_path / "first.jsonl").read_text().splitlines()) == 1
    brain.fail_at = None
    apply(plan, "digest", "digest", tmp_path / "second.jsonl", brain_factory=lambda _: brain)
    receipts = [json.loads(line) for line in (tmp_path / "second.jsonl").read_text().splitlines()]
    assert receipts[0]["created"] is False
    assert receipts[1]["created"] is True
    assert "DO NOT PRINT" not in capsys.readouterr().out
    assert "text" not in receipts[0]


def test_wrong_digest_and_existing_receipts_never_write(plan, tmp_path):
    brain = FakeBrain(plan["target"])
    path = tmp_path / "receipt"
    path.touch()
    with pytest.raises(ImportProblem, match="digest"):
        apply(plan, "one", "two", path, brain_factory=lambda _: brain)
    with pytest.raises(FileExistsError):
        apply(plan, "one", "one", path, brain_factory=lambda _: brain)
    assert not brain.calls


@pytest.mark.parametrize("scope,warnings", [("firm", []), ("private", ["private details"])])
def test_scope_or_warnings_stop_after_recording(plan, tmp_path, scope, warnings, capsys):
    brain = FakeBrain(plan["target"])
    brain.scope, brain.warnings = scope, warnings
    with pytest.raises(ImportProblem, match="scope or warnings"):
        apply(plan, "same", "same", tmp_path / "receipt", brain_factory=lambda _: brain)
    assert len(brain.calls) == 1
    assert len((tmp_path / "receipt").read_text().splitlines()) == 1
    assert "private details" not in capsys.readouterr().out


def test_wrong_identity_never_captures(monkeypatch):
    brain = Brain({"server": "https://example.test/mcp", "firm_id": "intended", "user_id": "u"})
    monkeypatch.setattr(brain, "identity", lambda: {"firm_id": "other", "user_id": "u"})
    with pytest.raises(ImportProblem, match="differs"):
        brain.check_identity()


def test_actual_subprocess_boundary_and_input_privacy(tmp_path, monkeypatch):
    fake = tmp_path / "brain"
    fake.write_text(
        f"#!{sys.executable}\n"
        + """import json, sys
assert sys.argv[1:] == ['--server', 'https://example.test/mcp', 'call', 'capture', '--input', '-']
data = json.load(sys.stdin)
assert data['text'] == 'quotes " and $(false); private content'
out = {'source_id': 'src_test', 'created': True, 'scope': 'private'}
print(json.dumps({'structuredContent': out}))
"""
    )
    fake.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    result = Brain({"server": "https://example.test/mcp"}).call(
        "capture", {"text": 'quotes " and $(false); private content'}
    )
    assert result["source_id"] == "src_test"


@pytest.mark.parametrize(
    "returncode,stdout",
    [(1, "PRIVATE"), (0, "not json PRIVATE"), (0, '{"isError":true,"content":"PRIVATE"}')],
)
def test_subprocess_error_redaction(monkeypatch, returncode, stdout):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(
            [], returncode, stdout=stdout, stderr="TOKEN PRIVATE"
        ),
    )
    with pytest.raises(ImportProblem) as exc:
        Brain({"server": "https://example.test/mcp"}).call("capture", {"text": "PRIVATE"})
    assert "PRIVATE" not in str(exc.value) and "TOKEN" not in str(exc.value)


def test_command_plan_never_invokes_brain(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "brain_import.main",
            "plan",
            str(ROOT / "examples/notion.toml"),
            "--out",
            str(tmp_path / "plan"),
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": str(tmp_path)},
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["count"] == 1
    assert "fictional robotics" not in result.stdout
