"""Human-readable guide and editable configs, kept outside the generated vaults."""

import json
from urllib.parse import quote


def write_guide(root, manifest):
    names = {e["key"]: e["name"] for e in manifest["entities"]}
    lines = [
        "# Synthetic Obsidian acceptance sets",
        "",
        "All text and identities are fictional. Open Curated or Volume as an Obsidian vault.",
        "The guide, configurations and answer key live outside the vaults and are not imported.",
        "",
        "## Start with Curated",
        "",
        "1. Read a few cases below, especially C001, C003, C004 and C034.",
        "2. Run the isolated Brain acceptance command in the starter's docs/sample-acceptance.md.",
        "   It creates the matching company/person records and checks the independent answer key.",
        "3. For a manual CLI run, copy curated.toml, set the isolated server/person/workspace from",
        "   `brain-import identity`, then plan, preview, review and apply the exact digest.",
        "   The placeholder cannot contact hosted Brain. Use only an isolated workspace.",
        "4. In the wizard, choose Curated, the four note folders, collection sample-curated-v1,",
        "   maximum 78 and stable ID property brain_id. Keep Templates and Archive excluded.",
        "   Mixed-schema cases under Mappings require the folder rules in curated.toml;",
        "   default global mappings alone do not reproduce those cases. A coding assistant can",
        "   help apply that configuration. Keep the original note properties.",
        "",
        "Pending is an expected result: choose only after checking the conflicting or incomplete",
        "evidence, or leave unlinked/review later. One candidate does not prove identity.",
        "Unmatched means no supported identity was found; no company is created.",
        "Notes stay private. Wikilinks and attachment references stay text; no attachment bytes.",
        "",
        "## Curated answer key",
        "",
        "| Case | Scenario | Expected subjects and candidates |",
        "| --- | --- | --- |",
    ]
    for case in manifest["sets"]["curated"]["cases"]:
        wanted = []
        for item in case["expected"]:
            candidates = ", ".join(names[k] for k in item["candidates"]) or "none"
            wanted.append(f"{item['status']} ({item['role']}): {candidates}")
        link = quote("Curated/" + case["path"], safe="/")
        lines.append(
            f"| [{case['id']}]({link}) | {case['title']} | "
            + ("; ".join(wanted) or "No supported subject; no link")
            + " |"
        )
    lines += [
        "",
        "## Volume and failures",
        "",
        "Volume has 1,000 notes: 600 matched, 200 pending, 200 with no active match.",
        "Use volume.toml, or collection sample-volume-v1, maximum 1000 and brain_id in the wizard.",
        "The runner imports, reads back every note, then repeats with zero new sources.",
        "This repeats controlled patterns: a scale test, not 1,000 unique edge cases.",
        "",
        "Failures contains 15 independent invalid selections. Never select the whole directory.",
        "Each must stop planning before Brain is contacted:",
        "",
    ]
    lines += [f"- {f['id']}: {f['error']}" for f in manifest["failures"]]
    lines += [
        "",
        "The manifest is the machine-readable independent answer key. Generated notes contain",
        "local stable IDs, never Brain record IDs or credentials. Nothing schedules an import.",
        "See the dated run report for observed outcomes; generation alone proves no live behavior.",
    ]
    (root / "README.md").write_text("\n".join(lines) + "\n")
    for name, spec in manifest["sets"].items():
        lines = [
            "# Synthetic only. Replace target with your explicitly isolated local Brain identity.",
            'scope = "private"',
            f"max_records = {spec['max_records']}",
            "",
            "[target]",
            'server = "http://127.0.0.1:1/mcp"',
            'firm_id = "REPLACE_FROM_IDENTITY"',
            'user_id = "REPLACE_FROM_IDENTITY"',
            "",
            "[source]",
            'type = "obsidian"',
            f"vault = {json.dumps(spec['vault'])}",
            f"namespace = {json.dumps(spec['namespace'])}",
            'identity_property = "brain_id"',
            'include = ["*.md", "*.markdown"]',
            'exclude = ["Templates/*", "Archive/*"]',
        ]
        for rule in spec["folder_rules"]:
            lines += [
                "",
                "[[source.folder_rules]]",
                f"folder = {json.dumps(rule['folder'])}",
                f"profile = {json.dumps(rule['profile'])}",
            ]
            if rule.get("fields"):
                lines.append("[source.folder_rules.fields]")
                lines += [f"{json.dumps(k)} = {json.dumps(v)}" for k, v in rule["fields"].items()]
        (root / f"{name}.toml").write_text("\n".join(lines) + "\n")
