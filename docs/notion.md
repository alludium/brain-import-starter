# Importing Notion

The live reader fetches **only the page IDs you list**. It uses Notion's read-only page and
Markdown endpoints, API version `2026-03-11`, Markdown `v2`. It does not search your workspace.

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
```

Use raw UUIDs (with or without hyphens), not whole URLs. Every selected child page needs its own
entry; there is no automatic recursive expansion. A database row is a page, but this reader imports
its body and title only, not its database properties. Keep the namespace stable and unique to the
origin workspace within the firm's Notion sources. `fixture` belongs only in the offline example;
remove it to use the live API.

The reader preserves API-rendered Markdown and the page's original URL. It refuses truncated
results, unknown blocks, warnings and archived/empty pages before a plan is written. Resolve access
or narrow the page rather than claiming completeness. It retries transient GET failures up to
three times, respects Retry-After up to 60 seconds, and stops for longer waits. 401/403/404 need
configuration or access fixes; errors don't print API response bodies or tokens.

Attachments are references, not downloaded bytes; signed Notion file URLs may expire and may
change between reads. A changed rendered URL can therefore cause a new Brain version even if the
visible prose didn't change. Comments, meeting transcripts, page history, database properties and
child-page bodies are outside the example's coverage. Notion permissions are not copied into Brain.

For a richer adapter, add explicit page discovery/pagination and property mapping with tests.
Don't follow arbitrary embedded URLs with the Notion Authorization header.

References (checked 4 November 2026):

- [Read page metadata](https://developers.notion.com/reference/retrieve-a-page)
- [Read Markdown and incomplete-content behavior](https://developers.notion.com/reference/retrieve-page-markdown)
- [Request limits and retries](https://developers.notion.com/reference/request-limits)
