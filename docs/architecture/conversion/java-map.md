# Java to Python Map

Where each part of Apache Atlas 2.4.0 goes. Updated by every increment; the status column is the
truth about what has been ported. Status values: _not started_, _in progress_, _ported_, _replaced_
(same purpose, different mechanism), _dropped_ (not carried over; reason in
[Deviations](./deviations.md) or the design log).

## Modules

| Atlas module                    | Purpose in Atlas                                      | Target                                              | Status      |
| ------------------------------- | ----------------------------------------------------- | --------------------------------------------------- | ----------- |
| `intg`                          | Model classes, type system, client-side utilities     | `aurelius-atlas-model`, `aurelius-atlas-typesystem` | in progress |
| `repository`                    | Stores, services, discovery, lineage, glossary, audit | `aurelius-atlas-core`, `aurelius-atlas-dsl`         | in progress |
| `graphdb`                       | JanusGraph abstraction and implementation             | `aurelius-atlas-store-es`                           | replaced    |
| `webapp`                        | REST resources, filters, authentication               | `aurelius-atlas-server`                             | in progress |
| `server-api`                    | Interfaces shared by server components                | `aurelius-atlas-core`                               | not started |
| `common`                        | Shared utilities                                      | where used                                          | not started |
| `authorization`                 | Simple and Ranger authorizers                         | `aurelius-atlas-server` (simple authorizer only)    | not started |
| `dashboardv2`, `dashboardv3`    | Web UIs (served at `/` and `/n/`)                     | `aurelius-atlas-dashboard` (unchanged)              | in progress |
| `notification`                  | Kafka hook and entity notifications                   | –                                                   | dropped     |
| `client`                        | Java client libraries                                 | –                                                   | dropped     |
| `addons/*-bridge`, `*-shim`     | Hooks for Hive, HBase, Kafka, Sqoop, Storm, …         | –                                                   | dropped     |
| `addons/models`                 | Built-in type definitions (JSON)                      | `aurelius_atlas_core.models` (unchanged, DD-032)    | in progress |
| `distro`, `build-tools`, `docs` | Packaging, build and site                             | template workflow                                   | replaced    |
| `tools/*`                       | Index repair, classification updater, analyzers       | –                                                   | dropped     |

## Classes

Rows are added by each increment for the classes it ports.

| Java class                                                                                                                                                                      | Python module                                                      | Increment | Status      |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ | --------- | ----------- |
| `AdminResource` (version, status, session, liveness, readiness)                                                                                                                 | `aurelius_atlas_server.routes.admin`                               | 0.5       | in progress |
| `AtlasBaseExceptionMapper`                                                                                                                                                      | `aurelius_atlas_server.errors`                                     | 0.5       | ported      |
| `AtlasBaseTypeDef`, `AtlasStructDef`, `AtlasEnumDef`, `AtlasClassificationDef`, `AtlasEntityDef`, `AtlasRelationshipDef`, `AtlasRelationshipEndDef`, `AtlasBusinessMetadataDef` | `aurelius_atlas_model.typedef`                                     | 1.1       | in progress |
| `AtlasTypeDefHeader`, `AtlasTypesDef`, `TypeCategory`                                                                                                                           | `aurelius_atlas_model.typedef`                                     | 1.1       | in progress |
| `AtlasTypeRegistry`, `AtlasType`, `AtlasBuiltInTypes`, `AtlasArrayType`, `AtlasMapType`, `AtlasEnumType`, `AtlasStructType` (definition side, DD-025)                           | `aurelius_atlas_typesystem`                                        | 1.2       | in progress |
| `AtlasEntityType`, `AtlasClassificationType`, `AtlasRelationshipType`, `AtlasBusinessMetadataType` (definition side, DD-025, DD-026)                                            | `aurelius_atlas_typesystem`                                        | 1.3       | in progress |
| `AtlasTypeDefGraphStore`, `AtlasTypeDefGraphStoreV2`, `Atlas*DefStoreV2` (checks and stored form; graph replaced, DD-028)                                                       | `aurelius_atlas_core.typedef_store`                                | 1.4       | in progress |
| `AtlasTypeDefStoreInitializer` (model loading and typedef patches), `AtlasPatchRegistry` (typedef patches, DD-031), `AtlasPatch`                                                | `aurelius_atlas_core.model_loader`, `aurelius_atlas_model.patches` | 1.5       | in progress |
| `AtlasErrorCode`, `AtlasBaseException` (the codes each increment raises)                                                                                                        | `aurelius_atlas_model.errors` (DD-023)                             | 0.5, 1.2  | in progress |
