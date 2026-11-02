# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-242. A DSL query is composed into the basic search's filter tree

- **Status:** Proposed
- **Increment:** 4.4
- **Date:** 2026-10-30

**Decision.** `DSLVisitor` and `GremlinQueryComposer` are replaced by one composer in `aurelius-atlas-core`
(`dsl_query_composer`) that walks the syntax tree of 4.3 (DD-241) and writes the `SearchQuery` of the basic
search (DD-089): the sources and conditions as one filter tree of `Criterion` and `Group` over the search
fields (DD-088), the `orderby` as its sort, the limit and offset as its page. `like` adds two tests to the
search query: `REGEX`, a regular expression the whole keyword value matches in case, and `WORD_REGEX`, one a
word of the text sub-field (DD-092) matches in any case; Elasticsearch answers both with `regexp`, the
in-memory documents with Python's `re`. The composer keeps Atlas's name resolution (`IdentifierHelper.Info`,
`RegistryBasedLookup`), its left-to-right joining of `and` and `or`, and its semantic errors, collected and
joined into one `INVALID_DSL_QUERY`. `aurelius-atlas-core` depends on `aurelius-atlas-dsl`.

**Reason.** Atlas's composer writes Gremlin text that its executor turns back into a traversal; every clause
of 4.4a is a test of the entity's own fields, which the basic search already translates to Elasticsearch and
evaluates in memory. One filter tree keeps a DSL query to one Elasticsearch request, reuses the paging,
sorting and tie-breaking of the basic search, and lets the in-memory documents answer the core tests.

**Alternatives.** Port `GremlinQueryComposer` clause by clause and translate the clause list: the closest
port, but a second translation of every predicate the basic search already has. Elasticsearch's query string
syntax: a client's query would reach Elasticsearch's parser, with neither Atlas's grammar nor its errors.

**Consequences.** Traversals into referred entities, classification attributes and projections (4.4b) are not
tests of one document's fields; 4.4b decides how they are evaluated, over the relationship documents (DD-061).
Lucene's regular expressions are not Java's or Python's: the patterns `like` writes (`.`, `.*`, escaped
characters, classes) read the same in all three, which the e2e tests check.
