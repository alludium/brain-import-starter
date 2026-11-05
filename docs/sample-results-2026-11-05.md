# Synthetic Obsidian acceptance — 5 November 2026

**Passed:** 78 curated cases, 1,000 volume notes and 15 isolated failure selections through the
actual importer, installed CLI and an isolated local Northwind Brain. Expected candidates/statuses
were authored independently of the matcher. No personal vault or hosted workspace was imported.

## Results

| Set | Preview | First import | Unchanged preview + repeat import |
| --- | ---: | ---: | ---: |
| Curated, 78 notes | 5.49 s | 4.70 s | 7.99 s; 0 new sources |
| Volume, 1,000 notes | 34.43 s | 38.71 s | 56.17 s; 0 new sources |

Both previews made no writes. Every original text, private audience, external ID, original URL,
link and association status passed independent database readback. Repeats reused every source ID
and grew none of the checked tables. All 15 failure selections refused during planning.

Curated produced 34 automatic, 40 pending and 7 unmatched **subjects** across 78 notes. The UI
shows 30 matched notes, 34 needing review and 14 without an active match. Volume produced exactly
600 matched notes, 200 pending and 200 without an active match: 100 explicit unknown subjects and
100 notes without a supported subject. The reference catalog contained 157 distinct identities.

The lifecycle pass also passed:

- Approve/reject/defer, actor attribution, unchanged decision retention and review after a text revision.
- Search for an existing identity to resolve an initially unmatched subject.
- Stable-ID rename without duplication; refused audience changes with no partial writes.
- Private, firm, people and group scopes, second-member HTTP readback and access revoked on group removal.
- A private identity absent from firm preview/search candidates and refused for firm approval.
- Changed candidates invalidating an earlier choice, with no partial write.
- An injected interruption between actual writes, followed by retry with the first receipt/source reused.

## What broke and changed

BOMs hid valid YAML properties. Code-block headings became subjects, while indented H1s were
missed. Parsing errors omitted the filename; duplicate stable IDs now identify both files.
The UI lost loaded folder mappings/nested rules on repeat dry runs, omitted parents without
direct notes, and did not clearly show inherited child selections. These are fixed with regressions.

The scale trial also exposed CLI process/connection startup dominating matching. The sequential
native run took about 0.66 seconds per previewed note while Brain calls were around 25 ms.
Optional `brain call --jsonl` now reuses one connection. The importer sends one record at a time,
checks each receipt before sending the next, and stops on error. Older CLIs retain the existing
single-call path. No matching, audience or review gate was relaxed; there is no automatic retry.

## Browser and package evidence

The real 78-note browser dry run matched the answer key. Malformed YAML named its file; changing
to a valid custom-mapped selection recovered without writes. The actual saved 1,000-note preview
rendered all rows, filtered to 200 pending notes and searched to one case. Observed initial render
was 522 ms and filtering 192 ms. Desktop and 390px screenshots had no horizontal overflow.
The 1,000-note display check loaded the real saved preview; it did not perform another import.
An imported conflict note and its pending review were also opened in Brain Sources.

Validation: 76 importer tests, 30 CLI tests (including real MCP transport), lint/format,
TypeScript/Vite build, browser regression with accessibility checks, and wheel contents passed.
The normal distribution builder produced the plugin ZIP and version-stamped CLI; manifest,
allowlist and checksum verification passed. No public publication or hosted deployment was performed.
The installed acceptance CLI was the locally built development wheel, version 0.1.0.

## Environment and limits

Earlier attempts are retained separately. The shared Docker VM became overloaded; it killed the
test S3 container with OOM/137 and database calls reached 30 seconds. The completed run used
isolated native PostgreSQL 17/pgvector and SeaweedFS 4.51 on loopback. A relative output-path bug
in the acceptance harness was fixed before the completed run. Timings describe this local run,
not a production throughput guarantee.

These patterns establish a stronger regression baseline, not universal identity accuracy.
Jay's real conventions, hosted OAuth, live Notion, native plugin installation, attachment ingestion
and cross-platform behavior need their own acceptance. Renames preserve identity but can retain
an old source title/URL until text changes. Sources currently uses terser explanations than the
importer; identical wording across both interfaces was not established.

Reproduce using [the sample guide](sample-acceptance.md). Raw plans, receipts and reports remain
private local artifacts. Implementation: [starter PR 2](https://github.com/alludium/brain-import-starter/pull/2)
and [Brain PR 587](https://github.com/alludium/vc-brain/pull/587).
