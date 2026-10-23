# aurelius-atlas-core

Atlas stores and services (DD-002): the typedef store (DD-028, DD-029, DD-030) and the built-in models
(DD-031, DD-032, DD-033). This file covers wiring
specific to this lib; workspace-wide rules — including the scaffold recipe for Python libs — live in the
root `AGENTS.md` and `libs/python/AGENTS.md`.

## Layout

- `aurelius_atlas_core/typedef_store.py` — `TypedefStore` (`AtlasTypeDefGraphStore` and the def stores'
  checks): create, update, delete, load and refresh
- `aurelius_atlas_core/stored_form.py` — what Atlas keeps of a definition (the attribute multiplicity round
  trip, relationship defaults, audit fields)
- `aurelius_atlas_core/typedef_document.py` — `TypedefDocument` and its Elasticsearch implementation: one
  document of definitions and patch records (`StoredTypedefs`), written with `if_seq_no`/`if_primary_term`
- `aurelius_atlas_core/model_loader.py` — `ModelLoader` (`AtlasTypeDefStoreInitializer`): the load order of a
  models directory and the nine typedef patch actions
- `aurelius_atlas_core/models/` — `addons/models` of Atlas 2.4.0, byte for byte: never edit, reformat or
  re-save it (`-text` in `.gitattributes`, excluded from the hooks and Sonar)
- `aurelius_atlas_core/entity_store.py` — `EntityStore`: GUIDs, reads by GUID and unique attributes,
  all-or-nothing writes through the journal, recovery and the type usage check (DD-043 to DD-048)
- `aurelius_atlas_core/relationship_store.py` — `RelationshipStore` (`AtlasRelationshipStoreV2`) and the checks
  and creation an entity write shares; `relationship_mapper.py` (`RelationshipMapper`) maps relationship
  attributes onto relationships in memory; `graph_helper.py` holds `GraphHelper`'s edge lookups over an entity's
  relationships
- `aurelius_atlas_core/transaction_view.py` — `TransactionView`: the store as a write request has changed it,
  which the delete handlers read (through `EntityView`) to delete the owned entities an update drops (DD-068)
- `aurelius_atlas_core/entity_classifications.py` — `EntityClassifications`: the classification methods of
  `AtlasEntityStoreV2` and `EntityGraphMapper`; `stored_classification.py` holds the stored instance (DD-070)
- `aurelius_atlas_core/tag_propagation.py` — `TagPropagation`: classification propagation over a request's view,
  whose entity changes the caller writes with the request (DD-075, DD-077)
- `aurelius_atlas_core/entity_documents.py` — `EntityDocuments` and its Elasticsearch implementation: the entity,
  unique value and journal indices; `stored_entity.py` (`StoredEntity`) and `unique_key.py` (`UniqueKey`)
- `aurelius_atlas_core/testing/memory.py` — `MemoryTypedefDocument` and `MemoryEntityDocuments` (with injected
  failures and crashes) for unit tests
- `tests/` — TDS-01 to TDS-13 and MDL-01 to MDL-15 on the in-memory document and the fake client;
  `tests/fixtures/` holds Atlas's `0010-base_model.json`, unchanged and skipped by the hooks
- `e2e/` — the store on the dev Elasticsearch, each test on an alias of its own

## Conventions

- A change runs inside `TypedefStore._change`: the asyncio lock, then the registry's transient copy, then
  the conditional write, then the commit. Never mutate the registry or the document outside it (TDS-10).
- Responses are the stored form (`stored_typedef`), never the request body: Atlas answers from what it
  stored.
- Checks copy Atlas's def stores, in Java's order; a Java check that the registry's resolution makes
  unreachable keeps its code with `# pragma: no cover` and a comment saying so.
- Whether a type is in use is the `TypeUsage` callback's question (DD-030); never query entity indices here.
- A patch handler only decides: it reads the registry and returns a `PatchChange`; the store applies it and
  writes the record in the same change (DD-031). Errors Java raises as `AtlasBaseException` are `AtlasError`
  (the patch is `FAILED`); its runtime exceptions are `PatchDataError` (the patch file stops).

## Wiring Checklist

- Registered in root `pyproject.toml` (workspace members, dev group, `uv.sources`); depends on
  `aurelius-atlas-model`, `aurelius-atlas-typesystem` and `aurelius-atlas-store-es`.
- `project.json` `implicitDependencies` on `aurelius-atlas-dev-elasticsearch`, so `nx e2e` starts it.
- `sonar-project.properties` and `.env.enc` (`SONAR_TOKEN`) for the CI Sonar job.
- `docs/api-reference/libs/python/aurelius-atlas-core.md` and its `mkdocs.yaml` nav entry.

## Commands

```bash
uv run pytest libs/python/aurelius-atlas-core/tests
npx nx test aurelius-atlas-core -c ci
npx nx e2e aurelius-atlas-core -c ci      # starts dev/elasticsearch first
uv run pyright libs/python/aurelius-atlas-core
```

## Removal

Not removable: the server keeps its types, and later its entities, through it.
