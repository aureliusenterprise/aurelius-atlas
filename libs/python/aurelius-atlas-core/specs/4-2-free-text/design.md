# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-091. Free text is split from quick search

- **Status:** Proposed
- **Increment:** 4.2
- **Date:** 2026-10-24

**Decision.** Increment 4.2 is split: 4.2a indexes and searches free text, in basic search's `query` and in
`search/fulltext`; 4.2b answers `search/quick` with its facets, and `search/suggestions`.

**Reason.** Quick search and suggestions build on the free text; each part is about one increment.

**Alternatives.** One increment of about twice the size.

**Consequences.** Until 4.2b, the dashboards' quick search box finds nothing.

### DD-092. String search fields carry an analysed text sub-field, searched with Atlas's weights

- **Status:** Proposed
- **Increment:** 4.2
- **Date:** 2026-10-24

**Decision.** The dynamic template of `keyword` search fields gives each a `text` sub-field, analysed by
Elasticsearch's standard analyser, and keeps values over 8,191 characters out of the keyword. An entity's
search fields gain `__classificationsText`. A free-text query is a `simple_query_string` over the text
sub-fields of the string attributes of the non-internal entity types and of `__classificationsText`,
`__labels`, `__customAttributes` and `__typeName`, each boosted by the weight Atlas's `SolrIndexHelper` gives
its Solr field. The in-memory documents match words the same way, without Elasticsearch's scoring.

**Reason.** Atlas's free text is Solr's `edismax` over the same fields with the same weights as `qf`; a
sub-field keeps each attribute's weight and its exact `keyword` for the filters of 4.1.

**Alternatives.** One catch-all text field: every attribute would weigh the same, and 4.2b's suggestions could
not keep to the fields weighted 8 or more. `query_string`: closer to `edismax`, but a malformed query fails.

**Consequences.** Fields mapped before 4.2a have no text sub-field; an entity index created before needs
creating again.
