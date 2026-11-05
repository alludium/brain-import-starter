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

## What the probe proves—and exposes

The probe uses the actual adapter and plan builder, not an alternative mock importer. It checks
exact original text, private scope and page identity after a title rename. It currently plans **36
of 38 rows**: 19 companies, 11 leads and 6 theses. The two property-only records are explicitly
excluded from the compatible TOMLs and separately tested for rejection. This exclusion is not a
recommended real-world workaround.

Current gaps are deliberately visible in its output:

- An empty page body is refused even when useful properties exist (C011 and L012).
- A score/status-only edit produces an identical imported record: the values are lost.
- A thesis-membership-only edit also produces an identical record.
- Mapping a company relation directly as company identity is refused.

This is page-import coverage, **not** authenticated Notion, Brain matching or origination-list
acceptance. Tests pin these observations so a future structured adapter must replace them with
positive preservation assertions. They do not certify all Notion cases. Pagination, revoked access,
API limits, interrupted runs, formula/rollup results, schema renames and real permission behavior
still need provider-level tests. The lab is intentionally small; it is not a load test.

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

The next implementation step is to preserve raw typed properties and page bodies separately,
including property-only revisions, then map explicit selections and relationships into reviewed
Brain identities and list memberships. Keep source scores separate from identity confidence.
Do not fabricate body edits to force metadata updates, execute source buttons, auto-promote Deals,
or infer sharing from the source. See [Notion setup](notion.md) and
[matching and sharing](matching-and-sharing.md).
