# Local Obsidian import wizard

The wizard runs on your computer. It reads only the vault you select and sends snapshots directly
through the Brain CLI. Your coding assistant can help install or customize it; routine imports
use the browser. It currently supports Obsidian. Notion and custom adapters use the CLI.

## Start

Install the Brain CLI as described in the README. From this repository, build once (Node 22.12+
required for building; Node is not required to run a wheel that already includes the UI):

```sh
npm ci --prefix ui
npm run build --prefix ui
uv sync --locked
uv run brain-import ui
```

A local browser window opens. Keep the session link private. The app listens on `127.0.0.1` only,
checks Host and Origin, and requires a random session key for every API request. It does not use
analytics, external fonts, a hosted upload service, or the assistant's conversation.

1. **Connect.** Check the workspace and person. If signed out, choose **Sign in through browser**.
   This uses `brain login`; it never automatically requests extra Keychain permissions.
2. **Select.** Pick a registered Obsidian vault, or enter its folder path, then load the folders.
   This reads filenames only. Select folders; subfolders are included. Hidden files, symlinks,
   non-Markdown files and your exclusion patterns are skipped. Nothing is selected initially.
3. **Map.** Choose general, company or person notes for a folder. Company/person profiles add a
   heading/filename name hint only when that type has no structured evidence. Properties remain
   stronger evidence. All files become document sources; no companies or people are created.
   Map custom property names and choose private, firm, specific people or an existing group.
4. **Dry run.** Python saves an exact local snapshot, verifies the signed-in identity and the
   server's preview capability, then calls `capture` with `dry_run=true`. This transmits the
   selected snapshot to Brain, but creates no sources, associations, review items or groups.
   Authentication/request logs may still be recorded. This is separate from offline `plan`.
5. **Review.** Search/filter notes and expand their evidence, candidate identities and reasons.
   Results show automatic matches, cases needing human review, and no active match. An unchanged
   import retains earlier human decisions. Existing audience or evidence conflicts stop the run.
6. **Import.** Tick the confirmation and import the full snapshot. Filters do not exclude records.
   The app rechecks identity, sharing and matches before writing. Changed results require another
   confirmation. The backend checks again during each write; concurrent changes can still alter
   matching or stop a run. There is no reservation or batch transaction.
7. **Follow through.** Completion shows created/versioned and unchanged counts. Resolve uncertain
   matches in Brain **Sources → Needs review**. Unmatched notes remain unlinked.

Changing any setting invalidates the UI confirmation. Source edits after preview do not change
the saved snapshot; run another dry run to include them. Keep the collection ID stable across
repeat imports; when moving from CLI configuration, reuse its exact namespace. Use a stable ID property before the first import if notes will be renamed.
For mixed property schemas, use separate selections or configure `source.folder_rules[].fields`
in code. Inline `Field:: value` properties are not parsed.

## Saved files and failures

`.local/ui/` contains private plan, settings, preview and receipt files (permissions 0600). Plans
contain original text. The app keeps the active preview in memory: restarting requires a new dry
run. To reuse saved settings from code, pass their JSON object into `Wizard.dry_run`, or translate
it into a normal TOML configuration. There is no automatic scheduler or deletion sync.

A partial import retains successful receipts and stops on the first failure. Inspect them before
creating a fresh preview. Stable source IDs make unchanged repeats reusable. Closing a browser
window does not cancel an import. Leave the terminal running until it finishes; Ctrl-C stops the
local server and can interrupt the current operation. A timed-out write may have succeeded.

An older Brain server is blocked by schema discovery **before any capture payload is sent**.
Do not remove `dry_run` or `preserve_audience` to work around that message. The matching-preview
backend must be released first. This repository cannot deploy it by itself.

## CLI preview and development

```sh
uv run brain-import preview .local/first.plan.json
```

`plan` and `inspect` remain offline with respect to Brain. `preview` needs sign-in and reads Brain;
`apply` writes. The browser uses the same plan, preview and apply modules.

Frontend: `ui/` (Vite, React, TypeScript). Python host: `local_ui.py`. CLI boundary: `brain.py`.
The built assets are included in CI wheels. CI runs Python tests, a production frontend build,
Chromium browser regression and a wheel asset smoke check. Browser fixtures are synthetic with
a stand-in transport; actual backend acceptance is reported separately.

For an isolated development backend, `--server http://127.0.0.1:PORT/mcp` is supported. Use `--viewer-url http://127.0.0.1:WEBPORT` when the local Brain viewer runs separately. A local
dev token supplied in `BRAIN_ACCESS_TOKEN` may have no OAuth workspace context; the importer
still checks exact firm/user IDs. Hosted connections always require their workspace context.
