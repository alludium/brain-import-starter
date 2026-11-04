"""Loopback-only wizard. The browser configures; Python reads files and invokes the CLI."""

import copy
import json
import mimetypes
import os
import secrets
import sys
import threading
import time
import webbrowser
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from brain_import.brain import Brain
from brain_import.main import apply
from brain_import.model import ImportProblem
from brain_import.plans import build_config, encode, private_file, save, summary, validate
from brain_import.preview import preview_plan

ASSETS = Path(__file__).parent / "web"


def vaults():
    """Read Obsidian's registry only, never scan personal folders or note contents."""
    if sys.platform == "darwin":
        registry = Path.home() / "Library/Application Support/obsidian/obsidian.json"
    elif sys.platform == "win32":
        registry = Path(os.environ.get("APPDATA", "~")).expanduser() / "obsidian/obsidian.json"
    else:
        registry = (
            Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
            / "obsidian/obsidian.json"
        )
    try:
        data = json.loads(registry.read_text())
        return [
            {"path": v["path"], "name": Path(v["path"]).name}
            for v in data.get("vaults", {}).values()
            if isinstance(v.get("path"), str)
        ]
    except (OSError, ValueError, AttributeError):
        return []


def inventory(raw):
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise ImportProblem("Choose an existing Obsidian vault folder.")
    folders = Counter()
    count = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(
            d for d in dirs if not d.startswith(".") and not (Path(directory) / d).is_symlink()
        )
        for name in files:
            path = Path(directory) / name
            if (
                name.startswith(".")
                or path.is_symlink()
                or path.suffix.lower() not in {".md", ".markdown"}
            ):
                continue
            count += 1
            if count > 10000:
                raise ImportProblem(
                    "More than 10,000 Markdown files; select a smaller vault folder."
                )
            folders[path.parent.relative_to(root).as_posix()] += 1
    return {
        "path": str(root),
        "name": root.name,
        "folders": [{"path": f, "count": n} for f, n in sorted(folders.items())],
        "count": count,
    }


class Wizard:
    def __init__(
        self, server, directory=Path(".local/ui"), brain_factory=Brain, *, viewer_url=None
    ):
        self.server, self.directory, self.brain_factory = server, directory.resolve(), brain_factory
        self.viewer_url = viewer_url or server.removesuffix("/mcp")
        self.key = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.state = {"phase": "idle", "progress": 0, "total": 0, "receipts": []}
        self.account = None
        self.plan = None
        self.preview = None
        self.sha = None

    def public(self):
        with self.lock:
            return copy.deepcopy(
                {
                    **self.state,
                    "server": self.server,
                    "viewer_url": self.viewer_url,
                    "account": self.account,
                }
            )

    def update(self, **values):
        with self.lock:
            self.state.update(values)

    def progress(self, done, total):
        self.update(progress=done, total=total)

    def start(self, phase, fn, *, required_phase=None):
        with self.lock:
            if required_phase and self.state["phase"] != required_phase:
                raise ImportProblem(
                    "The reviewed state changed. Run a new preview before importing."
                )
            if self.state["phase"] in {
                "connecting",
                "signing_in",
                "previewing",
                "reviewing",
                "importing",
            }:
                raise ImportProblem("An operation is already running. Wait for it to finish.")
            self.state.update(phase=phase, error=None, message=None, progress=0)

        def run():
            try:
                fn()
            except ImportProblem as exc:
                self.update(phase="error", error=str(exc))
            except Exception:
                self.update(
                    phase="error",
                    error=(
                        "The operation failed. Check the selection and connection; "
                        "private details were not logged."
                    ),
                )

        threading.Thread(target=run, daemon=True).start()
        return {"started": True}

    def connect(self, login=False):
        def run():
            brain = self.brain_factory({"server": self.server})
            if login:
                brain.login()
            self.account = brain.identity()
            self.plan = self.preview = self.sha = None
            self.update(phase="connected", plan=None, preview=None, receipts=[])

        return self.start("signing_in" if login else "connecting", run)

    def dry_run(self, options):
        if not self.account:
            raise ImportProblem("Connect to Brain first and check the workspace.")
        options = copy.deepcopy(options)

        def run():
            self.plan = self.preview = self.sha = None
            self.update(plan=None, preview=None, receipts=[])
            # Browser supplies settings, never a target account or an arbitrary saved plan.
            config = {
                "target": {"server": self.server, **self.account},
                "source": options["source"],
                "scope": options.get("scope", "private"),
                "max_records": options.get("max_records", 50),
            }
            if config["source"].get("type") != "obsidian":
                raise ImportProblem(
                    "The wizard currently supports Obsidian. Use the CLI for Notion."
                )
            for key in ("people", "group"):
                if key in options:
                    config[key] = options[key]
            plan = build_config(config, Path.cwd())
            stamp = str(time.time_ns())
            path = self.directory / f"{stamp}.plan.json"
            sha = save(plan, path)
            with private_file(self.directory / f"{stamp}.settings.json") as stream:
                json.dump(options, stream)
            self.update(
                plan=summary(plan, sha),
                plan_path=str(path),
                total=len(plan["records"]),
                settings=options,
            )
            result = preview_plan(plan, brain_factory=self.brain_factory, progress=self.progress)
            with private_file(self.directory / f"{stamp}.preview.json") as stream:
                json.dump({"plan_sha256": sha, "results": result}, stream)
            self.plan, self.preview, self.sha = plan, result, sha
            self.update(phase="ready", preview=result, previewed_at=time.time())

        return self.start("previewing", run)

    def review_item(self, data, *, search=False):
        with self.lock:
            if self.state["phase"] != "ready" or not self.plan or data.get("sha256") != self.sha:
                raise ImportProblem("The preview changed. Refresh before choosing a match.")
            index = data.get("record")
            if type(index) is not int or not 0 <= index < len(self.plan["records"]):
                raise ImportProblem("Choose a note from this preview.")
            plan, previews = copy.deepcopy(self.plan), copy.deepcopy(self.preview)
            item, preview = plan["records"][index], previews[index]
        if search:
            query = data.get("query", "")
            if not isinstance(query, str) or not 1 <= len(query.strip()) <= 200:
                raise ImportProblem("Enter a name to search (up to 200 characters).")
            brain = self.brain_factory(plan["target"])
            brain.check_identity()
            brain.require_preview(with_review=True)
            result = brain.call("capture", {**item, "dry_run": True, "matching_search": query})
            if result.get("writes") is not False or result.get("dry_run") is not True:
                raise ImportProblem("Unexpected search response. Update Brain.")
            return {"candidates": result.get("search_results", [])}
        fingerprint, action = data.get("fingerprint"), data.get("action")
        if action not in {"approve", "reject", "defer", "reset"}:
            raise ImportProblem("Choose a match, leave unlinked, or review later.")
        if not any(m.get("fingerprint") == fingerprint for m in preview["items"]):
            raise ImportProblem("Choose a subject from this preview.")
        choices = [
            c
            for c in item.get("import_review", {}).get("choices", [])
            if c["fingerprint"] != fingerprint
        ]
        if action != "reset":
            choices.append(
                {
                    "fingerprint": fingerprint,
                    "action": action,
                    "entity_id": data.get("entity_id") if action == "approve" else None,
                }
            )
        if choices:
            item["import_review"] = {"snapshot": preview.get("snapshot"), "choices": choices}
        else:
            item.pop("import_review", None)
        validate(plan)

        def run():
            brain = self.brain_factory(plan["target"])
            brain.check_identity()
            brain.require_preview(with_review=True)
            result = brain.call("capture", {**item, "dry_run": True})
            if result.get("dry_run") is not True or result.get("writes") is not False:
                raise ImportProblem("Unexpected review response. Nothing was imported.")
            previews[index] = {"title": item["title"], "external_id": item["external_id"], **result}
            stamp = str(time.time_ns())
            path = self.directory / f"{stamp}.plan.json"
            sha = save(plan, path)
            with private_file(self.directory / f"{stamp}.preview.json") as stream:
                json.dump({"plan_sha256": sha, "results": previews}, stream)
            self.plan, self.preview, self.sha = plan, previews, sha
            self.update(
                phase="ready",
                plan=summary(plan, sha),
                plan_path=str(path),
                preview=previews,
                previewed_at=time.time(),
                message="Choice saved locally. Nothing imported yet.",
            )

        return self.start("reviewing", run, required_phase="ready")

    def import_plan(self, confirmation):
        with self.lock:
            if self.state["phase"] != "ready" or not self.plan or confirmation != self.sha:
                raise ImportProblem(
                    "Run a fresh dry run and confirm its exact plan before importing."
                )
            plan, sha, expected = copy.deepcopy(self.plan), self.sha, copy.deepcopy(self.preview)

        def run():
            # Refresh every preview before writing, including account and audience checks.
            self.update(message="Checking that matches have not changed…")
            fresh = preview_plan(plan, brain_factory=self.brain_factory, progress=self.progress)
            if fresh != expected:
                self.preview = fresh
                self.update(
                    phase="ready",
                    preview=fresh,
                    previewed_at=time.time(),
                    message="Matches changed since the dry run. Review them and confirm again.",
                )
                return
            path = self.directory / f"{time.time_ns()}.receipts.jsonl"
            self.update(
                progress=0, message="Importing the reviewed snapshot…", receipt_path=str(path)
            )

            def receipt(value):
                with self.lock:
                    self.state["receipts"].append(value)
                    self.state["progress"] = len(self.state["receipts"])

            apply(
                plan, sha, confirmation, path, brain_factory=self.brain_factory, on_receipt=receipt
            )
            self.update(
                phase="complete",
                message="Import finished. Choices applied; remaining reviews are in Sources.",
            )

        return self.start("importing", run, required_phase="ready")

    def dispatch(self, path, data):
        if path == "/api/connect":
            return self.connect()
        if path == "/api/login":
            return self.connect(login=True)
        if path == "/api/inventory":
            return inventory(data["path"])
        if path == "/api/preview":
            return self.dry_run(data)
        if path == "/api/review":
            return self.review_item(data)
        if path == "/api/search":
            return self.review_item(data, search=True)
        if path == "/api/import":
            return self.import_plan(data.get("sha256"))
        raise ImportProblem("Unknown action.")


def make_server(wizard, port=8769, assets=ASSETS):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # URLs and local paths can contain private information.

        def send(self, status, body, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
                "style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            )
            self.end_headers()
            self.wfile.write(body)

        def allowed(self):
            host = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != host:
                self.send(403, b'{"error":"Invalid host"}')
                return False
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + host:
                self.send(403, b'{"error":"Invalid origin"}')
                return False
            return True

        def authenticated(self):
            if not secrets.compare_digest(self.headers.get("X-Import-Key", ""), wizard.key):
                self.send(
                    401, b'{"error":"Reopen the wizard using the link from brain-import ui."}'
                )
                return False
            return True

        def do_GET(self):
            if not self.allowed():
                return
            path = urlsplit(self.path).path
            if path.startswith("/api/"):
                if not self.authenticated():
                    return
                if path == "/api/state":
                    self.send(200, encode(wizard.public()))
                elif path == "/api/vaults":
                    self.send(200, encode(vaults()))
                else:
                    self.send(404, b"{}")
                return
            file = (assets / ("index.html" if path == "/" else path.lstrip("/"))).resolve()
            if not file.is_relative_to(assets.resolve()) or not file.is_file():
                self.send(404, b"Not found", "text/plain")
                return
            self.send(
                200,
                file.read_bytes(),
                mimetypes.guess_type(file.name)[0] or "application/octet-stream",
            )

        def do_POST(self):
            if not self.allowed() or not self.authenticated():
                return
            if self.headers.get("Content-Type") != "application/json":
                self.send(415, b'{"error":"JSON required"}')
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 1_000_000:
                    raise ImportProblem("Request exceeds the size limit.")
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ImportProblem("Expected settings object.")
                self.send(200, encode(wizard.dispatch(self.path, data)))
            except ImportProblem as exc:
                self.send(400, encode({"error": str(exc)}))
            except (ValueError, KeyError, TypeError, OSError):
                self.send(400, b'{"error":"Invalid settings; check your input."}')

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(server, port, *, open_browser=True, viewer_url=None):
    if not (ASSETS / "index.html").is_file():
        raise ImportProblem("Build the UI first: cd ui && npm ci && npm run build")
    wizard = Wizard(server, viewer_url=viewer_url)
    http = make_server(wizard, port)
    url = f"http://127.0.0.1:{http.server_port}/#key={wizard.key}"
    print(
        f"Local importer: {url}\nKeep this local session link private. Ctrl-C stops the wizard.",
        flush=True,
    )
    if open_browser:
        webbrowser.open(url)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http.server_close()
