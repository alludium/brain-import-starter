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

## Pre-import resolution — observed locally

The same real CLI/backend flow was repeated with five explicit choices: confirm the conflicting
company as Acme AI, search and confirm the meeting's company, confirm its attendee, leave one
subject unlinked, and defer another. Preview, search and choice saves left all six database counts
unchanged. Browser refresh retained the choices. The 11-note import preserved exact originals and
private sharing, persisted three approvals, one rejection and one deferral with the reviewing
actor, and left the eight automatic associations intact. The real Sources review filter showed
only the deliberately deferred note. A fresh dry run and second import returned 11 unchanged,
zero created. This is isolated synthetic acceptance, not hosted deployment evidence.

The maintained browser journey covers candidate choice, audience search, changing a choice,
rejection, deferral, refresh persistence and mobile accessibility. Backend MCP tests also reject
stale snapshots, wrong-type/hidden identities, incompatible actions and replayed decisions without
partial writes, and cover two reviewed notes shared with a newly created people audience.

## Guidance and matching explanations — observed locally

The actual synthetic vault was re-read through the CLI and isolated backend after adding field
help and candidate evidence. It still returned 6 matched notes, 3 needing review and 2 without an
active match. All six database counts remained unchanged. No notes were imported in this run.

The conflicting note really has `company: Acme AI` and `website: https://kestreldata.nl`: the live
preview now shows the name matching Acme AI and the website matching Kestrel Data. The meeting
note has `company_website`, while its current company mapping reads `website`, so no company
identifier was extracted. Its attendee supplies Maya's name without an email. Both one-candidate
cases correctly stay pending and explain why. These results are computed from files and the
backend; they are not hard-coded demo rows. Only the maintained browser test uses fake transport.

Keyboard help opening, Escape/focus return, narrow-screen stable-ID instructions, property
examples, conflict evidence, one-candidate review, candidate choices and refresh were checked.
Fresh desktop/mobile screenshots were inspected; an inherited flex rule that compressed the
evidence into narrow columns was fixed and a layout assertion added. Axe passes with help open
and with multiple review subjects expanded. Candidate metadata tests exclude private identifier
canaries from a firm-audience preview/search. Matching policy is unchanged.

## Automated coverage

60 Python tests cover existing adapters plus preview capability gating, immutable snapshots,
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
