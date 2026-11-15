# 16.2 The view family: search and read doors

- **Status:** in progress
- **Pull request:** #358
- **Records:** ADR 064; DD-584 to DD-588 (here); relies on 16.1 (AVS-01..09), 14.4 (ASE-05..09's
  matching and facet machinery, DD-525), 4.2b (QSR), 6.2c (AUZ-12)

## Scope

Two doors of ADR 064's family, on the Aurelius prefix of 11.4 and 12.5:

- `POST /api/aurelius/v1/search` — a query, filters, facet selections, a sort and a page in; 16.1
  cards, facet counts and totals out (`routes/view_search.py`);
- `GET /api/aurelius/v1/entity/guid/{guid}` — one entity's 16.1 view out (`routes/view_entity.py`).

In `aurelius-atlas-core`, the search composed over the entity index the way 14.4's engine is
(DD-523's table idea reused, the view's field names instead of the engine's), reusing the
matching, filter, facet and sort machinery. The read door derives one live view (16.1's DD-581
function on a fresh read) and is one store read.

Not delivered, with the increment that will:

| Not delivered                                    | Lands with |
| ------------------------------------------------ | ---------- |
| The semantic and hybrid modes of the search door | 16.4       |
| The mutation door answering with a view          | 16.3       |
| The webapp switched to the doors                 | 16.5       |
| The App Search wire retired                      | 16.6       |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AVR-01 | `POST /api/aurelius/v1/search` needs `ENTITY_READ` (AUZ-12) and answers 403 in the Aurelius error shape without it                                                                                                                                                                                                                                                                                             |
| AVR-02 | The body is a JSON object of `query`, `filters`, `facets`, `sort`, `limit` and `offset`; an unknown key, value kind or out-of-range option is answered 400 with one message per refusal (AVR-13's shape)                                                                                                                                                                                                       |
| AVR-03 | A filter is a field's value or list of values, a `{from, to}` range on a number field, or a nested `{all, any, none}` object, over the card's fields and their quality sub-fields (`quality.accuracy.score` and the like). An unknown field is refused (AVR-02)                                                                                                                                                |
| AVR-04 | `query` matches as 14.4's DD-525 does: its words over the analysed name, qualified name and definition, exact over the other text fields; an empty query matches every document                                                                                                                                                                                                                                |
| AVR-05 | A facet is a card field name with an optional `size` (1 to 250, 10 by default); the answer counts the matching documents' values, most first, empty left out. A quality score sub-field (`quality.accuracy.score`, DD-587) is one such name; a facet on an unknown field, or on a number field that is not one, is refused                                                                                     |
| AVR-06 | `sort` is a card field or `_score` with `asc` or `desc`, or a list; by default `_score` descending with ties by `guid`. An array field sorts as 14.4's ASE-08 does                                                                                                                                                                                                                                             |
| AVR-07 | `limit` is 1 to 100 (10 by default) and `offset` 0 to 10,000 (0 by default). The answer holds `total`, the exact count of matching documents                                                                                                                                                                                                                                                                   |
| AVR-08 | The answer is `{cards, facets, total}`: the cards in 16.1's shape and order, and `facets` a map of the asked field to `{value, count}` entries in request order                                                                                                                                                                                                                                                |
| AVR-09 | Only active entities are in the door (as ASE-03's engine), a stale document answered with its `stale` mark (AVS-06, DD-524)                                                                                                                                                                                                                                                                                    |
| AVR-10 | `GET /api/aurelius/v1/entity/guid/{guid}` needs `ENTITY_READ` and answers the live view of the entity: one read, derived fresh; `stale` follows AVS-06, so it is false for a current document and true only for one the worker still owes (DD-585). A GUID without an entity is answered 404 in the Atlas error shape; one of an entity without a document answers its view with empty derived fields (AVS-02) |
| AVR-11 | The search door answers entities of every type, typed out by `filters.typeName`, not the m4i types only: an entity without a document matches an empty query and its own fields, and appears with empty derived fields                                                                                                                                                                                         |
| AVR-12 | No answer of Apache Atlas's API and no App Search answer changes (AVS-09)                                                                                                                                                                                                                                                                                                                                      |
| AVR-13 | Errors are Aurelius's (SBM-08): the Atlas error shape with an Aurelius `errorCode`, `messages` one per refusal                                                                                                                                                                                                                                                                                                 |

## Aurelius origin

- ADR 064's doors; 14.4 (DD-523, DD-525) as the machinery to reuse, its request shapes redesigned
  rather than ported (the wire is what 16.6 retires).
- `apps/aurelius-atlas-webapp` 7.4a/7.4b: the results page's query, facet-as-filter, sort and
  paging — the same interaction against the new door; 7.20/7.21a: the details screen's reads the
  read door replaces.

## Deviations

None against Apache Atlas (AVR-12). Against the App Search wire (intentional, its retirement
road): the view's field names, no `{raw}` wrappers, `limit`/`offset` paging instead of
`page.current`, and the facet answer of AVR-08 instead of App Search's `{type, data}`.
14.1's engine holds m4i documents only; AVR-11 opens the new door to all types, recorded here as
its own deviation from the engine's population.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__view_search.py` on the fake client: query words
  and empty query (AVR-04), nested filters and ranges on quality (AVR-03), facet counts and
  orders (AVR-05), sorts and ties (AVR-06), limits and totals (AVR-07), an unindexed entity in
  the door (AVR-11), refusals (AVR-02, AVR-13); the sample catalogue's counts equal to 14.4's
  e2e numbers for the same query.
- `apps/aurelius-atlas-server/tests/test__view_family.py`: both doors' auth (AVR-01, AVR-10),
  the read door's 404 and no-document view (AVR-10), the error shape (AVR-13).
- `apps/aurelius-atlas-server/e2e/test__view_family_e2e.py` on the dev store: a results-page
  request (query, type filter, facets, sort) and the details read of one of its cards, the same
  entity from both doors agreeing on the card fields (AVR-08, AVR-10).
- One `@pytest.mark.critical` scenario per door (ADR 062), and every rule named by a test.
