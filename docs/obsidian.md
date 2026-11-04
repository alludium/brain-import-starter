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

Brain can attach imported documents to existing companies and people by matching known names,
aliases and email addresses in the text. The importer does not need to send note bodies through
the assistant to do this. Check the saved source's `entities` and the entity brief after a small
trial: a successful capture alone does not prove correct matching. Short or common names need
particular care; matching is not a guarantee that every mention was understood in context.

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
