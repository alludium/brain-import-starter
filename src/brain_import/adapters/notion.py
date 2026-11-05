"""An explicit page allowlist. No workspace crawl, write access or block renderer."""

import json
import os
import random
import time
from pathlib import Path
from uuid import UUID

import httpx

from brain_import.model import ImportProblem, Record
from brain_import.properties import evidence

API_VERSION = "2026-03-11"
RETRYABLE = {429, 500, 502, 503, 504, 529}


def get_json(client, path: str, *, params=None, sleep=time.sleep):
    for attempt in range(4):
        try:
            response = client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise ImportProblem("Notion network failure; retry planning later.") from exc
        if response.status_code in RETRYABLE and attempt < 3:
            try:
                body = response.json()
                if body.get("additional_data", {}).get("rate_limit_reason") == (
                    "public_api_request_blocked"
                ):
                    raise ImportProblem(
                        "Notion has restricted this connection; check its settings."
                    )
            except ValueError:
                pass
            try:
                delay = float(response.headers.get("Retry-After", 2**attempt))
            except ValueError:
                delay = 2**attempt
            if not 0 <= delay <= 60:
                raise ImportProblem("Notion requested a long retry delay; retry planning later.")
            sleep(delay + random.uniform(0, 0.25))
            continue
        if response.status_code != 200:
            raise ImportProblem(
                f"Notion returned HTTP {response.status_code}; check access or retry."
            )
        try:
            return response.json()
        except ValueError as exc:
            raise ImportProblem("Notion returned invalid JSON.") from exc
    raise ImportProblem("Notion retry limit reached.")


def page_record(
    page: dict, markdown: dict, namespace: str, page_id: str, config: dict | None = None
) -> Record:
    if str(UUID(page["id"])) != page_id or str(UUID(markdown["id"])) != page_id:
        raise ImportProblem("Notion returned a different page ID.")
    if page.get("archived") or page.get("in_trash"):
        raise ImportProblem("A selected Notion page is archived; remove it from the selection.")
    text = markdown["markdown"]
    if not isinstance(text, str) or not text.strip():
        raise ImportProblem("A selected Notion page has no Markdown content.")
    if (
        markdown.get("truncated") is not False
        or markdown.get("unknown_block_ids") != []
        or markdown.get("warnings")
        or "<unknown" in text
    ):
        raise ImportProblem(
            "Notion page is incomplete or has warnings; resolve it before importing."
        )
    title = next(
        (
            "".join(t.get("plain_text", "") for t in prop.get("title", []))
            for prop in page.get("properties", {}).values()
            if prop.get("type") == "title"
        ),
        "",
    )
    config = config or {}
    properties = {}
    for key, prop in page.get("properties", {}).items():
        kind = prop.get("type")
        if kind in ("title", "rich_text"):
            properties[key] = "".join(t.get("plain_text", "") for t in prop.get(kind, []))
        elif kind in ("url", "email"):
            properties[key] = prop.get(kind) or ""
        elif kind == "multi_select":
            properties[key] = [v["name"] for v in prop.get(kind, [])]
        elif kind == "select":
            properties[key] = (prop.get(kind) or {}).get("name", "")
        elif key in config.get("fields", {}).values():
            raise ImportProblem(
                "Mapped Notion identity properties must be text, URL, email or select values."
            )
    matching = evidence(properties, text, config)
    matching["heading"] = title[:500] or matching["heading"]
    return Record(
        "notion", namespace + ":" + page_id, title or page_id, text, page["url"], matching=matching
    )


def records(config: dict, base: Path):
    page_ids = [str(UUID(value)) for value in config["page_ids"]]
    if not page_ids or len(page_ids) != len(set(page_ids)):
        raise ImportProblem("Select at least one Notion page, without duplicate IDs.")
    namespace = config["namespace"]
    fixture = config.get("fixture")
    if fixture:
        # Synthetic offline examples exercise the same conversion as live reads.
        data = json.loads((base / fixture).read_text(encoding="utf-8"))
        for page_id in page_ids:
            item = data[page_id]
            yield page_record(item["page"], item["markdown"], namespace, page_id, config)
        return
    token = os.environ.get(config.get("token_env", "NOTION_TOKEN"))
    if not token:
        raise ImportProblem("Set the configured Notion token environment variable locally.")
    with httpx.Client(
        base_url="https://api.notion.com/v1/",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": API_VERSION,
        },
        timeout=60,
        follow_redirects=False,
    ) as client:
        for page_id in page_ids:
            page = get_json(client, f"pages/{page_id}")
            markdown = get_json(
                client,
                f"pages/{page_id}/markdown",
                params={
                    "markdown_version": "v2",
                    "include_transcript": "false",
                },
            )
            yield page_record(page, markdown, namespace, page_id, config)
