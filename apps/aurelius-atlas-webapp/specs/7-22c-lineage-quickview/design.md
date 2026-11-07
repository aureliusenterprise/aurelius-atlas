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

- **Status:** Superseded by DD-406
- **Increment:** 7.22c
- **Date:** 2026-11-07

> Superseded in the 7.22d reader-feedback round: the reader asked for the tree
> as the place future diagrams and views hang, and the cheap nested-list shape
> costs far less than this entry feared (DD-406).

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

### DD-401. The vendored modelview2 catalogue keeps the English key names

- **Status:** Proposed
- **Increment:** 7.22c
- **Date:** 2026-11-07

**Decision.** The legacy `modelview2` catalogues disagree on one pair:
en-US defines `modelBrowser.browse.viewSelect.nameDisplayName`/`.nameDescription`
("View name", "The name of the view") while nl-NL renamed the keys to
`viewNameDisplayName`/`viewNameDescription` with the same Dutch strings. The
vendored `modelview2-nl-NL.json` keeps the English key names with the Dutch
texts, so the fixture pair is symmetric (LDG-26).

**Reason.** The bridge (DD-128) keys every trans-unit by the dictionary key
path, and both the generator and `i18n-completeness.spec.ts` require the two
catalogues to hold the same set of ids — a key that exists only in nl-NL fails
either gate. The legacy's rename never reached the en file, so the templates
reference the en names; the rename is a translation-drift artifact, not a
meaning difference.

**Alternatives.** Vendor both spellings and alias them. It loses: a duplicate
trans-unit for one string and a rule about which id a template may use. Second,
keep the nl-only names and reference those. It loses: the en catalogue would
then lack the id, and the legacy templates' names leave no choice a reader of
both sources would prefer.

**Consequences.** The vendored nl file is the one place the pair differs from
the legacy source; the divergence note in LDG-26 records it. The key is unused
until the Browse tab's dropdown labels land, so no shipped string is affected
by the rename.

### DD-410. The quickview's chrome is the legacy's: Details header, footer Close, legacy tab order

- **Status:** Proposed
- **Increment:** 7.22c
- **Date:** 2026-11-07

**Decision.** The drawer's header reads "Details" — the legacy quickview's
default `name`, which `model-browser.component.html` never overrode — with the
vendored key `search.details.components.navigation.details` (already carried by
both catalogues). Its footer holds a Close button (the legacy footer's own),
projected into the drawer's `drawer-footer` slot, dismissing through the same
path as the head's close so the selection clears with the panel (DD-403). The
tab order becomes Browse, Model, View, Selection — the legacy's `keyvalue`
order over the tabs object (`preserveKeyOrder` returns 0), not the order the
first cut guessed (LDG-19).

**Reason.** The demo and the source agree: every legacy panel reads "Details"
whichever concept opened it, and the tab strip is insertion-ordered. The first
cut's model-name header and its selection-before-view order were both guesses
that the reference contradicts; the screenshot round exists to close exactly
this class of gap.

**Alternatives.** Keep the model name as the header. It loses: what the
product's own reference UI shows, and the model name adds nothing the Browse
tab does not already say. Port the pin toggle too. It loses: a pinned panel is
meaningless for an overlay whose dismissal deselects (DD-403), and the ui
drawer has no pin state — recorded as a deviation.

**Consequences.** The viewer stops binding the model name into the panel
(the `title` input leaves the component — no caller needed it). The footer bar
shows whenever the panel does, matching the legacy; the drawer's empty-foot
hiding stays for the other drawers.

### DD-411. The entities table draws the legacy's rows: icon Type cell, three-line relationship row

- **Status:** Proposed
- **Increment:** 7.22c
- **Date:** 2026-11-07

**Decision.** The quickview's entity table copies the legacy's row templates
row for row. An element row is the narrow Type cell holding the archimate icon
for the two lineage types (`lineage_dataset`/`lineage_process` — the only two
the legacy's icon set names; every other type draws nothing, as the legacy's
icon component did when its definitions had no entry) and the Name cell. A
relationship row is one `colspan` cell with the legacy's three lines: the
source end (icon + `<strong class="truncate">` name), the middle `<em>` line —
the relation's name, else the verb its type carries (`Flows into`, the legacy
`parse-relation.ts` table's `displayName` for `lineage_relation`), then the
human-readable type in parentheses — and the target end. A relation entity
gains `sourceType`/`targetType` so each end draws its own icon (LDG-19's
index). The Type column keeps its `humanReadableType` sort key: the legacy
sorted the raw `@xsi_type`; the shipped chain's one relation type makes the
two orders identical, and the name keeps the header honest.

**Reason.** The demo screenshot and the legacy source agree on this shape;
DD-404's one-line `source → target` cell was a simplification the reference
does not have. The demo's "Flows into (Data Lineage)" middle line is exactly
what the shipped chain renders with the verb table — the earlier worry that
the verb came from producer data was wrong: it is the parser's fixed table.

**Alternatives.** Keep the single-line row. It loses: the icon-per-end and the
middle line the reader sees in the demo. Sort by raw type as the legacy did.
It loses nothing today but shows a header lie the moment a second type ships
into a table — kept as the deviation it is.

**Consequences.** The relation rows grow three lines tall; the tables page at
five rows as the legacy's do. `lineage-metamodel.ts` gains `relationVerb` (the
one-entry slice of the legacy's twelve-verb table — the rest stays with the
explorer). DD-404's arrow row shape is superseded here.

### DD-412. The Referencing views table is the legacy's Name / Description table

- **Status:** Proposed
- **Increment:** 7.22c
- **Date:** 2026-11-07

**Decision.** The Selection tab's Referencing views section becomes the
legacy's own `viewsTableConfig` table: Name / Description headers (raw config
strings, as the legacy's never-resolved translate pipe left them), the view
name in a `<th scope="row">` cell, the documentation in the `<td>`, selectable
at five rows per page, the drawn view the selected row, and a row click draws
that view (the legacy's `selectView`). Re-clicking the selected row emits
nothing — a deviation: the legacy's `deselectView` had a no-view state to
return to and the shipped chain never has one (LDG-12's first-view default).

**Reason.** The demo shows a wide view-name column and a wide description
column with no Type cell — the entities table's shape is wrong there, and the
legacy source has its own config for exactly this table.

**Alternatives.** Reuse the entity table. It loses: the second column (a view
row shows a "View" icon and no description — the demo proves that is not what
the table is for).

**Consequences.** The selection panel imports the shared table directly for
this one section. The selected-row highlight follows the drawn view, so opening
the panel from a view entity shows its row marked, as the demo's does.

### DD-413. The shared table's pagination rides above the table, as the legacy shell's does

- **Status:** Proposed
- **Increment:** 7.22c
- **Date:** 2026-11-07

**Decision.** `aurelius-atlas-ui-sortable-table` renders its pagination bar
above the table, not below. The legacy's `sortable-table-shell` puts the
`pagination-template` nav in a `.field` before the table container, and the
plain `sortable-table` wraps that shell — so every paginated legacy table, the
quickview's included, shows the page row on top.

**Reason.** The demo shows the page row above each quickview table. The shared
component had it below — a port-time slip, not a decision: no design record
and no legacy source put it there. The fix belongs in the shared component so
every screen the legacy paginates matches, not only the drawer's.

**Alternatives.** A display flag defaulting to below, flipped for the lineage
tables. It loses: the only other callers (the three browse info modals) port
legacy tables that had the page row above too — the flag would encode the slip
as a default.

**Consequences.** The info modals' tables move their page row up as well —
verified parity, not churn: their legacy originals used the same shell. The
ui suite's pagination tests read the DOM by class, so they stay green.
