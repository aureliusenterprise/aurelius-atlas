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
