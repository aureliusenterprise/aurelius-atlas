# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-093. Facets are aggregations of the search's own query

- **Status:** Proposed
- **Increment:** 4.2
- **Date:** 2026-10-24

**Decision.** Quick search counts its facets with `terms` aggregations over the `keyword` search fields of
`__typeName`, `__state` and `Asset.owner`, in the same Elasticsearch request as the page of results: the query
of the search, unpaged, at most 100 values each, ordered by count and then by value. `ServiceType` is added up
from the `__typeName` counts with the registry's types. The in-memory documents count the same.

**Reason.** Atlas facets the Solr query its `AtlasSolrQueryBuilder` rebuilds from the same query, types,
filters and state as the search; aggregating the search's own query counts exactly the entities found, without
a second translation of the filters. 100 is Solr's default `facet.limit`.

**Alternatives.** A second request for the counts: one more round trip for the same query.

**Consequences.** Facets count what the search query matches, classification criteria included, which quick
search does not take.

### DD-094. Suggestions are terms aggregations of the text sub-fields

- **Status:** Proposed
- **Increment:** 4.2
- **Date:** 2026-10-24

**Decision.** The text sub-field of DD-092 enables `fielddata`. Suggestions are, for each field weighted 8 or
more (or the one named), a `terms` aggregation of its text sub-field over every entity document, of the 5
terms matching the prefix, most documents first; the fields' terms are then summed and the top 5 kept. The
in-memory documents count the words of the same fields.

**Reason.** Atlas reads Solr's terms component on the fields with `terms.limit` 5 and adds up the frequencies;
a terms aggregation is the Elasticsearch reading of a field's terms and their document frequencies. The
`_terms_enum` API knows no frequencies, and keyword fields hold whole values, not words.

**Alternatives.** A completion suggester: a field of its own per attribute, suggesting whole values. Terms of
the keyword fields: values, not words, and only case-sensitive prefixes.

**Consequences.** Fielddata of a text sub-field is loaded into the heap the first time it is aggregated, which
suggestions limit to the few fields weighted 8 or more. Fields mapped before 4.2b have no fielddata; an entity
index created before needs creating again.
