# 4.4a DSL search of entities

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-242, DV-89 to DV-96; relies on DD-087 to DD-092, DD-240, DD-241

The first part of increment 4.4: `GET /api/atlas/v2/search/dsl` answering the entities a DSL query finds, as
`DiscoveryREST.searchUsingDSL` and the traversal executor of `EntityDiscoveryService.searchUsingDslQuery`
answer them. `DSLVisitor` and `GremlinQueryComposer` are replaced: the syntax tree of 4.3 is composed into the
filter tree of the basic search (DD-242), searched in one Elasticsearch query. Projections (`select`,
`groupby`, aggregates) and traversals into referred entities are 4.4b.

## Scope

| Endpoint                       | Takes                                                    | Answers             |
| ------------------------------ | -------------------------------------------------------- | ------------------- |
| `GET /api/atlas/v2/search/dsl` | `query`, `typeName`, `classification`, `limit`, `offset` | `AtlasSearchResult` |

In `aurelius-atlas-core`, which now depends on `aurelius-atlas-dsl`: `identifier_helper` (`IdentifierHelper`),
`dsl_query_composer` (replacing `DSLVisitor` and `GremlinQueryComposer` with `RegistryBasedLookup`),
`dsl_query_executor` (`TraversalBasedExecutor`); the discovery service answers DSL queries; search queries
gain two regular expression tests. The server's `routes/discovery` answers the endpoint.

Not in this increment:

| What                                                                                               | Increment  |
| -------------------------------------------------------------------------------------------------- | ---------- |
| `select`, `groupby`, `count`/`min`/`max`/`sum` (`SelectClauseComposer`, `SelectClauseProjections`) | 4.4b       |
| Referred entities: `db.name`, `hive_table, columns`, `select db`, aliases of them                  | 4.4b       |
| Classification attributes (`Dimension where Dimension.tagAttr1 = 'x'`)                             | 4.4b       |
| `hasTerm`                                                                                          | 5.2        |
| `POST search/dsl/download/create_file` and the other search downloads                              | 4.5        |
| `ScriptEngineBasedExecutor`, the translation cache (`atlas.dsl.cached.translator`)                 | not ported |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| DSE-01 | `typeName` and `classification` are at most 4,096 characters (`INVALID_QUERY_PARAM_LENGTH`), the query at most 4,096 (`INVALID_QUERY_LENGTH`, `atlas.graph.dsl-max-query-str-length`). `limit` and `offset` are normalised as SRC-07 (1 to 10,000, else 100; at least 0)                                                                                                                                                                                                                                                                                                       |
| DSE-02 | The query searched is `typeName` in backticks (as given when already in them), a space and the query; with a `classification` and no query, a space and `isa <classification>` follow. The answer is of `queryType` `DSL` with this as `queryText`                                                                                                                                                                                                                                                                                                                             |
| DSE-03 | Unless the query holds `limit` or `offset` anywhere in its text, a space and `limit <limit> offset <offset>` are appended before it is parsed (DSL-01 to DSL-07); the query's own `limit` and `offset` then page the entities found. A query that does not parse fails naming this text                                                                                                                                                                                                                                                                                        |
| DSE-04 | A source naming an entity type finds the entities of it and its sub types, `_ALL_ENTITY_TYPES` every entity; a classification finds the entities it is attached or propagated to, not its sub classifications; `_CLASSIFIED` the entities with any classification, `_NOT_CLASSIFIED` those with none. Names may be quoted. Entities of every state are found. Every further source and condition narrows the entities found                                                                                                                                                    |
| DSE-05 | A source that is neither fails with `DSL Semantic Error - <name> type not found`. A source after the first that names the active type is no further condition; an alias (`T as t`) names the active type; a second alias of the same name fails with Atlas's `INVALID_DSL_DUPLICATE_ALIAS` message, whose quotes leave it unfilled: `Duplicate alias found: {0} for type {1} already present.`                                                                                                                                                                                 |
| DSE-06 | A `where`, and an expression after the sources, compares an attribute of the active type, also inherited, system (`__guid`, `__state`, `__timestamp`, ...) or named `<type>.<attribute>` or `<alias>.<attribute>`, with a value read as the attribute's type: a number (DV-90), a date as `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'` or `yyyy-MM-dd` in UTC, read as Java's lenient `SimpleDateFormat` does (else `Date format: <value>.`), `true` or `false`, or a string. An attribute the type does not have fails with `<name> type not found` and `Qualified name for <name> failed!` |
| DSE-07 | `=`, `<`, `<=`, `>`, `>=` and their words (`eq`, `lt`, ... in any case, DV-89) compare values; `!=` holds for an entity without a value when the value is a string, and only for entities with a value otherwise; a value array `[a, b]` holds for any of its values (DV-91); an array attribute holds when any element does                                                                                                                                                                                                                                                   |
| DSE-08 | `like` matches `*` as any characters and `?` as one: when the attribute's `indexType` is `STRING`, or the value holds other than letters and digits besides them, the whole value must match, in case; otherwise one of its words must, in any case (DV-92). A value that is not a string matches nothing                                                                                                                                                                                                                                                                      |
| DSE-09 | `__isIncomplete = 1` (or `true`) finds incomplete entities and `= 0` (or `false`, or empty) complete ones; `!=` the reverse                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| DSE-10 | `has <attribute>` finds the entities with a value of the attribute, which must be primitive, an enum or a collection of them (else `Property needs to be a primitive type: <name>`); `isa` or `is` a classification, `_CLASSIFIED` or `_NOT_CLASSIFIED` finds them as DSE-04 (else `<name> classification not found`). Their subject, when it names another type outside `and`/`or`, is a further source                                                                                                                                                                       |
| DSE-11 | `and` and `or` join conditions left to right, without precedence: `a and b or c and d` is `((a and b) or c) and d`; parentheses group. An expression after the sources before any type source is ignored, unless it is an `isa`, `is` or `has`, whose subject then is the source; a query without a type source finds every entity                                                                                                                                                                                                                                             |
| DSE-12 | `orderby` sorts by a primitive attribute, `asc` unless `desc`, leaving out entities without a value (else `OrderBy attribute <name> is non-primitive`); without it, entities come by creation time, then GUID (DV-94)                                                                                                                                                                                                                                                                                                                                                          |
| DSE-13 | The answer lists each entity found as its header with its classifications (`toAtlasEntityHeaderWithClassifications`); none found, it has no `entities`                                                                                                                                                                                                                                                                                                                                                                                                                         |
| DSE-14 | Semantic errors fail the search with `INVALID_DSL_QUERY`, the query of DSE-03 and the reason `DSL Semantic Error - ...` of each error found, in order, joined by a comma and a space (DV-93)                                                                                                                                                                                                                                                                                                                                                                                   |
| DSE-15 | `hasTerm`, arithmetic, `count()`, `max`, `min` or `sum` as a condition, a bare name or value as a condition, an expression after `isa` or `hasTerm`, and a `where` before any source fail with `INVALID_DSL_QUERY` (DV-95); until 4.4b, so do `select`, `groupby`, referred attributes and classification attributes (DV-96)                                                                                                                                                                                                                                                   |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/DiscoveryREST.java`: `searchUsingDSL`, `validateDSLSearchParameters`
- `repository/.../discovery/EntityDiscoveryService.java`: `searchUsingDslQuery`,
  `getDslQueryUsingTypeNameClassification`, `escapeTypeName`
- `repository/.../query/executors/TraversalBasedExecutor.java`, `GremlinClauseToTraversalTranslator.java`
- `repository/.../query/DSLVisitor.java`, `GremlinQueryComposer.java`, `GremlinClause.java`,
  `IdentifierHelper.java`, `RegistryBasedLookup.java`, `QueryParams.java`
- `intg/.../AtlasErrorCode.java`: `INVALID_DSL_*`
- Tests: `GremlinQueryComposerTest` (the clauses each query composes to), `DSLQueriesTest` (the entities
  found)

## Deviations

DV-89: Atlas upper-cases an operator and finds no `LT`, `EQ`, ... among `SearchParameters.Operator`'s symbols,
failing with an internal error; Aurelius compares as with `<`, `=`, ... DV-90: Atlas appends `L`, `f` or `d`
to a number before reading it as the attribute's type, which a `long` cannot read, so a `long` attribute
compares with `null` and finds nothing; Aurelius reads the number. DV-91: Atlas compares the strings of a
value array; Aurelius reads them as the attribute's type. DV-92: Atlas matches the words its index tokenised,
the pattern in case against lower-cased words; Aurelius the analysed words of the text sub-field (DD-092), in
any case. DV-93: Atlas lists every message its composer adds, some following from an earlier one; Aurelius
lists those of the rules above. DV-94: Atlas answers the entities in the order its graph finds them; Aurelius
by creation time, then GUID. DV-95: these forms fail in Atlas with an internal error, a malformed traversal or
no condition at all; Aurelius answers `INVALID_DSL_QUERY` with a reason. `hasTerm` follows the glossary (5.2).
DV-96: temporary, until 4.4b.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — DSE-02 to DSE-15 on the in-memory documents, with the queries of
  `GremlinQueryComposerTest` and `DSLQueriesTest` they cite.
- `libs/python/aurelius-atlas-core/e2e/` — the regular expression tests on Elasticsearch.
- `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/search/dsl-search.scenario.yaml`
  — DSE-01 to DSE-14 over HTTP.
- `uv run aurelius-atlas-trace check`.
