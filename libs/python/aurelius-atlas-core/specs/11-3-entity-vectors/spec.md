# 11.3 Entity vectors

- **Status:** in progress
- **Pull request:** to follow
- **Records:** ADR 059 (Proposed); DD-434 to DD-439; relies on 11.2 (the embedder, DD-429 to DD-433), DD-043,
  DD-046, DD-047, DD-088

Every entity in the store gets the embedding of its text, computed by the embedder of 11.2 and kept on the
entity's own document, so the searches of 11.4 can find entities by meaning with the filters and facets they
have today (ADR 047, ADR 059). The server embeds new and changed entities in the background, and the entities
already stored the same way.

## Scope

- `aurelius-atlas-core`: the embedded text and its hash (`entity_embedding.py`); the `embedding` of a stored
  entity; its mapping on the entity index; the store's reads and writes that keep it current; the indexer that
  embeds the entities without a current embedding.
- `aurelius-atlas-server`: the embedding settings, the client of an OpenAI-compatible embeddings API, and the
  worker that runs the indexer in the background.
- The standalone stack: the server embeds through the stack's `embedder`.

Not in scope: searching by the vectors (11.4); the webapp (11.5); metrics of the indexer; the dev stack and the
Helm chart.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VEC-01 | An entity's embedded text is its type name, then the text values of its attributes named `name`, `displayName`, `qualifiedName`, `description` and `definition`, in that order and without repeats, then the names of its classifications, sorted; one per line, cut at 32,000 characters                                                                                                                                                                                          |
| VEC-02 | An entity's source hash is the SHA-256 of what its text is made of as the entity holds it: its type name, those attribute values, and its classifications' GUIDs, sorted                                                                                                                                                                                                                                                                                                           |
| VEC-03 | With embedding on, the entity index is created with `index.mapping.exclude_source_vectors: false` and maps `embedding.vector` as a `dense_vector` of the configured dimensions with cosine similarity, and `embedding.model` and `embedding.sourceHash` as keywords. An existing entity index created otherwise moves at start to the next generation behind its alias, by a reindex of every document; an index whose vector has other dimensions stops the start with the reason |
| VEC-04 | Every document of the entity index keeps its source as written, its numbers' digits included (DD-039), also when it holds a vector and after the move; and every read of an entity returns its embedding with its vector, so a write carries it                                                                                                                                                                                                                                    |
| VEC-05 | A write keeps an entity's embedding only while its source hash is the entity's current one; otherwise the entity is written without one                                                                                                                                                                                                                                                                                                                                            |
| VEC-06 | The indexer embeds, as passages, the entities without an embedding of the configured model, except those of types whose names start with `__`, in pages of the batch size; it writes each embedding only if the entity is still at the version it read, and leaves an entity changed in between for a later round                                                                                                                                                                  |
| VEC-07 | The server runs the indexer in the background, a round at start and then every poll interval; a round that fails, as when the embedder cannot be reached, is logged and tried again, and neither the start nor a request waits for it                                                                                                                                                                                                                                              |
| VEC-08 | The settings `AURELIUS_ATLAS_SERVER_EMBEDDING_URL`, `_MODEL`, `_DIMENSIONS`, `_CA_FILE`, `_BATCH_SIZE` and `_POLL_SECONDS` configure it; without a URL embedding is off: no mapping, no indexer, and the server runs as before                                                                                                                                                                                                                                                     |
| VEC-09 | The client posts the texts, the model and `input_type: passage` to `{url}/v1/embeddings`, and fails on an answer with another number of embeddings or another number of dimensions                                                                                                                                                                                                                                                                                                 |
| VEC-10 | No answer of Apache Atlas's API shows an entity's embedding                                                                                                                                                                                                                                                                                                                                                                                                                        |
| VEC-11 | The standalone stack's server embeds through `https://embedder:21004`, trusting the stack's CA                                                                                                                                                                                                                                                                                                                                                                                     |

## Java origin

None: Apache Atlas has no embeddings (ADR 059).

## Deviations

None against Apache Atlas: Atlas's API answers as before (VEC-10).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__entity_embedding.py`: VEC-01, VEC-02, VEC-05, VEC-06 on the
  in-memory store and a fake embedder.
- `libs/python/aurelius-atlas-core/e2e/test__entity_embedding_e2e.py`: VEC-03 to VEC-06 on the dev
  Elasticsearch, in indices of their own: the mapping, a vector carried through a read and a write, dropped
  when the text changes, the indexer's conditional writes, kNN finding the entity, and an index stored before
  embedding moved with a decimal's digits kept.
- `apps/aurelius-atlas-server/tests/`: VEC-07 to VEC-10.
- `tests/test__standalone_embedder.py`: VEC-11.
