# First installation trial — 4 November 2026

This was a fresh clone on macOS 15.6.1, not a test using the original developer checkout.
No real source contents or credentials are included here.

## What ran

- Locked install, both synthetic Obsidian/Notion planning examples, inspect, lint, formatting and
  wheel/source build worked. The original 31 tests passed; diagnostic improvements bring this to 36.
- Local Obsidian installation and registered vaults were discovered without reading note bodies.
  Selection of the real vault is still pending, so no live-note plan or import has run.
- The assistant's Notion connection was available. The standalone importer had no configured
  `NOTION_TOKEN`; this is a distinct authentication path. No live Notion API page import ran.
- The public Brain CLI wheel was downloaded with its release checksum verified. A default Intel
  Python 3.12 environment on Apple Silicon failed loading cryptography before CLI startup.
  Installing with the native Python 3.14 interpreter made `brain --version` work with the same
  current cryptography dependency. No dependency downgrade is required by this workaround.
- Hosted Brain was reachable, but no authenticated account identity was established. The user
  observed macOS Keychain prompts and requested investigation before continuing sign-in.

## Changes from the trial

The importer now distinguishes missing executable, process-start failure and timeout. A failed
CLI call tells users to check `brain --version` before troubleshooting login, while still withholding
raw stderr to protect source text and credentials. Recognized sign-in and Keychain failures get
safe, specific next steps without relaying the underlying output. Setup docs explain the separate Notion API
connection and choosing a native Python interpreter when a mixed installation causes startup failure.

The Keychain issue belongs to the Brain CLI, not the source adapters. Its follow-up prevents default
macOS approval dialogs, stops signed-out commands before OAuth registration, explains credential
storage and requires explicit login opt-in for any needed macOS approval. That change must be
released separately; this starter does not copy or manage OAuth credentials.

## Remaining acceptance flow

1. Confirm a small Obsidian vault/folder selection. Keep scope private and namespace stable.
2. Complete intentional Brain login and verify the target person/workspace with `identity`.
3. Run `plan` and `inspect`; review metadata and original text locally.
4. Authorize the concrete selected records and audience, then `apply` the exact reviewed digest.
5. Check receipts, stored scope and background jobs. Repeat unchanged content, then change a
   disposable test note and verify version behavior before expanding the selection.
6. For live Notion, configure a read-content API connection and explicitly grant selected pages;
   choose page IDs and repeat the same review/apply flow.

The passing synthetic tests do not establish live-provider or authenticated Brain acceptance.
Remaining product friction includes manual vault discovery, target-ID configuration and a separate
Notion connection. Keep any improvements small and based on the next real trial.
