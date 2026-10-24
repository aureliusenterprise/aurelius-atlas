# Java to Python Map

Where each part of Apache Atlas 2.4.0 goes. Updated by every increment; the status column is the truth about what has been ported. Status values: *not started*, *in progress*, *ported*, *replaced* (same purpose, different mechanism), *dropped* (not carried over; reason in [Deviations](<https://aureliusenterprise.github.io/feat-api-client-libraries/architecture/conversion/deviations/index.md>) or the design log).

## Modules

| Atlas module | Purpose in Atlas | Target | Status |
| --- | --- | --- | --- |
| `intg` | Model classes, type system, client-side utilities | `aurelius-atlas-model`, `aurelius-atlas-typesystem` | in progress |
| `repository` | Stores, services, discovery, lineage, glossary, audit | `aurelius-atlas-core`, `aurelius-atlas-dsl` | in progress |
| `graphdb` | JanusGraph abstraction and implementation | `aurelius-atlas-store-es` | replaced |
| `webapp` | REST resources, filters, authentication | `aurelius-atlas-server` | in progress |
| `server-api` | Interfaces shared by server components | `aurelius-atlas-core` | not started |
| `common` | Shared utilities | where used | not started |
| `authorization` | Simple and Ranger authorizers | `aurelius-atlas-server` (simple authorizer only) | not started |
| `dashboardv2`, `dashboardv3` | Web UIs (served at `/` and `/n/`) | `aurelius-atlas-dashboard` (unchanged) | in progress |
| `notification` | Kafka hook and entity notifications | – | dropped |
| `client` | Java client libraries | – | dropped |
| `addons/*-bridge`, `*-shim` | Hooks for Hive, HBase, Kafka, Sqoop, Storm, … | – | dropped |
| `addons/models` | Built-in type definitions (JSON) | `aurelius_atlas_core.models` (unchanged, DD-032) | in progress |
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
| `AtlasEntityType`, `AtlasClassificationType`, `AtlasRelationshipType`, `AtlasBusinessMetadataType` (definition side, DD-025, DD-026) | `aurelius_atlas_typesystem` | 1.3 | in progress |
| `AtlasStructType`, `AtlasClassificationType`, `AtlasEntityType`, `AtlasBusinessMetadataType` (value side, DD-041); `AtlasTypeUtil.toStructAttributes`, `AtlasEntityUtil.getRelationshipType` | `aurelius_atlas_typesystem` (`struct_type`, `classification_type`, `entity_type`, `business_metadata_type`) | 2.1c | in progress |
| `AtlasEntityStoreV2` and `EntityGraphMapper` (storage: GUIDs, unique properties, transactions), `AtlasGraphUtilsV2.findByUniqueAttributes`, `AtlasPatchRegistry.getAllPatches` | `aurelius_atlas_core` (`stored_entity`, `unique_key`, `entity_documents`, `entity_store`), `aurelius_atlas_server.routes.admin` | 2.2 | in progress |
| `EntityGraphRetriever` (entities, headers, object ids), the read methods of `AtlasEntityStoreV2` and `EntityREST` | `aurelius_atlas_core.entity_retriever`, `aurelius_atlas_server.routes.entity` | 2.3 | in progress |
| `AtlasEntityGraphDiscoveryV2` and its resolvers, `AtlasEntityComparator`, `EntityGraphMapper` (values), the write methods of `AtlasEntityStoreV2` and `EntityREST` | `aurelius_atlas_core.entity_discovery`, `aurelius_atlas_core.entity_comparator`, `aurelius_atlas_core.entity_mapper`, `aurelius_atlas_core.entity_writer`, `aurelius_atlas_server.routes.entity` | 2.4 | in progress |
| `DeleteHandlerV1`, `SoftDeleteHandlerV1`, `HardDeleteHandlerV1`, `DeleteHandlerDelegate`, `DeleteType`, the delete methods of `AtlasEntityStoreV2`, `EntityREST` and `AdminResource#purgeByIds` | `aurelius_atlas_core.delete_handler`, `aurelius_atlas_core.soft_delete_handler`, `aurelius_atlas_core.hard_delete_handler`, `aurelius_atlas_core.delete_type`, `aurelius_atlas_core.entity_writer`, `aurelius_atlas_server.routes.entity`, `aurelius_atlas_server.routes.admin` | 2.5 | in progress |
| `AtlasRelationship`, `AtlasRelationshipStoreV2`, `RelationshipREST`, the relationship type's value side | `aurelius_atlas_model.instance.relationship`, `aurelius_atlas_typesystem.relationship_type`, `aurelius_atlas_core.relationship_store`, `aurelius_atlas_core.stored_relationship`, `aurelius_atlas_server.routes.relationship` | 3.1 | in progress |
| `EntityGraphMapper` (relationship attributes, inverse references), `EntityGraphRetriever` (relationship attributes, legacy ends), `GraphHelper` (edge lookups), `DeleteHandlerV1#getOwnedVertices`, `#deleteEdgeReference` | `aurelius_atlas_core.relationship_mapper`, `aurelius_atlas_core.graph_helper`, `aurelius_atlas_core.entity_retriever`, `aurelius_atlas_core.delete_handler` | 3.1b | in progress |
| `DeleteHandlerV1#deleteEdgeReference` and `#deleteTypeVertex` for owned entities, `EntityGraphMapper#updateInConsistentOwnedMapVertices`, `removeUnusedArrayEntries`, `removeUnusedMapEntries` | `aurelius_atlas_core.transaction_view`, `aurelius_atlas_core.entity_writer`, `aurelius_atlas_core.entity_mapper` | 3.2 | in progress |
| The classification methods of `EntityREST`, `AtlasEntityStoreV2` and `EntityGraphMapper`; `EntityGraphRetriever#toAtlasClassification`; `AtlasClassifications`, `PList`, `ClassificationAssociateRequest` | `aurelius_atlas_core.entity_classifications`, `aurelius_atlas_core.stored_classification`, `aurelius_atlas_model.instance`, `aurelius_atlas_server.routes.entity` | 3.3a | in progress |
| `ClassificationAssociator.Updater`, `EntityREST#setClassifications` | `aurelius_atlas_core.classification_associator`, `aurelius_atlas_server.routes.entity` | 3.3b | in progress |
| `DeleteHandlerV1` (tag propagation), `EntityGraphRetriever#traverseImpactedVertices`, `#readClassificationsFromEdge`, `GraphHelper` (propagation lookups) | `aurelius_atlas_core.tag_propagation` | 3.4a | in progress |
| `TaskManagement`, `TaskRegistry`, `TaskExecutor`, `AbstractTask`, `ClassificationPropagationTasks`, `ClassificationTask`, `AdminResource#getTaskStatus`, `#deleteTask`, `AtlasTask` | `aurelius_atlas_core.task_management`, `aurelius_atlas_core.classification_tasks`, `aurelius_atlas_model.tasks`, `aurelius_atlas_server.routes.admin`, `aurelius_atlas_server.task_worker` | 3.4b | in progress |
| `AtlasEntityChangeNotifier`, `EntityAuditListenerV2`, `EntityAuditRepository`, `HBaseBasedAuditRepository`, `InMemoryEntityAuditRepository`, `EntityAuditEventV2`, `EntityREST#getAuditEvents` | `aurelius_atlas_core.entity_change_notifier`, `aurelius_atlas_core.entity_audit_listener`, `aurelius_atlas_core.entity_audit_repository`, `aurelius_atlas_model.audit`, `aurelius_atlas_server.routes.entity` | 3.5a | in progress |
| `ClassificationAssociator.Retriever`, `EntityREST#getEntityHeaders`, `RequestContext#recordAddedPropagation`, `#recordRemovedPropagation` | `aurelius_atlas_core.classification_associator`, `aurelius_atlas_core.tag_propagation`, `aurelius_atlas_server.routes.entity` | 3.5b | in progress |
| `DiscoveryREST` (basic, attribute), `EntityDiscoveryService#searchWithParameters`, `SearchContext`, `EntitySearchProcessor`, `SearchProcessor`, `SearchPredicateUtil`, `SearchParameters`, `AtlasSearchResult` | `aurelius_atlas_core.search_fields`, `aurelius_atlas_core.search_context`, `aurelius_atlas_core.entity_search_processor`, `aurelius_atlas_core.discovery_service`, `aurelius_atlas_model.discovery`, `aurelius_atlas_server.routes.discovery` | 4.1a | in progress |
| `ClassificationSearchProcessor`, `SearchProcessor#buildTraitPredict` | `aurelius_atlas_core.classification_search_processor` | 4.1b | in progress |
| `FreeTextSearchProcessor`, `SolrIndexHelper`, `EntityDiscoveryService#searchUsingFullTextQuery`, `DiscoveryREST#searchUsingFullText` | `aurelius_atlas_core.free_text`, `aurelius_atlas_core.discovery_service`, `aurelius_atlas_server.routes.discovery` | 4.2a | in progress |
| `AtlasTypeDefGraphStore`, `AtlasTypeDefGraphStoreV2`, `Atlas*DefStoreV2` (checks and stored form; graph replaced, DD-028) | `aurelius_atlas_core.typedef_store` | 1.4 | in progress |
| `AtlasTypeDefStoreInitializer` (model loading and typedef patches), `AtlasPatchRegistry` (typedef patches, DD-031), `AtlasPatch` | `aurelius_atlas_core.model_loader`, `aurelius_atlas_model.patches` | 1.5 | in progress |
| `TypesREST`; `AtlasTypeDefGraphStore` reads and `searchTypesDef`; `FilterUtil`, `SearchFilter` | `aurelius_atlas_server.routes.types`, `aurelius_atlas_core.type_search` | 1.6 | in progress |
| `AtlasStruct`, `AtlasEntity` (with its ext info), `AtlasObjectId`, `AtlasRelatedObjectId`, `AtlasClassification`, `TimeBoundary`, `AtlasEntityHeader(s)`, `EntityMutationResponse`, `AtlasTermAssignmentHeader` (DD-037) | `aurelius_atlas_model.instance` | 2.1a | in progress |
| `AtlasType`, `AtlasBuiltInTypes`, `AtlasEnumType`, `AtlasArrayType`, `AtlasMapType` (value side, DD-041); `AtlasJson` (DD-039) | `aurelius_atlas_typesystem` (`atlas_type`, `builtin/`, `enum_type`, `array_type`, `map_type`, `java`), `aurelius_atlas_model.codec` | 2.1b | in progress |
| `AtlasErrorCode`, `AtlasBaseException` (the codes each increment raises) | `aurelius_atlas_model.errors` (DD-023) | 0.5, 1.2 | in progress |
