# 16.5e Filters on the details card sections

- **Status:** in progress
- **Pull request:** #368
- **Records:** DD-618 to DD-625 (here); DV-168, DV-169 (VCF-09 amended by 16.5f, DD-629,
  DV-170); relies on 16.5d (VCF-01..07,
  DD-614/615), 7.21a (DET-17..22, DD-367/DD-368), 7.4b (UIC-33..35, SDX-03..05, DD-426),
  16.1 (AVS-01/02, LAS-05)

The demo's card sections filter: the funnel button by the sort control opens a popover of
facet menus — the values of the section's cards with their counts — and ticking a row keeps
only the cards that carry that value. 16.5d put the legacy's rich card into every section and
resolved each card through the search door, so each card already answers the fields the
facets count: its stored derived relations (AVS-02, LAS-05), its type name and its display
text. This increment adds the funnel and its facet menus to the shared card section, derived
client-side from the resolved cards — like the keyword filter, the sort, and the paging, with
no server change (DD-619).

## Scope

- in `aurelius-atlas-ui`: the `DetailsCardSection` part grows the funnel button and the facet
  popover (VCF-08, DD-618); it renders the caller's facet groups through the existing
  `FacetList` component (UIC-33) and emits each tick;
- in `aurelius-atlas-webapp`: the facet groups per section (the legacy's per-section asks,
  VCF-10), the client-side rows and counts over the resolved cards (VCF-09), the selection
  rules (VCF-11, VCF-12), the count line and the reset extended to the selections (VCF-13),
  and the loading-card rule under a selection (VCF-14).

Not in scope, with the increment that will:

| Not delivered                                                                                                                          | Lands with |
| -------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| The legacy funnel's "Show all descendants" switch (the seed walks direct ends only, VDR-03; the door has no derived-chain GUID filter) | – (DV-169) |
| The person page's Governance Quality Rules box facets (the box is DET-42's plain list, no section chrome yet)                          | –          |
| The rule dimension and rule type groups (no card field carries them, DV-168)                                                           | –          |
| Server-side facets for the sections                                                                                                    | –          |

## Semantics

The door's rules (AVR) and the section's existing rules (DET-17..22, VCF-02/05) stay. The
rules below cover the filter on a section's cards.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| VCF-08 | Every card section's header carries a funnel button before the sort control (the legacy `details-cards-list` filter dropdown). It opens the section's facet popover and closes it. While any section state differs from its default — the keyword, a facet selection, the sort key, or the sort direction (the legacy's whole query object, DD-623) — the funnel tints its glyph primary, the button's face untouched as on the demo (the legacy `is-primary` pair, DD-623; DV-169 amended)                                                                                                                                                                                                                                    |
| VCF-09 | The facet rows come from the section's resolved cards, with no request of their own: a chain group (System, Collection, Dataset, Data Domain, Data Entity) counts the card's stored derived relations of that type, by name (AVS-02, LAS-05 — the direct ends, not the breadcrumb walk, as the demo shows); the people group counts the relation names of its key; Type Name counts the card's type name (the dictionary name, DET-26's rule); Name counts the display text. A card without the field adds no row. 16.5f asks the three role groups — Domain Lead(s), Data Owner(s), Data Steward(s) — over the door's role relations where the table carried the flat People group (amended by 16.5f, VCF-18, DD-629; DV-170) |
| VCF-10 | Each section shows the groups its legacy component asked (the table in DD-619): the technical sections the chain groups, the ownership sections the people group (the flat one until 16.5f's VCF-18), the process sections Type Name and the chain groups, and the person page's roles section Type Name, Data Domain, Data Entity and Name. A section whose table is empty renders the funnel with the catalogue's "No filters available." line (SDX-03's empty state, the legacy `filter.component` noFilters block)                                                                                                                                                                                                         |
| VCF-11 | The filters combine as the legacy query object did (DD-620): within a group the selected values match a card by OR, across groups by AND, and the keyword ANDs with all of them. A group with no selection filters nothing                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| VCF-12 | The rows and their counts show over the keyword-and-facet filtered set (the demo and Elasticsearch's aggregation, DD-426's seen-rows rule deliberately not reused here): a row whose count falls to zero disappears, a checked row with it, and the section's reset link recovers the whole set. Past five rows the popover carries the show-more link (UIC-34)                                                                                                                                                                                                                                                                                                                                                                |
| VCF-13 | The count line shows the seed count with no keyword and no selection, and the filtered card count with either (DET-17/DET-20 extended to the selections). The reset link (DET-20) clears the keyword, the selections, and the sort together; paging counts from the filtered set (DET-22 unchanged)                                                                                                                                                                                                                                                                                                                                                                                                                            |
| VCF-14 | A card that has not resolved shows while no selection is active and hides while one is (the store cannot test a field it does not have, DD-621). The seed count keeps it either way. The People box, the stats bar, the stats-bar and nav counts, and the results screen do not change (no rule here touches them) (R3, R4)                                                                                                                                                                                                                                                                                                                                                                                                    |

## Aurelius origin

- The legacy `details/components/details-cards-list` (`models4insight-details-cards-list`): the
  funnel dropdown (hoverable, `is-primary` while the query object differs from its default),
  the `filter` / `facet` / `check-box` trio rendering the answer's facets, the five-row slice
  with show-more, and the reset link.
- The per-section `SearchService` subclasses (`details/*/​*-cards/​*.component.ts`): each asked
  its own `facets` over the App Search entity engine (size 100) — the group table VCF-10.
- `filter/check-box/check-box.service.ts`: one key per group in `filters.all`, an array of
  values (OR within the group, AND across groups), the key deleted at its last untick; the
  demo's aggregation rule VCF-12 read from the live demo.
- 16.1 (LAS-05, AVS-02): the stored derived relation arrays the rows count — the same fields
  the legacy engine aggregated, now carried on every card.

## Deviations

Against Apache Atlas: none (R3, R4 — no Atlas answer changes; the door answers nothing new).

Against the demo (DV-168, DV-169, recorded in
[Deviations](../../../../docs/architecture/conversion/deviations.md)):

- the rule dimension and rule type groups render no rows, because no card field carries a
  rule's dimension or type (DV-168); the sections that asked them show "No filters available.";
- the "Show all descendants" switch stays out — VDR-03 seeds direct ends and the door has no
  derived-chain GUID filter (DV-169); the funnel marks like the demo — its glyph tinted
  primary, the face untouched, for any state off the default (DD-623); the popover opens on
  hover like the legacy CSS and, beyond it, on click, so the keyboard reaches it (DV-169).

## Acceptance

- `libs/angular/aurelius-atlas-ui/src/lib/details-card-section/details-card-section.component.spec.ts`:
  the funnel opens and closes the popover (VCF-08), the groups render through `FacetList`
  with their ticks, the empty popover shows the not-available line (VCF-10), the caller's
  applied state marks the funnel's glyph (VCF-08, DD-623), and a tick emits with its group
  key (VCF-11).
- `apps/aurelius-atlas-webapp/src/app/search/details/sections/section-config.spec.ts`: each
  layout row carries the legacy group table for its sections (VCF-10).
- `apps/aurelius-atlas-webapp/src/app/search/details/sections/related-sections.state.spec.ts`:
  the rows and counts per group over the resolved cards (VCF-09), a zero row dropped and a
  checked row dropped with it while the count line keeps the filtered number (VCF-12), OR
  within a group and AND across groups with the keyword (VCF-11), the loading-card rule
  (VCF-14), the reset clearing selections with the keyword and sort (VCF-13), and the
  funnel's mark riding the whole query object — a sort or direction off its default marks
  it while the count line stays on the seed (VCF-08, DD-623).
- `apps/aurelius-atlas-webapp/src/app/search/details/details.component.spec.ts`: the funnel
  and popover wired to the store per section, the count line and paging on the filtered set
  (VCF-08, VCF-13).
- `apps/aurelius-atlas-webapp/src/app/i18n-completeness.spec.ts`: green unchanged — every
  group title reuses an existing dictionary key (`derivedsystem` and siblings, `typename`);
  the Name title is the raw titlecased literal (DET-21's precedent).
- `apps/aurelius-atlas-webapp/e2e/test__aurelius_atlas_webapp_person_details.py`: the roles
  section's funnel lists the Type Name rows; ticking "Data Attribute" keeps only the
  attribute cards, moves the count line, and clears on reset (VCF-08..VCF-13).
