# 11.5 Search by meaning in the webapp

- **Status:** in progress
- **Pull request:** [#309](https://github.com/aureliusenterprise/aurelius-atlas/pull/309)
- **Records:** ADR 059 (Proposed); DD-444 to DD-447 (DD-444 and DD-446 superseded by DD-473 and DD-474,
  11.5b); relies on 11.4 (the endpoints, SBM-01 to SBM-08,
  DD-440), 7.4b (the facet sidebar, DD-424 to DD-427), 7.4a (the results store, DD-219), DD-388 (the lineage
  box's pattern)

Users choose how the search field searches: by its words, as before, by meaning, or by both. On an entity's
details page, a box shows the entities nearest to it in meaning. Both read the endpoints of 11.4, which answer
as quick search does, so the result list and the facet sidebar of 7.4b show them unchanged.

## Scope

- `aurelius-atlas-data-access`: `SearchByMeaningService`, the client of `POST
/api/aurelius/v1/search/semantic` and `GET /api/aurelius/v1/entity/guid/{guid}/similar`;
- the search hero: the switch between words, meaning and both;
- the results store: the searches by meaning, their paging and their errors;
- the details page: the Similar entities box;
- the new labels, in English and Dutch.

Not in scope: a chat on the catalogue; the hybrid weight's tuning (DD-442); the dev stack and the Helm chart.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                         |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SBW-01 | `SearchByMeaningService.search` posts quick search's parameters with `mode` to `{API_BASE_URL}/aurelius/v1/search/semantic`; `similar` gets `{API_BASE_URL}/aurelius/v1/entity/guid/{guid}/similar` with `limit`, `offset`, `typeName` and `excludeDeletedEntities`. Both answer `AtlasQuickSearchResult`                                                                    |
| SBW-02 | The search hero shows, under the field, a switch of three: Words, the default, Meaning and Both. The choice is the session's, as the type selection is, and stays when the query changes; it is not in the URL                                                                                                                                                               |
| SBW-03 | With Meaning or Both and a query, each page of results is a search by meaning, `semantic` or `hybrid`, with the type selection, the page size, `includeSubTypes` and `excludeDeletedEntities` of a quick search; the facets are its answer's. Without a query the results list as before, whatever the switch                                                                |
| SBW-04 | In Meaning and Both, a next page is asked while the last page was full and fewer than 1,000 entities are shown; the header counts the entities shown, as closest matches                                                                                                                                                                                                     |
| SBW-05 | Choosing another mode with a query restarts the search at its first page; the type selection stays                                                                                                                                                                                                                                                                           |
| SBW-06 | A server without search by meaning (`AURELIUS-404-00-001`) adds an alert saying so and turns the switch back to Words, which searches again; any other failure adds the alert a failed page of results adds                                                                                                                                                                  |
| SBW-07 | The details page shows, after its card sections, a Similar entities box: the 6 entities nearest to the entity, as entity cards that lead to their own details page; a spinner while they load; a note when the entity is not analysed yet (`AURELIUS-409-00-001`), when none is found, or when they could not be loaded; no box at all on a server without search by meaning |
| SBW-08 | Every new label has its English and Dutch text                                                                                                                                                                                                                                                                                                                               |

## Aurelius origin

None: the legacy webapp had no search by meaning (ADR 059). The switch is a small Bulma `buttons has-addons`
group under the field, as the legacy screens group their buttons; the box and its cards are the details page's
own (DET-19, DD-388).

## Deviations

None against Apache Atlas, whose dashboards are untouched.

## Acceptance

- `libs/angular/aurelius-atlas-data-access/src/lib/aurelius/search-by-meaning.service.spec.ts`: SBW-01.
- `apps/aurelius-atlas-webapp/src/app/search/search-state.spec.ts`: SBW-03 to SBW-06.
- `apps/aurelius-atlas-webapp/src/app/search/search-layout.component.spec.ts`: SBW-02.
- `apps/aurelius-atlas-webapp/src/app/search/details/similar/similar-entities.component.spec.ts`: SBW-07.
- `apps/aurelius-atlas-webapp/src/app/i18n-completeness.spec.ts` and the build of both locales: SBW-08. The
  ten new keys join the vendored dictionaries (`tests/fixtures/en-US.json`, `nl-NL.json`) and both catalogues,
  as 7.4b's four did (DD-128).
- By hand, on the standalone stack: the three modes on the sample data, a type ticked in Meaning, and the
  Similar entities box of `Personnel`.
