"""Only this module knows how to call Brain. Auth belongs to the installed CLI."""

import json
import os
import subprocess

from brain_import.model import ImportProblem


class Brain:
    def __init__(self, target: dict):
        self.target = target

    def call(self, tool: str, payload: dict) -> dict:
        try:
            result = subprocess.run(
                ["brain", "--server", self.target["server"], "call", tool, "--input", "-"],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                encoding="utf-8",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                timeout=180,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ImportProblem(
                "Brain CLI unavailable or timed out; check installation and login."
            ) from exc
        if result.returncode:
            # stderr and MCP error text may echo source contents or credentials.
            raise ImportProblem(
                "Brain call failed; check CLI login, permissions and live tool schema."
            )
        try:
            data = json.loads(result.stdout)
            if data.get("isError"):
                raise ImportProblem("Brain tool reported an error; inspect privately if needed.")
            structured = data["structuredContent"]
            if not isinstance(structured, dict):
                raise ValueError
            return structured
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ImportProblem(
                "Unexpected Brain CLI response; check the CLI/server versions."
            ) from exc

    def identity(self) -> dict:
        account = self.call("configure", {"account": {}}).get("account", {})
        if not account.get("firm_id") or not account.get("user_id"):
            raise ImportProblem("Brain did not return an account identity.")
        return {key: account.get(key) for key in ("firm_id", "firm_name", "user_id", "name")}

    def check_identity(self):
        account = self.identity()
        if any(account[key] != self.target[key] for key in ("firm_id", "user_id")):
            raise ImportProblem("Brain account differs from the plan target; no records were sent.")
