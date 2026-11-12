# 14.2 The derived documents

- **Status:** done
- **Pull request:** [#322](https://github.com/aureliusenterprise/aurelius-atlas/pull/322)
- **Records:** DD-498 to DD-501 (here); relies on ADR 060, 14.1 (LAS-01 to LAS-06, DD-484 to DD-486), and 11.3's
  whole-document writes (DD-434, DD-436)

## Scope

Every entity that the original webapp's `atlas-dev` engine had a document for gets that document on its own
entity document. Each document holds the entity's own fields, its breadcrumb and its derived relations, computed
from the store as 14.1's rules state them. For the sample catalogue, the derived documents equal the legacy ones
except for DD-485's list. In `aurelius-atlas-core`:

- the document as stored (`StoredAppSearch`, the entity's `appSearch`), its mapping on the entity index, and the
  hash a write checks (`app_search_document.py`);
- the indexer that derives the documents the store's entities lack (`app_search_indexer.py`);
- the listing of those entities in both entity document stores, Elasticsearch and in memory.

Not delivered, with the increment that will:

| Not delivered                                                                    | Lands with |
| -------------------------------------------------------------------------------- | ---------- |
| The documents a change of another entity affects: renames, deletes, relations    | 14.3       |
| The server worker that runs the indexer                                          | 14.3       |
| The engine's fields that are the entity's or constants: `id`, the type, LAS-07's | 14.4       |
| The score fields (LAS-12)                                                        | 14.5       |

## Semantics

14.1's LAS-01 to LAS-06 hold for the stored documents, with LAS-01 leaving out `m4i_dq_score` too (DD-500).
From 14.3, a write marks a document whose hash is not current stale instead of dropping it (ASU-01, DD-518).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                     |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ASD-01 | An entity's App Search document is kept on its entity document, as `appSearch`, under the engine's field names: `name`, `referenceablequalifiedname`, `definition`, `email`, `sourcetype`, `breadcrumbguid`, `breadcrumbname`, `breadcrumbtype`, `parentguid` and the 18 relation fields; and `sourceHash`, the hash it was derived with |
| ASD-02 | The entity index maps every field of `appSearch` as a keyword; the names, those of the entity, its breadcrumb and its relations, also as text. An existing entity index gets the mapping at start                                                                                                                                        |
| ASD-03 | An entity's source hash is the SHA-256 of its type name, its state, the values of its `name`, `qualifiedName`, `definition` and `email` attributes, and the GUIDs of the relationships it lists, sorted. A write keeps the entity's document only while the document's hash is the entity's current one                                  |
| ASD-04 | The indexer derives, in pages of the batch size, the documents of the active entities of m4i types that have one (LAS-01) and lack it. It writes each document only if the entity is still at the version it read, and leaves an entity changed in between for a later round                                                             |
| ASD-05 | No answer of Apache Atlas's API shows an entity's App Search document                                                                                                                                                                                                                                                                    |

The derived relations list the entity's relationships in the order the entity lists them, then the pairs that
a field joins (LAS-06), each other end once (DD-501).

## Aurelius origin

From `aureliusenterprise/aurelius` at commit b057389:

- `libs/m4i-flink-tasks/.../synchronize_app_search/event_handlers/entity_created/entity_created.py`: the own
  fields, `sourcetype`, the relation fields and the breadcrumb (LAS-01 to LAS-05).
- `backend/m4i-atlas-post-install/scripts/connect_datasets_with_entities.py`: the field's join (LAS-06).

## Deviations

None against Apache Atlas: its API answers as before (ASD-05). Against the legacy documents, the differences of
14.1's table, which DD-485 decided: [DV-149](../../../../docs/architecture/conversion/deviations.md) (the own
fields), DV-151 (the breadcrumbs) and DV-152 (the relations).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__app_search_indexer.py`:
    - the sample catalogue, imported into the in-memory store and indexed in one round, against `atlas-dev`: all
      684 documents, and LAS-02 to LAS-06 field by field. The only differences are those of 14.1's table: 1
      name, 20 qualified names and 87 definitions, 2 breadcrumbs, and 18 relations at 5 datasets;
    - small catalogues for what the sample does not show: the parents' order, a cycle, a deleted parent, the
      join, a type that is not mapped, a write in between (ASD-04), and the Atlas answer (ASD-05).
- `libs/python/aurelius-atlas-core/tests/test__app_search_document.py`: the own fields' fallbacks, the hash
  (ASD-03), the mapping (ASD-02), and the listing in both stores.
- `libs/python/aurelius-atlas-core/e2e/test__app_search_e2e.py`, on the dev Elasticsearch: the indexer's
  documents found by a term query on a relation and a breadcrumb; a rename drops the document, and the entity
  is listed again.
