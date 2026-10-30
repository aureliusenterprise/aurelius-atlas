# 1.5 Built-in models and patches

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-031, DD-032, DD-033, DV-07, DV-08; relies on DD-028, DD-029, DV-06

## Scope

When the server starts, it loads Atlas's built-in type definitions (`addons/models`) and their patches into the typedef store of 1.4, as `AtlasTypeDefStoreInitializer` does:

- the 2.4.0 models, vendored unchanged into `aurelius-atlas-core` ([DD-032](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-astral-sh-ruff-pre-commit-0.17.3/architecture/conversion/design-log/#dd-032-the-built-in-models-are-vendored-unchanged-and-read-from-a-directory>)), read from a directory the server can be pointed at (`AURELIUS_ATLAS_SERVER_MODELS_DIR`);
- each model file creates the types not yet stored and updates those whose `typeVersion` is newer (`createUpdateTypesDef`);
- the typedef patches, with the nine patch actions of Atlas 2.4.0, and the record of each patch's outcome, kept in the typedef document ([DD-031](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-astral-sh-ruff-pre-commit-0.17.3/architecture/conversion/design-log/#dd-031-the-patch-records-live-in-the-typedef-document>));
- processes that start together apply each file and each patch once ([DD-033](<https://aureliusenterprise.github.io/dependabot-pre_commit-https--github.com-astral-sh-ruff-pre-commit-0.17.3/architecture/conversion/design-log/#dd-033-start-up-loading-is-one-change-per-model-file-and-per-patch>)).

No endpoint changes: the loaded types are served by `/v2/types` in 1.6.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| `/v2/types/...` | 1.6 |
| `admin/patches`, and the Java patches (`AtlasPatchManager`, `UniqueAttributePatch`, …) | 2.2 |
| Setting the default of a new mandatory attribute, and new super types, on existing entities | 2.2 |
| Deferring the load until an instance becomes active (`atlas.server.ha.enabled`) | not ported |
| The legacy `TypesResource` (`/api/atlas/types`), the other caller of `createUpdateTypesDef` | not ported |

`AddMandatoryAttributesPatch` and `SuperTypesUpdatePatch`, which `ADD_MANDATORY_ATTRIBUTE` and `ADD_SUPER_TYPES` schedule, change entities; without entities there is nothing for them to do until 2.2. High availability is replaced by DD-029 and DD-033: every process may load the models.

## Semantics

| Id | Rule |
| --- | --- |
| MDL-01 | The models directory is read in name order: each sub-directory except one named `patches`, then the directory itself. Of each, the files are loaded in name order, then the files of its `patches` sub-directory are applied in name order. Other entries are ignored; a missing directory loads nothing. Names compare as Java's `String.compareTo` |
| MDL-02 | A model file is an `AtlasTypesDef`; an empty one is skipped. Its definitions whose name is not registered, as any kind or built-in, are created. A definition whose name is registered as the same kind is updated when its `typeVersion` is greater than the registered one, compared as strings with an absent version less than any; the update keeps the registered attributes it lacks, appended in order, and an enum the registered elements it lacks |
| MDL-03 | A file's creations and updates are one change (`createUpdateTypesDef`): the updates replace the registered definitions without resolving, the creations are then resolved (an unknown type name fails with `BAD_REQUEST`, as TDS-01) and stored with TDS-02 to TDS-06, then the updates are stored with TDS-07 and TDS-08. Nothing of the file is stored unless all of it passes |
| MDL-04 | A model file that cannot be read, is not an `AtlasTypesDef` or fails MDL-03 is logged and skipped; loading goes on with the next file |
| MDL-05 | A patch file holds `patches`, a list of patches with `id`, `description`, `action`, `typeName`, `applyToVersion`, `updateToVersion`, `params`, `attributeDefs`, `elementDefs`, `typeDefOptions`, `serviceType`, `attributeName` and `superTypes`; other fields are ignored. A patch whose action is not one of the nine is logged and skipped. A patch whose id is recorded `APPLIED` or `SKIPPED` is not applied again; one recorded `FAILED` or `UNKNOWN`, or not recorded, is. A patch without an id is applied at every start and not recorded (DV-08) |
| MDL-06 | A patch ends `APPLIED`, `SKIPPED` or `UNKNOWN` as its action decides, or `FAILED` when it raises an Atlas error; its record (id, description, type `TYPEDEF_PATCH`, action, status, created and updated time) is written with its change (DD-031), and an existing record's created time stays. Any other error ends the patch file: its later patches are not applied, and the failing patch is not recorded |
| MDL-07 | Every action: a `typeName` that is not stored fails with `PATCH_FOR_UNKNOWN_TYPE` (action, type name). A patch applies when the type's `typeVersion` is absent, equals `applyToVersion` ignoring case, or starts with `applyToVersion` followed by `.`; otherwise it is `SKIPPED`. An applied patch sets `typeVersion` to `updateToVersion` and stores the type with TDS-07 and TDS-08. An action given a kind it does not handle fails with `PATCH_NOT_APPLICABLE_FOR_TYPE` (action, Java class name such as `AtlasEnumDef`) |
| MDL-08 | `UPDATE_ENUMDEF` (enums): adds each of `elementDefs`, replacing an element with the same value |
| MDL-09 | `ADD_ATTRIBUTE` (entities, classifications, structs, relationships) and `UPDATE_ATTRIBUTE` (entities, classifications, structs): add each of `attributeDefs` at the end, replacing an attribute with the same name. TDS-08 applies, so a changed attribute type or a new mandatory attribute fails |
| MDL-10 | `ADD_MANDATORY_ATTRIBUTE` (entities, classifications, structs): of `attributeDefs`, keeps those the type does not have that are mandatory, have a non-empty default value, have a primitive type and are not unique; an unknown attribute type fails with its registry error. With none kept the patch is `SKIPPED`; otherwise they are added, and the update may add mandatory attributes |
| MDL-11 | `REMOVE_LEGACY_REF_ATTRIBUTES` (relationships; any other kind ends `UNKNOWN`): the label is `params.relationshipLabel`, else `__` and the qualified name of the attribute at the one legacy end, else the current label; with both ends legacy and no label it fails with `PATCH_MISSING_RELATIONSHIP_LABEL`. The ends swap when `params.swapEnds` is true, `params.relationshipCategory` replaces the category, and the attribute each end names is removed from its entity type. The relationship and both entity types are one update, in which attributes may be removed, the category may change and the ends may swap |
| MDL-12 | `UPDATE_TYPEDEF_OPTIONS` (any kind): fails with `PATCH_INVALID_DATA` without `typeDefOptions`, before the version check; merges them into the options, the patch's winning. `SET_SERVICE_TYPE` (any kind): sets the `serviceType`; without one the stored one stays, as TDS-07 keeps a blank `serviceType` |
| MDL-13 | `UPDATE_ATTRIBUTE_METADATA` (entities, structs): to the attributes named `attributeName`, ignoring case, applies each of `params`: `searchWeight`, a number, -1 or 1 to 10; `indexType`, `DEFAULT` or `STRING`, ignored when empty. Any other parameter or value is an error that ends the patch file (MDL-06). A type without the attribute still has the patch `APPLIED` |
| MDL-14 | `ADD_SUPER_TYPES` (entities): without `superTypes` the patch is `SKIPPED`, before the version check; otherwise each is added |
| MDL-15 | Each model file and each patch is one change of the typedef store (TDS-10, TDS-11), decided on the newest stored definitions and records: when another process wrote first, it is decided again, so processes starting together create, update and patch each type once (DD-033) |
| MDL-16 | The server loads the models after the stored definitions (TDS-12) and before it answers, from `AURELIUS_ATLAS_SERVER_MODELS_DIR`, by default the vendored 2.4.0 models, which are byte-identical to `addons/models` of `release-2.4.0`. Built-in model types and patch records name no user (DV-07) |

## Java origin

Apache Atlas `release-2.4.0`:

- `repository/src/main/java/org/apache/atlas/repository/store/bootstrap/AtlasTypeDefStoreInitializer.java`: `loadBootstrapTypeDefs`, `loadModelsInFolder`, `getTypesToCreate`, `getTypesToUpdate`, `updateTypeAttributes`, `isTypeUpdateApplicable`, `applyTypePatches`, `TypeDefPatch`, `TypeDefPatches` and the nine `PatchHandler`s
- `repository/.../patches/AtlasPatchRegistry.java`: `isApplicable`, `register`; the graph vertices are replaced by DD-031
- `repository/.../store/graph/AtlasTypeDefGraphStore.java`: `createUpdateTypesDef`
- `repository/.../store/graph/v2/AtlasStructDefStoreV2.java` and `AtlasRelationshipDefStoreV2.java`: what `RequestContext.isInTypePatching` allows
- `intg/.../model/patches/AtlasPatch.java`: `PatchStatus`
- `repository/.../graph/GraphBackedSearchIndexer.java`: `isValidSearchWeight`
- `addons/models/`: the models and patches, vendored
- tests: `repository/src/test/java/org/apache/atlas/patches/AtlasPatchRegistryTest.java`

## Deviations

DV-07: Atlas records the operating system account the server runs as on the built-in types and the patch records; Aurelius Atlas records none. DV-08: Atlas records a patch without an id, as a record without an id, at every start; Aurelius Atlas records nothing. Neither is visible before `admin/patches` (2.2) and `/v2/types` (1.6).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — MDL-01 to MDL-15 on the in-memory document, with small model directories written by the tests; and the vendored models loaded whole, with no file skipped and no patch `FAILED`, and the result of selected patches checked against the patch files that cause it.
- `libs/python/aurelius-atlas-core/e2e/` — MDL-15 against the dev store: two stores loading the models at once.
- `libs/python/aurelius-atlas-typesystem/tests/` — updating a transient registry without resolving.
- `apps/aurelius-atlas-server/tests/` — MDL-16.
- `uv run aurelius-atlas-trace check`.
