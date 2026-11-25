# 7.47 The type field leaves the editor drawer

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-873 (here). No new rule ids. Cites EDT-04 (7.7a: the create
  picker and the edit badge), DD-330 (the chosen type rides the route), VDE-02
  (7.20: the type material the picker reads), MMS-07 (7.31: only metamodel types
  are offered), MMS-09/DD-721 (7.33: the alias badge), DD-378/DD-379 (the icon
  and display-name resolution), DD-497 (the label-ordered rows), SHL-08 (the
  byte-identical catalogue string), and DD-870 (7.44: the layer rules this move
  stays inside).

## Scope

The entity editor drawer (7.46) still held two small pieces of markup that are
not the form: the create-mode type picker and the edit-mode static type badge
(both EDT-04, DD-330). This increment moves both into one new component, with no
change to what a user sees, clicks, or reads.

The change (no behaviour, template text, or string change):

- A new `search/editor/type-field.component.ts` holds `TypeField`, with its
  `.scss`. It paints the picker (`Select` over the shipped typedefs) or the
  badge (`TypeName` with the alias), nothing else. It injects no store, no
  router, and no HTTP client — the rows, the route's type, and the badge come in
  as signal inputs, and a pick rides out.
- The drawer keeps the route: the pick still navigates `create/<type>`
  (DD-330), and the seed effect still rebuilds the form from the URL. The
  drawer also answers the two facts the field cannot see: it is create mode
  (the picker flag) and what the stored entity says its type and alias are
  (the badge).
- The picker row mapping, the selection-by-name, and the badge's display name
  and icon resolution (`nameDisplay`, `typeIcon`) move into the field with
  the markup — they are only ever used to paint it.
- The spec splits the same way. `type-field.component.spec.ts` holds the four
  list/badge/pick tests with their names unchanged, plus one new test that no
  field paints before the read names a type. The drawer spec keeps the seed,
  switch, and route-reuse tests, because those pin the route, which stayed.

It does **not** deliver: any change to a string, a css class, an id, or a role
(the e2e suite pins `.aurelius-editor-picker select` by exactly that class);
the entity form moving out (Phase 5c of the webapp refactor plan); a
`Storybook` story (the webapp has none, by the ui-lib-only convention); or a
change to `java-map.md` and `deviations.md` (nothing here touches Atlas
behaviour).

## Semantics

No new rule ids. What this increment pins, as stated:

- **The field renders from its inputs alone.** `TypeField` touches no HTTP
  service, no router, and no store. Every string it prints sits in the same
  `$localize` block it sat in before (SHL-08).
- **The pick is still a navigation** (EDT-04, DD-330). The field emits the
  row; the drawer navigates; the URL still owns the type. An empty pick
  (the placeholder) is still ignored.
- **The badge still means a stored entity** (DD-330). Create mode never
  shows a badge, even though a seeded draft has a type name — the badge
  answers the read, not the draft.
- **The rows are still the metamodel types only** (MMS-07, VDE-02): the
  field maps the store's picker-types slice unchanged — same filter, same
  label order (DD-497), same identity-matched selection.
- **1,047 tests stay green** across 83 files: the same 67 editor-drawer
  tests, now 62 in the drawer spec and 5 in the field spec, plus every other
  suite untouched.
- **The trace tool sees no change.** The test names that carry EDT-04 are
  moved verbatim, so `uv run aurelius-atlas-trace check` reports the same
  single pre-existing finding (ALR-02) as before this PR.

## Java origin

Apache Atlas 2.4.0 has no Aurelius `TypeField`. The type material it reads is
already ported and specced at the store and door layers (VDE-02). Moving
Aurelius code between Aurelius files adds nothing a parity test can see, so
this increment adds no row to `java-map.md`.
