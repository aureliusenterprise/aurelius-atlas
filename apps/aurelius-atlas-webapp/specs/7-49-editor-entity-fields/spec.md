# 7.49 The editor's field controls leave the drawer

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-875 (here). No new rule ids. Cites EDT-03 (7.7a: the form the
  for-type chain builds, every kind it renders), EDT-07 (the error line under a
  control), EDT-11 (the label's `for` seat), EDT-20/DD-352/DD-353 (the markdown
  field and the labels it prints), FORM-REQ-001 and FORM-ERR-002 (DD-354: the
  required star announced, the error line named), EDT-33/DD-722 (the catalogue
  label beats the displayName), SHL-08 (the string catalogue's completeness),
  DD-874 (7.48: the banner move this one follows), and DD-870 (7.44: the layer
  rules this move stays inside).

## Scope

The entity editor drawer (7.46) had one last piece of repeated markup of its
own: the loop that turns each resolved field into its control — the text,
number, boolean, enum, multi and markdown kinds with their label, required star
and error line. This increment moves that loop into one new component, with no
change to what a user sees, clicks, or types.

The change (no behaviour, template text, or string change):

- A new `search/editor/entity-fields.component.ts` holds `EntityFields`, a
  template component. It renders every kind the drawer's loop rendered, in the
  same order, with the same classes and ids — the `data-field` block, the
  `label.label` seat, the red star and its `aria-hidden`, the `#editor-<name>`
  control, the `#editor-<name>-error` line, and the banner under the control. It
  injects no store, no router, and no HTTP client.
- The drawer keeps every piece of form state it had. `form` (the signal form and
  its rules, DD-354), `values` (the model the seed effect writes), the validation
  round (EDT-23), the save and its door body (EDT-06), the conflict re-edit
  (VDE-07) and the name-taken line (VDE-08) all stay where they were — the
  component is handed the form and the model and answers to the drawer for the
  two edits only it can see (a chosen enum row, a deleted multi row).
- `errorFor` and `verdictsFor` arrive as function inputs (`showError` and
  `validationItems`, now arrow properties so they keep their `this`). The typed
  per-kind slot readers the loop needed (`textField`, `numberField`,
  `booleanField`, `multiRows`, `enumRows`, `enumSelected`) and the markdown
  field's three labels move with the loop; `EditorValue` and `EnumRow` move to
  `form-fields.ts`, their owner.
- The spec splits the same way. `entity-fields.component.spec.ts` holds the six
  control-render tests with their names unchanged. They still drive the whole
  drawer, which owns the field set, the form, and the save, so the render rule
  ids stay attributed to the drawer. The drawer spec keeps the save, conflict,
  notification, and validation tests, which are not about the controls.

It does **not** deliver: any change to a string, a css class, an id, or a role
(the controls keep `#editor-*`, `data-field`, and the e2e pins unchanged); the
drawer's form state or save moving out (that is Phase 5c-part2, not this one); a
Storybook story (the webapp has none, by the ui-lib-only convention); or a
change to `java-map.md` and `deviations.md` (nothing here touches Atlas
behaviour).

## Semantics

No new rule ids. What this increment pins, as stated:

- **The controls render from their inputs alone.** `EntityFields` touches no
  HTTP service, no router, and no store. It paints the fields handed to it over
  the form handed to it; the two writes it can make (enum pick, multi delete)
  go out as outputs the drawer already answered.
- **Every kind still renders as EDT-03 states.** The order, the label seat
  (EDT-11), the required star (FORM-REQ-001), and the error line with its
  `aria-describedby` (FORM-ERR-002) are byte-identical; the markdown field still
  carries its `required` through the shared editor and still prints the labels
  DD-353 parked next to it (EDT-20, DD-352).
- **The catalogue label still wins** (EDT-33, DD-722) and the raw name still
  falls back — that precedence lives in the field builder (`form-fields`), which
  this move does not touch.
- **1,047 tests stay green** across 85 files: the same editor tests with the six
  render tests now in the new spec, plus every other suite untouched (84 files
  before, 85 now that the controls have their own file).
- **The string catalogue is unchanged.** The three markdown labels move with the
  loop under the same ids, so both locale fixtures stay byte-equal (SHL-08).
- **The trace tool sees no change.** The test names that carry EDT-03, EDT-07,
  EDT-20, FORM-REQ-001 and FORM-ERR-002 are moved verbatim, so
  `uv run aurelius-atlas-trace check` reports the same single pre-existing
  finding (ALR-02) as before this PR.

## Java origin

Apache Atlas 2.4.0 has no Aurelius `EntityFields`. The form it renders is
already ported and specced at the drawer (EDT-03). Moving Aurelius code between
Aurelius files adds nothing a parity test can see, so this increment adds no row
to `java-map.md`.
