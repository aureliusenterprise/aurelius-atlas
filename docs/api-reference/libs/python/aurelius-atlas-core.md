# aurelius-atlas-core

[![SonarQube Cloud](https://sonarcloud.io/images/project_badges/sonarcloud-light.svg)](https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-core)

Atlas stores and services for Aurelius Atlas
([DD-002](../../../architecture/conversion/design-log.md#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer)).
Since increment [1.4](../../../architecture/conversion/increments/1-4-typedef-store.md): the typedef
store, which keeps type definitions in one Elasticsearch document and serves them from the type registry.
Since [1.5](../../../architecture/conversion/increments/1-5-builtin-models.md): Apache Atlas's built-in
models and their typedef patches, loaded at start-up.

```python
store = TypedefStore(TypeRegistry(), ElasticsearchTypedefDocument(elasticsearch_store.client))
await store.load()  # every stored definition into the registry
created = await store.create_types_def(types_def)
await store.refresh()  # pick up another process's change (at most every 5 s)
await ModelLoader(store).load(BUILTIN_MODELS_DIR)  # addons/models of Atlas 2.4.0, and their patches
```

## Installation

```toml
dependencies = ["aurelius-atlas-core"]

[tool.uv.sources.aurelius-atlas-core]
workspace = true
```

## Documentation

::: aurelius_atlas_core.typedef_store

::: aurelius_atlas_core.model_loader

::: aurelius_atlas_core.typedef_document

::: aurelius_atlas_core.stored_form
