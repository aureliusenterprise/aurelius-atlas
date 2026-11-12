# 7.29 Person details

- **Status:** in progress
- **Pull request:** — (this increment's PR)
- **Records:** DET-39..43 (the tenth row of DET-16); adds DD-518..522 (here) and
  DV-154..156 to
  [deviations](../../../../docs/architecture/conversion/deviations.md) in the
  implementation PR; relies on DET-15..27/DD-365..371 (the layout table and the
  card-section machinery), DET-33/DD-383 (the row that deferred this page),
  DET-35/DD-444 (the section seeded from an end), VEV-01..06/DD-498..501 (the
  verdict answer this page reads), DV-84 (the browse card's person filter), and
  12.7's note that the rule box lands with this increment.

Part of the [7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01
to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

The details screen answers a type layout for nine m4i types (DET-16). The person
is the tenth: 7.21c ports the process page and leaves `m4i_person` out
(DD-383's "last row"). The legacy person page is unlike the other nine, so 7.21a
could not fold it into the table. It has no description box. Its stats bar holds
four grouped boxes, and its one card box lists everything the person is
responsible for: the domains they lead, the entities and attributes they own,
and the entities and attributes they steward. Below that sits the Governance
Quality Rules box, and then the properties accordion.

Delivered here:

- the tenth **layout row** (DET-39): `m4i_person` enters the dispatch and the
  config table, with its own stats bar and no description box.
- the **stats bar** (DET-40): the legacy's four grouped boxes — Domain Lead,
  Data Owner, Data Steward, Other — each heading a link to its box.
- the **Governance Responsibilities box** (DET-41): one card section seeded from
  the person's five responsibility ends, drawn by the 7.21a machinery.
- the **Governance Quality Rules box** (DET-42): the governance rules written
  for the entity's own type, each with its verdict for the opened record.
- the **side navigation** (DET-43): the legacy's three entries.

Explicitly not delivered here, with the increment that will:

| Not delivered                                                         | Lands with | Why                                                                                     |
| --------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------- |
| The governance rule editor form and the gov rows of 12.5's vocabulary | 7.28       | 12.7 reserves that number for the editor; the box here reads rules, it never edits them |
| The other pages' Governance Quality Rules boxes                       | 7.25       | 7.24's deferral, unchanged: this increment ships the box for `m4i_person` only          |
| Score boxes, pies, and badges (DD-369's hold-out)                     | 7.25       | No `dqscore_*` source, unchanged                                                        |
| The role heads' filter-through (a stats click that searches)          | —          | The legacy's App Search facet cannot exist here (DV-156)                                |
| The Lineage Model box                                                 | —          | A person owns no lineage, and the legacy page carries none                              |

## Semantics

TS tests name the ids (the 7.21a convention). The five responsibility ends are
`domainLead`, `businessOwnerEntity`, `businessOwnerAttribute`, `stewardEntity`,
and `stewardAttribute`, the ends the m4i relationship definitions name and the
demo's person records carry.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DET-39 | The dispatch (DET-15) answers a layout for `m4i_person`, and the table carries it as its tenth row. The row carries no description box: the screen draws no `#description-details` box for a person, and every other type keeps its box. The row carries no People box, no lineage box, and no `ProcessOwner` end. A type whose supertype chain reaches `m4i_person` answers the layout the way DET-15's walk answers the other nine.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| DET-40 | The person layout's stats bar renders the legacy's four grouped boxes in legacy order: Domain Lead, Data Owner, Data Steward, Other. The Domain Lead box holds one entry, `search.details.person.dataDomains`, counted from `domainLead`. The Data Owner box holds `dataEntities` from `businessOwnerEntity` and `dataAttributes` from `businessOwnerAttribute`. The Data Steward box holds `dataEntities` from `stewardEntity` and `dataAttributes` from `stewardAttribute`. The Other box holds `search.details.person.properties`, counted from the rendered property rows (DET-11). Every heading links to its box (DET-24's rule): the four responsibility headings to `#governance-roles`, the Properties heading to `#properties-details`.                                                                                                                                                                                                                                                                     |
| DET-41 | The person layout's one card section carries the anchor `governance-roles`, the title `search.details.person.governanceRolesCards.title`, and the five responsibility ends as its seed keys, in the order: `domainLead`, `businessOwnerEntity`, `businessOwnerAttribute`, `stewardEntity`, `stewardAttribute`. DET-17..22 apply unchanged: ACTIVE entries with a guid, deduped by guid across the keys, chunked bulk resolve, client-side search, sort, and paging. A person with no responsibility renders the box at its zero count (DET-27's case). `ProcessOwner` seeds nothing (DV-154).                                                                                                                                                                                                                                                                                                                                                                                                                         |
| DET-42 | The person page renders a `#gov-quality` box titled `search.details.components.governanceQualityCards.title`. Its rows, sorted by rule name, are the ACTIVE `m4i_gov_data_quality` entities whose `qualifiedName` starts with the opened entity's type name followed by `--`, read through the basic search. "ACTIVE" is 12.2's reading (VEV-03): only a false `active` is not. A row's title is the rule's `name` and opens the rule's details page. Its body shows the rule's `ruleDescription` as a line when it stores one, then the verdict line for the opened record: the success icon when the rule's verdict for the entity is compliant, the warning icon when it is not, and no icon when the verdicts hold no verdict for the rule — an unread rule (VEV-03) — beside the rule's dimension titlecased. The box shows no count line and no search box: it is not a card section. A failed rule read or a failed verdict call renders an empty box and alerts nothing (the editor's quiet swallow, EDT-23). |
| DET-43 | The person layout's side navigation carries the legacy's three entries in order: `search.details.person.governanceResponsibilities` to `#governance-roles`, `search.details.person.governanceQualityRules` to `#gov-quality`, `search.details.person.properties` to `#properties-details`. DET-25's anchor rules apply unchanged, a deep link's landing included.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`),
cited by path so a reviewer can compare:

- `apps/atlas/src/app/search/details/person/person-details.component.html` — the
  four-box stats row (`search.details.person.domainLead`, `.dataOwner`,
  `.dataSteward`, `.other`), the `#governance-roles` and `#gov-quality` boxes,
  the properties accordion, and the three-entry navigation DET-40..43 port. The
  page has no description box, so DET-39 gives the layout a flag rather than a
  title.
- `apps/atlas/src/app/search/details/person/person-details.component.ts` — the
  six counts DET-40 reads: the five ends' lengths (each `defaultIfFalsy(0)`) and
  the filtered-properties count for Other.
- `apps/atlas/src/app/search/details/person/governance-roles-cards/**` — the box
  DET-41 ports. Its query ran against the App Search `atlas-dev` engine with the
  filter `derivedperson: [person name]`, the page size 9, and the sorts
  `typename`, `deriveddatadomain`, `deriveddataentity`, `name`, and the five
  `dqscore_*`. The seed source changes (DV-154) and the sorts stay out (DD-369).
- `apps/atlas/src/app/search/details/components/governance-quality-cards/**` —
  the box DET-42 ports: the title `search.details.components.governanceQualityCards.title`
  and the `details-cards-list` it feeds. Its query ran the `atlas-dev-gov-quality`
  engine with the filter `entity_guid: [entityId]`; the read changes (DV-155).
- `apps/atlas/src/app/search/components/cards/gov-quality/governance-quality-card.component.html` —
  the card body DET-42 ports: the `dataqualityruledescription.raw` line, the
  warning icon on `compliant.raw === '0'`, the success icon on `'1'`, and the
  titlecased dimension.
- `apps/atlas/src/app/search/details/details.component.ts` — the dispatch's
  `getSuperTypes` rule that DET-15 already ports and DET-39 reuses.

## Deviations

Deliberate differences from the legacy app, each added to
[Deviations](../../../../docs/architecture/conversion/deviations.md):

- **DV-154**: the Responsibilities box seeds from the person's own five ends,
  not from the search's `derivedperson` name match. `atlas-dev` is retired
  (ADR 054/060) and its name-keyed index has no twin; the ends are the same
  facts the store holds, they need no extra read, and a name rename cannot
  orphan the box. `ProcessOwner` stays out because the legacy box never lists a
  person's processes.
- **DV-155**: the Governance Quality Rules box reads rules from the store and
  verdicts from the aux API, not from the `atlas-dev-gov-quality` engine. That
  engine has no twin (ADR 060), and the verdicts of 12.7 are the product's real
  answers (VEV-02). The rule set is keyed by the qualified-name prefix, the rule
  LAS-13 states.
- **DV-156**: a stats heading only scrolls. The legacy heading also rewrote the
  box's search filters (`filterResponsibilitiesByType`, keyed by
  `derived<role>guid` and `typename`), a facet of the retired engine. The heading
  still names its box, and the box holds everything at once.

## Acceptance

Unit (offline, `uv run vitest` through `nx test aurelius-atlas-webapp -c ci`):

- `src/app/search/details/sections/section-config.spec.ts` — DET-39/DET-40/DET-43:
  the tenth key, the missing `descriptionBox`, the grouped stats shape, the nav
  order. It replaces the "maps every other name to no layout" case that names
  `m4i_person` today.
- `src/app/search/details/details.component.spec.ts` — DET-39..DET-43 on the
  screen: the absent description box, the four stats groups, the seeded
  responsibilities box, the two boxes' anchors.
- `src/app/search/details/sections/related-sections.state.spec.ts` and
  `gov-quality.state.spec.ts` — DET-41/DET-42: the five-end seed order and
  dedupe (`endCount`), the rule read and its prefix filter, the verdict join,
  the empty box on a failure.
- `src/app/search/details/sections/gov-quality-cards.component.spec.ts` —
  DET-42's row rendering: the two icons, the no-icon verdict, the description
  fallback.

E2E (Level 2, `nx e2e aurelius-atlas-webapp`):

- `e2e/test__aurelius_atlas_webapp_person_details.py` — the served page. A
  seeded person with one responsibility on each of the five ends opens at
  DET-40's four counts and DET-41's five cards (DET-39's missing description
  box, DET-43's three nav entries). A seeded `m4i_person` governance rule that
  the opened person fails renders its non-compliant line, and a person that
  holds the value renders the compliant one (DET-42, DV-155). Rules ride
  `qualifiedName` prefixes outside the run's names, self-cleaned by the shared
  m4i purge (DD-223); the suite never restarts a shared service.
