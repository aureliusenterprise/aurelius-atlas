# Plan: 19.4 One document module set and one narrow engine seam

The rules are EDS-01 to EDS-05 of [the spec](./spec.md), the design DD-788 to DD-792.

## Analysis

- **Two large modules, three jobs each.** `entity_documents.py` (1,343 lines, 67 importers) holds index setup,
  the document client, and the query translation. `app_search_engine.py` (779 lines) holds the engine schema,
  the query build, and the answer render.
- **The query job already moved.** 19.1 put the clause builders in `es_clauses` and the word rules in
  `free_text`, so the split here moves only what is left.
- **The protocol is wider than its callers.** `EntityDocuments` lists 34 methods while the indexers call about
  six, and the contract omits `search_app_search` (`:1151`), which is why the engines had to type on the
  concrete client. 19.1 already fixed the search contract; this one narrows the storage contract.

## Steps

1. `index_setup.py`: the index names, the seven mappings, and `ensure_index`. `entity_documents` re-exports so
   importers are untouched in this commit. Pure move (DD-788, DD-789).
2. `documents_es.py`: the `ElasticsearchEntityDocuments` client, importing names from the index module and
   clauses from `es_clauses`. Pure move. Commit two.
3. Engine split into schema, query, and answer. Delete the private `_WORD` and import the `free_text` word
   (DD-790). Pure move. Commit three.
4. Narrow `EntityDocuments` to the methods the callers call, and drop the now-unused fake methods (DD-791).
   This is the one behaviour-adjacent commit and it gets the typecheck gate.
5. Move each test with its function and re-run the trace check to confirm no path changed (DD-792).

Commits 1 to 3 and 5 are pure moves a reviewer checks with `git diff -w`. Commit 4 is the only one that
removes
methods, so it is the only one the parity scenarios must prove again.

## Verification

Level 0: `uv run pytest libs/python/aurelius-atlas-core/tests libs/python/aurelius-atlas-store-es/tests`,
ruff,
pyright, and `git diff -w` empty on each pure-move commit. Level 1: `nx test aurelius-atlas-core
aurelius-atlas-store-es aurelius-atlas-server -c ci` and the parity scenarios. EDS-05 is the gate: the
scenarios
and `test__app_search_governance.py` answer identical to the base, byte for byte. Level 2: `nx
e2e aurelius-atlas-server -c ci` once, after commit 4. Trace check scoped to EDS, compared against the base.
