# Import wizard acceptance — 4 November 2026

## Observed locally

Used the actual 11-note synthetic Obsidian trial vault, a Vite production build, the Python UI
host, the installed Brain CLI, and an isolated Northwind backend with five known synthetic
company/person identities. No production services, personal vault contents or live Notion reads.

- Browser connection showed the selected person and Northwind workspace.
- Selected five folders, mapped Research to company notes and People to person notes, kept sharing
  private, then ran the preview from the browser.
- Result: **6 matched notes, 3 needing review, 2 with no active match**. Across those notes there
  were eight automatic associations and five pending associations; a note can mention several subjects.
- The conflicting company/website note returned Acme AI and Kestrel Data with the explicit
  contradictory-identifier reason. No false automatic association.
- Six independent database table counts were identical before and after preview: sources,
  source links, associations, association events, groups and group members.
- Confirmed import: all 11 originals matched their stored text byte-for-byte and all audiences
  were private. Every persisted association agreed with its preview.
- Repeated apply: **11 unchanged, zero created**. Source count stayed 11.
- Followed the completion link into the actual local Brain Sources viewer. Its Needs review
  filter showed the same three notes. Its initial `networkidle` wait timed out because the viewer
  keeps activity running; explicit rendered-content/readback checks succeeded.
- The unmapped custom-property example remains unlinked, as does the unidentified contact. Mapping
  custom fields is explicit; the test does not imply support for every Obsidian plugin's schema.

## Automated coverage

58 Python tests cover existing adapters plus preview capability gating, immutable snapshots,
changed-match reconfirmation, partial failure receipts, local HTTP access controls, metadata-only
vault discovery, folder profile hints and loopback-only development authentication.

The Chromium journey exercises connection, vault selection, folder profiles, preview, search,
filters, evidence expansion, refresh restoration, setting-change invalidation, explicit confirmation,
completion and a 390px layout. It uses a synthetic transport stand-in, separately from the real
CLI/backend run above. Axe checks desktop and mobile; contrast findings were corrected.

The backend change also has real MCP tests for read-only previews, matching/apply parity, retained
rejections, revision/audience conflicts, private canaries, no people-group creation and incompatible
capture actions. Existing Sources component tests and card compatibility tests pass.

## Limits

Hosted release and installed-host OAuth acceptance are separate. The preview backend must be
deployed before using this UI against hosted Brain. Notion remains CLI-only and live Notion
acceptance is still outstanding. Preview is a point-in-time result; concurrent updates may alter
later matches. Imports stop on first error and retain successful records.
