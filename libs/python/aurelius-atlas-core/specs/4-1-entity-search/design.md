# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-087. Basic search is split into entity and classification search

- **Status:** Proposed
- **Increment:** 4.1
- **Date:** 2026-10-24

**Decision.** Increment 4.1 is split: 4.1a searches entities by type, entity filters, state, sort and paging,
with the search fields it needs (DD-088); 4.1b adds the classification search of
`ClassificationSearchProcessor`. The free-text `query` of basic search goes with quick search to 4.2.

**Reason.** Atlas's two processors are separate, and each is as large as one increment.

**Alternatives.** One increment of about twice the size; the free text with 4.1, where it would need the full
text index 4.2 builds anyway.

**Consequences.** Until 4.1b a search naming a classification is refused (DV-46).

### DD-088. Entity attributes are searched in typed search fields named after their defining type

- **Status:** Proposed
- **Increment:** 4.1
- **Date:** 2026-10-24

**Decision.** An entity document carries `search`, a flat object (`subobjects: false`) of its searchable
values: each primitive, enum or array-of-primitive attribute under `<kind>.<qualified name>`, the qualified
name being Atlas's vertex property key (`hive_table.name`, `Referenceable.qualifiedName`, `__guid`), and
`<kind>` the Elasticsearch type its Atlas type maps to: `keyword` for strings and enums, `long` for the
integer types and dates, `double` for `float`, `double` and the big number types, `boolean`. Dynamic templates
on the kind map each new field. The system attributes of the entity root are filled from the document's own
fields. The entity store computes `search` with the registry when it writes an entity.

**Reason.** Atlas's index keys a property by its defining type, so one attribute is one field across sub
types, and its type decides how it compares. A kind in the field's name lets Elasticsearch map a field the
first time it is written, in any process, without a mapping kept in step with the type definitions.

**Alternatives.** Mapping each field from the type definitions when they change: the same fields, but every
process and every type change would update the mapping. One `flattened` field: no range or numeric sort.
Filtering in memory: every search reads every entity of its types.

**Consequences.** Entities written before 4.1a have no `search` until written again. The field limit of the
entity index is raised to 100,000. The big number types compare as doubles.

### DD-089. A search is a query of the entity documents, ordered by creation when no sort is given

- **Status:** Proposed
- **Increment:** 4.1
- **Date:** 2026-10-24

**Decision.** `EntitySearchProcessor` builds a search query of its own: the types, the state, the filter tree
over search fields with Atlas's operators, the sort, offset and size. The entity documents answer it with the
matching entities and their total, which is `approximateCount`; Elasticsearch as a `bool` query, the in-memory
documents by evaluating it. Without `sortBy` entities come by creation time, then GUID.

**Reason.** One query instead of Atlas's index query, graph query and in-memory predicates, whose combination
the rules of SRC-05 state; Atlas's order without a sort is the index's and has nothing to keep.

**Alternatives.** Elasticsearch's query language in the core: the in-memory documents could not answer it.

**Consequences.** `approximateCount` is exact.

### DD-704. A page past the store's search window is a bad request

- **Status:** Proposed
- **Increment:** 4.1 (a fix, 2026-11-19)
- **Date:** 2026-11-19

**Decision.** `verify_page` refuses a page whose `offset` and `size` together pass
`MAX_RESULT_WINDOW` (10,000). `EntitySearchProcessor.query` calls it for a basic
search and for a marker page, and `DslQueryExecutor.execute` calls it before each
search it pages. `AppSearchEngine` keeps its own clamp and reads the one constant.

**Reason.** Elasticsearch answers no document past its `max_result_window`, so no
page past 10,000 can ever be answered. The store raised `ApiError` and the server
turned it into an internal error, which told a caller nothing about its own
request (DV-176, DV-110's reason). A search by meaning already answers
`BAD_REQUEST` past `MAX_NEAREST`, and a view search past its window, so this
message joins two rules of the same shape.

**Alternatives.** Raise the window: the setting is expensive per shard and it only
moves the wall. Answer an empty page: a caller cannot tell a past-the-end page
from one with no matches. Page with `search_after` under the hood: the store has
no sort key that is unique and stable for every search, and a deep page would
then read 10,000 documents per request.

**Consequences.** `offset + limit` above 10,000 fails with `BAD_REQUEST`
`offset + limit may not exceed 10000`, for a marker page too: a decoded marker
feeds the offset the guard reads. The DSL's own `limit` and `offset` take part,
so a query of `limit 100 offset 9950` fails on its own text. A caller that needs
every entity of a large result reads it with a DSL query without `limit` or with
a `select`, which pages the store from 0. `AppSearchEngine` clamps instead,
because App Search answers the page it can and its callers read a list, not a
search result.

### DD-709. A search page reads its headers over one shared reading

- **Status:** Proposed
- **Increment:** 4.1 (a fix, 2026-11-19)
- **Date:** 2026-11-19

**Decision.** `EntityRetriever.headers` reads a whole page's headers over one
`_Reading`. The reading preloads every entity's listed relationships and
classification instances in one read of each kind, and the entities those
references and term assignments name in one read. The four paths that answer
headers for a page call it: the DSL executor's `processVertices` (DSE-13), a
basic search (SRC-09), a free-text search (FTX-05), and a projection's header
columns (DSP-02). A basic search reads the entities a header refers to the same
way, through `header_by_guids`.

**Reason.** Each header took its own `_Reading`, so a page of N entities read
the relationships and classifications of each entity once each, a number of
reads that grew with the page (an N+1). One `_Reading` already caches each
entity's relationships (DD-061) and classifications (DD-070) for one response.
A page shares one such reading, so a relationship, classification or referred
entity named by more than one of them is read once. Apache Atlas reads a page's
vertices in one traversal and maps each header from that one read.

**Alternatives.** A cache above the reading, for a whole request: a wider scope
than the per-response one DD-061 and DD-070 chose, holding reads a later
response must not reuse. A join in the store: Elasticsearch's multi-get already
reads them in one request, so it was the count of reads, not their shape, that
cost.

**Consequences.** The headers are the same JSON one way or the other, which a
test checks by reading a page both ways. The caches span one response, so no
header sees data a single read does not. A search that reads whole entities (a
glossary list, the type counts) still builds them one at a time, as
`entity_with_ext_info` and `entities_with_ext_info` answer them.
