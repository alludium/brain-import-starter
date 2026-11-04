# Brain import starter

**Your sources → a small Python script → your firm's Brain.**

This repository is private; you need access granted by Alludium before cloning or using the template.
Once you have access, clone it, understand it and change it with Claude Code or Codex.
Read an Obsidian vault or selected Notion pages, review a local plan, then import
through the [Alludium Brain CLI](https://github.com/alludium/brain-plugin#alludium-brain-cli).
Source text travels from your script to Brain without passing through an assistant's conversation.
Brain's normal processing, permissions and usage charges still apply.

This is deliberately a few ordinary Python modules. No connector framework, background service,
or separate Brain authentication to maintain.

## Import Obsidian through a local UI

Build once with `npm ci --prefix ui && npm run build --prefix ui`, then run
`uv run brain-import ui`. Choose your vault and folders, map properties, set sharing and run a
no-write matching preview before confirming the import. See the [wizard guide](docs/local-ui.md).
The backend must advertise `capture.dry_run`; older servers are blocked before sending notes.

## Try it in two minutes

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.12+.
No account, token or Brain CLI is needed for these synthetic examples.

```sh
git clone https://github.com/alludium/brain-import-starter.git
cd brain-import-starter
uv sync --locked
uv run brain-import plan examples/obsidian.toml --out .local/obsidian.plan.json
uv run brain-import plan examples/notion.toml --out .local/notion.plan.json
uv run brain-import inspect .local/obsidian.plan.json
```

The output lists selected records, their scope and hashes. The `.local/` plans contain the original
text, so treat them as private source copies. Planning reads sources but makes **no Brain calls**. The separate `preview` command and UI dry run contact Brain without importing.
The Notion example reads synthetic API responses; the live adapter uses the same conversion.
Outputs are never overwritten: choose a new filename for a new plan or run.

## Make it yours

Use GitHub's **Use this template** to create your own private repository, or clone this one.
Open the folder in Claude Code or Codex and start with:

> Read AGENTS.md and the source guide. Help me configure a small, private import from my
> Obsidian vault / selected Notion pages. Keep source contents out of this conversation.
> Make a local plan and explain its coverage and omissions before applying anything.

1. Install the CLI wheel from [Brain downloads](https://github.com/alludium/brain-plugin/tree/main/downloads)
   with `uv tool install ./alludium_brain_cli-<version>-py3-none-any.whl`.
   This starter requires CLI **0.29.100 or later** and the `capture` and `configure(account={})` tools.
2. Run `brain --version` to check that the CLI starts, then `brain login` and `uv run brain-import identity`. Check the workspace and person.
   Put its exact `firm_id` and `user_id` in your configuration.
3. Copy `config.example.toml` to `config.local.toml`. Follow the
   [Obsidian](docs/obsidian.md) or [Notion](docs/notion.md) guide to select your sources.
4. Create and inspect a small plan:

   ```sh
   uv run brain-import plan config.local.toml --out .local/first.plan.json
   uv run brain-import inspect .local/first.plan.json
   ```

5. Review the selection and original text locally, then use the printed `sha256`:

   ```sh
   uv run brain-import apply .local/first.plan.json --confirm <sha256> --receipts .local/first.receipts.jsonl
   ```

The digest binds approval to the exact saved plan, including the target and sharing scope.
Changing a source after planning doesn't change what gets sent. `apply` checks your signed-in
Brain account against the plan and stops on the first failure or server warning. It never logs
raw tool responses. Receipts identify stored sources, versions, scope and any background job.
If a receipt includes `structure_job_id`, check it with `brain jobs <id>` before calling processing
complete. Inspect imported sources in Brain before expanding the selection.

On failure, fix the problem and rerun the same plan with a **new receipt filename**. Brain normally
reuses unchanged records and versions changed text under a stable source ID. This is not a
transaction: earlier successful records remain stored. A timeout may occur after a successful
write; retrying recovers through the same source identity. Don't run concurrent imports for the
same source, change accounts mid-run, or replay old plans after newer versions have been imported.

## If the first run fails

- **`brain` is missing:** it is a separate tool, not installed by `uv sync`. Install the downloaded
  wheel, ensure the uv tool directory is on PATH, then check `brain --version` in the same terminal.
- **`brain --version` crashes:** this is an installation problem, before authentication. On a Mac
  with both Intel and Apple Silicon Python installations, select a native Python 3.12+ explicitly:
  `uv tool install --force --python /path/to/native/python /path/to/the/downloaded.whl`.
  Verify the chosen interpreter with `python -c 'import platform; print(platform.machine())'`.
  Do not work around certificate or authentication checks.
- **Version works but identity fails:** run `brain login` yourself and complete browser sign-in,
  then retry `uv run brain-import identity`. The importer suppresses raw CLI errors because they
  may contain source text or credentials.
- **Notion works in your assistant but not here:** the assistant's Notion connection is separate.
  The standalone importer needs its own read-content connection, access to the selected pages and
  a local `NOTION_TOKEN`. See [Notion setup](docs/notion.md); do not copy assistant OAuth credentials.

## What you get

| Source | Included | Deliberate boundary |
| --- | --- | --- |
| Obsidian | Selected UTF-8 Markdown, original frontmatter and wikilinks, vault-relative IDs, open-in-Obsidian links | Typed property evidence and heading review; no attachment bytes, Canvas or graph reconstruction |
| Notion | Explicit page IDs, original API Markdown, title, stable IDs and Notion URLs | No workspace crawl, database property export, child-page traversal, comments, attachment download or meeting transcripts |

Imports default to **private**; firm, selected people and existing groups are explicit choices.
See [matching and sharing](docs/matching-and-sharing.md). Source permissions are not
mirrored. Existing versions retain their earlier audience: changing config is not a sharing
operation. A returned scope mismatch stops the run for review. Deleted source files stay in
Brain; renaming an Obsidian file changes its identity unless configured with a stable property. See [source behavior](docs/architecture.md).

## Extend it

```text
src/brain_import/
  adapters/obsidian.py   Local Markdown → Records
  adapters/notion.py     Notion API → Records
  model.py              Record: text, title, source identity, URL
  plans.py              Configuration, validation, local snapshots
  brain.py              The only subprocess boundary to the Brain CLI
  main.py               Plan, inspect, apply and receipts
```

Start with [adding a source](docs/extending.md), including a CRM mapping example and a short
list of useful next adapters. Keep source-specific fetching and normalization in one adapter;
leave authentication, plan review and receipts in the shared path.

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
```

GitHub Actions tests Python 3.12 and 3.14, runs both offline examples, and builds and smoke-tests
the wheel. No credentials or real source data are used in CI. Live Notion reads and authenticated
Brain imports need your own scoped acceptance run; automated tests are not evidence of those.

[MIT licensed](LICENSE). Start small, then make it fit how your firm works.

Structured imports require the matching-review backend release. Check the tool fields described
in [matching and sharing](docs/matching-and-sharing.md) before live apply. Offline examples do not
require a Brain connection.
