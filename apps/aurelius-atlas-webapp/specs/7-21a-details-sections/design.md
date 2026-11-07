# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-365. The section data path: forward walks over the entity's own relationship attributes, not a search index

- **Status:** Proposed
- **Increment:** 7.21a
- **Date:** 2026-11-06

**Decision.** Every card section seeds from the resolved entity's
`relationshipAttributes` (ERD-06: each entry carries `guid`, `typeName`,
`displayText`, `qualifiedName`, `entityStatus`, `relationshipStatus`), keeps
only `ACTIVE` edges, and resolves the guids into full entities through
`GET /v2/entity/bulk` (ERD-01, client method AEN-04). The legacy's forward
sections — a domain's entities, an entity's attributes and children, an
attribute's fields, a field's attributes and children, a dataset's fields and
children, a collection's datasets, a system's collections, children and
processes — are exactly the entity's own SET-cardinality relationship ends, so
the seed answers the same set with no server change. The bulk answer carries
each related entity's own `attributes`, `classifications`, and
`relationshipAttributes`, which is what the card body renders (the description,
the chips, the owner/steward rows). No new endpoint enters.

**Reason.** The legacy sections queried Elastic App Search: `supertypenames:
['m4i_data_attribute']` plus `parentguid`/`derived*guid` filters (the legacy
source: `apps/atlas/src/app/search/details/*/*-cards/*.component.ts`), and
those fields existed only because a Flink job computed them at index time (the
legacy source: `libs/m4i-flink-tasks/.../entity_created/entity_created.py`).
DD-140 refused that index for this product, and the alternatives are bigger: a
server-side relationship-search port (`GET /v2/search/relationship/{guid}`,
Atlas's own `RelationshipSearchREST`, which this server has never shipped)
answers only one hop and still needs the full entities fetched by hand; a
derived-index replica inside the store would rebuild, per write, the
denormalisation this architecture exists to avoid (ADR 047). The forward walk
is exact for the sections in scope, rides two reads already under contract
with parity scenarios, and keeps the details screen's request count at one
plus one-per-chunk. The reverse sections (the dataset's related entities,
producers, consumers) cannot ride it — a browser holds only the opened
entity's own ends — so they are named deferrals, not silently wrong empties.

**Alternatives.** (a) Port `GET /v2/search/relationship/{guid}` first and query
it per section (deferred as its own increment: it is new server surface with
Atlas parity to specify, and it still returns `AtlasLineageEntityInfo`-style
headers, not the full entities the cards need, so the bulk join stays).
(b) Reuse `POST /search/basic` with attribute filters (refused: entity search
indexes own attributes only — `search_fields()` never indexes relationship
ends — so "attributes of this entity" is not a searchable condition; the walk
is the only honest forward path today). (c) A server-side sections endpoint
that composes the walk (refused for now: it is a second contract duplicating
two live reads for one screen; if request counts ever demand it, a DD can add
it without touching this slice's components — the store is the seam).

**Consequences.** Section counts come true before the cards resolve (the seed
is synchronous with the entity read), which the legacy could not do. The bulk
route takes its guids as repeated query parameters, so the store chunks at 25
(a browser/edge-safe URL, not a server limit — the server caps nothing). The
missing-guid case is real (a related entity deleted between the seed read and
the bulk read) and renders as no-card-keeps-count.

### DD-366. One section-config table replaces the legacy's nine type components

- **Status:** Proposed
- **Increment:** 7.21a
- **Date:** 2026-11-06

**Decision.** The seven layouts are one typed config table
(`details/sections/section-config.ts`): per type, the card sections (anchor,
title key, seed keys), the stats entries, the navigation entries, and the
People-box flag. One `DetailsLayout` component renders any row. Dispatch is a
lookup on the entity's `typeName`, falling back to its super types via the
typedef cache, and to the DET-01 default layout.

**Reason.** The legacy carried nine sibling folders with copy-pasted Bulma
skeletons that differed only in their box ids, their title keys, and which
cards components they projected (compare `details/entity/` and
`details/collection/` under `.scratch/aurelius`); the shared chrome lived in
injected per-type maps (`cardsByType`, the App Search search services bound by
provider). A config table is that map made explicit: the spec's table and the
code are the same object, a reviewer diffs them, and the eighth type (process,
person, or a custom sub-type) is a row. The super-type fallback is the same
rule the legacy dispatch used (`getSuperTypes`), so a subtype of
`m4i_data_entity` lands on the entity page as it did in the demo. Reading the
supertypes from `TypeDefsService`'s cache (7.3) adds no HTTP call; the details
screen already guarantees the typedefs are loaded before its data (the editor
drawer's precondition, DD-325).

**Alternatives.** (a) Nine components ported 1:1 (refused: nine copies of
markup this repo would then keep in sync, and the legacy's differences were
copy drift already — `subSystems` versus the section's `childSystems`-style
naming). (b) Server-driven layout metadata (refused: invents a contract with
no Java twin; ADR 046 keeps the server contract Atlas's).

### DD-367. One uniform card body until the data for the legacy's per-type bodies exists

- **Status:** Proposed
- **Increment:** 7.21a
- **Date:** 2026-11-06

**Decision.** Every card renders the same body: classification chips, the
description text (`definition` then `description`, the DD-320 order) as
markdown, and the card entity's own people rows. The legacy's per-type card
bodies (`components/cards/*/[type]-details-card.component.html`) are not
ported; the 7.13 `entity-card` shell stays, with its quality column off.

**Reason.** Read side by side, the nine legacy bodies lead with the same two
things: a `dqscore_*` pie or badge column (no source, DD-369) and a breadcrumb
trail (no source, DD-317). What is left differs only in which of the same
fields it prints first. The uniform body is the honest shape of the data that
exists; when the governance-quality slice (7.8) brings scores, it adds the
quality slot back to every card at once, and a per-type order can return as a
config tweak. The card's badge alias comes from `attributes.typeAlias` (the
legacy card read the same attribute into its `typeAlias` input), so type
identity survives without the bodies.

**Alternatives.** Port the nine bodies minus their sourceless slots (refused:
same markup twice over with nothing left to differ on). Port them whole with
empty slots (refused: placeholder chrome in a real product screen, the same
refusal DET-13 makes of mock data).

### DD-368. Search, sort, and paging run client-side over the resolved set

- **Status:** Proposed
- **Increment:** 7.21a
- **Date:** 2026-11-06

**Decision.** A section resolves its whole seed (chunked bulk reads), then
filters by keyword, sorts, and pages 9 at a time in the browser. The keyword
matches display text, `name`, `qualifiedName`, and the description text,
case-insensitive. The sort options are Relevance (seed order) and Name; the
direction button reverses.

**Reason.** The legacy sent each keystroke's term and each sort change to App
Search because the index held every entity; here the seed _is_ the whole set,
so a server round trip per interaction would re-fetch what the browser is
holding. The match-field list is narrower than App Search's analysed document
(the legacy matched its `name`/`qualifiedname`/definition-derived fields), a
recorded deviation: it drops DQ-score text that has no source anyway, and the
set is small enough that a missed match on exotic attributes is a cheaper
defect than a request storm. Nine per page keeps the demo's loading rhythm.
Chunking (25 guids) bounds the URL, not the set: an entity with 31 attributes
costs 2 bulk calls, and the demo's own "31 result(s)" page resolved its cards
one App Search page at a time — the card count here is exact and immediate
where the legacy's count came from the query total.

**Alternatives.** Query `POST /search/basic` per section (refused twice over:
DD-365's index argument, and `SearchParameters` has no relationship condition).
Virtualise with per-page bulk reads (deferred: page-per-9 bulk reads cost more
requests for the same rows; if a pathological entity appears, the store keeps
the chunk seam and a DD can window it).

### DD-369. Sourceless sections render nothing, not zeros

- **Status:** Proposed
- **Increment:** 7.21a
- **Date:** 2026-11-06

**Decision.** The Data Quality box, the score stats, the DQ sort options, the
card DQ badges, the field's Data Quality Rules section, and every deferred
navigation link are absent from the seven layouts in this slice. A stats entry
with no source drops its whole cell (the legacy's own `noDataQuality` branch
dropped the value, not zeroed it).

**Reason.** The legacy's DQ numbers were Flink-computed `dqscore_*` documents
(`entity_created.py`, the governance-rule evaluators); this server evaluates no
rule expressions (the `m4i_gov_data_quality` entities carry expressions like
`length('dataDomain', 1) | length('parentEntity', 1)` and nothing interprets
them). Rendering zero or an empty box would advertise a broken feature; the
roadmap already owns the real one (7.8 "Governance quality and domains"). The
deferral table names each returning piece, so the demo's page assembles
section by section across 7.21a, 7.21b, and 7.8 with nothing hidden.

**Alternatives.** Ship the rule evaluator in this slice (refused: it is a
server-side feature — expression grammar, evaluation, per-entity results —
far bigger than the webapp slice and without its own spec yet; 7.8's territory
by the roadmap's wording). Ship disabled placeholders (refused: DET-13's
no-mock-data rule by the same reasoning).

### DD-370. The descendants toggle and the facet filter dropdown stay out

- **Status:** Proposed
- **Increment:** 7.21a
- **Date:** 2026-11-06

**Decision.** The card sections ship without the legacy's "show all
descendants" checkbox and without the App Search facet dropdown inside the
filter control. The filter control's chrome (the dropdown wrapper) is out too —
with nothing to put in it, the demo's filter icon would open an empty menu.

**Reason.** Both controls changed the App Search query's _field_, not its
text: `parentguid` to `deriveddataentityguid` and a facet on `derivedperson` /
`dataqualityruledimension` (the legacy's `show-descendants-control.directive`
and `filter` components). The derived fields are DD-365's refused index, and a
transitive-closure walk over the live reads would be unbounded recursion the
browser cannot price. Facets have no Aurelius answer either: 7.4b (SDX) is the
slice that decides what this product's facets are, over quick-search
aggregations — inventing a per-section facet vocabulary here is exactly the
premature design ADR 053's review culture refuses.

**Alternatives.** Ship the toggle as a BFS walk (refused: unbounded,
unspecifiable cost; if a real catalogue needs it, a relationship-search server
slice bounds it in ES and a DD adds the control back). Ship a dead toggle
(refused, the DD-369 rule).

### DD-371. The type badge carries the alias without the icon

- **Status:** Proposed
- **Increment:** 7.21a
- **Date:** 2026-11-06

**Decision.** Where the legacy badge led with a per-type icon, this slice's
badge shows only the alias and base type: `attributes.typeAlias` as a
non-empty string becomes the `type-name`/`entity-card` alias input with
`showBaseTypeName`. No icon map enters the webapp.

**Reason.** The legacy icons came from `iconsByType`, an app-level type→icon
map (the legacy's `details/components/...cards config` consumers), and the
editor slice already refused that map for its chips: "the type icons the legacy
chips led with — Never — `iconsByType` is app metadata the webapp does not
port" (7.7c, DD-341). The details screen is the same product surface; the
second refusal keeps the story true. The alias itself is real data riding the
entity (the demo's cards show "Data Attribute" beside the base type), so it is
in scope for the badge the 7.13/7.16 components already take.

**Alternatives.** Ship the icon map (refused by DD-341's precedent; if a later
branding slice wants type icons, it owns the map, the palette classes, and the
fallback — a DD supersedes this row then). Drop the alias too (refused: it is
the demo's clearest type signal and free).

### DD-374. The visual parity pass: five demo-measured corrections

- **Status:** Proposed
- **Increment:** 7.21a
- **Date:** 2026-11-07

**Decision.** A side-by-side inspection of the details screen against the
legacy demo (desktop and a 390px viewport) produced five corrections, each
measured on the demo page. One, the card badge, is a behaviour change; the
other four are styling.

1. The link ink. The brand sheet pins `--bulma-link`, but Bulma 1 inks
   text links from `--bulma-link-on-scheme-l`, which our pin never touched.
   The app rendered links at Bulma's default blue while the demo inks them
   at #0073dd. The brand sheet now pins `--bulma-link-on-scheme-l` to the
   same lightness the `--bulma-link` pin uses, and the dark-ink mixin
   re-pins it to the dark value (the DD-156 pattern: a `:root` pin
   out-cascades the dark scheme block).
2. The corner ramp and the border channels. Bulma 1 raised the radius ramp
   (.375rem/.75rem) and tinted its border channels, so our boxes read
   12px-round with warm-grey borders against the demo's 6px/4px neutral
   #dbdbdb. The brand sheet pins `--bulma-radius` to 0.25rem (controls,
   tags, and via `.card { --bulma-card-radius: var(--bulma-radius) }` the
   cards all read 4px), `--bulma-radius-large` to 0.375rem (the `.box`
   reads 6px), and zeroes the border hue/saturation channels.
3. The hero gradient. Bulma 1 rebuilt `is-bold` as HSL offsets from the
   primary; the demo ships Bulma 0.9.4's literal
   `linear-gradient(141deg, #009e6c, #00d1b2 71%, #00e7eb)`. The brand
   sheet overrides the rule with the literal.
4. The People separator. The legacy row renders `Label` + `" : "` with a
   thin gap before the colon; ours glued the colon to the label. The
   `people-box` part now emits the legacy spacing. The header gap under
   the title is the same family: the demo nets 4px (h1 24px, badge
   -20px), Bulma 1's `.title:has(+ .subtitle)` zeroes ours, and the
   details sheet gives the badge a 4px margin instead.
5. The card badge (behaviour). The details screen passed
   `showBaseTypeName` to the cards, so each badge read
   "Data Attribute (m4i_data_attribute)". The legacy card template never
   passes it; only the header's `entity-type-name` does. On the demo the
   card badge shows the alias alone, and on a phone the long suffixed
   badge is what squeezes the card title out of its flex line. DET-26
   narrows to header-only.

**Reason.** Each value came off the live demo through computed-style
probes, not from reading Bulma's source and guessing. The two structural
ones (the link token, the radius ramp) explain why the app "looked
slightly off" everywhere at once: a component-level fix would have chased
one symptom per screen. The card badge is the one visible bug a user hits
without a stylesheet open: on a phone, an attribute card's title simply
disappeared.

**Alternatives.** Restyle each component (refused: the deltas are
theme-level, and every screen pays for them). Keep the card suffix (used
to: DET-26 as written; refused once the legacy template and the phone
collapse were measured). Pin `--bulma-control-radius` directly (refused:
Bulma's `:root` already maps it to `--bulma-radius`, so the second pin
would drift).

### DD-375. The keyword filter follows the typing; the control row owns its spacing

- **Status:** Proposed
- **Increment:** 7.21a
- **Date:** 2026-11-07

**Decision.** Two follow-ups to the parity pass (DD-374), both on the card
section's header.

1. Live filtering (behaviour). The keyword filter follows every keystroke,
   and clearing the box by backspace restores the set. DET-20's
   on-submit-and-clear rule narrows accordingly: submit and clear still
   work (the ui input's contract is untouched), they just no longer gate
   the filter. The paging window returns to its first page on each text
   change, so a narrowed set shows from the top.
2. The control row (styling). The sort group and the search box sit on one
   explicit gap row. The section scss drops the sort field's stray
   bottom margin and the row's right margin, which Bulma's
   `.field:not(:last-child)` rule put there.

**Reason.** The user asked for the typing to filter. The legacy could not:
its search input emitted `queryChanged` per keystroke, but the cards list
bound only `querySubmitted`, so every keystroke was dropped until Enter or
the button (the legacy sources: `libs/components/src/lib/simple-search-input/
simple-search-input.component.ts`,
`apps/atlas/src/app/search/details/components/details-cards-list/
details-cards-list.component.html`). The Aurelius filter is a client-side
`includes` over cards the browser already holds (DD-368), so typing costs
nothing and the submit step only delays the answer the user can see. The
deviation is recorded because DET-20's old wording cited the legacy.

The misalignment was the same family as DD-374's rhythm items. Bulma gives
a `.field` that is not the last child a 12px bottom margin. In the demo the
sorting field is the level item's only child, so the rule never fires. Our
markup wraps the search box in its own div, so the sort field is "not last"
inside `.level-right` and carries the margin; the centered level splits it
and lifts the select 6px above the input (measured: select top 728.5, input
top 734.5). When the row stacks below the widescreen breakpoint, the old
12px right margin indented the select off the search box's edge. The row's
spacing belongs to the row: an explicit `gap` on `.level-right` and the
field's margin off fixes both orientations.

**Alternatives.** Keep submit-only filtering (refused: the user asked; and
a client-side filter has no reason to wait). Debounce the keystrokes
(refused: there is nothing to debounce — no request leaves the browser;
if a server search ever rides this input, that slice adds its own
debounce). Zero every `.field` margin app-wide (refused: Bulma's form
stacking depends on it; only this row's field is wrong).

### DD-376. The stacked card-section header uses the box's width

- **Status:** Proposed
- **Increment:** 7.21a
- **Date:** 2026-11-07

**Decision.** Below Bulma 1's level breakpoint (768px) the card-section
header stops centering its stacked groups. The level and both its groups
stretch; the title and count sit flush left as blocks; the sort field
takes the full width, its select control growing so the row spans like
the search box under it (the search box already does — its `control`
carries `is-expanded`). DET-21 carries the one-line rule; the shape is
measured in the browser at 390px (control row 44→346 of the 24→366 box,
select 263px) and the desktop row is untouched (DD-375's alignment
re-measured green).

**Reason.** The user asked: on a phone the title and controls floated
centered in the box, wasting the width. Two facts made this a section fix
and not a theme one. First, Bulma 1 dropped `.level.is-widescreen` — the
class our markup carries from the legacy template matches nothing in
Bulma 1's CSS, so the level stacks at its own 769px breakpoint, not the
legacy's widescreen one; the media query must match Bulma's real
breakpoint or it fights the cascade. Second, the demo centers the same
stacked groups (its `level-left`/`level-right` inherit Bulma 0.9.4's
centering below widescreen) and its cards overflow the phone screen at
the same time — the stacked demo is the broken half of the parity rule
(DD-374's own criterion), left behind by choice. The legacy stacked
controls did stretch where they could: its sorting field carried
`is-expanded` (`details-cards-list.component.html`), which is what the
stretched sort row here keeps.

**Alternatives.** Center as the demo does (refused: the user asked, and
the demo's stacked layout is broken anyway). Keep `is-widescreen` alive
with our own media query at 1215px (refused: it changes where the row
breaks, and Bulma 1's own stacking point is the shape the rest of the
screen already follows). Restyle `.level` app-wide (refused: every other
level on the site may want Bulma's centering; only this header's stacked
shape is wrong).

### DD-377. The card grid caps at three across; a long card title ellipsizes

- **Status:** Proposed
- **Increment:** 7.21a
- **Date:** 2026-11-07

**Decision.** Each card column of a section's grid carries Bulma's
sizing helpers `is-half-tablet is-one-third-desktop` (the caller's
projected div, DET-22): three cards across on a desktop at most, two on
a tablet, one full-width on a phone. The section's stylesheet drops the
ported `.column` rule (min-width 333px, stretch) — it never matched, see
**Reason**. The `entity-card`'s title shows one line: nowrap, overflow
hidden, `text-overflow: ellipsis` on the `.media-content .title`, with
the whole name kept in the anchor's `title` attribute (amending UIC-12
in its own spec, 7.13).

**Reason.** The real demo dataset (the sample export, imported through
`admin/import`) puts eight dataset cards in one Fields section, and six
sat on one row: Bulma's base `.column` is `flex-grow: 1` with no width,
so columns only stop sharing a row when a width or min-width stops
them. The long hyphenated qualified names then broke at every hyphen,
which rendered the titles downward, one fragment per line. The legacy
never showed this: its cards-list built its own column divs, so its
component rule `min-width: 333px` matched them and three per row fell
out (measured: 427px card columns in the demo). Ours projects the
caller's cards (WBP-04), and a component's scoped rule never reaches
projected content — the ported rule was dead on arrival, and with it
the legacy's cap. The helpers are Bulma's idiom for the cap (the demo's
own grid has no more structure than a third per row at its width); the
ellipsis is what the user asked for and is the shape the legacy used
elsewhere for one-line text (`bread-crumbs.component.scss`, the
relationships input). A clipped title keeps its whole text in `title`
because the card links to the entity — the name must stay readable.
Measured after the change: 3/row at 1280px+ (rows of 3, 3, 2), 2/row at
1000px, one full-width column per row at 390px; a forced long name
clips at one line (27px high) with the ellipsis.

**Alternatives.** Port `min-width: 333px` in the caller's stylesheet
(refused: it caps at three only by accident of width — an ultrawide
screen still gets five, and the user asked for a max of three). A
`grid-template-columns: repeat(auto-fill, minmax(…))` of our own
(refused: the columns are Bulma's, the helpers are the platform's
answer, and a CSS grid fights the `.column` padding model). Ellipsize
with Angular's CDK instead of CSS (refused: CSS does it in one line and
the link keeps its click target). Scope the ellipsis to the details
screen only (refused: the shared card is the component that clips, and
the results screen's rows are full-width, where an unclipped title
never reaches the ellipsis — checked with the sample data).
