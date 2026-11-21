# 7.35 Entity editor history tab

- **Status:** in review
- **Pull request:** #437
- **Records:** DD-816 (the history lives in the editor drawer), DD-817 (the audit
  read rides the drawer, not the form store); DV-190 (the list caps at one page).
  Relies on EDT-01/EDT-10 (7.7a's drawer shell and foot), VDE-11 (16.5c: a read
  outside the view doors stays an Atlas endpoint), AEN-05 (8.17's audit client),
  AUD-06..AUD-09 (server 3.5), LR-002 (the persistent loading line), UIC-26 (the
  tablist anatomy), DD-180 (the drawer subhead slot) and SHL-08 (the catalogue
  bridge).

## Scope

The legacy app showed an entity's change history in the editor, beside the
form. This increment brings that History tab back:

- the tab pair (Entity, History) in the editor drawer's subhead, in edit mode
  only. A create has no entity to audit
- the audit list: the entity's newest audit events, newest first, one row per
  event with the change's label, its user and its time
- the read: one `GET /api/atlas/v2/entity/{guid}/audit` every time the History
  tab opens, through `AtlasEntitiesService.getAuditEvents` (AEN-05)
- the failure path: a refused or failed read adds one alert and leaves the list
  empty. The drawer stays open

Not delivered here:

| Deferred                              | Lands with | Why                                                                                                                           |
| ------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Paging past the newest 100 events     | —          | The legacy page-fetched every event of the entity. The drawer lists the newest 100 and no screen asks for more today (DV-190) |
| The audit trail on the details screen | —          | The product's history place is the editor, as the legacy had it (DD-816)                                                      |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name
in the Vitest title (the e2e names it in the docstring).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HST-01 | The editor drawer shows the tab pair (Entity, History) in edit mode only. Create mode renders the form alone, as before (EDT-04 kept). The pair sits in the drawer's `drawer-subhead` slot (DD-180), so a long form or a long list cannot scroll it away.                                                                                                                                                                                                                                                                                                                       |
| HST-02 | The pair is one tablist in UIC-26's anatomy: the active tab carries `aria-selected="true"` and tabindex 0, the other `false` and -1. Left/Right move the active tab and carry focus with it (the markdown field's roving pattern). The two panes both stay mounted and the inactive hides (`[hidden]`), so the form keeps its DOM state and the loading region stays watched (DD-352, LR-002).                                                                                                                                                                                  |
| HST-03 | The History tab lists the audit events of the entity at the route's guid. Every switch to History fires one `GET /api/atlas/v2/entity/{guid}/audit` with no query parameters (AEN-05). The server's defaults then answer its newest 100 events in newest-first key order (AUD-08: an absent `count` reads as 100, an absent `offset` as -1, and -1 keeps that order). Sending `offset=0` would move the server onto its sorted path, which answers oldest first (AUD-07). A switch does not stack reads: an in-flight read is not repeated, and a superseded answer is dropped. |
| HST-04 | Each event renders one row (Bulma's media anatomy, as the legacy had it): the change's label, then a meta line with the event's user and its time formatted `yyyy-MM-dd HH:mm:ss` through `DatePipe` (SPL-07's display zone applies). The label comes from the audit-action display map, the type-name display's pattern: a known action shows its catalogue string in both locales, an unknown one keeps its raw name.                                                                                                                                                         |
| HST-05 | While the read is in flight, the panel shows the persistent line `search.services.entityAudit.retrieve` (LR-002's region: mounted always, text comes and goes). An answered read with no events shows no rows (every stored entity carries at least its create event, so this is the purged or aged case).                                                                                                                                                                                                                                                                      |
| HST-06 | A refused or failed audit read adds one error alert through the app's alerts store with `search.services.entityAudit.retrieve` (the failed-slice idiom, EDT-04's type-material line) and leaves the list empty. The drawer stays open (EDT-08's posture).                                                                                                                                                                                                                                                                                                                       |
| HST-07 | The foot bar's Save and Delete render in the Entity tab only (the legacy's footer rule). In History the foot bar holds nothing, which hides it (the drawer's empty-foot rule). Escape, the X and the backdrop still close the drawer from either tab (EDT-01 kept).                                                                                                                                                                                                                                                                                                             |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`),
`apps/atlas/src/app/search/`:

- `components/editor/editor.component.html` — the tab pair and the history
  template: `currentTab` swaps the entity form for the audit list, and the foot
  renders only on the entity tab. HST-01/HST-02 port the pair as a real tablist,
  and HST-07 ports the foot rule.
- `components/editor/editor.component.ts` — `currentTab: 'entity' | 'history'`.
  Ported as a component signal; the legacy's plain state needed no routing.
- `services/entity-audit/entity-audit.service.ts` — the read behind the list:
  `retrieveAuditsPaged` page-fetches every event through `getEntityAudit`
  (`count`/`offset`), and the store resets on every entity change. HST-03
  replaces the walk with the newest page of 100 (DV-190), and DD-817 moves the
  read out of a store into the drawer itself.

## Deviations

None against Apache Atlas: this slice is an Aurelius product screen and the
stock dashboard is not its parity reference (ADR 046, as 7.7a had it). The
endpoint it calls is the ported Atlas v2 audit read (server 3.5), used as the
legacy client used it. Against the legacy Aurelius app the list caps at the
newest 100 events and offers no paging, recorded as DV-190.

## Acceptance

- `apps/aurelius-atlas-webapp/src/app/search/editor/audit-display.spec.ts` —
  the action map resolves the catalogue string and falls back to the raw name
  (HST-04).
- `apps/aurelius-atlas-webapp/src/app/search/editor/entity-editor.component.spec.ts` —
  the strip renders in edit mode alone (HST-01), the tablist roles and the
  arrow keys (HST-02), the audit request and the listed rows (HST-03, HST-04),
  the loading line (HST-05), the failed read (HST-06), and the foot bar rule
  (HST-07). Run from the repo root: `nx test aurelius-atlas-webapp -c ci`.
- `apps/aurelius-atlas-webapp/e2e/test__aurelius_atlas_webapp.py` —
  `test__the_editor_shows_its_edit_history`: a seeded and edited entity shows
  its create and update rows with the writer's name, newest first, in the
  drawer's History tab (HST-03, HST-04). Run with `nx e2e aurelius-atlas-webapp`.
