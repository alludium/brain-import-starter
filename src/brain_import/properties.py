"""Provider properties become bounded identity evidence, never permissions or entity IDs."""

import re
from urllib.parse import urlsplit

import yaml

from brain_import.markdown import heading
from brain_import.model import ImportProblem

DEFAULT_FIELDS = {
    "company": "company",
    "website": "website",
    "person": "person",
    "email": "email",
    "company_website": "company_website",
    "companies": "companies",
    "attendees": "attendees",
}


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ImportProblem("Property names must be unique strings.")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def frontmatter(text):
    match = re.match(r"\A\ufeff?---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
    if not match:
        return {}, text
    raw = match[1]
    if len(raw) > 32000:
        raise ImportProblem("Property block exceeds 32000 characters.")
    try:
        # No YAML aliases: avoid recursive/unbounded values in user-owned notes.
        if any(
            isinstance(t, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken)) for t in yaml.scan(raw)
        ):
            raise ImportProblem("Expand YAML anchors and aliases before importing properties.")
        data = yaml.load(raw, Loader=UniqueLoader) or {}
    except yaml.YAMLError as exc:
        raise ImportProblem(
            "Invalid YAML properties; fix the selected note before planning."
        ) from exc
    if not isinstance(data, dict):
        raise ImportProblem("Properties must be a mapping.")
    return data, text[match.end() :]


def label(value):
    if not isinstance(value, str):
        raise ImportProblem("Mapped identity properties must be text or lists of text.")
    value = value.strip()
    if value.startswith("[[") and value.endswith("]]"):
        value = value[2:-2].split("|", 1)[0].rsplit("/", 1)[-1].split("#", 1)[0]
    if len(value) > 300:
        raise ImportProblem("An identity property exceeds 300 characters.")
    return value


def evidence(properties, body, config):
    mapping = {**DEFAULT_FIELDS, **config.get("fields", {})}
    if set(mapping) != set(DEFAULT_FIELDS) or any(not isinstance(v, str) for v in mapping.values()):
        raise ImportProblem("Unknown identity field mapping; use the documented canonical fields.")

    def value(key):
        raw = properties.get(mapping[key], "")
        return label(raw) if raw is not None else ""

    def values(key):
        raw = properties.get(mapping[key], []) or []
        return [label(x) for x in (raw if isinstance(raw, list) else [raw])]

    def domain(raw):
        if not raw:
            return ""
        url = urlsplit(raw if "://" in raw else "https://" + raw)
        if url.scheme not in ("https", "http") or not url.hostname or url.username or url.password:
            raise ImportProblem("A mapped website is not an HTTP website or domain.")
        return url.hostname.lower().removeprefix("www.")

    subjects = []
    person, company = value("person"), value("company")
    website = domain(value("company_website") if person else value("website"))
    if company or website:
        subjects.append(
            {
                "type": "organization",
                "name": company,
                "domain": website,
                "location": "properties." + mapping["company" if company else "website"],
                "role": "affiliation" if person else "subject",
            }
        )
    email = value("email")
    if person or email:
        subjects.append(
            {
                "type": "person",
                "name": person,
                "email": email,
                "location": "properties." + mapping["person" if person else "email"],
                "role": "subject",
            }
        )
    for key, kind, role in (
        ("companies", "organization", "subject"),
        ("attendees", "person", "participant"),
    ):
        subjects.extend(
            {"type": kind, "name": name, "location": "properties." + mapping[key], "role": role}
            for name in values(key)
            if name
        )
    if len(subjects) > 30:
        raise ImportProblem("More than 30 identity subjects; narrow this note's mapped properties.")
    return {"subjects": subjects, "heading": heading(body)}
