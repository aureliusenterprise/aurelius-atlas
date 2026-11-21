# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-767. One module builds every Elasticsearch clause core emits

- **Status:** Proposed
- **Increment:** 19.1
- **Date:** 2026-11-21
- **Relates to:** QRY-01.

**Decision.** A new module `aurelius_atlas_core/es_clauses` owns the translation from a `SearchQuery` filter
tree, an App Search filter, a free-text query, and a vector query to Elasticsearch clause dictionaries.
`entity_documents` keeps its methods and delegates. The App Search engine stops building `bool`, `should`,
`range`, and `knn` dictionaries itself.

**Reason.** Today four places build the same clause kinds: `entity_documents._es_filter` and its neighbours
(`:1249-1343`), `app_search_engine.filter_clauses` and `query_body` (`:352-635`), the in-memory store
(`testing/memory.py:285-480`), and the store fake (`aurelius_atlas_store_es/testing/fake.py:508-660`). Adding
one predicate means editing all four, and nothing says so. `SearchQuery` and `Test` are already the neutral
vocabulary that Atlas's `SearchPredicateUtil` became, so the builder that walks them is the natural owner.

**Alternatives.**

- **Fold the builder into `entity_documents.py`.** That file is 1,343 lines and imported by 64 modules. Growing
  it makes 19.4's split harder, not easier, and the engine would keep importing the storage module for query
  work.
- **Leave the engine and the store apart, as today.** The duplication is the finding. The two readings already
  disagree on `minimum_should_match` (DD-769), which is the cost of the split.

### DD-768. The fake keeps its own reading of Elasticsearch query JSON

- **Status:** Proposed
- **Increment:** 19.1
- **Date:** 2026-11-21
- **Relates to:** QRY-02, QRY-03, QRY-04.

**Decision.** The store fake continues to interpret the Elasticsearch query dictionaries itself, and does not
call the shared clause builder. It stops carrying its own word patterns and imports them from
`aurelius_atlas_store_es.text_analysis`, the module DD-772 puts them in. It gains an honest
`minimum_should_match`. One differential test compares the in-memory store and the fake on a saved matrix of
basic searches.

**Reason.** The fake stands in for a server we do not run, so its value is that it reads the emitted JSON the
way Elasticsearch does. If it called the builder, a wrong builder and a wrong fake would agree silently, which
is the failure the increment exists to remove. The patterns it copies are the exception: `fake.py:668-669`
duplicate `free_text.py:28-29` exactly, and a divergence there is a bug rather than a second opinion.

**Alternatives.**

- **The fake delegates to the shared builder.** One semantics and less code, and it was the first choice in the
  plan's open decision D1. It gives up the only independent check on the emitted query, so a wrong clause shape
  passes every unit test.
- **Two independent fakes plus a differential test on both.** A third reading buys little over the two that
  exist, and both would need the same fix in the same pull request anyway.

### DD-769. The fake honours the `minimum_should_match` a clause carries

- **Status:** Proposed
- **Increment:** 19.1
- **Date:** 2026-11-21
- **Relates to:** QRY-03.

**Decision.** The fake's `bool` handling counts how many `should` clauses matched and compares that with the
clause's `minimum_should_match`, defaulting to Elasticsearch's own rule: one when `should` is the only clause
kind, and zero when `filter`, `must`, or `must_not` is present.

**Reason.** The fake today treats `should` as `any(...)` (`fake.py:527-533`) and ignores the value. Production
emits the key in ten places, always with `1`, so the fake agrees by luck. `app_search_engine._or_missing`
(`:396`) is the shape where a future `2` is plausible, and a query that needs two alternatives currently passes
every unit test and fails against a real server.

**Alternatives.**

- **Fix production to never pass a value other than `1`.** That hides the gap instead of closing it, and the
  engine's own `_or_missing` composition is exactly where such a value arrives.
- **Leave it and note it.** The finding is that a green suite hides a wrong answer. A note keeps it hidden.

### DD-770. The engines are typed against a narrow search contract

- **Status:** Proposed
- **Increment:** 19.1
- **Date:** 2026-11-21
- **Relates to:** QRY-05.

**Decision.** A new `@runtime_checkable Protocol` `SearchDocuments` names the two methods the engines call: the
App Search search and the terms search. `AppSearchEngine` and `ViewSearchEngine` take that instead of the
concrete class. `ElasticsearchEntityDocuments` satisfies it unchanged. The in-memory store keeps answering the
basic search and the terms search it already answers, and does not gain an App Search search. Specs that drive
an engine pass a small purpose-built fake for the one method they need, the pattern `FakeEmbedder` uses.

**Reason.** `search_app_search` is missing from the store protocol (`entity_documents.py:1151` is absent from
`:340-495`), so the engines must take the concrete class, and 28 test call sites carry
`# type: ignore[arg-type]`. Naming the contract removes those casts without inventing an implementation. An
App Search search needs the engine's field table, its nested index paths, and its weighted vector scoring, so
an honest in-memory version is a third query engine. Building one would grow the duplicate semantics this
increment sets out to shrink.

**Alternatives.**

- **Widen `EntityDocuments` to 35 methods and make the memory fake satisfy it.** The protocol already forces
  every fake to carry 34 methods while the indexers call six. A 35th makes the fake larger and used less.
- **Give the memory store an App Search search.** Costs about the size of the existing fake's search code, and
  the differential test then has three engines to reconcile rather than two.

### DD-771. The differential matrix is saved data, not generated queries

- **Status:** Proposed
- **Increment:** 19.1
- **Date:** 2026-11-21
- **Relates to:** QRY-04.

**Decision.** One test reads a fixture that lists searches in the `SearchQuery` form with the entity fixtures
they run against, and asserts the same hit GUID sequence and the same facet counts on both stores. The matrix
names each `Test` predicate, both sort tie-breaks, present-before-absent ordering, and one vector query.

**Reason.** A generated matrix is a generator to debug, and a generator that produces only queries both engines
already handle proves nothing. A named list is the same artefact the parity scenarios are: reviewed as code, so
a reviewer sees which predicate the suite would stop covering when one drops out.

**Alternatives.**

- **Property test over random queries.** Stronger in theory, and unusable when it fails, because the reported
  query is not one a person wrote. The frozen corpus in 14.6 set the precedent for saved expectations.
- **Rely on the existing per-rule unit tests.** They assert each engine against its own expectation, so a shared
  misreading passes both. That is precisely the gap QRY-04 closes.

### DD-772. The word rules move, the text weights stay

- **Status:** Proposed
- **Increment:** 19.1
- **Date:** 2026-11-21
- **Relates to:** QRY-02.

**Decision.** A new module `aurelius_atlas_store_es.text_analysis` owns the word pattern, the query-word
pattern, `words` and the term match, so core's free-text reading, the App Search engine and the fake use one.
`free_text` keeps the weighted field table and the query preparation, and re-exports `words` where its callers
already read it. The engine's private `_WORD` (`app_search_engine.py:58`) goes away.

**Reason.** Three modules define a word: `free_text.py:28`, `app_search_engine.py:58`, and `fake.py:668`. The
first two are the same expression, and the third matches a `.text` sub-field's words, so a change to tokenising
that misses one of them makes the highlighter disagree with the index that matched. The module belongs to the
store package because `aurelius-atlas-store-es` depends on no Aurelius package while core depends on it, so a
core module is not importable from the fake, and the words a `.text` sub-field keeps are Elasticsearch analysis
rather than core business logic. The weight table stays put, because the fake does not use weights and moving
it would touch 4.2's rules for no gain.

**Alternatives.**

- **Let each module keep its pattern.** It is the current state, and the audit named it as a finding.
- **Put the patterns in `free_text`.** The first plan step said so, and it cannot work: core depends on the
  store package, so the fake cannot import a module from core.
- **Move the weight table too.** `FTX-01` to `FTX-03` own those weights, and 4.2's parity tests guard them. No
  duplication exists there, so a move is churn.
