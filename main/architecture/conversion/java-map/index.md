# Java to Python Map

Where each part of Apache Atlas 2.4.0 goes. Updated by every increment; the status column is the truth about what has been ported. Status values: *not started*, *in progress*, *ported*, *replaced* (same purpose, different mechanism), *dropped* (not carried over; reason in [Deviations](<https://aureliusenterprise.github.io/main/architecture/conversion/deviations/index.md>) or the design log).

## Modules

| Atlas module | Purpose in Atlas | Target | Status |
| --- | --- | --- | --- |
| `intg` | Model classes, type system, client-side utilities | `aurelius-atlas-model`, `aurelius-atlas-typesystem` | in progress |
| `repository` | Stores, services, discovery, lineage, glossary, audit | `aurelius-atlas-core`, `aurelius-atlas-dsl` | not started |
| `graphdb` | JanusGraph abstraction and implementation | `aurelius-atlas-store-es` | replaced |
| `webapp` | REST resources, filters, authentication | `aurelius-atlas-server` | in progress |
| `server-api` | Interfaces shared by server components | `aurelius-atlas-core` | not started |
| `common` | Shared utilities | where used | not started |
| `authorization` | Simple and Ranger authorizers | `aurelius-atlas-server` (simple authorizer only) | not started |
| `dashboardv2`, `dashboardv3` | Web UIs (served at `/` and `/n/`) | `aurelius-atlas-dashboard` (unchanged) | in progress |
| `notification` | Kafka hook and entity notifications | – | dropped |
| `client` | Java client libraries | – | dropped |
| `addons/*-bridge`, `*-shim` | Hooks for Hive, HBase, Kafka, Sqoop, Storm, … | – | dropped |
| `addons/models` | Built-in type definitions (JSON) | loaded by `aurelius-atlas-core` (1.4) | not started |
| `distro`, `build-tools`, `docs` | Packaging, build and site | template workflow | replaced |
| `tools/*` | Index repair, classification updater, analyzers | – | dropped |

## Classes

Rows are added by each increment for the classes it ports.

| Java class | Python module | Increment | Status |
| --- | --- | --- | --- |
| `AdminResource` (version, status, session, liveness, readiness) | `aurelius_atlas_server.routes.admin` | 0.5 | in progress |
| `AtlasBaseExceptionMapper` | `aurelius_atlas_server.errors` | 0.5 | ported |
| `AtlasBaseTypeDef`, `AtlasStructDef`, `AtlasEnumDef`, `AtlasClassificationDef`, `AtlasEntityDef`, `AtlasRelationshipDef`, `AtlasRelationshipEndDef`, `AtlasBusinessMetadataDef` | `aurelius_atlas_model.typedef` | 1.1 | in progress |
| `AtlasTypeDefHeader`, `AtlasTypesDef`, `TypeCategory` | `aurelius_atlas_model.typedef` | 1.1 | in progress |
| `AtlasTypeRegistry`, `AtlasType`, `AtlasBuiltInTypes`, `AtlasArrayType`, `AtlasMapType`, `AtlasEnumType`, `AtlasStructType` (definition side, DD-025) | `aurelius_atlas_typesystem` | 1.2 | in progress |
| `AtlasErrorCode`, `AtlasBaseException` (the codes each increment raises) | `aurelius_atlas_model.errors` (DD-023) | 0.5, 1.2 | in progress |
