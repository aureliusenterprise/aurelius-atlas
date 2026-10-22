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
several entities all or nothing through a journal (DD-043 to DD-048).

```python
store = TypedefStore(TypeRegistry(), ElasticsearchTypedefDocument(elasticsearch_store.client))
await store.load()  # every stored definition into the registry
created = await store.create_types_def(types_def)
await store.refresh()  # pick up another process's change (at most every 5 s)
await ModelLoader(store).load(BUILTIN_MODELS_DIR)  # addons/models of Atlas 2.4.0, and their patches
store.get_by_name("hive_table")  # the registered definition, as resolution completed it
search_types_def(store.registry, TypeSearchFilter.from_query([("type", "ENTITY")]))  # each kind sorted by name
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

::: aurelius_atlas_core.entity_documents

::: aurelius_atlas_core.stored_entity

::: aurelius_atlas_core.unique_key

::: aurelius_atlas_core.type_search

::: aurelius_atlas_core.model_loader

::: aurelius_atlas_core.typedef_document

::: aurelius_atlas_core.stored_form
