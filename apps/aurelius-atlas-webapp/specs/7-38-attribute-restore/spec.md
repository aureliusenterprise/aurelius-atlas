# 7.38 History attribute restore

- **Status:** in review
- **Pull request:** #443
- **Records:** DD-822 (the restore writes one attribute, and the form follows
  with the conflict merge). Adds HST-11. Relies on HST-01..HST-10 (7.35..7.37),
  EWR-15 (the single-attribute write), EDT-09 (write gating), EDT-19
  (hold-to-confirm), DD-610 (the conflict merge), VDE-07 (the re-edit) and
  SHL-08 (every string is catalogued).

## Scope

A person reading an entity's History tab can see what each change did (7.37).
They cannot put a value back: when they change a description by mistake, they
must retype the old text from the change list (DD-822's problem). This
increment puts a restore button on the changed attribute rows of an open
change list. One press writes that one attribute's old value back and keeps the
drawer open, so the person sees the stored result instead of a drawer that
navigates away.

Not delivered here:

| Deferred                                              | Lands with | Why                                                                                    |
| ----------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------- |
| Restoring an added, removed or multi-valued attribute | –          | The single-attribute write cannot remove a value, and a list is not one value (EWR-15) |
| Restoring a relationship end                          | –          | The user asked for attribute changes only; an end write needs the picker's rules       |
| Restoring several attributes at once                  | –          | One row, one write (DD-822): the person chooses each value                             |
| A server-side "restore" endpoint                      | –          | `PUT .../v2/entity/guid/{guid}` already sets one attribute (EWR-15)                    |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name
in the Vitest title.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HST-11 | A changed attribute line (`kind: "changed"`, HST-10) whose old value is a single text, number or boolean value carries a restore button, and every other line carries none: an added, removed or multi-valued attribute shows the change list line of 7.37 alone, and a relationship line shows none. A create has no History tab to reach a button from (HST-01); in edit mode the button appears only while the person holds the entity-write privilege (EDT-09), and it is disabled while a save, delete or restore is in flight — the Save and Delete posture. Its accessible name names the attribute it restores. A press writes the old value to the entity through the single-attribute door (`PUT /api/atlas/v2/entity/guid/{guid}` with the attribute name and the value as a bare JSON body, EWR-15), and nothing else: no other attribute travels, no body carries the entity, and the person's unsaved edits stay untouched. While the write is in flight the button is disabled and no second press sends a request. On success the editor's status line says the entity was restored, and the change list stays as the person left it: the trail re-reads on the next History visit (HST-03), which is where the restore's own row appears. On a refusal one alert says the restore failed (the audit read's alert shape, HST-06), the drawer stays open, the change list stays open, and the person's unsaved edits stay. The success re-reads the entity through the read door (the cache entry is dropped first, VDR-07) and merges the stored entity into the form the VDE-07 conflict path uses: every control the person never touched answers the restored value, and every one they did touch keeps their value. The drawer never navigates away and never closes on a restore, because the person came from the change list they were reading (DD-822). The client sends no request for a button it does not show: the buttons are the only writes this increment can make. |

## Aurelius origin

No reference screen has a restore control (ADR 046), so this slice has no
parity reference for the button:

- Apache Atlas 2.4.0 `audit-table.component.js` — the stock dashboard's audit
  table lists the action, the time and the user only. It has no write control.
- The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`),
  `apps/atlas/src/app/search/components/editor/editor.component.html` — the
  history template shows the translated action, the user and the time, and
  nothing else. It has no write control.
- The write the button rides is already ported: `EntityWriter.update_attribute_by_guid`
  (`libs/python/aurelius-atlas-core/aurelius_atlas_core/entity_writer.py`,
  EWR-15) sets one primitive or reference attribute, and the client's
  `AtlasEntitiesService.partialUpdateAttribute` sends it. No server or wire
  change is part of this increment.

The confirm posture follows the delete button (EDT-19): a hold-to-confirm
lives at the button, and the store trusts its caller. A restore is cheap
enough — one attribute, and the change list can restore the new value back —
so no hold applies here; see DD-822.

## Deviations

Against Apache Atlas: none. The stock dashboard has no restore control, and it
is not the parity reference for an Aurelius product screen (ADR 046, as 7.35
to 7.37 had it).

Against the legacy Aurelius app: none recorded. The legacy history template
shows no change list and offers no write, so this increment adds what the
legacy screens never had and changes nothing they showed (HST-04, HST-10
stand).

## Acceptance

- `apps/aurelius-atlas-webapp/src/app/search/editor/audit-details.spec.ts` —
  the helper answers which changed attributes can be restored: text, number
  and boolean values yes; null, object, array, added, removed and relationship
  rows no (HST-11).
- `apps/aurelius-atlas-webapp/src/app/search/editor/entity-editor.component.spec.ts` —
  a changed line carries a button and a press sends one single-attribute write
  with the old value; the button is absent for an added, removed,
  multi-valued or relationship line, and for every line when the person cannot
  write; the button is disabled while the write is in flight and a second press
  sends nothing; a success re-reads and merges the stored entity into the form
  so an untouched control answers the restored value and a touched one keeps
  its value, fills the status line, and navigates nothing; a refusal alerts
  once, keeps the drawer, the change list and the unsaved edit, and sends no
  re-read (HST-11, VDE-07, DD-610).
- `apps/aurelius-atlas-webapp/src/app/search/editor/editor-state.spec.ts` —
  the store's write is one PUT of the bare value with the attribute name
  (EWR-15); the success evicts the cache, ticks the write bus and hands the
  re-read to the component; a refusal alerts and re-reads nothing; one write
  travels at a time (HST-11, DD-822).
- `apps/aurelius-atlas-webapp/src/app/i18n-completeness.spec.ts` — the four new keys
  are in both vendored dictionaries and both catalogues (SHL-08).
  Run from the repo root: `nx test aurelius-atlas-webapp -c ci`.
