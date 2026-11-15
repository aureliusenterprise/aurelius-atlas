# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an
accepted entry is never edited except its status line, and a changed decision is a new entry that
supersedes the old one.

## DD-618. The card section part grows the funnel and its popover

- **Status:** Proposed
- **Increment:** 16.5e
- **Date:** 2026-11-15
- **Supersedes:** none

**Decision.** `DetailsCardSection` grows the legacy filter dropdown (UIC-42): a funnel button
before the sort select that opens and closes the section's facet popover. The part owns only the
opening, the chrome labels, and the active mark; every facet group, row, count, and tick state
arrives as an input and every tick leaves as one output carrying the group key and the value.
The popover renders the groups through the existing `FacetList` component (UIC-33..35), and an
empty set renders the catalogue's "No filters available." line inside the popover.

**Reason.** The legacy put the same dropdown in the one shared `details-cards-list` component and
filled it from the engine's facet answer (`.scratch/aurelius`
`details/components/details-cards-list/details-cards-list.component.html`). The part already owns
the section's whole chrome — the count-line reset, the sort select and direction button, the
keyword field — because one renderer draws all ten pages (DD-366); the funnel belongs there, not
in each screen. `FacetList` is already the legacy `filter`/`facet`/`check-box` trio rebuilt dumb
for the results sidebar (DD-424): the same menus, the same five-row slice with show-more, the
same tick contract. A second facet menu would fork that chrome a second time. The part stays
dumb (WBP-04, DD-154): the store owns what a tick does.

**Alternatives.**

- A popover per screen (results already owns its sidebar): the details sections would lose the
  one-renderer rule and each screen would carry the dropdown markup (fails DD-366).
- The funnel as a content child projected beside the sort control: the sort control is the
  part's own (DET-21) and the two are one addons group in the legacy; projecting the button
  outside would split one control across two components for no gain.

**Consequences.** The section header grows one control on every page; a section with no groups
still shows the funnel, as the legacy showed the empty dropdown's "No filters available." line.
The part's public surface gains three inputs (`facets`, `filterLabel`, `notAvailableLabel`) and
one output (`facetToggled`), all in DD-136's caller-labelled form. Stacked (the section's own
width at or under Bulma's 768px, DD-376's container rule), the funnel rides left of the sort
row and the search box spans the line under it — the review of the first cut rejected the
funnel floating alone on a line above the controls; the place "before the sort control" holds
in both layouts. The `Stacked` story pins the geometry (DD-618's shape lives in the visual
tests, not in e2e, per the layout rule).

## DD-619. The facet rows are derived client-side from the resolved cards

- **Status:** Proposed
- **Increment:** 16.5e
- **Date:** 2026-11-15
- **Supersedes:** none

**Decision.** `RelatedSectionsState` derives each section's facet rows and counts from the cards
it already resolved, with no new request: a chain group counts the cards' stored derived
relations of its type (`relations`, attribute `m4i_system` / `m4i_collection` / `m4i_dataset` /
`m4i_data_domain` / `m4i_data_entity`, by entity name); People counts the `m4i_person` relation
names; Type Name counts the card's `typeName` under its dictionary name (DET-26); Name counts
the display text. Each section asks the groups its legacy component asked:

| Section (anchor)                                                                                                                                                                                                                    | Groups, in legacy order                   |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| domain `related-entities`, entity `related-attributes` / `related-entities`, field `related-fields`, dataset `related-fields` / `related-datasets`, collection `related-datasets`, system `related-collections` / `related-systems` | People                                    |
| attribute `related-fields`                                                                                                                                                                                                          | System, Collection, Dataset               |
| field `related-attributes`                                                                                                                                                                                                          | Data Domain, Data Entity, People          |
| dataset `related-producers` / `related-consumers`, system `related-processes`, process `related-systems`                                                                                                                            | Type Name, System                         |
| process `related-inputs` / `related-outputs`                                                                                                                                                                                        | Type Name, System, Collection             |
| person `governance-roles`                                                                                                                                                                                                           | Type Name, Data Domain, Data Entity, Name |
| rule `related-fields`, field `related-rules`                                                                                                                                                                                        | none ("No filters available.")            |

**Reason.** The legacy rows came from the App Search engine's facet aggregation over the same
documents the section resolved (the per-section `facets` ask in each legacy `*-cards`
component). 16.5d moved the resolve to the view door (DD-615), and the door's card already
carries the aggregated fields themselves: its `relations` field is the stored `derived*` arrays
verbatim (AVS-02, LAS-05) — the same source the legacy engine counted — plus `typeName` and
`displayText`. Counting those arrays over the resolved set answers the same rows with no server
change, and the filter then composes with the keyword, the sort, and the paging, which are
already client-side over that set (DD-368). A server facet would re-query the door per
interaction for a set of at most a few hundred cards the browser already holds. The demo shows
the direct ends, not the breadcrumb walk: its Fields card trails through `change-event` yet the
Dataset facet lists only the cards' own `deriveddataset` ends. The client rule copies that
source exactly (DV-168 records the types with no card field).

**Alternatives.**

- Door facets asked per section (`facets: {relations...}`): the door facets index fields, not
  relation names inside a card, so the door would gain relation-name facet machinery for one
  screen (fails 16.6's plan to retire facet machinery with the wire, and re-queries per tick).
- A second request per section for its facet counts: doubles the door traffic to re-read cards
  the store already holds (fails DD-615's one-pass resolve).

**Consequences.** Rows and counts appear as chunks resolve, like the cards do; a failed or
deleted relation contributes no row (DET-18 keeps it out of the cards anyway). The rule page and
the field's rules box have no legacy ask and show the empty popover; the person box's dimension
and rule-type groups have no card field and are not asked (DV-168).

## DD-620. Selections compose in one query object and counts ride the filtered set

- **Status:** Proposed
- **Increment:** 16.5e
- **Date:** 2026-11-15
- **Supersedes:** none

**Decision.** The selections live in the section record as one map of group key to chosen values,
mirroring the legacy `filters.all` shape (`check-box.service.ts`): within a group a card matches
when it carries any chosen value, across groups when it matches every group, and the keyword
ANDs over all of it. The rows and counts derive over the set that the keyword and the selections
already filtered — a row at zero disappears, a checked row with it, and the last untick returns
it. The count line shows the seed count with no keyword and no selection and the filtered count
with either; the reset link clears keyword, selections, and sort together.

**Reason.** These are the demo's measured semantics, and both fall out of the legacy shape: one
key per group in `filters.all` gives OR within the group and AND across it for free, and the
empty-array key deletion is why an untick costs nothing. The Elasticsearch terms aggregation
counts the query's hits, so a value with no matching hit leaves the popover — the behaviour
measured on the live demo (the count line moved 3 → 1 while the unticked `hr` row vanished with
it). DD-426's seen-rows rule (rows stay at their last count) belongs to the results sidebar,
where the type facet re-narrows the whole query; copying it here would keep dead rows that the
demo itself drops. What marks the funnel active is the legacy's `isEqual`-on-the-query-object
test, taken as written — the review on the open PR kept the demo's behaviour, and DD-623
records that reading.

**Alternatives.**

- Re-query the door per tick (the legacy's every-interaction round-trip): the browser holds the
  whole seed set, so the round-trip buys nothing (fails DD-368's client-side posture).
- Keep unticked rows at their last count (DD-426's seen set): rows that match nothing sit in the
  popover and beg a click that shows an empty grid — the demo drops them.

**Consequences.** One filter pass (keyword then groups) feeds the count line, the grid, the
paging, and the facet rows, so all five always agree. A selection can hide every card and leave
the count line reading `0 result(s)` with the grid empty — the reset link recovers, as DET-20
already prescribes.

## DD-621. An unresolved card hides while any selection is active

- **Status:** Proposed
- **Increment:** 16.5e
- **Date:** 2026-11-15
- **Supersedes:** none

**Decision.** While a facet selection is active, a card that has not resolved is out of the
filtered set (and out of the counts). While no selection is active it stays, as DET-18's loading
row. The keyword rule is unchanged: an unresolved card still matches on its seed's own texts.

**Reason.** The store cannot test a field the card has not arrived with (VCF-02's resolve is
chunked), so the honest reading of "only cards carrying the value" excludes the unknown. Keeping
loading rows in would paint rows the user did not ask for until the last chunk answers, on a
section whose grid the demo keeps clean while filtered. The seed count still counts the entry
(DET-18), so the count line and the stats bar never disagree with the seed.

**Alternatives.**

- Keep loading rows under a selection: the grid shows cards that may not match when the chunk
  answers — a flicker the demo does not have.
- Guess the value from the seed entry's `typeName`: the chain and People groups count relation
  names the seed does not carry, so the guess would be wrong for most groups.

**Consequences.** A first tick can drop every loading row until the chunks answer; the rows and
counts settle as the cards arrive, which DD-619 already states as the rule.

## DD-622. The group titles ride existing dictionary keys; Name is the raw literal

- **Status:** Proposed
- **Increment:** 16.5e
- **Date:** 2026-11-15
- **Supersedes:** none

**Decision.** The popover's group titles reuse the Aurelius catalogue keys the legacy menu labels
used: `derivedsystem` ("System" / "Systeem"), `derivedcollection`, `deriveddataset`,
`deriveddatadomain`, `deriveddataentity`, `derivedperson` ("People" / "Personen"), `typename`
("Type Name" / "Typenaam"). The person section's Name group has no catalogue key, so it carries
the raw literal `Name`, titlecased — the legacy rendered the raw option value, untranslated in
both locales (DET-21's precedent for the same value).

**Reason.** Every other key already sits in both catalogues (`messages.xlf`, `messages.nl-NL.xlf`
carry all seven from the dictionary read, SHL-08), and the i18n-completeness gate keeps them
green unchanged. Inventing new keys for labels the dictionary already owns would fork the glossary
(VCF-10's table names the legacy's own keys, and the demo's popover renders exactly these
words).

**Alternatives.**

- New `search.components.filter.*` keys: duplicated English for keys the catalogue holds (fails
  SHL-08's one-glossary rule).

**Consequences.** No catalogue change ships with this increment. The `Name` title stays English in
the Dutch locale, as the legacy's did — the same accepted wart as the Name sort option.

## DD-623. The funnel marks the glyph, for any state off the default

- **Status:** Proposed
- **Increment:** 16.5e
- **Date:** 2026-11-15
- **Supersedes:** none (amends DD-620's marking note and DV-169, both unmerged)

**Decision.** The funnel's active mark is the glyph's colour, not the button's face: while the
mark is on, the filter icon takes the primary hue and the button keeps its own background
(DD-618's scss rule now sets only `color`). The mark turns on for any section state that
differs from its default — the keyword, a facet selection, the sort key, or the sort direction —
the legacy's `isFilterActive$` test (`queryObject` different from `defaultQueryObject`) taken
as written. The count line keeps its narrower rule (VCF-13): only the keyword and the
selections change the number, since a sort filters nothing.

**Reason.** The demo page says both parts of the rule in pixels: an active funnel's computed
styles are button background `rgb(255,255,255)` (its own) with the `fa-icon` at
`rgb(0,209,178)` (the primary) — the mark lives in the inherited icon colour, because Bulma's
`.button.is-text`, defined after `.button.is-primary`, strips the pair's background. And the
legacy mark's condition is the section's whole query object, which the legacy `sorting`
component writes into: its `sortBy` and `sortDirection` controls patch `queryObject.sort`, so
re-picking the sort or flipping the direction lights the funnel on the demo. The first cut of
16.5e read the fill as the mark and the sort as "never marks"; the review kept the demo.

**Alternatives.**

- The primary fill as the mark (the first cut): the demo shows no fill on an active funnel —
  a filled button is a mark the demo does not have, and on the light theme it buries the
  glyph.
- Keyword and selections only (DV-169's first wording): a funnel that stays dark while the
  demo's glows after a sort change is a parity miss; a direction toggle is a filter state the
  reset link also clears, so one control set and one mark set belong together.

**Consequences.** `SectionView.filterActive` becomes the query-object test (keyword, selection,
sort, direction), while `filtered` stays the keyword-or-selection test for the count line — two
fields, each with one meaning. The reset (VCF-13) already returns all four to their defaults,
so the mark always clears with the link, as on the demo. DV-169's ledger row now records only
the descendants switch and the hover-plus-click opening.

## DD-624. The active crumb is plain text, not a dead link

- **Status:** Proposed
- **Increment:** 16.5e
- **Date:** 2026-11-15
- **Supersedes:** none (amends UIC-11, merged)

**Decision.** The `breadcrumbs` component renders the `activeGuid` crumb as a plain-text
`<span class="truncate" aria-current="page">`; only the clickable crumbs stay
`<a href="#">`. The component's scss gives the span the flex line and the 0.75em side padding
(first crumb flush) that Bulma's `.breadcrumb li.is-active a` gave the anchor, but its ink is
the plain strong text (`--bulma-text-strong`), not Bulma's active-breadcrumb colour.

**Reason.** The active crumb names the entity already on screen: it navigates nowhere. The
ported markup gave it `href="#"` and let Bulma's `pointer-events: none` silence it, which is
a link to assistive technology — it lands in the link list and on Enter jumps the page to the
top — while doing nothing for a sighted keyboard user. The review asked for plain text. The
demo agrees in substance: its crumbs are `<a>` without `href` (measured: `href: null` on both
the trail and the card crumbs), and a no-href anchor is not a link in the accessibility tree,
so the span matches the demo's semantics rather than deviating from them — no DV row. The ink
follows the same evidence: Bulma's active-breadcrumb colour is `--bulma-link-text-active`, a
darkened link blue (measured `rgb(0,88,170)`), which the review rightly still read as a link;
the demo's active crumb is `rgb(54,54,54)` — plain grey ink — which is exactly what
`--bulma-text-strong` resolves to, in both themes (its dark value, `rgb(237,237,237)`, reads
as the surface's own strong text).

**Alternatives.**

- Keep the anchor with `aria-disabled`: still a link in the link list, and Enter still
  scrolls to the top — the flaw the review named.
- Copy the demo's no-href anchor exactly: a link-shaped element that only our click handler
  could silence; a span states the intent in the element itself.

**Consequences.** UIC-11's "items are anchors" gains an amendment note (the UIC-12 / DD-377
precedent). The story's `Primary` play now counts one link plus the active crumb's text; the
component spec's active-crumb test asserts the span and the absence of an anchor. Consuming
tests are unchanged: the details and card specs read the crumb's text and class, and the e2e
trail scenario clicks the parent's anchor, which stays a link.

## DD-625. A section card's plain-text crumb is the entity being viewed

- **Status:** Proposed
- **Increment:** 16.5e
- **Date:** 2026-11-15
- **Supersedes:** none (amends VCF-01, unmerged)

**Decision.** `CatalogueCard` grows a `pageGuid` input: the details sections pass the page's
guid, and the card's trail marks that crumb active — plain text by DD-624 — while the card's
own crumb stays a link. Unset (a results row, where no entity is open) leaves the card's own
crumb active, the VCF-02 behaviour.

**Reason.** The legacy card passed `[activeGuid]="parentId$ | async"` — the entity the screen
is showing, taken from the injected `EntityDetailsService.parent` — never the card's own guid;
only the header passed the viewed entity. The rule the review named: the non-clickable crumb
is the entity you are already at. On a Cost Centre page, a related-attribute card's trail is
Finance → Cost Centre → cost_centre_code, and it is the Cost Centre crumb — the one under the
reader's eyes — that should read as text, while the card's own crumb still routes like its
title does. 16.5d ported the card marking its own crumb, which copies the results row's
behaviour onto the section cards, where the legacy marks the parent.

**Alternatives.**

- Keep the card's own crumb active everywhere: the same entity renders active on the results
  row and plain-text in the header, but as a card on its own children's page it stays a
  link next to a non-link copy of the page title — two readings of one crumb (fails the
  one-rule intent of DD-616).

**Consequences.** VCF-01's trail clause gains the active-crumb wording (PR #364 is open, so
the row is amended in place). The header is untouched — VDR-06's own-crumbed trail is already
right. A card whose trail does not contain the page entity (a person reached sideways, say)
marks nothing and every crumb stays a link, as the legacy's guid equality did. The e2e trail
scenario rides the results row, whose `pageGuid` stays unset.
