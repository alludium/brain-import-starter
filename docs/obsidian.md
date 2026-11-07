# Importing Obsidian

Obsidian stores notes as local Markdown; no Obsidian plugin or account token is needed.
Use a vault you have permission to import. Configure `vault` (an absolute path, `~/...`, or a
path relative to the TOML file) and `vault_name` (for open links). Choose a stable namespace
unique to this vault within the firm's Obsidian sources. Keep it when moving the vault to a
new computer; use another namespace for a different vault.

`include` and `exclude` use Python fnmatch patterns on vault-relative, case-sensitive paths.
`*` matches slashes: `Research/*.md` includes nested research notes. For all Markdown, use
`["*.md", "*.markdown"]`; do not use `**/*.md` if you also want root files. Excludes win.
Hidden directories/files and symlinks within the vault are always skipped. Non-Markdown files
are outside this adapter's scope. Empty notes are skipped; non-UTF-8 and oversized notes stop
planning rather than being silently cut.

The note text is preserved, including line endings, frontmatter and wikilinks. Title comes from
the filename. Source identity is `obsidian` + `<namespace>:<vault-relative-path>`; editing text
keeps the identity, renaming/moving a note changes it. Brain may also deduplicate identical text.
An `obsidian://open` link preserves a way back to the original, usable on a device with that vault.

The starter sends explicit matching evidence from configured properties and headings. Brain
compares it with existing identities visible to the chosen audience. Body-only mentions do not
create links in this path. Name-only candidates and contradictory identifiers need review.
Check actual associations after a small trial: a successful capture alone does not prove correct
matching. The original text never needs to pass through an assistant conversation.

These records remain `document` sources, including Markdown files in a Meetings folder.
That does not automatically create a dated meeting interaction, extract new entities or facts,
or turn wikilinks into relationship edges. An adapter that needs those behaviors must explicitly
model them and test them against the current Brain tool schema.

This does not interpret wikilinks as Brain entity relationships, import `.canvas` files, resolve
transclusions, or copy attachments. Embedded images and file links stay as text references.
If you need original PDF/Office attachments, the existing CLI's `brain upload` is available;
choose and review that separate selection and namespace. Its file imports are additive snapshots,
which differ from this starter's versioned text capture. Neither path deletes missing originals.

See [Obsidian's vault documentation](https://docs.obsidian.md/Plugins/Vault) and
[attachment behavior](https://obsidian.md/help/attachments).

## Structured identity properties

The original YAML remains in the note. These default properties also become bounded matching
hints: `company`, `website`, `person`, `email`, `company_website`, `companies`, `attendees`.
A person note's `company_website` identifies their affiliation, never the person's identity.
Lists and quoted wikilinks such as `company: "[[Companies/Acme AI]]"` are supported. Arbitrary
inline `Field:: value` text stays prose; it is not parsed as a property. Headings nominate
candidates only. The first H1 outside fenced code and HTML comments is used; indentation of up to three spaces is supported. If there is no H1, the filename is the heading hint. UTF-8 BOMs are supported without removing them from the preserved original.

For custom field names add a table after the source settings:

```toml
[source.fields]
company = "Company"
website = "URL"
person = "Contact"
```

This maps exact property names; unmapped properties remain in the original only. Invalid YAML,
duplicate keys, anchors, non-text identity values and oversized fields stop planning. See
[matching and sharing](matching-and-sharing.md) for review, audiences and stable identity options.

Use the [synthetic acceptance sets](sample-acceptance.md) for broader local testing.

A parsing failure names the vault-relative file. Duplicate stable IDs name both offending files
without echoing the ID value, so you can correct the properties before planning again.
