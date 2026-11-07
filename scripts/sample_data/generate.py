"""Generate synthetic vaults only into a new directory; never touch a personal vault."""

import argparse
import json
from pathlib import Path

import yaml
from catalog import automatic, curated, entities, pending, unmatched
from guide import write_guide


def write_note(root, path, properties, heading, body, crlf=False):
    text = "---\n" + yaml.safe_dump(properties, sort_keys=False, allow_unicode=True) + "---\n"
    if heading is not None:
        text += "# " + heading + "\n\n"
    text += body + "\n"
    if crlf:
        text = text.replace("\n", "\r\n")
    dest = root / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(text.encode())


def generate(root):
    root.mkdir(parents=True, exist_ok=False)
    manifest = {"format": 1, "entities": entities(), "sets": {}, "failures": []}
    curated_root = root / "Curated"
    rules = []
    cases = curated()
    for i, c in enumerate(cases):
        folder = (
            "Companies" if i < 30 else "People and meetings" if i < 51 else "Formats and boundaries"
        )
        if c["fields"] or c["profile"]:
            folder = "Mappings/" + c["id"]
            rules.append(dict(folder=folder, profile=c["profile"] or "notes", fields=c["fields"]))
        if c["id"] == "C066":
            folder = "Formats and boundaries/Nested/2026/November"
        name = (
            "Acme AI"
            if c["id"] == "C054"
            else "Ünicode 日本語"
            if c["id"] == "C067"
            else c["title"]
        )
        c["path"] = f"{folder}/{c['id']} {name}.md"
        write_note(
            curated_root,
            c["path"],
            {"brain_id": c["id"], "synthetic": True, **c["properties"]},
            c["heading"],
            c["body"],
            c["crlf"],
        )
        if c.get("bom"):
            dest = curated_root / c["path"]
            dest.write_bytes(b"\xef\xbb\xbf" + dest.read_bytes())
    # Outside the selected Markdown set, with explicit preservation expectations.
    (curated_root / "Attachments").mkdir()
    (curated_root / "Attachments/chart.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><text y="20">Synthetic chart</text></svg>'
    )
    (curated_root / "Attachments/board.canvas").write_text('{"nodes":[],"edges":[]}')
    for folder in ["Archive", "Templates", ".obsidian"]:
        (curated_root / folder).mkdir(exist_ok=True)
        (curated_root / folder / "excluded.md").write_text(
            "# Acme AI\nControl: this must never be imported."
        )
    (curated_root / "Formats and boundaries/empty.md").write_text("  \n")
    (curated_root / "Formats and boundaries/.hidden.md").write_text("# Acme AI")
    (curated_root / "Formats and boundaries/link.md").symlink_to(curated_root / cases[0]["path"])
    manifest["sets"]["curated"] = {
        "vault": "Curated",
        "namespace": "sample-curated-v1",
        "cases": cases,
        "folder_rules": rules,
        "max_records": len(cases),
        "identity_property": "brain_id",
    }
    scale = []
    for i in range(1000):
        key = f"co{i % 100:03}"
        pkey = f"person{i % 40:03}"
        name = f"Sample Venture {i % 100:03}"
        props = {
            "brain_id": f"B{i:04}",
            "synthetic": True,
            "company": name,
            "website": f"https://venture-{i % 100:03}.test",
        }
        expected = [automatic(key)]
        mode = i % 10
        if mode == 1:
            props.pop("website")
            expected = [pending(key)]
        elif mode == 2:
            props["website"] = f"venture-{(i + 1) % 100:03}.test"
            expected = [pending(key, f"co{(i + 1) % 100:03}")]
        elif mode == 3:
            props = {
                "brain_id": f"B{i:04}",
                "synthetic": True,
                "person": f"Sample Founder {i % 40:03}",
                "email": f"founder-{i % 40:03}@venture-{i % 40:03}.test",
            }
            expected = [automatic(pkey)]
        elif mode == 4:
            props = {"brain_id": f"B{i:04}", "synthetic": True}
            expected = []
        elif mode == 5:
            props = {
                "brain_id": f"B{i:04}",
                "synthetic": True,
                "company": f"Unregistered Company {i:04}",
            }
            expected = [unmatched()]
        body = f"Synthetic sample B{i:04}. Meeting date 2026-{1 + i % 12:02}-{1 + i % 28:02}.\n"
        body += "Discussed runway, hiring, product milestones and competition.\n" * (
            500 if i % 50 == 0 else 5 + i % 20
        )
        if mode == 6:
            body += "\n| Item | Value |\n|---|---|\n| Pipeline | €9,000 |\n"
        if mode == 7:
            body += "\n![[Attachments/chart.svg]]\n[[Missing note]]\n"
        if mode == 8:
            body += '\n```json\n{"scope":"firm","company":"Acme AI"}\n```\n'
        if mode == 9:
            body += "\nFrançais : données fictives. 日本語の合成メモ。\n"
        folder = ["Companies", "Meetings", "Research"][i % 3]
        path = f"{folder}/{2024 + i % 3}/{1 + i % 12:02}/B{i:04}.md"
        write_note(root / "Volume", path, props, "Synthetic research record", body, i % 17 == 0)
        scale.append(dict(id=f"B{i:04}", path=path, expected=expected))
    manifest["sets"]["volume"] = {
        "vault": "Volume",
        "namespace": "sample-volume-v1",
        "cases": scale,
        "folder_rules": [],
        "max_records": 1000,
        "identity_property": "brain_id",
    }
    failures = [
        ("invalid-yaml", "---\ncompany: [broken\n---\nNote", {}, "Invalid YAML"),
        ("duplicate-property", "---\ncompany: A\ncompany: B\n---\nNote", {}, "unique strings"),
        ("yaml-alias", "---\ncompany: &x [*x]\n---\nNote", {}, "anchors"),
        ("nontext-company", "---\ncompany: 42\n---\nNote", {}, "text or lists"),
        ("nested-attendee", "---\nattendees: [{name: Maya}]\n---\nNote", {}, "text or lists"),
        ("invalid-website", "---\nwebsite: ftp://acme.test\n---\nNote", {}, "HTTP website"),
        (
            "credential-website",
            "---\nwebsite: https://user:password@acme.test\n---\nNote",
            {},
            "HTTP website",
        ),
        (
            "oversized-property",
            "---\ncompany: " + ("x" * 301) + "\n---\nNote",
            {},
            "300 characters",
        ),
        (
            "oversized-frontmatter",
            "---\ncomment: " + ("x" * 32001) + "\n---\nNote",
            {},
            "32000 characters",
        ),
        (
            "too-many-subjects",
            "---\ncompanies: " + json.dumps([f"Company {i}" for i in range(31)]) + "\n---\nNote",
            {},
            "30 identity",
        ),
        ("non-utf8", b"\xff\xfe\x00", {}, "UTF-8"),
        ("oversized-note", "x" * 500001, {}, "max_text_bytes"),
        (
            "missing-stable-id",
            "# Note\nSynthetic",
            {"identity_property": "brain_id"},
            "stable identity",
        ),
        (
            "duplicate-stable-id",
            "---\nbrain_id: repeated\n---\nNote",
            {"identity_property": "brain_id"},
            "Duplicate source ID",
        ),
        ("max-notes", "# Note\nSynthetic", {}, "Plan is too large"),
    ]
    for key, content, config, error in failures:
        dest = root / "Failures" / key
        dest.mkdir(parents=True)
        (dest / "one.md").write_bytes(content if isinstance(content, bytes) else content.encode())
        if key in {"duplicate-stable-id", "max-notes"}:
            (dest / "two.md").write_text(str(content) + "\nSecond")
        manifest["failures"].append(
            dict(
                id=key,
                vault="Failures/" + key,
                source=config,
                max_records=1 if key == "max-notes" else 100,
                error=error,
            )
        )
    for name in ["Curated", "Volume"]:
        (root / name / ".obsidian").mkdir(exist_ok=True)
        (root / name / ".obsidian/app.json").write_text("{}")
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    write_guide(root, manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest = generate(args.out.expanduser().resolve())
    print(
        json.dumps(
            {
                "curated": len(manifest["sets"]["curated"]["cases"]),
                "volume": len(manifest["sets"]["volume"]["cases"]),
                "failures": len(manifest["failures"]),
                "identities": len(manifest["entities"]),
            }
        )
    )
