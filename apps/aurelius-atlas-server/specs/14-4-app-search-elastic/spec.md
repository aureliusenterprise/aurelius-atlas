# 14.4 The App Search API: `/elastic`

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-523 to DD-527 (here), DV-157 and DV-158; relies on ADR 060, 14.1 (LAS-01 to LAS-07,
  LAS-12), 14.2 (ASD-01 to ASD-05) and 14.3 (ASU-01)

## Scope

The original webapp searches the `atlas-dev` engine: its search page, its facets, its browse pages and the
cards of every details page. Its reverse proxy sends `<base>/elastic` to App Search's
`/api/as/v1/engines/atlas-dev/search.json` (`k8s/charts/reverse-proxy/conf.d/search-api.yaml`). This
increment answers that request from the entity documents, as App Search answered it. In `aurelius-atlas-core`:

- the engine's fields and where each comes from: the entity, its stored App Search document, or a constant
  (`app_search_engine.py`);
- the request, checked as App Search checks it, translated into one search of the entity index, and the
  answer in App Search's shape (`app_search_engine.py`);
- the search itself, on the Elasticsearch entity documents (`entity_documents.py`).

In `aurelius-atlas-server`, `POST /api/as/v1/engines/{engine}/search` and `.../search.json`
(`routes/app_search.py`).

Not delivered, with the increment that will:

| Not delivered                                                               | Lands with |
| --------------------------------------------------------------------------- | ---------- |
| The `atlas-dev-quality` engine (`/data_quality`) and the score fields' sums | 14.5       |
| The `atlas-dev-gov-quality` engine (`/gov_quality`)                         | 14.6       |
| A deployment's route from the original webapp's `elastic` to this endpoint  | none       |

The last row is the operator's: the original webapp's reverse proxy names the server instead of the search
API. The server's README shows the route.

## Semantics

The engine's fields are those of 14.1's `atlas-dev` documents:

| Fields                                                                                | Kind   | From                                     |
| ------------------------------------------------------------------------------------- | ------ | ---------------------------------------- |
| `id`, `guid`                                                                          | text   | the entity's GUID                        |
| `typename`; `supertypenames`                                                          | text   | the entity's type; `[typename]` (LAS-02) |
| The fields of ASD-01 but `sourceHash`                                                 | text   | the stored document (14.2)               |
| LAS-07's ten fields                                                                   | either | their constant: `0`, `[]` or none        |
| `dqscore_<d>`, `dqscorecnt_<d>`, `dqscoresum_<d>` for the five dimensions and overall | number | `0` until 14.5 (LAS-12)                  |
| `qualityguid_<d>` for the five dimensions                                             | text   | `[]` until 14.5 (LAS-12)                 |

`businessruleid` is LAS-07's one number; its other nine fields are text.

| Id     | Rule                                                                                                                                                                                                                                                                                                              |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ASE-01 | `POST /api/as/v1/engines/atlas-dev/search` and `.../search.json` answer alike. Another engine's name answers 404 `{"errors": ["Could not find engine."]}`                                                                                                                                                         |
| ASE-02 | The request needs a user, as every API path does, who holds `ENTITY_READ`; one who does not is answered 403 `{"errors": [...]}`                                                                                                                                                                                   |
| ASE-03 | The engine holds a document for each active entity with a stored App Search document, stale or not (DD-524), with the fields of the table above                                                                                                                                                                   |
| ASE-04 | The body is a JSON object of `query`, `filters`, `facets`, `sort`, `page`, `result_fields` and `search_fields`; other keys are ignored. A body or an option App Search refuses, such as an unknown field, a value of the wrong kind or a page out of range, is answered 400 `{"errors": [...]}`, one message each |
| ASE-05 | An empty `query` matches every document. Otherwise a document matches if one of the query's words is in one of its text fields, or in those `search_fields` names, each with its `weight`; more matches rank it higher (DV-157)                                                                                   |
| ASE-06 | A filter is a field's value or list of values, which a document matches when the field holds one; a number field's range `{from, to}`, from included, to not; or an object of `all`, `any` and `none`, each a list of filters, nested. The fields of a top-level object are joined as `all`                       |
| ASE-07 | A facet is `{type: value}`, or a list of them, per field, with `size` 1 to 250 (10 by default) and `sort` by count or by value. It counts the values of the documents the query and filters match, the most first, empty values left out. A range facet is refused (DV-158)                                       |
| ASE-08 | `sort` is a field or `_score` with `asc` or `desc`, or a list of them; by default `_score` descending. Ties go by `id`. An array field sorts by its least value ascending and its greatest descending; a constant sorts nothing                                                                                   |
| ASE-09 | `page.current` is 1 to 100 (1 by default) and `page.size` 1 to 1,000 (10 by default). `meta.page` holds `current`, `size`, `total_results` and `total_pages`, the results over the size rounded up                                                                                                                |
| ASE-10 | Each result holds the `result_fields` asked for, every field when none is, each as `{"raw": value}`, a text cut to `raw.size` characters; `snippet` adds the value HTML-escaped with the query's words in `<em>`, cut to its `size`, or none unless `fallback` (DV-158). `_meta` holds `id`, `engine` and `score` |
| ASE-11 | `meta` holds `alerts` and `warnings`, both `[]`, `precision` 2, `engine` `{"name": "atlas-dev", "type": "default"}`, the `page`, and a `request_id`; `facets` holds each facet field's list in the request's order                                                                                                |
| ASE-12 | No answer of Apache Atlas's API changes                                                                                                                                                                                                                                                                           |

## Aurelius origin

From `aureliusenterprise/aurelius` at commit b057389:

- `libs/atlas/api/src/lib/elastic/app-search.service.ts`: the request and answer types the webapp sends and
  reads (ASE-04 to ASE-11).
- `apps/atlas/src/app/search/services/`: the search page's query, its facets and paging (`search/`,
  `app-search-results/`), the facets made filters (`components/filter/check-box/`), sorting
  (`components/sorting/`), and the details cards' filters (`details/*/…-cards.component.ts`).
- `backend/m4i-search-api/m4i_search_api/routes/proxy.py`: the two paths App Search was reached by
  (ASE-01).

App Search's own behaviour is that of Elastic's Search API reference for 8.x.

## Deviations

None against Apache Atlas (ASE-12). Against App Search:
[DV-157](../../../../docs/architecture/conversion/deviations.md) (the words a query matches and their order)
and DV-158 (the options not reproduced: range facets, `group`, `boosts`, `precision`, analytics, and
snippets made without App Search's analysis).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__app_search_engine.py`, on the fake client:
    - the engine's fields against the legacy documents' (ASE-03, LAS-07);
    - each rule on small sets of documents: stale, deleted and unindexed entities, a query's words, nested
      filters and constants, facets, sorts, pages and the result window, raw values and snippets;
    - every refusal of ASE-04 in one request;
    - the sample catalogue imported and indexed: the search page's first request answers all 684 documents,
      its type and source type facets counting what `atlas-dev` counted, and a domain's entity card finds
      what `atlas-dev` held.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_app_search_engine.py`: the two paths, an
  unknown engine, a user without `ENTITY_READ`, and a refused body (ASE-01, ASE-02, ASE-04).
- `libs/python/aurelius-atlas-core/e2e/test__app_search_engine_e2e.py`, on the dev Elasticsearch: a filter
  on a derived GUID with a name sort and facets, by count and by value, a definition's word with its
  snippet, an email matched exactly, and a page with the exact total.
