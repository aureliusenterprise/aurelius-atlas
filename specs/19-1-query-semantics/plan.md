# Plan: 19.1 One query semantics for the store and its fakes

The rules are QRY-01 to QRY-06 of [the spec](./spec.md), the design DD-767 to DD-772.

## Analysis

- **The four builders.** `entity_documents.py:1249-1343` translates the `SearchQuery` filter tree.
  `app_search_engine.py:352-635` builds the App Search clauses. `testing/memory.py:285-480` reads queries in
  Python. `aurelius_atlas_store_es/testing/fake.py:508-660` reads the Elasticsearch JSON. The first two write
  clauses, and the last two read them.
- **What moves.** Only the clause writers merge into `es_clauses`. The two readers stay separate, because a
  reader that shares code with the writer cannot catch the writer (DD-768).
- **The clause kinds.** `_es_filter` is one 18-branch `match` over `Test`. The engine adds ranges, the
  missing-means-default pair, and the kNN block. The kNN block already exists in three near-copies, so the
  builder takes it from `entity_documents` and the engine calls the same function.
- **The contract gap.** `search_app_search` is defined on `ElasticsearchEntityDocuments` (`:1151`) and absent
  from the protocol (`:340-495`), so `AppSearchEngine` and `ViewSearchEngine` take the concrete class. The fake
  needs an honest `minimum_should_match`, which no current test exercises because production always passes `1`.
- **The word patterns.** `fake.py:668-669` copy `free_text.py:28-29` exactly, and `app_search_engine.py:58`
  repeats the first one. Three definitions, one meaning. The store package owns them, because core depends on
  it and not the other way round, so the fake can import them (DD-772).

## Steps

1. `aurelius_atlas_store_es/text_analysis.py`: the `WORD` and `QUERY_WORD` patterns and the word helpers the
   engine and the fake need; `free_text.py` and `app_search_engine.py` use them (DD-772).
2. `es_clauses.py`: the filter, text, range, kNN, and facet builders, taking the bodies from
   `entity_documents` and the engine. Tests move with each builder.
3. `entity_documents.py` and `app_search_engine.py`: call the builders. No method signature changes here, so
   every existing test still names the method it covers.
4. `fake.py`: honour `minimum_should_match`, import the word patterns (DD-768, DD-769).
5. `SearchDocuments` protocol, and the two engines typed against it. Give the engine specs a purpose-built fake,
   and replace the 28 `# type: ignore[arg-type]` call sites with the cast `FakeClient` prescribes (DD-770).
6. The differential matrix fixture and its test (DD-771).

Commit 1 to 3 is behaviour-preserving and reviewable by diff. Commit 4 changes the fake, and its failures are
the increment's purpose: triage each new failure on this branch, and fix a real query bug in its own commit.

## Verification

Level 0: `uv run pytest libs/python/aurelius-atlas-store-es/tests libs/python/aurelius-atlas-core/tests`,
ruff, pyright. Level 1: `nx test aurelius-atlas-server -c ci` and the parity scenarios. QRY-06 is the gate: the
scenarios and `test__app_search_governance.py` must answer identical to the base, byte for byte. Level 2:
`nx e2e aurelius-atlas-server -c ci` once, at the end. Trace check scoped to QRY, compared against the base.
