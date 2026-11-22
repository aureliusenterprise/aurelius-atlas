# 7.37 History change details

- **Status:** in review
- **Pull request:** #442
- **Records:** DD-821 (the client diffs the stored audit bodies). Adds HST-10.
  Relies on HST-01..HST-09 (7.35, 7.36), AUD-03/AUD-04 (server 3.5's details
  and their size cap), AUD-06 (the audit wire is read-only),
  FORM-CUSTOM-001 (the accordion's expanded-name pairing) and SHL-08 (every
  string is catalogued).

## Scope

A person reading an entity's History tab sees which action happened, by whom,
and when. They cannot see what the action changed (DD-821's problem). The
server already stores the whole entity in each entity-state audit event
(AUD-03), so this increment reads that stored body back and shows the person
what changed, per row:

- an entity-state row (created, updated, or either by import) gains a toggle
  that opens the row's change list
- the change list compares the event's stored entity with the stored entity of
  the older event before it in the trail, and lists each attribute that was
  changed, added or removed with its old and new value, plus the relationships
  the event added or removed
- an event with no older stored state to compare with says so instead of
  guessing; a create event is its own case, because the entity did not exist
  before it

Not delivered here:

| Deferred                    | Lands with | Why                                                                    |
| --------------------------- | ---------- | ---------------------------------------------------------------------- |
| Rolling an attribute back   | 7.38       | It writes; the confirm and the write path are their own rules (HST-11) |
| A server-side diff endpoint | –          | Not needed: the stored bodies answer the question (DD-821)             |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name
in the Vitest title.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HST-10 | The four entity-state actions (`ENTITY_CREATE`, `ENTITY_UPDATE`, `ENTITY_IMPORT_CREATE`, `ENTITY_IMPORT_UPDATE`) carry the entity's stored attributes and relationships in their `details` string (AUD-03), and only their rows offer a change list: every other row keeps the label, user and time of 7.35 (HST-04) and shows no toggle. The row's toggle opens and closes the change list in place, and its `aria-expanded` says what the list is, with `aria-controls` naming the list only while it is open (the accordion's pairing, FORM-CUSTOM-001); more than one row can be open at the same time. The list compares the row's stored state with the stored state of the nearest older row in the list that carries one. It lists each attribute whose value differs as changed with its old and new value, each attribute the row has and the older state lacks as added, and each attribute the older state has and the row lacks as removed; it lists each relationship end the row has and the older state lacks as added, and each end the older state has and the row lacks as removed, named by its end entity's display text, or its GUID when the end carries none. An added or removed end matches on its end entity's GUID, so a changed display text is never read as a removed end and an added one. A row with a state to compare against whose two states differ in nothing says nothing changed. A create with no older state to compare with is answered from the empty state: every attribute and every relationship end it carries is listed as added. A row that needs an older state, where no older row in the loaded list carries one, says the earlier state is not loaded and claims nothing; a next page that brings the older state answers that row on the next read (HST-08). A row whose stored body lost its attributes because the server cut it down for size (AUD-04) says the details are not recorded. The client reads no endpoint for a change list and sends nothing: the trail it already loaded is the only input (AUD-06). |

## Aurelius origin

Neither reference screen answers this question, so this slice has no parity
reference for the change list itself (ADR 046):

- Apache Atlas 2.4.0 `audit-table.component.js` — the stock dashboard's audit
  table lists the action, the time and the user only, for the newest page.
- The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`),
  `apps/atlas/src/app/search/components/editor/editor.component.html` — the
  history template in the editor drawer shows the translated action, the user
  and the time, and nothing else. It never reads the event's `details`.
- The stored bodies this increment reads come from the ported listener
  (`libs/python/aurelius-atlas-core/aurelius_atlas_core/entity_audit_listener.py`,
  `audit_detail`): the action's prefix and the entity's JSON, with attributes
  dropped when the body passes the size cap (AUD-04). The client parses the
  same text the server wrote; the wire does not change.

The in-place toggle follows the two disclosure shapes the app already has: the
UI library's `Accordion` names its state with `aria-expanded` and pairs
`aria-controls` with it (FORM-CUSTOM-001, 7.30), and the editor's
classification combobox pairs a plain control with `aria-expanded` inside a
list row.

## Deviations

Against Apache Atlas: none. The stock dashboard shows no change details, and it
is not the parity reference for an Aurelius product screen (ADR 046, as 7.35
and 7.36 had it).

Against the legacy Aurelius app: none recorded. The legacy history template
shows the action, the user and the time; this increment adds what those screens
never showed, and it changes nothing the legacy screens showed (HST-04 stands).

## Acceptance

- `apps/aurelius-atlas-webapp/src/app/search/editor/audit-details.spec.ts` —
  the parser reads the stored body of each of the four actions, answers
  `partial` for a body the server cut down (AUD-04), and answers none for a
  body it cannot use; the differ lists changed, added and removed attributes
  with both values, added and removed relationship ends matched by GUID,
  nothing-changed, the empty-state create, and the row with no older state on
  screen (HST-10).
- `apps/aurelius-atlas-webapp/src/app/search/editor/entity-editor.component.spec.ts` —
  a state row opens and closes its change list and its toggle names the state,
  the open list shows the changed attribute with its old and new value,
  non-state rows carry no toggle, a cut-down row says the details are not
  recorded, an oldest row with no older state says the earlier state is not
  loaded and then answers itself once a next page brings that state (HST-10,
  HST-08), and two rows can be open at once.
- `apps/aurelius-atlas-webapp/src/app/i18n-completeness.spec.ts` — the eight
  new keys are in both vendored dictionaries and both catalogues (SHL-08).
  Run from the repo root: `nx test aurelius-atlas-webapp -c ci`.
