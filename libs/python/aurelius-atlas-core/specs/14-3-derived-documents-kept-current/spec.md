# 14.3 The derived documents kept up to date

- **Status:** in progress
- **Pull request:** [#328](https://github.com/aureliusenterprise/aurelius-atlas/pull/328)
- **Records:** DD-518 to DD-521 (here); relies on 14.1 (LAS-04 to LAS-06, LAS-08 to LAS-10, DD-486) and 14.2
  (ASD-01 to ASD-05, DD-498 to DD-501)

## Scope

A change in the catalogue reaches every App Search document it affects. That covers the changed entity's own
document, and the breadcrumbs and derived relations of other entities that name it. The server keeps them up to
date in the background. In `aurelius-atlas-core`:

- the stale document, which a write keeps and marks instead of dropping (`app_search_document.py`);
- the state a relationship's ends' documents last saw, on the stored relationship (`stored_relationship.py`);
- the indexer's upkeep of the documents a change affects (`app_search_indexer.py`);
- the listings of stale documents, of the documents that name an entity, and of the relationships whose ends
  have not seen their state, in both entity document stores, Elasticsearch and in memory.

In `aurelius-atlas-server`, the worker that runs the indexer (`app_search.py`) and its settings.

Not delivered, with the increment that will:

| Not delivered                                                                    | Lands with |
| -------------------------------------------------------------------------------- | ---------- |
| The engine's fields that are the entity's or constants: `id`, the type, LAS-07's | 14.4       |
| Whether a search shows a stale document's fields                                 | 14.4       |
| The score fields and their roll-up (LAS-12)                                      | 14.5       |

## Semantics

14.1's LAS-08 to LAS-10 hold for the stored documents. ASU-01 replaces the second sentence of ASD-03, and ASU-02
extends ASD-04's listing.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ASU-01 | A write keeps an entity's document whose hash is not the entity's current one, marked `stale`                                                                                                                                                                                                                                       |
| ASU-02 | The indexer also lists the entities whose document is stale. It gives each the document LAS-01 to LAS-06 give it now, or none if LAS-01 gives it none                                                                                                                                                                               |
| ASU-03 | An entity whose document goes, or whose name, breadcrumb or relation GUIDs differ from its stale document's, affects the documents that name it in a breadcrumb or a relation, and the entities its old and new documents name. Each affected document is derived again; one that changes so affects others in turn                 |
| ASU-04 | A relationship records the state its ends' documents were derived with once it has been deleted. The indexer lists the relationships whose state is not the one recorded, deleted or restored; their ends are affected as in ASU-03, and the relationship then records its state                                                    |
| ASU-05 | The indexer writes an affected document only if it changed, on the version it read. It writes the documents a page affects before the page's own; if one of those writes fails, the page's entities and relationships stay listed for a later round                                                                                 |
| ASU-06 | The server runs the indexer in the background of every process: a round at start, then every poll interval. A failed round is logged and the next one tries again. The worker is on unless `AURELIUS_ATLAS_SERVER_APP_SEARCH_ENABLED` is false; `..._APP_SEARCH_BATCH_SIZE` and `..._APP_SEARCH_POLL_SECONDS` set its page and pace |
| ASU-07 | No answer of Apache Atlas's API shows a relationship's recorded state                                                                                                                                                                                                                                                               |

## Aurelius origin

From `aureliusenterprise/aurelius` at commit b057389, the changes the legacy pipeline made to the documents:

- `libs/m4i-flink-tasks/.../synchronize_app_search/event_handlers/attribute_changed/`: names and definitions
  (LAS-08).
- `.../entity_deleted/delete_breadcrumbs.py`, `delete_derived_entities.py`: deletes (LAS-09).
- `.../relationship_audit/`: relations added and removed (LAS-05, LAS-06).

The handlers patched documents in place, event by event. Here the indexer derives an affected document again
from the catalogue's state (DD-486).

## Deviations

None against Apache Atlas: its API answers as before (ASD-05, ASU-07). None against the legacy documents:
for a given catalogue they hold what 14.2's do.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__app_search_upkeep.py`, small catalogues in the in-memory store,
  each change followed by one round, and each document compared with the one 14.2 derives from scratch:
    - a rename shows in the breadcrumbs below and in the relations at the other ends (LAS-08), and a changed
      definition only on the entity's own document;
    - a deleted entity's document goes, and it leaves the relations and breadcrumbs that named it; the entities
      below get the breadcrumb of their next parent (LAS-09);
    - a relationship deleted on its own, and one an update of a relationship attribute deletes, leave their
      ends' relations, and their record follows (ASU-04);
    - a field joined to an attribute shows the dataset on the data entity, two hops away (ASU-03, LAS-06);
    - an affected entity changed in between keeps the page listed (ASU-05);
    - a relationship's answer leaves out its recorded state (ASU-07).
- `libs/python/aurelius-atlas-core/tests/test__app_search_document.py`: the stale mark (ASU-01), and the
  listings in both stores (ASU-02, ASU-04).
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_app_search.py`: the worker's rounds, a failed
  round, the settings, and the worker started with the server (ASU-06, LAS-10).
- `libs/python/aurelius-atlas-core/e2e/test__app_search_e2e.py`, on the dev Elasticsearch: a rename found by a
  term query on the other end's relation after a round, the listings' queries, and an existing relationship
  index getting the new field mapped.
