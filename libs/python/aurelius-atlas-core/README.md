# aurelius-atlas-core

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-core)

Atlas stores and services for Aurelius Atlas
([DD-002](../../../docs/architecture/conversion/design-log.md#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer)).
Since increment [1.4](../../../docs/architecture/conversion/increments/1-4-typedef-store.md): the typedef
store, which keeps type definitions in one Elasticsearch document and serves them from the type registry.
Since [1.5](../../../docs/architecture/conversion/increments/1-5-builtin-models.md): Apache Atlas's built-in
models and their typedef patches, loaded at start-up. Since
[1.6](../../../docs/architecture/conversion/increments/1-6-types-rest.md): the store's reads and the search of
`/v2/types/typedefs`. Since [2.2](../../../docs/architecture/conversion/increments/2-2-entity-store.md): the
entity store, which keeps each entity as one Elasticsearch document, reserves unique attribute values and writes
several entities all or nothing through a journal (DD-043 to DD-048). Since
[2.3](../../../docs/architecture/conversion/increments/2-3-entity-read-rest.md): the entity retriever, which reads
entities, their owned entities and headers back as Atlas answers them (DD-049, DD-050). Since
[2.4](../../../docs/architecture/conversion/increments/2-4-entity-write-rest.md): the entity writer, which
discovers the entities a request names, resolves its references, maps it onto stored entities and writes them
in one write (DD-052, DD-053). Since
[2.5](../../../docs/architecture/conversion/increments/2-5-delete-semantics.md): soft and hard deletes and
purges with the owned-reference cascade, through writes that also remove documents and an indexed field of the
GUIDs each entity refers to (DD-056 to DD-060). Since
[3.1a](../../../docs/architecture/conversion/increments/3-1-relationship-instances.md): relationship instances,
documents of their own index listed by both ends and written with them (DD-061, DD-062). Since
[3.1b](../../../docs/architecture/conversion/increments/3-1-relationship-attributes.md): the relationship
attributes of entities, mapped onto relationships by the relationship mapper and read back through them, and
delete cascades that follow owned relationships (DD-064 to DD-067). Since
[3.2](../../../docs/architecture/conversion/increments/3-2-ownership-cascades.md): updates delete the owned
entities they drop, through a view of the request's changes and in the request's one write (DD-068). Since
[3.3a](../../../docs/architecture/conversion/increments/3-3-direct-classifications.md): classifications
attached to entities, instances of their own index listed by their entity and written with it (DD-070, DD-071).
Since [3.3b](../../../docs/architecture/conversion/increments/3-3-bulk-classifications.md): the classification
associator behind `bulk/setClassifications`. Since
[3.4a](../../../docs/architecture/conversion/increments/3-4-classification-propagation.md): classification
propagation over relationships, computed and written within the request that causes it (DD-075 to DD-077).
Since [3.4b](../../../docs/architecture/conversion/increments/3-4-propagation-tasks.md): that propagation
deferred to tasks written with the request, which task management claims and runs (DD-079, DD-080). Since
[3.5a](../../../docs/architecture/conversion/increments/3-5-entity-audit.md): the change notifier the entity
writer tells what it changed, and the audit listener and repository that record and list entity events
(DD-082 to DD-084). Since
[3.5b](../../../docs/architecture/conversion/increments/3-5-classification-audit.md): classification events from
every operation that attaches or propagates classifications, recorded in Atlas's order, and the retriever behind
`bulk/headers` (DD-085, DD-086). Since
[4.1a](../../../docs/architecture/conversion/increments/4-1-entity-search.md): the search fields every entity
document carries, and basic search for entities by type, attribute filters, sort and paging, as one query the
entity documents answer (DD-087 to DD-089). Since
[4.1b](../../../docs/architecture/conversion/increments/4-1-classification-search.md): search by
classification and tag filters (DD-090).

```python
store = TypedefStore(TypeRegistry(), ElasticsearchTypedefDocument(elasticsearch_store.client))
await store.load()  # every stored definition into the registry
created = await store.create_types_def(types_def)
await store.refresh()  # pick up another process's change (at most every 5 s)
await ModelLoader(store).load(BUILTIN_MODELS_DIR)  # addons/models of Atlas 2.4.0, and their patches
store.get_by_name("hive_table")  # the registered definition, as resolution completed it
search_types_def(store.registry, TypeSearchFilter.from_query([("type", "ENTITY")]))  # each kind sorted by name
await EntityRetriever(entity_store, min_ext_info=True).entity_with_ext_info(guid)  # as GET /v2/entity/guid/{guid}
await EntityWriter(entity_store).create_or_update(entities)  # as POST /v2/entity/bulk
await EntityWriter(entity_store).delete_by_id(guid)  # as DELETE /v2/entity/guid/{guid}: soft by default
```

## Installation

```toml
dependencies = ["aurelius-atlas-core"]

[tool.uv.sources.aurelius-atlas-core]
workspace = true
```

## Vendored models

`aurelius_atlas_core/models/` is `addons/models` of Apache Atlas `release-2.4.0`, byte for byte
([DD-032](../../../docs/architecture/conversion/design-log.md#dd-032-the-built-in-models-are-vendored-unchanged-and-read-from-a-directory)).
To prove it, compare it with the tag:

```bash
diff -r <apache-atlas checkout at release-2.4.0>/addons/models libs/python/aurelius-atlas-core/aurelius_atlas_core/models
```

## Documentation

::: aurelius_atlas_core.typedef_store

::: aurelius_atlas_core.entity_store

::: aurelius_atlas_core.entity_retriever

::: aurelius_atlas_core.entity_writer

::: aurelius_atlas_core.entity_discovery

::: aurelius_atlas_core.entity_mapper

::: aurelius_atlas_core.entity_comparator

::: aurelius_atlas_core.delete_handler

::: aurelius_atlas_core.soft_delete_handler

::: aurelius_atlas_core.hard_delete_handler

::: aurelius_atlas_core.delete_type

::: aurelius_atlas_core.relationship_store

::: aurelius_atlas_core.relationship_mapper

::: aurelius_atlas_core.graph_helper

::: aurelius_atlas_core.transaction_view

::: aurelius_atlas_core.entity_classifications

::: aurelius_atlas_core.stored_classification

::: aurelius_atlas_core.classification_associator

::: aurelius_atlas_core.tag_propagation

::: aurelius_atlas_core.stored_task

::: aurelius_atlas_core.classification_tasks

::: aurelius_atlas_core.task_management

::: aurelius_atlas_core.entity_change_notifier

::: aurelius_atlas_core.entity_audit_listener

::: aurelius_atlas_core.entity_audit_repository

::: aurelius_atlas_core.search_fields

::: aurelius_atlas_core.search_query

::: aurelius_atlas_core.search_context

::: aurelius_atlas_core.entity_search_processor

::: aurelius_atlas_core.classification_search_processor

::: aurelius_atlas_core.discovery_service

::: aurelius_atlas_core.stored_relationship

::: aurelius_atlas_core.entity_documents

::: aurelius_atlas_core.stored_entity

::: aurelius_atlas_core.unique_key

::: aurelius_atlas_core.type_search

::: aurelius_atlas_core.model_loader

::: aurelius_atlas_core.typedef_document

::: aurelius_atlas_core.stored_form
