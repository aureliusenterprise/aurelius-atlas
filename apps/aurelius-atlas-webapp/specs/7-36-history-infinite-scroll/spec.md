# 7.36 History tab infinite scroll

- **Status:** in review
- **Pull request:** #441
- **Records:** DD-820 (the trail pages itself from its newest key). Adds
  HST-08/HST-09, amends HST-03/HST-05/HST-06 (7.35), and closes DV-190's cap.
  Relies on HST-01..HST-07 (7.35), AEN-05 (8.17's audit client), AUD-08 (server
  3.5's key cursor), UIC-21/UIC-22 (the results list's infinite-scroll
  container), LR-002 (the persistent loading line) and CLE-10 (given
  parameters travel).

## Scope

A person reading an entity's History tab today sees at most the newest 100
audit events and has no way to the older ones (DV-190). This increment gives
the tab the same scroll the results list has:

- the trail keeps loading older events while the person scrolls to the bottom
  of the list, one page at a time, until the entity's oldest event is on screen
- the pages ride the server's key cursor (AUD-08): each next page starts at the
  last event already listed, and the client drops the one event that cursor
  repeats
- the sentinel, its load button and its spinner are the results list's
  `InfiniteScrollContainer` (UIC-21, UIC-22), reused unchanged

Not delivered here:

| Deferred                                           | Lands with | Why                                                                    |
| -------------------------------------------------- | ---------- | ---------------------------------------------------------------------- |
| What changed in each event (the old and new value) | 7.37       | A read of the event bodies; its own rule set (HST-10)                  |
| Rolling an attribute back                          | 7.38       | It writes; the confirm and the write path are their own rules (HST-11) |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name
in the Vitest title.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HST-08 | The History pane lists the entity's audit events one page at a time (HST-03's page size, 100, stays). The pane wraps its rows in the results list's infinite-scroll container (UIC-21): while more events may exist, the container shows its sentinel, and scrolling the sentinel into view — or clicking its load button — asks for one more page (UIC-22). One ask fires one page: while a page is in flight the container suppresses both triggers and the pane guards again, so a fast scroll stacks no reads. The pane sends one `GET /api/atlas/v2/entity/{guid}/audit` per page with `count=100` and, from the second page on, `startKey` set to the `eventKey` of the oldest event already listed. That cursor is inclusive (AUD-08), so a page repeats the oldest row already on screen: the pane drops a received event whose `eventKey` it already lists, and the row count never grows by the repeat. A page shorter than the asked count is the entity's oldest page: the container hides its sentinel and no further read fires. A page that answers exactly the count keeps the sentinel shown, even when the trail ends there. The list stays in the server's newest-first key order and the client never re-sorts it. |
| HST-09 | A page's ask is a read like the tab switch's: while one page is in flight the pane repeats no read — a tab switch and a second sentinel ask among them — and the drawer's teardown drops an answer it no longer needs (HST-03's no-stacking rule, which the scroll now shares).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

HST-03, HST-05 and HST-06 are 7.35's rules, amended with this increment: the
first read names the page size and starts the list empty (HST-05), a next page
appends to the rows already on screen, and a failed next page keeps the rows it
did have and keeps the sentinel. HST-01, HST-02, HST-04 and HST-07 stand as
7.35 wrote them.

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`),
`apps/atlas/src/app/search/`:

- `services/entity-audit/entity-audit.service.ts` — `retrieveAuditsPaged`
  page-fetches the whole trail: `getEntityAudit` with `count`/`offset`, the
  offset walking by the page size until a page comes back short, every page
  appended to the store. HST-08 matches that reach — every event of the entity
  ends up on screen — but walks the key cursor instead of the offset, because
  the offset moves the server onto its sorted path (AUD-07) and a store that
  grows under a writer shifts offsets between pages.
- `components/editor/editor.component.html` — the audit list inside the editor.
  The legacy template shows `audits$ | async` with no container and no
  sentinel: the store's walk put every event on screen at once, and the drawer
  body scrolled. HST-08 keeps the drawer body as the scroller and adds the
  container the results list already has.
- `components/results/results.component.html` /
  `services/infinite-scroll-container/` — the container HST-08 reuses.
  The results list feeds it the same three states (a page in flight, all
  loaded, the label) and takes `nextPage` back (UIC-21, UIC-22).

## Deviations

Against Apache Atlas: none. The stock dashboard's audit tab (2.4.0
`audit-table.component.js`) is a plain table of the newest page with no
scroll; this slice is an Aurelius product screen and the stock dashboard is not
its parity reference (ADR 046, as 7.35 had it).

Against the legacy Aurelius app: DV-190 recorded the newest-100 cap. This
increment closes it — the scroll reaches every event the legacy walk reached —
and DV-190's row is rewritten to say so.

## Acceptance

- `apps/aurelius-atlas-webapp/src/app/search/editor/entity-editor.component.spec.ts` —
  the first read carries `count=100` and no `startKey` (HST-03 as amended), the
  sentinel's ask sends `startKey` of the oldest listed event and appends the
  page without the repeated row (HST-08), a short page hides the sentinel and
  ends the trail (HST-08), a full page keeps it shown (HST-08), a second ask
  during a flight sends nothing (HST-08, HST-09), a failed next page alerts and
  keeps the rows and the sentinel (HST-06 as amended), a next page keeps the
  rows and the pane's own line silent while it runs (HST-05 as amended), and a
  first read still clears the rows (HST-05). Run from the repo root:
  `nx test aurelius-atlas-webapp -c ci`.
