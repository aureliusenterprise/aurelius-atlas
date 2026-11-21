# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-788. The split ships as a pure-move commit first

- **Status:** Proposed
- **Increment:** 19.4
- **Date:** 2026-11-21
- **Relates to:** EDS-01, EDS-02, EDS-05.

**Decision.** The first commit of this increment moves code between files and changes no behaviour and no
signature. A second commit narrows the contracts.

**Reason.** `entity_documents.py` is 1,343 lines and imported by 67 modules, and a move that also renames or
re-types makes the review a guess. With a pure-move commit, a reviewer checks that the same functions exist in
the new files and that `git diff -w` is empty, which is a file-existence check rather than a logic read.

**Alternatives.**

- **Move and narrow in one pass.** Smaller total diff, and impossible to review, because a reviewer cannot
  tell a moved method from a changed one across 67 importers.

### DD-789. Three modules by job, not three modules by size

- **Status:** Proposed
- **Increment:** 19.4
- **Date:** 2026-11-21
- **Relates to:** EDS-01, EDS-02.

**Decision.** `index_setup` owns the index names, the seven mappings, and the create-once logic.
`documents_es` owns the Elasticsearch client. The query translation already lives in `es_clauses` (19.1). The
split follows the job a reader changes, not a line count.

**Reason.** Adding one filter type today means editing the contract, the client, and the index settings
together,
because they share a file. When index setup, storage, and query each have a home, a reviewer opens one module
for
one kind of change. The audit read the file as doing six jobs, and three of those six are index, storage, and
query.

**Alternatives.**

- **Split by size into any three parts.** Parts cut across a job make every change touch two modules, which is
  the coupling the split exists to remove.
- **Leave it and add an index README.** A README does not stop a mapping and a query change landing in the
  same file.

### DD-790. The engine splits into schema, query, and answer

- **Status:** Proposed
- **Increment:** 19.4
- **Date:** 2026-11-21
- **Relates to:** EDS-04.

**Decision.** `app_search_engine.py` becomes the engine schema (its field table and kinds, `filter_clauses`
and
the `Kind` word table), the engine query (`query_body` and the request build), and the engine answer (the hit
render and `_snippet`). The private `_WORD` at `:58` goes away and the answer part imports the exported word
from
`free_text` (19.1's DD-772).

**Reason.** The file holds three reasons to change: what fields an engine exposes, how a search is asked, and
how
a hit is shown. Its word pattern is the third definition of a word that 19.1 already collapsed into
`free_text`,
so the answer part uses the shared one and the highlighter cannot disagree with the index.

**Alternatives.**

- **Split the engine by method.** A field-table change and a request-build change land in the same module, and
  the word definition stays private to it.

### DD-791. A contract lists only the methods its callers call

- **Status:** Proposed
- **Increment:** 19.4
- **Date:** 2026-11-21
- **Relates to:** EDS-03.

**Decision.** The `EntityDocuments` contract and the `SearchDocuments` contract from 19.1 list only the
methods
the indexers and the doors call, not the full method set of the client. `ElasticsearchEntityDocuments` stays
full;
the contracts it satisfies are per-caller.

**Reason.** The present `EntityDocuments` protocol lists 34 methods while the indexers call about six, so the
in-memory and fake stores each carry methods no one calls. A per-caller contract keeps the client whole and
makes
each fake as large as the seam it stands in for. This is the same reasoning as DD-770 in 19.1, applied to the
storage contract rather than the search contract.

**Alternatives.**

- **Keep one wide protocol so every store implements all of it.** The fakes grow, and a method no one calls
  still has to be satisfied, which is the cost the audit named.

### DD-792. Each moved function keeps its own test identity

- **Status:** Proposed
- **Increment:** 19.4
- **Date:** 2026-11-21
- **Relates to:** EDS-05.

**Decision.** A test that names a function by dotted path moves with the function, and the `covers` marker
keeps
naming the rule it named before. No test is merged or dropped because the code moved.

**Reason.** ADR 049 ties each function and rule to a test that names it. A move that changes the dotted path
breaks that link silently, and `aurelius-atlas-trace check` then reports a gap that is only a path change.
Moving
the test with the function keeps the link honest and keeps the trace report comparing like with like.

**Alternatives.**

- **Rewrite the `covers` paths after the move.** Extra churn in the same review, and it lets a genuinely
  dropped test hide inside a path rename.
