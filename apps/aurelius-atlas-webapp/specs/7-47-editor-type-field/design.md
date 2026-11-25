# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-873. The type field is one presentational component, not a picker and a badge

- **Status:** Proposed
- **Increment:** 7.47
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** The create-mode type picker and the edit-mode static type badge
(both EDT-04, DD-330) move into one component, `TypeField`, in the editor
feature. It takes four signal inputs — `picker` (whether create mode shows it),
`pickerTypes` (the store's slice), `typeName` (the route's type), and `badge`
(the stored entity's raw type and alias) — and emits one output, `picked`. It
injects nothing. The picker row mapping, the row selection by name, and the
badge's display-name and icon resolution (`nameDisplay`, `typeIcon`) move into
it, because they only ever serve its own template; the drawer keeps the route
navigation, the create seed, and the form rebuild, which are the drawer's
behaviour, not the field's. `TypeField` paints exactly the two wrapper blocks
that sit above the form (`.aurelius-editor-picker`,
`.aurelius-editor-static-type`/`.aurelius-editor-type`), so the classes the e2e
suite and the drawer's specs pin move with the markup and stay byte-identical.
The single catalogue string both states share (`search.details.typeSelect.label`)
rides the field's `$localize` now, unchanged.

**Why.** Two sibling fragments of the same rule (EDT-04's "pick in create,
badge in edit") belong in one file: each is about twenty lines, and the
drawer had grown to 1,084 lines for want of a home for them. A single component
can pick one of the two states internally — the badge wins when it exists,
otherwise the picker shows when `picker` is set — which is the same precedence
the drawer's two `@if`s enforced, stated once. Keeping the field presentational
(no store, no router) is what lets it stay reviewable in one file and testable
through the drawer it mounts in; it also keeps the DD-870 layer boundary clean,
because the field reads only the editor feature's own `editor-state` types and
the `meta/` layer. Resolving `nameDisplay`/`typeIcon` inside the field follows
the precedent 7.46 set with `HistoryTab`: a presentational child resolves
display names and icons off `meta/` for its own paint, and the parent passes
raw data. The alternative — the drawer mapping rows, names, and icons and
passing them in — would leave the field a shell and keep the drawer wide for
no benefit.

**Considered and rejected.** _A `TypePicker` and a `TypeBadge` component each_ —
two files for two fragments that are one rule, and the parent still needs the
"one or the other" precedence the field already encodes. _Keep the state in the
drawer and pass the mapped rows in_ — then the drawer owns the picker's row
shape and the Select's identity-matching, which are presentation, so the drawer
stays the widest file in the feature. _Let the field inject `EditorState` and
read `pickerTypes`/`entity` itself_ — it would then reach into the store that
models the entity being written (WFE-01), where a dumb input is enough; the
drawer already reads those signals for its own reasons, and passing them keeps
the field speccable without a store. _Move the pick's navigation into the
field_ — the chosen type is the drawer's route (`create/<type>`, DD-330) and
the seed and form rebuild hang off it, so the navigation must stay with the
drawer that owns the route.

**Consequences.** `entity-editor.component.ts` drops from 1,084 to 1,060 lines
and its template from 493 to 467; `type-field.component.ts` (121 lines with its
doc) and a 10-line `.scss` take the moved markup and one rhythm rule. The
drawer's stylesheet loses the picker's `margin-bottom` rule and gains nothing;
the badge needed no rule (Bulma spaces the `field`/`label` pair). The spec
split holds the total at 1,047 across 83 files — the four list/badge/pick
tests move verbatim, and one new test pins that nothing paints before the
read names a type. The string set is unchanged, so `extract` output and both
locale fixtures stay byte-equal (SHL-08's completeness gate is untouched). No
`AGENTS.md` change: the editor feature documents its own components in their
file headers, and the webapp's removal map already covers it as one unit.
Accepted edge: `TypeField` is editor-specific as named — its badge shape is
the details header's (MMS-09) and its picker is scoped to the metamodel types
(MMS-07) — so a second consumer would generalise it, which no second consumer
asks for today.
