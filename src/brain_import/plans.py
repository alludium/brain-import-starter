"""An immutable-by-digest local snapshot, reviewed before any Brain writes."""

import hashlib
import json
import os
import re
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

from brain_import.adapters import notion, obsidian
from brain_import.model import ImportProblem

MAX_PLAN_BYTES = 32 * 1024 * 1024
ADAPTERS = {"obsidian": obsidian.records, "notion": notion.records}
PAYLOAD_KEYS = {"system", "external_id", "title", "text", "url", "kind", "scope"}
OPTIONAL_KEYS = {"matching", "people", "group", "preserve_audience", "import_review"}


def validate_audience(item):
    scope = item.get("scope", "private")
    if scope not in {"private", "firm", "people", "group"}:
        raise ImportProblem("Scope must be private, people, group or firm.")
    if scope == "group":
        if (
            not isinstance(item.get("group"), str)
            or not item["group"].strip()
            or item.get("people")
        ):
            raise ImportProblem("Group scope needs one group name and no people list.")
    elif scope == "people":
        people = item.get("people")
        if (
            not isinstance(people, list)
            or not 1 <= len(people) <= 50
            or any(not isinstance(p, str) or not p.strip() for p in people)
            or item.get("group")
        ):
            raise ImportProblem("People scope needs 1–50 member names/emails and no group.")
    elif item.get("people") or item.get("group"):
        raise ImportProblem("Recipients require people or group scope.")


def server_url(value: str):
    url = urlsplit(value)
    if (
        (
            url.scheme != "https"
            and not (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"})
        )
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise ImportProblem(
            "Brain server must use HTTPS (HTTP only on loopback), "
            "without credentials, query or fragment."
        )
    return value


def load_config(path: Path):
    with path.open("rb") as stream:
        config = tomllib.load(stream)
    return validate_config(config)


def validate_config(config):
    server_url(config["target"]["server"])
    for key in ("firm_id", "user_id"):
        if not isinstance(config["target"].get(key), str) or not config["target"][key].strip():
            raise ImportProblem("Set target firm_id and user_id (see the identity command).")
    source = config["source"]
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", source["namespace"]):
        raise ImportProblem(
            "Use a stable namespace of 1–80 letters, digits, underscores or hyphens."
        )
    if source["type"] not in ADAPTERS:
        raise ImportProblem("Unknown source type; add its reader to ADAPTERS.")
    validate_audience(config)
    if not 1 <= config.get("max_records", 500) <= 5000:
        raise ImportProblem("max_records must be between 1 and 5000.")
    if not 1 <= source.get("max_text_bytes", 500_000) <= 2_000_000:
        raise ImportProblem("max_text_bytes must be between 1 and 2000000.")
    return config


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def digest(data: bytes):
    return hashlib.sha256(data).hexdigest()


def validate(plan: dict):
    if plan["format"] != 1:
        raise ImportProblem("Unsupported plan format; regenerate the plan.")
    target = plan["target"]
    server_url(target["server"])
    if not all(
        isinstance(target.get(k), str) and target[k].strip() for k in ("firm_id", "user_id")
    ):
        raise ImportProblem("Plan has no target account.")
    if not isinstance(plan["records"], list) or not plan["records"]:
        raise ImportProblem("Selection is empty; check filters and source access.")
    seen = set()
    for item in plan["records"]:
        if not PAYLOAD_KEYS <= set(item) or set(item) - PAYLOAD_KEYS - OPTIONAL_KEYS:
            raise ImportProblem("Unexpected capture fields in plan; regenerate it.")
        if not all(
            isinstance(item[k], str) and item[k].strip()
            for k in ("system", "external_id", "title", "text")
        ):
            raise ImportProblem("Every record needs text, title and stable source IDs.")
        validate_audience(item)
        if item.get("preserve_audience") is not True:
            raise ImportProblem("Imports must preserve existing audiences.")
        if "matching" in item and not isinstance(item["matching"], dict):
            raise ImportProblem("Matching evidence must be an object.")
        if "import_review" in item:
            review = item["import_review"]
            if (
                not isinstance(review, dict)
                or set(review) != {"snapshot", "choices"}
                or not re.fullmatch(r"[a-f0-9]{64}", str(review.get("snapshot", "")))
                or not isinstance(review["choices"], list)
                or len(review["choices"]) > 30
            ):
                raise ImportProblem("Invalid reviewed choices; run a new dry run.")
            seen_choices = set()
            for choice in review["choices"]:
                if (
                    not isinstance(choice, dict)
                    or set(choice) - {"fingerprint", "action", "entity_id"}
                    or not re.fullmatch(r"[a-f0-9]{64}", str(choice.get("fingerprint", "")))
                    or choice["fingerprint"] in seen_choices
                    or choice.get("action") not in {"approve", "reject", "defer"}
                    or (choice["action"] == "approve") != bool(choice.get("entity_id"))
                ):
                    raise ImportProblem("Invalid reviewed choice; run a new dry run.")
                seen_choices.add(choice["fingerprint"])
        if item["kind"] not in {
            "document",
            "external_record",
        }:
            raise ImportProblem("Unsupported scope or kind in plan.")
        if item["url"] is not None and not isinstance(item["url"], str):
            raise ImportProblem("Source URL must be a string or null.")
        identity = (item["system"], item["external_id"])
        if identity in seen:
            raise ImportProblem("Duplicate source ID; fix the adapter before importing.")
        seen.add(identity)


def build(config_path: Path):
    return build_config(load_config(config_path), config_path.resolve().parent)


def build_config(config, base):
    validate_config(config)
    source = config["source"]
    items, total = [], 0
    for record in ADAPTERS[source["type"]](source, base):
        item = record.payload(config.get("scope", "private"))
        item["preserve_audience"] = True
        for key in ("group", "people"):
            if key in config:
                item[key] = config[key]
        size = len(record.text.encode("utf-8"))
        total += len(encode(item))
        if size > source.get("max_text_bytes", 500_000):
            raise ImportProblem("A record exceeds max_text_bytes; narrow or adapt the selection.")
        if len(items) >= config.get("max_records", 500) or total > MAX_PLAN_BYTES - 10000:
            raise ImportProblem("Plan is too large; choose a smaller batch before importing.")
        items.append(item)
    plan = {
        "format": 1,
        "target": {k: config["target"][k] for k in ("server", "firm_id", "user_id")},
        "records": items,
    }
    validate(plan)
    return plan


def private_file(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Exclusive creation prevents overwriting a reviewed plan, receipt, or symlink target.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    return os.fdopen(fd, "w", encoding="utf-8", newline="\n")


def save(plan: dict, path: Path):
    data = encode(plan)
    if len(data) > MAX_PLAN_BYTES:
        raise ImportProblem("Plan is too large; choose a smaller batch.")
    with private_file(path) as stream:
        stream.write(data.decode("utf-8"))
    return digest(data)


def load(path: Path):
    with path.open("rb") as stream:
        data = stream.read(MAX_PLAN_BYTES + 1)
    if len(data) > MAX_PLAN_BYTES:
        raise ImportProblem("Plan exceeds the size limit.")
    plan = json.loads(data)
    validate(plan)
    return plan, digest(data)


def summary(plan: dict, sha: str):
    return {
        "sha256": sha,
        "target": plan["target"],
        "count": len(plan["records"]),
        "records": [
            {k: v for k, v in item.items() if k != "text"}
            | {"bytes": len(item["text"].encode()), "text_sha256": digest(item["text"].encode())}
            for item in plan["records"]
        ],
    }
