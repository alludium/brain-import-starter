# Synthetic Obsidian acceptance

The original 11-note walkthrough is not a scale or diversity test. This suite generates separate
vaults and an independent answer key. All names, identifiers and text are fictional. It never
reads personal vaults. No CI test calls Brain or imports these notes.

## Generate locally

```sh
uv run python scripts/sample_data/generate.py --out /path/to/new/sample-directory
```

The output directory must not exist; generation refuses to overwrite work. Open Curated or Volume
as an Obsidian vault. The answer key and guide are outside both vaults so they are not imported.
The guide links every curated note to its expected outcome. Editable curated.toml and volume.toml
include stable IDs and all folder-specific mappings; replace their inert target with the isolated
Brain identity before a manual preview.

| Set | Content | Purpose |
| --- | --- | --- |
| Curated | 78 independently specified cases | Correct candidates, status, role, links and original text |
| Volume | 1,000 notes; 100 company and 40 person reference identities | Sustained preview/import/repeat and review UI |
| Failures | 15 separate selections | Actionable refusal before any import |

The complete reference catalog has 157 identities, including private canaries, shared names,
shared domains and Unicode names. The same-name people have separate full display names and a
shared alias; this makes their separate identities observable. Shared domains are attached only
after separate identities have been created. Fixture readiness checks reject accidental merges.

Curated cases include conflict between company/domain and person/email, known/unknown aliases,
heading-only clues, company/person/participant roles, mixed property conventions, unsupported
inline fields, long Markdown, tables, quoted instructions, attachments-as-references, BOM and
CRLF encoding, nested and Unicode paths, and hidden/empty/excluded/symlink controls.

Volume cases intentionally include 600 automatically matched notes, 200 pending notes and 200
with no active match. One hundred of the last group contain an explicit unknown subject; the
other hundred have no supported subject. Expected results are authored independently of the
matcher. They must not be regenerated from the actual response to make a run pass.

## Run against an isolated Brain

The developer acceptance runner uses the actual adapter, immutable plan, installed `brain` CLI,
MCP server and database. `scripts/sample_data/verify.py` provides its verification functions.
It requires explicit local-write opt-in and refuses non-loopback targets. Run from the Brain checkout's `evals/` directory after starting its local test services:

```sh
uv run python -m evals.import_samples --starter /path/to/brain-import-starter \
  --samples /path/to/sample-directory --out /path/to/new/private-results \
  --apply-local --keep-running
```

`VCBRAIN_EVALS_ADMIN_DSN` and `VCBRAIN_EVALS_S3_ENDPOINT` select the local backing services.
The command creates its own database, bucket and ports; Ctrl-C cleans only those resources.
Omit `--keep-running` for automatic cleanup. The explicit flag permits only synthetic writes to
that fresh local stack. Do not run two acceptance writers against the same stack: preview checks
compare table counts to detect unexpected writes.

A fresh isolated Brain stack supplies its exact firm/user, seeded record IDs and an independent database connection.
Credentials stay in the process environment and ignored local files, never in generated notes.

The runner verifies every preview against the manifest, checks that preview made no writes,
applies the reviewed digest, and independently reads back exact text, audience, provenance,
association statuses and links. An unchanged preview/reimport must reuse every source and grow
none of the checked tables. A separate lifecycle pass tests approve/reject/defer, audit attribution,
text revisions, stable-ID renames, four audiences with second-member readback, private identity
canaries, stale choices and retry after an injected interruption between actual writes.
Use `--skip-lifecycle` only when that separate pass is not needed. Failure fixtures are planned independently and must refuse before
Brain is contacted. Do not point these acceptance scripts at a personal or hosted workspace.

Per-folder custom mappings are in the manifest's folder_rules. Use those settings for the curated
set; default mappings deliberately cannot interpret every mixed-schema note. The UI retains
loaded folder-specific mappings and shows them explicitly, with an option to use global mappings.
Parents with no direct notes remain selectable; included descendants show their selected parent.

## Limits and evidence

See the dated run report for timings, fixes and actual outcomes. Generated scale notes repeat
controlled patterns; they do not establish universal matching accuracy. Jay's real conventions,
hosted OAuth, live Notion and attachment ingestion are separate acceptance work. Name-only cases
remain reviewable even when an exact email/domain narrows a shared name: the current conservative
policy does not silently decide that the ambiguity has disappeared.
