"""A deterministic source document: typed properties plus untouched Markdown, never actions."""

import json

from brain_import.model import ImportProblem


def snapshot(page, markdown):
    properties = {}
    for name, prop in page.get("properties", {}).items():
        kind = prop.get("type")
        if not isinstance(kind, str) or kind not in prop:
            raise ImportProblem("Notion returned an incomplete property value.")
        if prop.get("has_more") or (
            kind == "rollup" and prop[kind].get("type") in {"incomplete", "unsupported"}
        ):
            raise ImportProblem("Notion property is incomplete; fetch every property page first.")
        value = prop[kind]
        if kind == "relation":
            # A set of source page references, not assertions about Brain identities.
            value = sorted(value, key=lambda item: item["id"])
        properties[name] = {"type": kind, "value": value}
        if "id" in prop:
            properties[name]["id"] = prop["id"]
    return (
        json.dumps(
            {
                "format": "notion-source-v1",
                "page_id": page["id"],
                "url": page["url"],
                "parent": page.get("parent"),
                "properties": properties,
                "markdown": markdown,
                **({"provenance": page["provenance"]} if page.get("provenance") else {}),
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )


def complete_properties(client, page, get_json):
    """Complete bounded property pagination without following provider-supplied URLs."""
    for prop in page.get("properties", {}).values():
        kind = prop.get("type")
        if kind not in {"relation", "title", "rich_text", "people"}:
            continue
        if not prop.get("has_more") and len(prop.get(kind, [])) < 25:
            continue
        property_id = prop.get("id", "")
        # Notion returns URL-encoded property IDs. Keep those escapes, reject path injection.
        if not property_id or any(c in property_id for c in "/?#") or property_id in {".", ".."}:
            raise ImportProblem("Notion returned an invalid property ID.")
        path = f"pages/{page['id']}/properties/{property_id}"
        values, seen, cursor = [], set(), None
        for _ in range(100):
            result = get_json(client, path, params={"start_cursor": cursor} if cursor else None)
            if result.get("object") != "list" or not isinstance(result.get("results"), list):
                raise ImportProblem("Notion returned an invalid property page.")
            for item in result["results"]:
                if item.get("type") != kind or kind not in item:
                    raise ImportProblem("Notion returned a different property type.")
                values.append(item[kind])
            if result.get("has_more") is False:
                prop[kind], prop["has_more"] = values, False
                break
            cursor = result.get("next_cursor")
            if not isinstance(cursor, str) or not cursor or cursor in seen:
                raise ImportProblem("Notion property pagination did not advance.")
            seen.add(cursor)
        else:
            raise ImportProblem("Notion property exceeds pagination limit; narrow the selection.")
