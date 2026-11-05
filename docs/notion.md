# Importing Notion

The live reader fetches **only the page IDs you list**. It uses Notion's read-only page and
Markdown endpoints, API version `2026-03-11`, Markdown `v2`. It does not search your workspace.

An existing Notion connection in Claude, Codex or ChatGPT does not authenticate this script.
You do not need to reconnect that assistant: configure a separate API connection for this importer.

Create a Notion connection with read-content capability and grant it access to the selected pages.
Store its secret in `NOTION_TOKEN` locally using your shell or secret manager; never paste it into
chat or commit it. Copy config.example.toml to config.local.toml and replace its source section:

```toml
[source]
type = "notion"
namespace = "my-notion-workspace"
page_ids = ["00000000-0000-4000-8000-000000000001"] # Replace with your page's UUID.
token_env = "NOTION_TOKEN"
max_text_bytes = 500000
content_mode = "snapshot" # Default: properties, relations and original Markdown together.
```

Use raw UUIDs (with or without hyphens), not whole URLs. Every selected child page needs its own
entry; there is no automatic recursive expansion. A database row is a page, but this reader imports
a versioned source snapshot containing its original Markdown and typed properties. Configured
identity properties remain separate matching evidence. Keep the namespace stable and unique to the
origin workspace within the firm's Notion sources. `fixture` belongs only in the offline example;
remove it to use the live API.

The reader preserves API-rendered Markdown and the page's original URL. It refuses truncated
results, unknown blocks, warnings and archived pages before a plan is written. Resolve access
or narrow the page rather than claiming completeness. It retries transient GET failures up to
three times, respects Retry-After up to 60 seconds, and stops for longer waits. 401/403/404 need
configuration or access fixes; errors don't print API response bodies or tokens.

Attachments are references, not downloaded bytes; signed Notion file URLs may expire and may
change between reads. A changed rendered URL can therefore cause a new Brain version even if the
visible prose didn't change. Comments, meeting transcripts, page history and child-page bodies
are outside the example's coverage. Notion permissions are not copied into Brain.

The reader completes paginated relation/title/rich-text/people properties and refuses incomplete
rollups. It does not crawl database views or fetch related pages automatically.
Don't follow arbitrary embedded URLs with the Notion Authorization header.

References (checked 4 November 2026):

- [Read page metadata](https://developers.notion.com/reference/retrieve-a-page)
- [Read Markdown and incomplete-content behavior](https://developers.notion.com/reference/retrieve-page-markdown)
- [Request limits and retries](https://developers.notion.com/reference/request-limits)

## Identity properties

Use `[source.fields]` as in the Obsidian guide, for example `company = "Company"` and
`website = "Website"`. Supported mapped values are title/rich text, URL, email, select and
multi-select. Unsupported mapped types are refused rather than guessed. Relation and people
properties are not expanded into remote records. The page title supplies a heading hint; original
Markdown is unchanged. [Matching and sharing](matching-and-sharing.md) explains review and the
Obsidian limitation on property-only changes. Notion snapshots include property values, so those
changes now produce source revisions without rewriting the Markdown.

## Research databases and origination lists

Try the [38-record synthetic research lab](notion-samples.md) for richer company, thesis and
person/company-lead examples. Its probe checks all 38 records, including property-only pages, scores, statuses and relation IDs.
These are preserved as source evidence; they do not automatically become Brain entities,
relationships or origination-list memberships.

## Snapshot format and repeat imports

The default `snapshot` mode stores deterministic JSON text with format `notion-source-v1`:
page identity, original URL, parent, named typed properties (including stable property IDs when
provided), and the untouched API-rendered Markdown in `markdown`. JSON decoding restores the
original body exactly, including whitespace and Unicode. Unknown values remain null; zero remains
zero. Scores and workflow statuses never become matching confidence, permissions or commands.

This complete record is the source document sent through the existing Brain CLI capture contract.
A score-only or relation-only edit changes that record and creates a source revision. It is not a
fabricated edit to the note body. Reordered property keys/relation sets and top-level provider edit
timestamps do not change the snapshot. Page IDs and the namespace remain stable across renames.
Property names are retained alongside IDs; configured identity mappings currently use names, so
update a mapping when its property is renamed.

Existing Markdown-only imports will receive one new revision when switched to snapshots, under
the same external source identity. Review this in preview before applying. `content_mode = "markdown"` retains
the former behavior, including refusal of empty pages and omission of unmapped properties. Old
saved plans are unchanged; never replay them out of order. The text size limit covers the entire
snapshot, not just the body.

Relations preserve referenced Notion page IDs, not verified Brain identity assertions. Access to a
relation target must be granted separately; Notion can hide inaccessible relationships. A source
relation must not be treated as a complete graph of records outside the connection's access.
A relation still cannot be mapped directly to a company name: select text identity fields or add
an explicit, reviewed resolution step. No automatic record creation, list population or ACL sync.

The live lab can also be read through the connected host's MCP tools, with results kept in code
and saved locally. `scripts/notion_samples/live_probe.py` is a bounded test bridge for those captured
lab responses, not a general MCP login implementation. It records the transport and unavailable
property IDs. It does not prove that standalone `NOTION_TOKEN` authentication has been exercised.
Do not switch transports between repeat imports without reviewing the resulting snapshot changes.

References for structured properties (checked 5 November 2026):

- [Typed property values and stable IDs](https://developers.notion.com/reference/page-property-values)
- [Complete paginated properties](https://developers.notion.com/reference/retrieve-a-page-property)
