"""Exercise actual pipes and process lifetime without a live Brain or credentials."""

import json
import os
import sys

import pytest

from brain_import.brain import Brain, CaptureStream
from brain_import.main import apply
from brain_import.model import ImportProblem


@pytest.fixture
def cli(tmp_path, monkeypatch):
    executable = tmp_path / "brain"
    executable.write_text(
        f"#!{sys.executable}\n"
        + """import json,os,sys,time
if "--help" in sys.argv:
 print("--jsonl" if os.environ.get("STREAM_SUPPORT","yes")=="yes" else "--input");sys.exit(0)
if os.environ.get("STALL"):time.sleep(10)
stream="--jsonl" in sys.argv
while True:
 raw=sys.stdin.readline() if stream else sys.stdin.read()
 if not raw:break
 data=json.loads(raw)
 with open(os.environ["CALL_LOG"],"a") as f:
  f.write(json.dumps({"pid":os.getpid(),"argv":sys.argv,
   "id":data.get("external_id")})+"\\n")
 if data.get("external_id")=="two":
  print(json.dumps({"isError":True}),flush=True);sys.exit(1)
 print(json.dumps({"structuredContent":{"source_id":"src_"+data.get("external_id","x"),"created":True,"scope":"private","pid":os.getpid(),"echo":data.get("text")}}),flush=True)
 if not stream:break
"""
    )
    executable.chmod(0o755)
    log = tmp_path / "calls.jsonl"
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("CALL_LOG", str(log))
    return log


def test_stream_reuses_process_preserves_text_and_stops_on_error(cli):
    brain = Brain({"server": "http://127.0.0.1:1/mcp"})
    with brain.capture_session():
        first = brain.call("capture", {"external_id": "one", "text": "PRIVATE\n日本語"})
        again = brain.call("capture", {"external_id": "three", "text": "other"})
        assert first["echo"] == "PRIVATE\n日本語" and first["pid"] == again["pid"]
    assert brain._stream is None
    assert "PRIVATE" not in cli.read_text()


def test_older_cli_keeps_single_call_behavior(cli, monkeypatch):
    monkeypatch.setenv("STREAM_SUPPORT", "no")
    brain = Brain({"server": "http://127.0.0.1:1/mcp"})
    with brain.capture_session():
        first = brain.call("capture", {"text": "first"})
        second = brain.call("capture", {"text": "second"})
    assert first["pid"] != second["pid"]


def test_stream_failure_keeps_first_receipt_and_never_sends_third(cli, tmp_path, monkeypatch):
    monkeypatch.setattr(Brain, "check_identity", lambda self: None)
    target = {"server": "http://127.0.0.1:1/mcp", "firm_id": "test", "user_id": "test"}
    plan = {
        "target": target,
        "records": [
            {"system": "obsidian", "external_id": key, "text": "Synthetic", "scope": "private"}
            for key in ["one", "two", "never"]
        ],
    }
    receipt = tmp_path / "receipt.jsonl"
    with pytest.raises(ImportProblem, match="tool reported an error"):
        apply(plan, "reviewed", "reviewed", receipt)
    assert [json.loads(line)["id"] for line in cli.read_text().splitlines()] == ["one", "two"]
    assert len(receipt.read_text().splitlines()) == 1


def test_timeout_includes_blocked_stdin_writer_and_reaps_process(cli, monkeypatch):
    monkeypatch.setenv("STALL", "yes")
    monkeypatch.setattr(CaptureStream, "timeout", 0.1)
    stream = CaptureStream("http://127.0.0.1:1/mcp")
    with pytest.raises(ImportProblem, match="write may already have succeeded"):
        stream.call({"text": "x" * 1_000_000})
    assert stream.process.poll() is not None
    stream.close()  # Context cleanup is idempotent after timeout.
