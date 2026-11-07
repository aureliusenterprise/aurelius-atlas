# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-393. The quickview is the ui drawer, not a ported quickview component

- **Status:** Proposed
- **Increment:** 7.22c
- **Date:** 2026-11-07

**Decision.** The model browser rides the `aurelius-atlas-ui` drawer (LDG-19):
`active` two-way, title, projected tab bar and body. No `Quickview` component is
ported from the legacy `libs/components`.

**Reason.** The legacy quickview is one more overlay with its own dismissal set;
the webapp already ships the drawer with the same anatomy (backdrop click, close
button, Escape — the alerts feed and the editor drawer use it), and WBP-02 bars
the legacy NgModule anyway. Building the panel on the existing drawer costs one
tab strip and keeps the dismissal behaviour uniform across the app's overlays —
one mental model for the reader, one component for the theme work to cover.

**Alternatives.** Port the legacy quickview as a new ui component. It loses:
two overlay primitives that differ in nothing a user can see. Second, a modal.
It loses: the panel is a side surface the reader reads beside the diagram, and
the modal's centred card hides the diagram it explains.

**Consequences.** The drawer's sticky `drawer-subhead` slot carries the tab bar
(DD-180's anatomy), so the tabs never scroll away — the same fix the alerts feed
uses. If a later explorer ever needs the legacy's resize handle, that is the
drawer's rule to grow, not a second component's.

### DD-394. The metadata merge is a display rule over the answer's rows

- **Status:** Proposed
- **Increment:** 7.22c
- **Date:** 2026-11-07

**Decision.** The Selection tab's properties table merges the concept's parsed
`ar3_properties` with the metadata row of the same id, spread order metadata
last (LDG-21: `{ ...properties, ...row.data }`). The rows are keyed once when
the answer arrives (`dataById: computed(...)` beside the parsed model), and no
server change joins the slice.

**Reason.** The metadata rows are the chain's provenance channel: 8.2's answer
(LM-04) carries one row per concept with `Type name`, `created_by`, and
`m4i_original_id` — the Atlas guid the diagram's node hides behind the concept
id. The legacy shows them by spreading them over the properties
(`selection.component.ts`: `{ ...properties, ...data }`), and that order is a
contract a test pins: when a concept carries a property the metadata row names
too, the row wins, because the row is what the extract just produced. The merge
stays in the panel, not the reader: the parsed model keeps the document's shape
(LDG-11), and LDG-24's View tab reuses the same rule over the view's row.

**Alternatives.** Merge at parse time into one properties dict. It loses the
provenance: a later surface (a governance view, an "open in Atlas" link keyed on
`m4i_original_id`) needs the row as a separate fact, and a merged dict cannot
come apart again cleanly. Second, show the rows in their own table. It loses
parity: the legacy's one merged table is what reviewers compare against.

**Consequences.** Duplicate `id` rows (the fixture shows the process id twice —
two relations map the same concept) collapse to the last row, as the legacy's
`dataByConceptId` object did. The 7.22b reader grows the properties field with
this slice's test (DD-389's planned consequence, now due).

### DD-395. The Browse tab drops the organization tree

- **Status:** Proposed
- **Increment:** 7.22c
- **Date:** 2026-11-07

**Decision.** The Browse tab is the view dropdown only (LDG-23). The legacy's
second part — the folder tree built from the model's `ar3_organizations` — is
not ported, and the `ar3_organizations` parse stays out of the reader (DD-389).

**Reason.** The tree's job is to help a reader find one view among a repository
model's folders. The lineage document has one view, and its folders are fixed
text the rule set emits: "Other" (the concepts), "Relations", "Views" — the
fixture shows the same three every time. A tree over a constant is decoration
that costs a `MatTree`-class component, a path index, and their tests, and it
cannot be different. The dropdown already reaches the only view the tree's leaf
would name.

**Alternatives.** Port the tree for shape parity. It loses: the e2e rule prunes
chrome that cannot change; nothing in the page varies it. Second, drop the whole
Browse tab. It loses: the legacy's Browse button is the documented entry to the
panel (7.22d's toolbar keeps it), and the dropdown is the tab's content when a
second view ever arrives.

**Consequences.** If a future producer emits multi-view models (a bigger lineage
depth, saved views), the dropdown already lists them and the tree returns as a
new rule then — no stub reserves space for it now.

### DD-396. The Model tab filters by keyword, not by fuzzy index

- **Status:** Proposed
- **Increment:** 7.22c
- **Date:** 2026-11-07

**Decision.** The Model tab's search box narrows the element and relation tables
with a case-insensitive substring match on name and type (LDG-23). The legacy's
fuzzy machinery (`FuzzySearchInputComponent`: a mnemonist inverted index plus
SymSpell) is not ported.

**Reason.** The legacy index exists because a repository model holds thousands
of concepts and its search tolerates misspellings. The lineage model holds the
entities within depth 3 of one guid — dozens of rows, all visible in two tables
while the reader types. DET-20/DD-368 made the same trade for the details
sections on the same grounds (DD-368's narrower net, cited), and one filter
idiom across the screen is one behaviour for the reader. Porting mnemonist and
SymSpell for a dozen rows would be two dependencies and their tests for no
reachable difference.

**Alternatives.** Port the fuzzy stack. It loses: dependencies, and a typo
against a list of names the reader can see is a rare failure the tables already
survive. Second, no search box at all. It loses parity with the legacy's layout,
and the box is cheap.

**Consequences.** The filter state is a signal beside the tables (no store). If
a real model outgrows the substring match, the filter widens to a tokenised
match — a new rule with a perf reason, not a ported component.
