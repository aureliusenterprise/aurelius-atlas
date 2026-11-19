# aurelius-atlas-core

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-core)

Atlas stores and services for Aurelius Atlas
(`DD-002` (the record: `specs/0-1-adopt-template/design.md`)).
Since increment `1.4` (the spec: `libs/python/aurelius-atlas-core/specs/1-4-typedef-store/spec.md`): the
typedef store, which keeps type definitions in one Elasticsearch document and serves them from the type
registry. Since `1.5` (the spec: `libs/python/aurelius-atlas-core/specs/1-5-builtin-models/spec.md`): Apache
Atlas's built-in models and their typedef patches, loaded at start-up. Since `1.6` (the spec:
`apps/aurelius-atlas-server/specs/1-6-types-rest/spec.md`): the store's reads and the search of
`/v2/types/typedefs`. Since `2.2` (the spec:
`libs/python/aurelius-atlas-core/specs/2-2-entity-store/spec.md`): the entity store, which keeps each entity
as one Elasticsearch document, reserves unique attribute values and writes several entities all or nothing
through a journal (DD-043 to DD-048).

```python
store = TypedefStore(TypeRegistry(), ElasticsearchTypedefDocument(elasticsearch_store.client))
await store.load()  # every stored definition into the registry
created = await store.create_types_def(types_def)
await store.refresh()  # pick up another process's change (at most every 5 s)
await ModelLoader(store).load(BUILTIN_MODELS_DIR)  # the Area0 models of Atlas 2.4.0, and their patches
store.get_by_name("AtlasGlossary")  # the registered definition, as resolution completed it
search_types_def(store.registry, TypeSearchFilter.from_query([("type", "ENTITY")]))  # each kind sorted by name
```

## Installation

```toml
dependencies = ["aurelius-atlas-core"]

[tool.uv.sources.aurelius-atlas-core]
workspace = true
```

## Vendored models

`aurelius_atlas_core/models/0000-Area0/` is the `0000-Area0` directory of `addons/models` of Apache Atlas
`release-2.4.0`, byte for byte
(`DD-032` (the record: `libs/python/aurelius-atlas-core/specs/1-5-builtin-models/design.md`)).
The five domain model directories of Atlas do not ship, because a catalogue bootstraps only the metamodel it
serves (`ADR 068`, `DD-715`).
`ModelLoader.load` reads any directory you pass it, so an operator who copies Atlas's `addons/models` there
gets the old set. To prove it, compare the directory with the tag:

```bash
diff -r <apache-atlas checkout at release-2.4.0>/addons/models/0000-Area0
libs/python/aurelius-atlas-core/aurelius_atlas_core/models/0000-Area0
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
