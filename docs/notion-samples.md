# A synthetic Notion research lab

Generate a small, reproducible dataset before connecting a real workspace:

```sh
uv sync --locked
uv run python -m scripts.notion_samples.generate --out .local/notion-lab
uv run python -m scripts.notion_samples.probe .local/notion-lab
uv run brain-import plan .local/notion-lab/companies.toml --out .local/companies.plan.json
uv run brain-import plan .local/notion-lab/leads.toml --out .local/leads.plan.json
uv run brain-import plan .local/notion-lab/theses.toml --out .local/theses.plan.json
```

Run from the repository root. Choose a new output directory for each generation; existing files
are never overwritten. The target is deliberately an unused local port and synthetic account IDs.
These commands need no authentication and make no Brain calls. Do not apply these plans to a real
workspace. A matching preview would require a separately configured synthetic Brain and records.

## What is included

| Database | Rows | Shapes and cases |
| --- | ---: | --- |
| Discovery Pipeline | 20 | Company title, website, action/status, track, headquarters, analyst notes, deal fit, aliases and thesis memberships |
| Theses | 6 | Bear case, best-company text, market domain, old/new conviction, engine status, research tables and linked lead summaries |
| Thesis Hunt Leads | 12 | Both person and company leads; email, company relation, thesis relations, lead score/tier, reachable/starting-company unknowns |

Bodies contain callouts, question/answer/points/evidence tables, collapsible detail, research prose,
citation links and change-of-mind triggers. Thesis lead tables contain page mentions as well as
separate structured relationships. All names, research claims and evidence URLs are fictional;
`.test` links intentionally do not resolve. No screenshots or customer records belong in this repo.

The generator produces `catalog.json` (all records and relations), `pages.json` (API-shaped snapshots),
three CSVs and three runnable TOMLs. CSVs omit bodies and relations; they are inspection aids, not
lossless Notion exports. Deterministic fixture UUIDs do not identify live pages. For live provisioning,
allocate real page IDs and rewrite both relations and page mentions; never send fixture UUIDs as
live targets. The schema is a testing choice informed by observed layouts, not a verified copy of
someone else's underlying database schema.

## What the probe proves

The probe uses the actual adapter and plan builder. It now plans **all 38 records**, including the
two property-only pages. It verifies original Markdown within each snapshot, typed property values,
relations, private scope, stable source identity across a rename, and detection of score/status and
relation-only edits. Directly mapping a relation as a company name still refuses unsafe guessing.

Offline fixtures do not establish live provider authentication or Brain persistence. The separate
`live_probe.py` verifies captured host-MCP fetches against the independently maintained synthetic
catalog, including two live property edits. It labels missing REST property IDs and keeps the
transport explicit. Local captures and live IDs stay in ignored `.local/`, never in Git.

`acceptance.py` additionally exercises the installed CLI and a fresh isolated Brain stack, verifies
stored text, provenance and private audience, proves preview makes no writes, checks unchanged
repeat imports do not grow tables, and checks metadata-only edits create linked revisions. Run it
with the Brain eval environment and both checkout roots on PYTHONPATH; `--apply-local` is required.
It generates unique local database/bucket names and cleans those resources on completion. This is
an operator acceptance script, not a customer installation dependency. See the dated results below.

This small lab is not exhaustive or a load test. Complex formula/rollup results, source ACL changes,
live REST authentication and end-to-end origination-list creation remain separate acceptance work.

## Observed acceptance — 5 November 2026

A private personal Notion workspace was populated with all 38 fictional records across three
databases. Queries returned 20 companies, 6 theses and 12 leads with no remaining result pages.
Read-back checked every expected property and relationship against the synthetic catalog. Rich
bodies, native page mentions and both empty-body records were included. A score/status edit and
a thesis-relation edit were made, fetched, tested and restored in Notion.

Those captured live MCP responses then ran through the actual importer and installed Brain CLI
against a fresh local Brain backend. Independent database reads confirmed:

- All 38 source documents stored exactly, with original URLs/external IDs and private audiences.
- Preview changed no source, association, association-event, link or entity counts.
- An unchanged repeat reused all 38 source IDs without increasing those table counts.
- The two property-only edits created revisions linked to their respective original sources.
- The isolated database and bucket were removed after the successful run.

The importer suite passed 89 tests; lint, formatting and distribution builds passed. An initial
local backend startup failed in an Intel Python cryptography library on Apple Silicon; the
successful acceptance used an isolated native Python 3.12 environment and locked Brain dependencies.
No security code was bypassed or changed. Python 3.14 also exposed an unrelated Brain annotation
compatibility error; use the tested Python 3.12 runtime for this operator check.

This proves live host-MCP retrieval and local Brain persistence. It does not prove standalone
Notion REST authentication, hosted Brain acceptance, or automatic entity/list-membership creation.
Live page IDs, source exports and detailed receipts remain outside Git in the operator's ignored
local evidence directory. No real customer rows were used.

## Expected identity behavior

These are review expectations for a later matching run, not assertions of observed Brain results.

| Cases | Expected behavior |
| --- | --- |
| C001/C002 | Match only when the target contains independently verified company identifiers |
| C003, L011 | Conflicting name and website/email require review, regardless of lead score |
| C005/C006 | Shared alias must not merge distinct companies |
| C007/C008 | Parent and subsidiary sharing a domain require disambiguation |
| L003/L004 | Same name, different email: retain separate people |
| L007 | A person without a company stays a person; do not invent an employer |
| L009/L010 | Company leads reference pipeline companies, without creating duplicate identities |
| C017/L001 | One identity can retain membership in multiple theses |
| C015/C016 | Unknown score and numeric zero remain distinct |
| C018 | Source-reported outreach remains a claim; no message is sent |
| C020 | Quoted instructions remain inert source text |

Typed properties and page bodies are now preserved separately within the source snapshot. The next
product step is mapping explicit selections and relationships into reviewed Brain identities and
list memberships. Keep source scores separate from identity confidence.
Do not fabricate body edits to force metadata updates, execute source buttons, auto-promote Deals,
or infer sharing from the source. See [Notion setup](notion.md) and
[matching and sharing](matching-and-sharing.md).
