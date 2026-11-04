# Add your next source

Start with a reader you can test on three synthetic records. You don't need a framework.

1. Create `src/brain_import/adapters/<source>.py` with `records(config, base)` yielding `Record`.
2. Add it to `ADAPTERS` in plans.py. Keep authentication and provider pagination in the adapter.
3. Add a synthetic fixture, example TOML, tests and a guide describing coverage and omissions.
4. Run the offline plan first; review the target, audience and mapping before real writes.

## A CRM mapping, without guessing identity

```python
from brain_import.model import Record


def crm_record(row, namespace):
    # row is normalized by YOUR CRM's reader; check required fields there.
    return Record(
        system="custom-crm",
        external_id=f"{namespace}:company:{row['id']}",
        title=row["name"],
        text=row["original_description"],
        url=row["record_url"],
        kind="external_record",
    )
```

This illustrative function is not a third supported importer. The provider ID identifies the
source record, not a Brain company. Do not match companies solely by name or fabricate source URLs.
Use stable account/list namespaces and provider record IDs, never titles or row numbers. Prefix
record kinds so company `42` and person `42` cannot collide. Don't reuse reserved Brain connector
systems (`google_drive`, `sharepoint`, etc.) or impersonate a built-in CRM integration.

Keep prose intact. If your source is structured fields, decide with the user which fields matter,
then render them deterministically with explicit labels. Keep notes separate with their own IDs;
don't collapse every contact and meeting into a lossy company summary. A provider timestamp for
'last edited' is not the date of a meeting. Adding dates or entities requires updating the small
plan allowlist, mapping documentation, tests and live schema compatibility deliberately.

## Useful next sources

| Source | Practical starting point | What to settle first |
| --- | --- | --- |
| CRM CSV/JSON exports | Explicit export, stable record ID column, one record per row | Person/company/note IDs, field mapping, duplicates, audience |
| Attio / HubSpot / other CRM APIs | Read-only selected list with pagination | API scope, rate limits, note authorship, field semantics; prefer Brain's built-in import when it fits |
| Markdown folders / Logseq | Adapt the Obsidian file reader | Block IDs, transclusions, attachments and path stability |
| Confluence / internal wiki | Selected space/page IDs, body-to-text conversion | Pagination, child pages, table loss and page permissions |
| Google Drive / SharePoint | Prefer Brain's existing drive connections | Avoid a second overlapping source identity and permission path |
| Meeting exports / email archives | Explicit local export, stable meeting/message IDs | Participants, dates, private audiences and quoted-history handling; needs richer capture mapping |

For provider pagination, test multiple pages, an empty page with a cursor, duplicate results and a
midstream failure. Partial fetches must not produce a 'complete' plan. Respect rate limits and retry
only safe reads. Avoid fetching arbitrary attachment URLs or propagating provider credentials.

Minimum regression cases: repeated input, edited text with unchanged source ID, duplicate IDs,
empty selection, oversized content, inaccessible content, non-ASCII text, wrong Brain identity,
partial apply and private error messages. Use HTTP mocks and a fake CLI, never production writes.

After the user approves scheduling, run the same plan/apply flow from their scheduler with a stable
selection and target. Decide how new records get reviewed first; don't bypass review simply by
having a scheduled script compute its own approval digest. Keep scheduling in the user's deployment,
not as a daemon added to this starter.
