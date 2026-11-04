# Installation and live Obsidian trial — 4 November 2026

This used a fresh clone on macOS 15.6.1 and the hosted Northwind Ventures test workspace.
All imported content was synthetic. Existing personal vaults were left untouched. Private
receipts, account IDs and OAuth material are not included in this repository.

## Installation findings

The locked install, both offline Obsidian/Notion planning examples, inspect and package build
worked. The public Brain CLI wheel was downloaded with its release checksum verified. A default
Intel Python 3.12 environment on Apple Silicon failed loading cryptography before CLI startup.
Using native Python 3.14 worked with the same current cryptography dependency; no downgrade
was needed.

The user observed unexpected macOS Keychain prompts during initial sign-in. A separate CLI fix
now prevents approval dialogs by default, explains credential storage, caches credential reads,
and requires explicit login opt-in if macOS approval is necessary. This trial used that local
CLI development build, not an assertion that the public wheel already contains the fix.
Intentional browser login then succeeded and `identity` confirmed the test workspace.

Importer diagnostics now distinguish missing executable, process-start failure, timeout and
recognized sign-in/Keychain errors. Raw stderr stays withheld because it can contain private data.

## Authenticated Obsidian trial

A third local vault, **Northwind Brain Import Trial**, was created and opened in Obsidian. Six
notes were selected: Acme AI and Kestrel Data research, Maya Lindqvist and Henrik Vos contact
notes, an Acme walkthrough, and an intentionally unidentified Acme/Dev scrap. Welcome, template
and archive files were excluded. Names were checked against existing Northwind records first.

The first live apply exposed a compatibility bug: account verification succeeded, but capture
failed because the starter dropped the `workspace_context` returned by `configure(account={})`.
The importer now starts a fresh context for each identity check and carries it to subsequent CLI
calls. The context stays in memory, outside saved plans. Account mismatch still stops the import.

| Check | Live result |
| --- | --- |
| Selected source intake | Six notes captured, private, without warnings |
| Text and provenance | Readback matched full Markdown, source IDs and Obsidian URLs |
| Existing company/person links | Correct existing records linked for both companies and people |
| Unchanged repeat | All six sources reused; no new versions |
| Two edited notes | Two new versions pointed to their predecessors; four others reused |
| Full extraction | No structure jobs; Markdown is captured as `document` |
| Overmatching | Failed: ordinary “demo” linked to a person named Demo |
| Unidentified company | Failed: “Acme” alone linked to Acme AI despite the deliberately unresolved context |

Brain performs deterministic known-name mention matching on this capture path. It does not
require the assistant to read or rewrite source text. That is useful, but a mention link is not
proof of contextual identity resolution. The ambiguous Dev mention was not linked. Both Acme AI
and Acme Robotics GmbH existed in the test workspace; the unresolved scrap still selected Acme AI.

The initial unresolved fixture included both full company names in its explanation, which
legitimately created mention links and made it an unsuitable abstention test. It was revised to
only the short Acme/Dev wording, then re-imported as a new version. The overmatch above is from
that revised fixture. Earlier private versions remain as test history.

The notebook imports as documents even when a folder is called Meetings. This does not establish
meeting timestamps/attendees, extract new facts, resolve attachment contents, or infer relationship
edges from wikilinks. Existing known-name links and full structured extraction are distinct paths.

## Validation and remaining work

38 automated tests pass, including context propagation across CLI subprocesses, discarding a stale
context, missing-context rejection, identity mismatch, source selection, version behavior and error
redaction. Lint, formatting and source/wheel builds pass. Local unit tests and hosted readback are
separate evidence.

The next matching work should cover common-word person names and short company aliases with
multiple plausible interpretations. Do not claim the test establishes general matching accuracy.
The starter fix does not change Brain's resolver.

Live Notion remains untested. The assistant's Notion connection was available, but the standalone
importer had no `NOTION_TOKEN`; it needs its own read-content API connection and selected page IDs.
No personal notes or live Notion page bodies were imported. Manual vault discovery and target-ID
configuration remain setup friction; improve them based on this small working flow.
