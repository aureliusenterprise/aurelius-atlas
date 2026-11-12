# 14.7 The derived documents in the embedding

- **Status:** in progress
- **Pull request:** [#335](https://github.com/aureliusenterprise/aurelius-atlas/pull/335)
- **Records:** ADR 059 (Proposed); DD-538 to DD-540 (here); relies on 11.3 (VEC-01 to VEC-06, DD-435 to DD-437),
  14.2 (ASD-01, LAS-04, LAS-05) and 14.3 (ASU-01, DD-518, DD-519)

An entity's embedding is made of its own text: its type, names, description and classifications (VEC-01). A
dataset called `orders` says little on its own; the domain it sits in and the entities and fields it relates to
say what it is about. 14.2 derives exactly that onto the entity's App Search document: its breadcrumb and its
derived relations, by name. This increment adds those names to the embedded text, so a search by meaning for
"customer payments" also finds the `orders` dataset of the Finance domain that holds the `payment` field.

## Scope

- `aurelius-atlas-core`: the embedded text and its hash read the App Search document's breadcrumb and relation
  names (`entity_embedding.py`); the embedding indexer and both stores' listing wait for an entity's document
  (`entity_embedding_indexer.py`, `entity_documents.py`, `testing/memory.py`).
- `aurelius-atlas-server`: the embedding worker's indexer waits for documents while the App Search worker runs.

Not in scope: the query side (11.4 embeds the query as before); the other fields of the App Search document
(scores, verdicts, the person's email); any entity that has no App Search document (LAS-01), whose text stays
VEC-01's.

## Semantics

VEC-01 to VEC-06 hold, with the text and hash below. "The document's names" are the breadcrumb's names and the
derived relations' names the entity's App Search document holds, leaving out none values.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| EMC-01 | An entity's embedded text is VEC-01's text, then, when its document has names: a line of the breadcrumb's names from the top, joined by `>`, if it has any; then for each relation field in LAS-05's order (domain, entity, attribute, field, dataset, collection, system, person, process) that has names, a line of the field's type name, a colon, and its names joined by `,`. The whole is cut at 32,000 characters |
| EMC-02 | An entity's source hash is VEC-02's when its document has no names; otherwise the SHA-256 of VEC-02's parts and the document's names, as the breadcrumb and each relation field hold them                                                                                                                                                                                                                                |
| EMC-03 | A write keeps an entity's embedding only while its source hash is EMC-02's of the entity written (VEC-05): a document derived again with other names drops it; a stale flag, a governance mark, a quality total, or a document derived again with the same names keeps it                                                                                                                                                |
| EMC-04 | With the App Search indexer running, the embedding indexer leaves out the entities that should have a document (LAS-01) and have none, or have a stale one (ASU-01); it embeds them once their document is derived. With it off, the indexer embeds as VEC-06 says                                                                                                                                                       |
| EMC-05 | An entity whose document has no names keeps its embedding across this change; one whose document has names is embedded once more, as its hash is now another                                                                                                                                                                                                                                                             |

## Java origin

None: Apache Atlas has no embeddings (ADR 059), and the derived documents are Aurelius's (ADR 060).

## Deviations

None against Apache Atlas: its API answers as before (VEC-10, ASD-05).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__entity_embedding.py`: EMC-01 to EMC-03 and EMC-05 on stored
  entities: the text's lines, a document without names, what the hash takes and leaves out, the embedding kept
  or dropped. EMC-04 on both stores' listings, with and without waiting, and on the indexer: a dataset embedded
  once its document is there.
- `libs/python/aurelius-atlas-core/tests/test__app_search_indexer.py`:
    - a domain, a data entity, an attribute and a system indexed by both indexers: nothing embedded before the
      documents, then each entity with its neighbours' names; the domain renamed embeds again the three
      entities its name reaches, and not the system;
    - the sample catalogue, indexed by both: every entity embedded once, each documented one with its legacy
      breadcrumb as its path line but DD-485's two; a second round embeds none.
- `libs/python/aurelius-atlas-core/e2e/test__entity_embedding_e2e.py`, on the dev Elasticsearch: the listing of
  EMC-04 by the query on the entity index, kNN finding a dataset by its domain's name, and its document derived
  again with another name dropping the vector.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_embedding.py`: the indexer waits for documents
  exactly while `APP_SEARCH_ENABLED` is on.
