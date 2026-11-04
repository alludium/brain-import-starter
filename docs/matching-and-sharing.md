# Matching and sharing

The adapters keep the original Markdown and emit a separate, typed `matching` object. Obsidian
YAML and configured Notion properties are evidence, never instructions or sharing settings.
The backend compares these fields with identities visible to the source's audience:

- One exact company domain or person email, with no conflicting name, can link automatically.
- Names or headings alone, several candidates and conflicting identifiers wait in **Sources →
  Needs review**. The same review is reachable from a company or person's Sources tab.
- Body mentions, including competitors, do not create subject links in this import path.
- No candidate means the source remains unlinked. The importer does not create entities or aliases.

The reviewer sees the evidence and candidates, then confirms, rejects, defers or undoes a match.
Decisions are audited and bound to the source revision and review version. An edit gets a new
review; replaying unchanged input cannot override a rejection. Reviewing never shares a source.
The backend makes no AI calls for these matches and does not invent percentage confidence.

## Preview before importing

The [local Obsidian wizard](local-ui.md), or `brain-import preview PLAN`, asks the same backend
matcher for candidates without storing sources or decisions. It shows new/revision/unchanged,
automatic/pending/unmatched evidence, and retains prior human decisions on unchanged notes.
Unresolved subjects can be confirmed, left unlinked or deferred in the wizard before import.
Search another existing identity of the same type if the suggested candidates are wrong. Search
respects the selected audience. Your choices are saved in `import_review` in the exact plan, with
a backend snapshot digest; apply checks the snapshot, then stores the source and decisions in
one transaction. Stale choices fail rather than overriding a concurrent reviewer. They do not
teach aliases or affect future revisions. Untouched/deferred subjects stay in Sources review.
This contacts Brain; offline `plan`/`inspect` do not. Preview is a point-in-time result, not a lock.

## Choose an audience in the configuration

At the top of the TOML file, before `[target]` or `[source]`, choose one:

```toml
scope = "private" # default: only the importing person
```

```toml
scope = "firm" # everyone in the selected Brain workspace; never the public internet
```

```toml
scope = "group"
group = "Research team" # an existing group you belong to
```

```toml
scope = "people"
people = ["alice@example.test", "bob@example.test"] # existing firm members
```

Use separate configurations for folders/page selections with different audiences. `inspect` shows
the planned audience and matching fields. Protect plan files: they contain the original documents.
No source field can change these permissions. Notion page access is not permission to reshare it.

Every generated capture sets `preserve_audience = true`. If an earlier record has a different
audience, the server refuses the call atomically. Use Brain Share explicitly first, then rebuild
and review the plan. Membership changes still affect who can read a group source. This starter
does not synchronize provider permissions, deletions or moves.

## Server compatibility

Before applying, inspect `brain tools`: capture must accept `matching` and `preserve_audience`,
and configure must accept `source_review`. These features require the matching-review backend
release; until deployed, planning and offline tests work but live apply will be refused. Do not
remove safety fields to bypass an older server. Update the CLI/server and rebuild old plans.

Existing captures made without matching review cannot be retrofitted by replaying identical text.
A real source edit creates a new snapshot with the evidence. Changing only Notion properties or
mapping rules while leaving the Markdown unchanged is also refused: review the mismatch locally;
do not add artificial text to force a new version. Metadata-only versioning remains a future extension.

## Stable identities

Obsidian uses the namespace plus vault-relative path by default. To preserve identity across
renames, set `source.identity_property = "brain_id"` before the first import, and put a unique,
stable text value in each selected note's YAML. Missing or duplicate IDs stop planning. Changing
this setting for an already imported collection changes its identity and can duplicate records;
migrate deliberately. The source's saved URL/title may retain the old path until its text changes.
Notion uses its stable page ID. No rename deletes an earlier source.
