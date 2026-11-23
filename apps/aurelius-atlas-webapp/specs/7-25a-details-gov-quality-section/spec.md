# 7.25a The Governance Quality Rules box becomes a card section on every page

- **Status:** in review
- **Pull request:** #458
- **Records:** DD-841 to DD-843, DV-199 new; DET-42 and DET-43 amended;
  relies on 7.29 (DET-42's box, DD-520/DD-521, DV-155), 7.24 (DET-35/DET-36, the
  rule box on the field page), 16.5e (VCF-08..VCF-14, the card section chrome
  UIC-27 and its facet popover UIC-42), 12.7 (VEV-02, the live verdicts)

This is the webapp's first part of roadmap increment 7.25 "Quality scores and
compliance". It delivers the Governance Quality Rules box, the one part of 7.25
that has a data source today. The scores, the pies, the badges and the compliant
and non-compliant card lists stay with the rest of 7.25, because they all read
the `dqscore_*` entities that 7.25's score story has to settle (DD-369's
hold-out).

The legacy details screen carried a `#gov-quality` box on nine pages: domain,
entity, attribute, field, dataset, collection, system, process and person. Each
was a full card section (`governance-quality-cards` over `details-cards-list`):
a title, a result count that resets the filters, a keyword input, a sort select
with four options, a funnel with two facet groups, and a scroll of nine cards at
a time, plus a side-navigation entry. 7.29 ported the feature as DET-42, but as
a plain list on the person page only: rules sorted by name, each with a verdict
icon, and no count, no search, no sort, no funnel and no nav entry. The other
eight pages got nothing, and 7.29's own table deferred them to this increment.

This increment gives the box the legacy's section shape and all nine pages. The
box keeps DET-42's reads and its verdict source (DV-155): it searches the type's
ACTIVE rules and asks the aux validate call for the opened record's verdicts.

## Scope

- the box's shape: the chrome it borrows, the count line, the keyword input, the
  four sorts, the two facet groups, the nine-at-a-time scroll (DET-44 to DET-47);
- the nine layouts: the box as a section in the legacy position, its side-nav
  entry, its title key (DET-42 and DET-43 amended, DET-48);
- the row's rule type, which the sort and the funnel read from the rule the box
  already holds (DET-45, DET-46);
- the unchanged neighbours: the scores, pies and badges, the field page's Data
  Quality Rules box (DET-35), the card's governance mark (VCF-19), the editor's
  banner (EDT-24).

Not in scope:

| Not delivered                                                                                                             | Lands with |
| ------------------------------------------------------------------------------------------------------------------------- | ---------- |
| The DQ score stats, pies, card badges, dimension lists and the search-side DQ list (7.25's score half, DD-369's hold-out) | 7.25b      |
| A rule's own details page (the legacy's `#gov-quality` page for a rule: compliant and non-compliant card lists, pie)      | 7.25c      |
| A read of the verdicts index (the box keeps the live aux answer, DV-155)                                                  | –          |
| The rule links' landing page (a row title opens the rule's page of 7.25c; until then it opens DET-38's rule page)         | 7.25c      |

## Semantics

The ids continue DET-42. TS tests name them, the 7.21a convention. "The box"
below is the one `#gov-quality` box the details screen renders for a layout with
`govQualityBox` true.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DET-42 | Amended, shape only. The box is a card section of the layout's section list, not a plain list: it renders the shared card section chrome (UIC-27) over its own store, and its rows are the projected cards. Its rows stay DET-42's rows in content and order: the ACTIVE `m4i_gov_data_quality` entities whose `qualifiedName` starts with the opened entity's type name followed by `--`, read through the basic search, each with the verdict the aux call answered for the opened record. A row gains one field, the rule's `ruleType`, which the sorts and facets read (DET-45, DET-46); the row body a person sees does not change. The chrome does not change what a row is, or which rules qualify. DET-42's old sentence that the box "shows no count line and no search box" is withdrawn. |
| DET-44 | The box's count line is the chrome's: the row count with the `result(s)` word, underlined and clickable, and it resets the box's keyword, facets, sort and direction (DET-20's rule, carried). While a filter is active the line shows the filtered count. The box's loading state is the chrome's spinner, and a section that is still loading shows the count it holds, as DET-17 does.                                                                                                                                                                                                                                                                                                                                                                                                           |
| DET-45 | The sort select carries the legacy box's four options over its own Relevance default, in the legacy order: Relevance, `name`, `dataqualityruledimension`, `compliant`, `dataqualitytype`. Relevance is DET-42's name order, the store's read order. `name` compares the rule name, `dataqualityruledimension` the dimension, `dataqualitytype` the rule's `ruleType`, and `compliant` the verdict, so a compliant rule sorts before a non-compliant one and a rule with no verdict sorts last. A missing value sorts last in ascending order. The direction button reverses, and an equal pair keeps Relevance order.                                                                                                                                                                               |
| DET-46 | The funnel carries the legacy box's two facet groups, in the legacy ask's order: `dataqualityruledimension` (labelled `Dimension`) and `dataqualitytype` (labelled `Rule Type`). A group's value is the row's rule `qualityDimension` or `ruleType`, so the box's rule read carries both. A group's rows are the values that occur among the box's rows, counted over the set the keyword and the selections already passed, empty groups dropped, empty selections ignored (VCF-09..VCF-12's rules, carried). A row that stores no value for a group carries no value for it, so it cannot match a selection of that group. Within a group the card matches by OR, across groups by AND (VCF-11).                                                                                                  |
| DET-47 | The keyword input and the paging are the chrome's, over the box's own rows. The keyword matches, case-insensitively, in the rule name, its description, its dimension or its rule type (the texts a row carries, DET-20's rule read over the box's fields). The scroll container shows nine rows at a time and grows the page by nine per next-page request (DET-22's page size).                                                                                                                                                                                                                                                                                                                                                                                                                   |
| DET-48 | Each of the nine layouts carries the box as the last entry of its section list, the legacy position on all nine (after the last card box and before the Properties accordion, and on the person page after Governance Responsibilities). The entry replaces DET-42's `govQualityBox` flag: one list now orders every box the screen draws. Each layout gains the legacy's side-nav entry in the same position: the per-layout key `search.details.<layout>.governanceQualityRules`, anchored to `#gov-quality` (DET-25's anchor rules apply unchanged, deep links included). The box's title is the shared key `search.details.components.governanceQualityCards.title`, which the box already uses. The stats bar gains no heading, because the legacy's carried none.                             |
| DET-49 | The box keeps DET-42's failure posture (DD-521): a failed rule read renders the empty box, and a failed verdict call keeps the rows and paints them iconless. Both swallow quietly. Because the rows now sort, filter and page client-side, an empty box shows the chrome at a zero count, and the sort and funnel controls hold their defaults.                                                                                                                                                                                                                                                                                                                                                                                                                                                    |

## Aurelius origin

- `search/details/components/governance-quality-cards/` (legacy): the box, and
  the whole reason it is a section. Its `sortingOptions` are
  `['name', 'dataqualityruledimension', 'compliant', 'dataqualitytype']` and its
  engine ask is `{ entity_guid: [entityId] }` with facets
  `dataqualityruledimension` and `dataqualitytype` at size 100 and a page size
  of 9. `enableDescendantsControl` is false, so its funnel carries no
  descendants switch.
  switch.
- `search/details/components/details-cards-list/` (legacy): the chrome the box
  borrows, ported as UIC-27. The count line, the keyword input, the sort select
  with its direction button and the infinite scroll are the same controls. The
  legacy's `sorting` component renders Relevance (`_score`) first, then each
  option titlecased.
- `search/components/cards/gov-quality/governance-quality-card.component.html`:
  the row body, ported as UIC-38's sibling `gov-quality-cards.component.ts`. The
  legacy row shows `dataqualityruledescription.raw`, then the verdict icon for
  `compliant.raw` (`'0'` warning, `'1'` success) beside the titlecased
  `dataqualityruledimension.raw`. DET-42 already ports this and DET-42's row body
  is unchanged here.
- `search/details/{domain,entity,attribute,field,dataset,collection,system,
process,person}/*-details.component.html`: the nine pages. Each places the
  `<div id="gov-quality" class="box">` after its last card box and before the
  Properties accordion, and each lists the entry
  `search.details.<layout>.governanceQualityRules` in the same position in its
  `details-navigation`. The legacy stats bar never carries a Governance Quality
  heading, and no layout gains one.
- `search/details/gov-quality/` (legacy): not this increment. That page is the
  rule type's own details page (a score, a pie, two card lists), the roadmap's
  7.25c.

## Deviations

Against Apache Atlas: none. The box is the m4i demo's furniture, as DET-42
recorded (DV-155).

Against the demo, DV-199 new: the box's rows are no longer the entity's verdict
documents. The legacy box asked the engine for the verdict documents of the
opened entity, so a rule with no verdict for that record never appeared, and a
rule with one appeared once per verdict document. DET-42 already changed the
read (DV-155), and this increment keeps it: the rows are the type's ACTIVE rules
and the verdict is the aux call's answer for the opened record. Two visible
results follow. A rule the engine never judged still shows, iconless (DET-42's
unread-rule rule, VEV-03). And the four sorts and the two facets run over the
browser's rows instead of the engine's query, because the box has no engine to
ask; the keyword, facet and paging behaviour they produce is the same as the
shared section's (VCF-08..VCF-14).

## Acceptance

Unit (offline, `nx test aurelius-atlas-webapp -c ci`):

- `src/app/search/details/sections/gov-quality.state.spec.ts`: DET-45's four
  comparators, including the no-verdict rule last on `compliant` and a missing
  dimension last on its own sort; DET-46's group counts over the keyword-and-
  selection filtered set and its OR-within, AND-across match;
  DET-47's keyword fields and its page growth by nine; DET-49's empty box on a
  failed read and its iconless rows on a failed verdict call. The existing
  DET-42 cases (the prefix read, the name order, the verdict join) stay green.
- `src/app/search/details/sections/gov-quality-cards.component.spec.ts`: the
  projected rows keep DET-42's row body unchanged, and the component now sits
  inside the chrome it is given.
- `src/app/search/details/details.component.spec.ts`: DET-48 per layout, the
  box at the end of the section list, and DET-44's reset clearing keyword,
  facets, sort and direction.
- `src/app/search/details/sections/section-config.spec.ts`: DET-48 for all nine
  layouts: the box's position last, and the per-layout nav entry in the legacy
  position. The person layout's existing DET-43 assertions move under DET-48.
- `src/app/i18n-completeness.spec.ts`: green, unchanged. Every key the box needs
  already rides both catalogues and both fixtures: the nine
  `search.details.<layout>.governanceQualityRules`, the shared title, and the two
  facet labels `dataqualityruledimension` and `dataqualitytype`.

E2E (Level 2, `nx e2e aurelius-atlas-webapp`):

- `e2e/test__aurelius_atlas_webapp.py`: one scenario on a dataset seed, the
  corpus type the demo data rides. It seeds three ACTIVE rules on the type with
  different dimensions, rule types and verdicts, opens the dataset's page, and
  asserts the box as a section: the count line, a keyword that narrows it, the
  `compliant` sort that puts the refused rule first, a dimension facet that
  drops the other rows, and the nav entry that scrolls to `#gov-quality`
  (DET-44..DET-48). The rules ride this run's names, self-cleaned, and the suite
  never restarts a shared service (DD-223).
