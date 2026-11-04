"""Synthetic transport stand-in for browser regression; never connects to Brain."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from brain_import.local_ui import Wizard, make_server  # noqa: E402


class SyntheticBrain:
    def __init__(self, target):
        self.target = target

    def identity(self):
        return {
            "firm_id": "test",
            "user_id": "test",
            "firm_name": "Browser test firm",
            "name": "Test user",
        }

    def login(self):
        pass

    def check_identity(self):
        assert self.target["firm_id"] == "test"

    def require_preview(self, **kwargs):
        pass

    def call(self, tool, payload):
        if payload.get("dry_run"):
            status = {"Acme": "automatic", "Conflict": "pending", "Unknown": "unmatched"}[
                payload["title"]
            ]
            result = {
                "snapshot": "a" * 64,
                "search_results": [{"id": "birch", "name": "Birch", "type": "organization"}],
                "dry_run": True,
                "writes": False,
                "disposition": "new",
                "scope": payload["scope"],
                "items": [
                    {
                        "fingerprint": "b" * 64,
                        "status": status,
                        "evidence": {
                            "type": "organization",
                            "name": payload["title"],
                            "domain": "acme.test",
                            "location": "properties.website",
                        },
                        "reason": "Synthetic browser fixture: identifier check.",
                        "candidates": []
                        if status == "unmatched"
                        else [{"id": "acme", "name": "Acme", "type": "organization"}],
                    }
                ],
            }
            for choice in payload.get("import_review", {}).get("choices", []):
                row = result["items"][0]
                row.update(
                    reviewed=True,
                    entity_id=choice.get("entity_id"),
                    status={"approve": "approved", "reject": "rejected", "defer": "deferred"}[
                        choice["action"]
                    ],
                )
                if choice.get("entity_id") == "birch":
                    row["candidates"].append(
                        {"id": "birch", "name": "Birch", "type": "organization"}
                    )
            return result
        return {"source_id": "src_" + payload["title"], "created": True, "scope": payload["scope"]}


with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    (root / "Notes").mkdir()
    for name in ["Acme", "Conflict", "Unknown"]:
        (root / "Notes" / f"{name}.md").write_text(
            f"---\ncompany: {name}\n---\n# {name}\nSynthetic note."
        )
    wizard = Wizard("https://brain.example/mcp", root / "plans", SyntheticBrain)
    http = make_server(wizard, 0)
    print(
        json.dumps(
            {"url": f"http://127.0.0.1:{http.server_port}/#key={wizard.key}", "vault": str(root)}
        ),
        flush=True,
    )
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http.server_close()
