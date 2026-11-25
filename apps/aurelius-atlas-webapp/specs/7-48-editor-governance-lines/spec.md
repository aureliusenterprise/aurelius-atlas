# 7.48 The governance banner leaves the editor drawer

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-874 (here). No new rule ids. Cites EDT-24 (7.7a as amended by
  12.7: the banner lines under a control), DD-446/DD-498 (the validate round and
  its verdicts), VEV-02 (7.33: the verdict answer shape), VEV-03 (an unread rule
  renders nothing), VEV-09/DD-636 (an `anyOf` verdict rides every control it
  names), SPA-06/DD-633 superseded (the retired key borrows nothing), and DD-870
  (7.44: the layer rules this move stays inside).

## Scope

The entity editor drawer (7.46) still held one piece of repeated markup that is
not the form: the governance banner lines that sit under each control and each
relationship picker (EDT-24 as amended by 12.7, DD-446/DD-498). They were one
shared `ng-template` rendered twice through `NgTemplateOutlet`. This increment
moves them into one new component, with no change to what a user sees, clicks,
or reads.

The change (no behaviour, template text, or string change):

- A new `search/editor/governance-lines.component.ts` holds `GovernanceLines`,
  an inline-template component. It paints one line per verdict it is handed —
  the warning triangle or the success circle by the boolean `compliant`, then
  the verdict's message, at the legacy's small size — and nothing else. It
  injects no store, no router, and no HTTP client; the verdicts come in as one
  signal input.
- The drawer keeps the routing of verdicts to controls: `validationItems(name)`
  stays, because deciding which verdicts measure a control (a verdict rides its
  `attribute` and every `anyOf` alternative, VEV-09) is the drawer's job, not the
  lines'. The two `NgTemplateOutlet` calls become two component mounts —
  `GovernanceLines` fed by `[verdicts]="validationItems(field.name)"` — and the
  shared `ng-template` and the `NgTemplateOutlet`/banner-icon imports go away.
- The validate round itself (EDT-23: the debounced `validateDraft`, its
  generation guard, and its quiet swallow on failure) is untouched — it stays
  the drawer's, because it drives the store the form reads, not the paint.
- The spec splits the same way. `governance-lines.component.spec.ts` holds the
  four banner render tests with their names unchanged. They still drive the whole
  drawer, which owns the verdict routing, so the banner's rule ids stay
  attributed to the drawer. The drawer spec keeps the validate-round tests
  (EDT-23), which are not about the lines.

It does **not** deliver: any change to a string, a css class, an id, or a role
(the banner lines carry `data-gov-line`, and the e2e suite pins it, unchanged);
the entity form moving out (Phase 5c-part2 of the webapp refactor plan); a
`Storybook` story (the webapp has none, by the ui-lib-only convention); or a
change to `java-map.md` and `deviations.md` (nothing here touches Atlas
behaviour).

## Semantics

No new rule ids. What this increment pins, as stated:

- **The lines render from their input alone.** `GovernanceLines` touches no
  HTTP service, no router, and no store. It paints the verdicts handed to it and
  says nothing else; no verdict, no lines (VEV-03).
- **The verdict-to-control routing stays the drawer's** (EDT-24, VEV-09,
  DD-636). `validationItems` still decides which verdicts measure a control — a
  verdict's `attribute` and every `anyOf` alternative — so one rule still paints
  under each control it names, and the component never counts a rule twice.
- **The icon pair is unchanged** (EDT-24, DD-446): the warning triangle or the
  success circle by `compliant`, in Bulma's icon seat, at `is-size-7`.
- **The retired key still borrows nothing** (SPA-06, DD-633 superseded): a
  verdict that names no control renders no line, whether the drawer routes it
  or not.
- **1,047 tests stay green** across 84 files: the same 62 editor-drawer tests
  with the four banner tests now in the new spec, plus every other suite
  untouched (83 files before, 84 now that the lines have their own file).
- **The trace tool sees no change.** The test names that carry EDT-24 are moved
  verbatim, so `uv run aurelius-atlas-trace check` reports the same single
  pre-existing finding (ALR-02) as before this PR.

## Java origin

Apache Atlas 2.4.0 has no Aurelius `GovernanceLines`. The verdicts it paints are
already ported and specced at the door layer (VEV-02). Moving Aurelius code
between Aurelius files adds nothing a parity test can see, so this increment adds
no row to `java-map.md`.
