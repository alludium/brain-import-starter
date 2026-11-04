"""Only this module knows how to call Brain. Auth belongs to the installed CLI."""

import json
import os
import subprocess
from urllib.parse import urlsplit

from brain_import.model import ImportProblem


class Brain:
    def __init__(self, target: dict):
        self.target = target
        self.workspace_context = None

    def call(self, tool: str, payload: dict) -> dict:
        # Context is runtime routing, never source data or part of a saved plan.
        if self.workspace_context:
            payload = {**payload, "workspace_context": self.workspace_context}
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
        except FileNotFoundError as exc:
            raise ImportProblem(
                "Brain CLI not found on PATH. Install it, then check brain --version."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ImportProblem(
                "Brain CLI timed out. A write may already have succeeded; "
                "review receipts before retrying."
            ) from exc
        except OSError as exc:
            raise ImportProblem(
                "Cannot start Brain CLI. Check brain --version in this terminal."
            ) from exc
        if result.returncode:
            # Recognize only locally authored CLI diagnostics; never echo raw stderr.
            if result.stderr.startswith("Sign-in required. Run brain login first;"):
                raise ImportProblem(
                    "Brain CLI is not signed in. Run brain login, then retry identity."
                )
            if result.stderr.startswith(
                "Cannot access Alludium Brain CLI credentials in the OS keyring."
            ):
                raise ImportProblem(
                    "Brain CLI credential access needs attention. Run brain login yourself; "
                    "follow its explanation before allowing any Keychain prompt."
                )
            # Other stderr and MCP error text may echo source contents or credentials.
            raise ImportProblem(
                "Brain call failed. First check brain --version, then brain login; "
                "if both work, check permissions and the live tool schema. "
                "CLI output was withheld because it may contain private data."
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

    def login(self):
        try:
            result = subprocess.run(
                ["brain", "--server", self.target["server"], "login"],
                capture_output=True,
                timeout=300,
                check=False,
            )
            if result.returncode:
                raise ImportProblem(
                    "Sign-in did not finish. Run brain login in your terminal for guidance."
                )
        except (OSError, subprocess.TimeoutExpired):
            raise ImportProblem(
                "Cannot finish sign-in. Check the Brain CLI and try again."
            ) from None

    def require_preview(self, *, with_review=False):
        # Discover before ever sending capture: older servers must not silently ignore dry_run.
        try:
            result = subprocess.run(
                ["brain", "--server", self.target["server"], "tools"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=180,
                check=False,
            )
            tools = json.loads(result.stdout).get("tools", []) if result.returncode == 0 else []
            capture = next(t for t in tools if t.get("name") == "capture")
            fields = capture["inputSchema"]["properties"]
            if fields.get("dry_run", {}).get("type") != "boolean" or "matching" not in fields:
                raise ValueError
            if with_review and not {"import_review", "matching_search"} <= fields.keys():
                raise ValueError
        except (
            OSError,
            subprocess.TimeoutExpired,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            StopIteration,
        ):
            raise ImportProblem(
                "This Brain connection does not advertise safe import previews. "
                "Update the matching-preview backend before continuing. Nothing was imported."
            ) from None

    def identity(self) -> dict:
        self.workspace_context = None
        result = self.call("configure", {"account": {}})
        account = result.get("account", {})
        if not account.get("firm_id") or not account.get("user_id"):
            raise ImportProblem("Brain did not return an account identity.")
        context = result.get("workspace_context") or account.get("workspace_context")
        if not isinstance(context, str) or not context.strip():
            # Local dev tokens are bound to one firm and do not issue OAuth workspace contexts.
            local = urlsplit(self.target["server"]).hostname in {"localhost", "127.0.0.1", "::1"}
            if local and os.environ.get("BRAIN_ACCESS_TOKEN"):
                return {
                    key: account.get(key) for key in ("firm_id", "firm_name", "user_id", "name")
                }
            raise ImportProblem("Brain did not return a workspace context; update the server.")
        self.workspace_context = context
        return {key: account.get(key) for key in ("firm_id", "firm_name", "user_id", "name")}

    def check_identity(self):
        account = self.identity()
        if any(account[key] != self.target[key] for key in ("firm_id", "user_id")):
            self.workspace_context = None
            raise ImportProblem("Brain account differs from the plan target; no records were sent.")
