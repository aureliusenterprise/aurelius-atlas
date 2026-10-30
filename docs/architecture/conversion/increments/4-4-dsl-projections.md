# 4.4b DSL projections and traversals

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-243, DV-97, DV-98; relies on DD-057, DD-061, DD-064, DD-090, DD-242; ends DV-96

The second part of increment 4.4: what 4.4a declined until now (DV-96). `select` answers an attribute table,
with `count()`, `max`, `min` and `sum`; `groupby` groups it; a DSL query follows references, from a source or
a condition (`hive_table, columns`, `hive_table where db.name = 'Sales'`, `select db`), and compares the
attributes of the entities' classifications (`hive_table where Dimension.tagAttr1 = 'x'`). These are not tests
of one document's fields: the executor evaluates them in steps over the entity documents, the relationships
and the classification instances (DD-243).

## Scope

`GET /api/atlas/v2/search/dsl` as in 4.4a. In `aurelius-atlas-core`: `select_clause_composer`
(`SelectClauseComposer`) and `select_clause_projections` (`SelectClauseProjections`); `dsl_query_composer` and
`dsl_query_executor` extended.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DSP-01 | A `select` lists one item per expression, labelled by its `as` name as written, else by its text (`count()`, `max(name)`, `t.name`); the answer is then `attributes`, its `name` the labels and its `values` a row per entity found, a row equal to an earlier one left out, and without `queryType` and `queryText` (Atlas answers a new result). Nothing found, the answer has no `attributes`                                                                                                                                                      |
| DSP-02 | A row holds a primitive attribute's value as stored, `""` for none; an item that refers to entities (`select db.name`) holds the header of the entity the row is of. A `select` of the type or an alias of it alone (`DB as d select d`) answers the entities, a `select` of a referred attribute alone (`select db`) the entities referred to (DSP-06)                                                                                                                                                                                               |
| DSP-03 | `count()` is the number of entities found; `sum(a)` the sum of the numbers held, as a double; `max(a)` and `min(a)` the greatest and least value, compared as Java compares them: no value is least, values of different kinds are equal, so `min` is null when an entity has no value. With an aggregate the rows are of every entity found, unpaged; without one, of the page                                                                                                                                                                       |
| DSP-04 | An item naming no attribute fails with `Unable to find qualified name for <name>`, an aggregate of a non-primitive attribute with `Select clause has aggregation on referred attributes <name>`, items referring to more than one type with `Select clause has multiple referred attributes <count>`, referred and primitive items together with `Select clause has simple and referred attributes`, and a label that names an alias already with the duplicate alias error (DSE-05)                                                                  |
| DSP-05 | `groupby(a)` groups the entities found by the value of the primitive attribute `a`, leaving out those without one (else `Select clause has aggregation on referred attributes <name>`). With a `select`, each group gives its rows as DSP-01 to DSP-03 over its entities, groups in order of their value (DV-97); of all rows, those from index `offset - 1` (0 at least) to that plus `limit`, as Atlas's `getSublistForGroupBy` takes them. Without a `select`, the answer lists the entities of every group. An `orderby` with both orders nothing |
| DSP-06 | A source naming a non-primitive attribute of the active type (`hive_table, columns`, `hive_table columns`), and a `select` of one, moves to the entities it refers to, plain references and relationship ends alike, which become the active type; the conditions after it are of them, and the limit and offset page them                                                                                                                                                                                                                            |
| DSP-07 | A condition on `<attribute>.<name>` of a referred attribute holds for the entities whose attribute refers to an entity for which the comparison of `<name>` holds (`hive_table where db.name = 'Sales'`); `orderby` and `groupby` of one fail as DSE-12 and DSP-05                                                                                                                                                                                                                                                                                    |
| DSP-08 | A condition on `<classification>.<attribute>` holds for the entities with a classification of that type or a sub type, attached or propagated, whose attribute compares as DSE-06 to DSE-08                                                                                                                                                                                                                                                                                                                                                           |
| DSP-09 | Each step that reads every entity found (a move, a referred condition, aggregates, groups) reads at most 10,000 (DV-98)                                                                                                                                                                                                                                                                                                                                                                                                                               |

## Java origin

Apache Atlas `release-2.4.0`:

- `repository/.../query/SelectClauseComposer.java`, `executors/SelectClauseProjections.java`
- `repository/.../query/GremlinQueryComposer.java`: `addSelect`, `process`, `addGroupBy`, `addOrderBy`,
  `addLimit`, `introduceType`, `addWhere` (referred and classification attributes), `Context.addAlias`
- `repository/.../query/DSLVisitor.java`: `visitSelectExpr`, `visitGroupByExpression`, `processExprForTrait`
- `repository/.../query/IdentifierHelper.java`: `Info.updateEdgeInfo`,
  `getDefaultQualifiedNameForSinglePartName`
- `repository/.../query/executors/TraversalBasedExecutor.java`, `GremlinQuery.java#hasValidSelectClause`
- `intg/.../AtlasErrorCode.java`: `INVALID_DSL_SELECT_*`
- Tests: `DSLQueriesTest` (`basicProvider`, `minMaxCountProvider`, `errorQueriesProvider`),
  `GremlinQueryComposerTest`

## Deviations

DV-97: Atlas collects a select's rows in a `HashSet` and a group's in Gremlin's map, in no order; Aurelius
answers rows in the order of the entities found, groups by their value. DV-98: Atlas follows every edge;
Aurelius reads at most 10,000 entities in a step that reads them all. DV-96 ends.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — DSP-01 to DSP-09 on the in-memory documents, with the queries of
  `DSLQueriesTest` they cite.
- `libs/python/aurelius-atlas-core/e2e/` — a traversal and a group on Elasticsearch.
- `apps/aurelius-atlas-server/scenarios/search/dsl-projections.scenario.yaml` — DSP-01, DSP-03, DSP-05, DSP-07
  over HTTP.
- `uv run aurelius-atlas-trace check`.
