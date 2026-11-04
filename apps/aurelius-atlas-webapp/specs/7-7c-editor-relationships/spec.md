# 7.7c Entity editor: relationship inputs

- **Status:** proposed
- **Pull request:** —
- **Records:** DD-338..DD-348; extends 7.7a (EDT-03/EDT-06); relies on
  DD-140 (the App Search index is not ported), UIC-16/UIC-24 (the chip and its
  delete), DD-335/DD-336 (the tag-box anatomy this reuses), UIC-25 (the
  drawer's foot slot)

## Scope

The editor drawer's relationship-attribute pickers. 7.7a ships the entity
editor (EDT-01..EDT-12) and defers this slice: "the legacy pickers searched
the App Search index this product does not have (DD-140); the search contract
needs its own decision." The decision is DD-339: the pickers search the
ported `GET /search/attribute` endpoint — the endpoint the stock Apache Atlas
2.4 dashboard itself uses for these inputs, with the same parameters.

Delivered here:

- the fields: every relationship attribute of the entity's type (its own and
  its supertypes') joins the editor form after the plain attributes and
  before the classification box (EDT-13)
- the picker: each field is one bordered box with the chosen entities as
  deletable chips and a text input (EDT-14) — the classification box's anatomy
  (DD-335/DD-336) pointed at a live search instead of the classification
  typedef list
- the search: typing searches entities of the attribute's target type whose
  `name` begins with the text (EDT-14); an empty focused box browses up to
  five candidates of the target type, so the picker suggests before anything
  is typed (DD-343); results that are already chosen or
  are the edited entity itself are left out
- the seed: an editing entity's existing relationships pre-fill the chips,
  only the ones whose `relationshipStatus` is `ACTIVE` (EDT-15); removed
  edges the server still lists as `DELETED` stay out of the form
- the save: the picker's list replaces that key's list in the entity body —
  the same full-replace semantics the server gives an array relationship
  attribute (EDT-16); an emptied picker clears the key's edges
- the required gate: a relationship attribute the definition marks
  non-optional shows the required marker, and a save with it empty is refused
  in the form (EDT-17), the way the name field is (EDT-07)
- the single-cardinality picker: it holds at most one chip; the input is
  hidden while the chip is there, as the legacy picker hid it
- the editor foot: the commit pair (Delete, Save) moves to the drawer's fixed
  foot bar (EDT-19), and Delete confirms by a three-second hold, the legacy
  pattern (DD-347/DD-348)

Explicitly not delivered here, with the increment that will:

| Deferred                                                        | Lands with | Why                                                                                                                    |
| --------------------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------- |
| The stock dashboard's duplicate-name relationship-type selector | Never      | Three shipped types carry one name over two relationship types; the field sends the first definition's type (DD-338)   |
| The type icons the legacy chips led with                        | Never      | `iconsByType` is app metadata the webapp does not port; the chip leads with the target type's name instead (DD-341)    |
| Reviving a relationship the server already marked `DELETED`     | Never      | Apache Atlas 2.4 keeps it `DELETED` on re-add (its `updateRelationship` returns the edge it finds); this port keeps it |

The `meanings` attribute (the glossary-term assignment every shipped type
inherits) is not deferred: it renders as a picker like every other
relationship attribute, the same generic path the stock dashboard uses. The
details screen already shows relationship attributes (7.6), so term
assignment reads back there.

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name
(7.6/7.20's pattern — Vitest names the id in the test title; the e2e names it
in the docstring).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EDT-13 | The relationship-attribute fields come from the entity's entity definition and its supertype chain (the same walk EDT-03 makes, over `relationshipAttributeDefs` — the server synthesizes them for every shipped type at the read path). A name that two definitions carry once (the shipped store: `hive_column.table`, `spark_ml_directory.model` and `.pipeline`) merges to one field and keeps the first definition's `relationshipTypeName`. The fields render after the plain attributes and before the classification box, each in the definition's own order rank. A field's label is the attribute's `displayName` else its name, with the target type in brackets (the name alone, not `array<X>`). The target type is the definition's `typeName`, unwrapped from `array<X>` when it is an array; the cardinality is the definition's — `SINGLE` holds one entity, `SET`/`LIST` hold many. A definition whose `isOptional` is `false` carries the required marker (`*`), like the name field. The picker always renders even when the target type has no typedef of its own in the shipped store (`spark_ml_model` and its peers) — the search simply finds nothing.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| EDT-14 | Each picker is the classification box's anatomy (DD-335/DD-336): the chosen entities ride inside the bordered box as `classification-chip` components (UIC-16) with the UIC-24 delete, and the text input sits borderless in the same box. The chip's lead word is the chosen entity's own `typeName` (DD-341); its label is the entity's `displayText` else its `qualifiedName` else its guid. Typing at least one character searches through `SearchService.searchUsingAttribute` (SRC-11) with `typeName` set to the field's target type, `attrName` "name", `attrValuePrefix` the typed text, and `limit` 10 — the stock dashboard's own contract for these pickers. The search is debounced (250 ms), like the stock's delayed select2. An empty box that gains focus — and text cleared back to empty — runs the same search with no prefix and `limit` 5: a browse of up to five candidates of the target type, so the picker suggests before anything is typed (DD-343). A full-width panel opens over the fields above the box — the classification box's own Bulma `is-up` pattern, offset and all (DD-343) — and lists the found entities that are neither already chosen nor the edited entity itself, newest text first as the server answers them. The input is a combobox with the same aria wiring and key handling as the classification box (Down/Up move the active row, Enter or a mousedown commits, Escape closes the panel only). A pick appends the chip and clears the input. A `SINGLE` picker hides the input while it holds one chip (the legacy behaviour): the change is a delete, then a pick. Panel rows clear the 24px touch floor (48px on coarse pointers), as the box's rows do. |
| EDT-15 | Editing seeds the pickers from `entity.relationshipAttributes`: each key's list keeps only the entries whose `relationshipStatus` is `ACTIVE` (the server keeps removed edges in the read as `DELETED`); `SINGLE` fields seed from the first ACTIVE entry. The chips keep the entity's `displayText`, `typeName` and guid for display and for the save. The `DELETED` entries are never shown, never sent, and never block re-adding their entity (EDT-16's parity note). Create mode seeds nothing.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| EDT-16 | Save extends EDT-06's merge: for every picker the form rendered, the entity body's `relationshipAttributes` carries that key's full value — a list of one object per chip (`guid`, `typeName` (the chip's own, so a subtype keeps its name), `displayText`, `relationshipType` (the field definition's `relationshipTypeName` when it carries one), and `relationshipStatus: "ACTIVE"`), or — for a `SINGLE` field — that one object alone. An emptied multi picker sends the empty list and an emptied `SINGLE` picker sends null; both remove the key's edge(s) (the server marks each `DELETED`). The merge also drops each rendered key from `attributes`: the picker owns the key, and a reference left in `attributes` re-attaches the edge the picker just removed (the server moves an attribute-named relationship value back into `relationshipAttributes` — `compactAttributes`, probed live). A key no picker rendered (an attribute of a type set the form does not walk, or a value the read carried beyond the defs) passes through untouched, exactly as an unwritten attribute does. No `DELETED` seed entry is ever echoed into the body — echoing one would re-list a removed edge. A target whose edge the server already marked `DELETED` stays `DELETED` after a save that re-adds it: Apache Atlas 2.4 reuses the edge its lookup finds for the position and leaves it as it is (`EntityGraphMapper#updateRelationship` returns the current edge when it reaches the target), and this port keeps that reading. The e2e does not name this rule; no client can undo it (the relationship API's create answers `RELATIONSHIP_ALREADY_EXISTS` for the tombstoned pair).                         |
| EDT-17 | A required relationship attribute (EDT-13's marker) with an empty picker makes the save behave as an invalid form behaves in EDT-07: the save fires no request, the field's control marks touched with Bulma's danger state, the `search.components.editor.attribute.notification` line rides at the top of the form, and the help line under the picker names what is missing. A save attempt re-shows the notification until dismissed. Every picker string rides a catalogue key the app already ships (`search.components.editor.components.relationshipsInput.addPlaceholder` and `.selectPlaceholder` as the input's placeholder by cardinality, `search.components.editor.delete` on the chip's delete); no key is added (SHL-08).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| EDT-18 | While a save or a delete is in flight (the spans `editor-state.save()` and `editor-state.delete()` guard) the acting button is disabled, carries Bulma's `is-loading` spinner, and is marked `aria-busy="true"`, and the status line shows in the foot as a live status (DD-342): `search.services.entityUpdate.save` ("Saving the entity") for a save, `search.services.entityDelete.delete` ("Deleting the entity") for a delete. The other button is disabled too, so one commit runs at a time. A refused save (EDT-07/EDT-17) or a failed one (EDT-08) ends the state with the drawer open and the edits kept; a saved save navigates away. No new string (SHL-08).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| EDT-19 | The foot bar (the drawer's `drawer-footer` slot, UIC-25) holds the commit pair in Bulma's `buttons is-right` container, which carries the spacing between the two and their right alignment, and both are normally sized buttons (no size modifier) (DD-350). Save is EDT-18's button, unchanged. Delete shows in edit mode only (create has nothing to delete) and only for a writer (EDT-09's `atlas-write` grant, the same seam the pencil rides). A click is not enough: the `aurelius-atlas-ui-hold` directive (DD-348) fires its completion only after the pointer has held the button for three seconds, and only that completion sends `DELETE /api/atlas/v2/entity/guid/{guid}` (EDL-04: no `deleteType`, so the server strategy applies). An early release, leave, or cancel sends nothing. While the hold runs the button behaves like Bulma's `is-loading`: the label clears and a donut takes its place, the loading spinner's own look, drawn as an SVG ring stroke so its edges are smooth, growing clockwise from the top over the hold's three seconds by one CSS animation (DD-349, UIC-03). A deleted entity closes the drawer and lands on browse. A refused or failed delete (4xx/5xx) alerts through the app's alerts store (EDT-08's shape) and keeps the drawer open. The strings ride catalogue keys (`search.components.editor.delete`, `search.services.entityDelete.delete`), and no key is added (SHL-08). The hold carries no tooltip: the legacy key (`holdable.tooltip.*`) is not in the shipped dictionary fixtures, and none may be added.                                                                                                                                         |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`):

- `apps/atlas/src/app/search/components/editor/components/relationships-input/` —
  the Bulma dropdown-over-tags box the 7.7a tag box already mirrors; EDT-14
  ports its interaction shape (chips, focus-gated results, the single pick
  hiding the input). Its search ran against the App Search index (DD-140);
  DD-339 retargets it to `search/attribute`. Its payload (a placeholder
  `relationshipGuid`) is dropped: this server's array path ignores a
  client-made edge guid (DD-340)
- `apps/atlas/src/app/search/components/editor/editor.component.*` and the
  per-type forms — the hard-coded relationship fields (m4i types only);
  DD-338 replaces them with the def-driven field set, the same call 7.7a made
  for plain attributes (DD-323). Its footer is EDT-19's shape: Delete (danger,
  holdable, edit mode only) beside Save (success), and a deleted entity
  navigates to the search screen
- `libs/directives/src/lib/holdable/holdable.directive.ts` — the hold
  mechanic EDT-19 ports (`models4insight-holdable`): a timer that starts on
  mousedown, cancels on mouseup/leave, and confirms once the hold passes the
  given seconds (DD-348)

Parity reference (stock Apache Atlas 2.4, vendored at
`apps/aurelius-atlas-dashboard/dashboardv2/`):

- `public/js/views/entity/CreateEntityLayoutView.js` — renders every
  relationshipAttributeDef in a "Relationships" section (label = the name,
  the target type as hint); its entity pickers search
  `searchApiUrl('attribute')` with `attrValuePrefix` = the typed text,
  `typeName` = the target type, `limit` 10, delay 250, minimum input 1 — the
  contract EDT-14 ports verbatim; the save posts `relationshipAttributes`
  inside the entity body, the shape EDT-16 ports
- `repository/.../v2/EntityGraphMapper.java` — `mapArrayValue` /
  `updateRelationship`: the edge lookup by position, reused as-is when it
  reaches the target — the reading behind EDT-16's re-add note and DD-340

## Deviations

Against Apache Atlas: none in the REST contract — the pickers are a client
of the ported endpoints (`search/attribute` SRC-11, the entity write of
2.4/REL-11..16), used the way the stock dashboard uses them. Two deliberate
differences: the stock dashboard's duplicate-name relationship-type selector
is not ported, and the merged field sends the first definition's type
(DD-338). And the seed is stricter than the stock's — its picker re-seeds a
`DELETED` relationship entry after a save that removed it (it filters only
by the target entity's own status), so a removed relationship reappears in
the stock editor; EDT-15 keeps the tombstones out, so a reopened editor
shows the relationships that exist.

Against the Aurelius product, three intended differences are recorded beside
this spec. The picker searches the entity store's attribute search instead
of the App Search index the legacy used (DD-339, the successor of DD-140 —
the index this product does not have). The chips lead with the entity type's
name instead of the legacy's type icon (DD-341 — `iconsByType` is app
metadata that never ported). The hold listens to pointer events instead of
the legacy's mouse events, so a touch press confirms too (DD-348), and it
carries no tooltip because the legacy tooltip key is not in the shipped
dictionary fixtures (EDT-19, SHL-08). The deferral table carries the rest,
including the accepted `DELETED`-edge parity (DD-340).

## Acceptance

- Vitest (unit, `apps/aurelius-atlas-webapp`):
    - `src/app/search/editor/form-fields.spec.ts` — the relationship fields
      join the set from the def and its supertypes, merged for duplicate
      names with the first definition's `relationshipTypeName` (EDT-13),
      the required marker follows `isOptional` (EDT-17), a `SINGLE` def
      seeds one chip and a `SET` seeds the ACTIVE entries only (EDT-15),
      the save merge writes one full value per rendered key with the
      EDT-16 entry shape (an emptied multi picker sends `[]`, an emptied
      `SINGLE` picker sends null), each rendered key drops from
      `attributes`, a `DELETED` seed
      entry never echoes, and an unrendered key passes through untouched
      (EDT-16).
    - `src/app/search/editor/entity-relationship-input.component.spec.ts` —
      the search call carries the stock parameters and debounces (EDT-14),
      chosen entities and the edited entity itself drop out of the results,
      a pick appends and clears (EDT-14), the combobox aria wiring matches
      the box's (EDT-14), a `SINGLE` picker hides the input at one chip
      (EDT-14), the chip's delete drops it (EDT-17).
    - `src/app/search/editor/entity-editor.component.spec.ts` — the pickers
      render between the plain fields and the classification box (EDT-13);
      a save with a required picker empty fires no request and shows the
      field error and the notification (EDT-17); a normal save posts the
      entity body with `relationshipAttributes` merged per EDT-16 and
      navigates as EDT-06 does. The head carries only the X, and the foot
      holds Delete and Save (EDT-10, EDT-19). Create mode hides Delete
      (EDT-19). A completed hold sends the DELETE by guid and lands on
      browse (EDT-19). A premature release sends nothing (EDT-19). A
      refused delete alerts and keeps the drawer (EDT-19, EDT-08's shape).
    - `i18n-completeness.spec.ts` unchanged and green (EDT-17/EDT-19: no key
      is added).
- ui library:
    - `src/lib/holdable/holdable.directive.spec.ts` — the hold mechanic
      (EDT-19, DD-348): a quick press cancels and completes nothing, a full
      hold confirms once, a leave mid-hold cancels, and the fill property
      sweeps and clears.
    - `src/lib/drawer/drawer.component.spec.ts` — the `drawer-footer` slot
      (UIC-25, DD-347): projected content lands in the foot bar after the
      body, and the bar stays empty for a drawer that projects none.
    - The picker component itself lives in the webapp because it searches
      (DD-341); the chip (UIC-16/24), the box anatomy (DD-335/336) and the
      Bulma dropdown already ship.
- e2e (`nx e2e aurelius-atlas-webapp`): the scenarios below run in the
  chromium/firefox/webkit matrix against the shared dev stack, self-cleaning
  through the purge helper (DD-223: no shared-service restarts). The dev
  writer holds `atlas-write` (EDT-12). Each scenario waits for its write to
  show on the entity read before reopening the editor: the relationship
  records are searched, not joined, so a read landing right after a write can
  answer the pre-write state (CLS-12's propagation race), and the reopened
  editor reads once and keeps its answer.
    1. Add a relationship (EDT-14/EDT-16): on a seeded `DataSet`, open the
       editor, type a seeded `Process`'s name into the `inputToProcesses`
       picker, pick it, save; reopening the editor shows the chip, and the
       seeded `Process` reads the data set on its `inputs` end through the
       API (the details table cannot show either end: the legacy blacklist
       DET-11 ports verbatim lists `inputs`, `outputs`, `inputToProcesses`
       and `outputFromProcesses`, so the edge earns no property row).
    2. Remove a relationship (EDT-15/EDT-16): delete the chip, save;
       reopening shows no chip.
    3. Create with a required relationship (EDT-13/EDT-17): `ozone_bucket`
       carries the non-optional `volume` relationship attribute (probed:
       `SINGLE`, mandatory, and neither type requires a plain attribute —
       the self-contained pair; `aws_s3_object.pseudoDirectory`'s target
       chain needs `bucket` + `objectPrefix`, so it stands down). The type
       is picked in create mode, the `*` marker rides the label, and the
       save is refused while the picker is empty; picking a target the
       scenario seeds by name through the API helper lands the create and
       shows the chip on reopen.
- Storybook: `drawer` gains a foot story (UIC-25) and `holdable` gains the
  two hold stories (DD-348). The webapp ships no Storybook host and the
  picker lives outside the ui library (7.7a's precedent).
- `nx test aurelius-atlas-webapp -c ci`, `nx lint aurelius-atlas-webapp`,
  `nx run aurelius-atlas-webapp:check-purity`, `nx build aurelius-atlas-webapp`,
  `uv run aurelius-atlas-trace check` reports the EDT gaps as expected
  (local-only by ADR 056/DD-215).
