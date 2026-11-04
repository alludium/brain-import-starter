"""Read original Markdown. Paths are identities; no entity or wikilink inference."""

import os
from fnmatch import fnmatchcase
from pathlib import Path
from urllib.parse import quote

from brain_import.model import ImportProblem, Record
from brain_import.properties import evidence, frontmatter, label


def records(config: dict, base: Path):
    vault = (base / Path(config["vault"]).expanduser()).resolve()
    if not vault.is_dir():
        raise ImportProblem("Obsidian vault is not a directory.")
    namespace = config["namespace"]
    includes = config.get("include", ["*.md", "*.markdown"])
    excludes = config.get("exclude", ["Templates/*", "Archive/*"])
    max_bytes = config.get("max_text_bytes", 500_000)
    for directory, dirs, names in os.walk(vault, followlinks=False):
        dirs[:] = sorted(
            d for d in dirs if not d.startswith(".") and not (Path(directory) / d).is_symlink()
        )
        for name in sorted(names):
            path = Path(directory) / name
            relative = path.relative_to(vault).as_posix()
            if name.startswith(".") or path.is_symlink():
                continue
            if path.suffix.lower() not in {".md", ".markdown"}:
                continue
            if not any(fnmatchcase(relative, p) for p in includes):
                continue
            if any(fnmatchcase(relative, p) for p in excludes):
                continue
            # Limit the read itself, including if a file grows between stat and read.
            with path.open("rb") as stream:
                data = stream.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise ImportProblem("A Markdown file exceeds max_text_bytes; narrow the selection.")
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ImportProblem(
                    "A Markdown file is not UTF-8; convert it locally first."
                ) from exc
            if not text.strip():
                continue
            url = (
                "obsidian://open?vault="
                + quote(config.get("vault_name", vault.name), safe="")
                + "&file="
                + quote(relative, safe="")
            )
            properties, body = frontmatter(text)
            identity = relative
            if key := config.get("identity_property"):
                identity = label(properties.get(key, ""))
                if not identity:
                    raise ImportProblem(
                        "A selected note has no configured stable identity property."
                    )
                identity = "id:" + identity
            matching = evidence(properties, body, config)
            matching["heading"] = matching["heading"] or path.stem[:500]
            yield Record(
                "obsidian",
                namespace + ":" + identity,
                path.stem,
                text,
                url,
                matching=matching,
            )
