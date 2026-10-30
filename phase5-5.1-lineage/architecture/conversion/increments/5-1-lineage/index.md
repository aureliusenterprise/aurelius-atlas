# 5.1 Lineage

- **Status:** in progress
- **Pull request:** [\#167](<https://github.com/aureliusenterprise/aurelius-atlas/pull/167>)
- **Records:** DD-244, DD-245; relies on DD-061, DD-065, DV-39

Lineage as `LineageREST` and `EntityLineageService` answer it with Atlas's default traversal (`atlas.lineage.query.use.gremlin` false, `getLineageInfoV2`) and lineage on demand (`getLineageInfoOnDemand`): the processes and data sets an entity's `__Process.inputs` and `__Process.outputs` edges reach, here the relationships of those labels (DD-245).

## Scope

| Endpoint | Takes | Answers |
| --- | --- | --- |
| `GET /api/atlas/v2/lineage/{guid}` | `direction` (`BOTH`), `depth` (3) | `AtlasLineageInfo` |
| `POST /api/atlas/v2/lineage/{guid}` | a `LineageOnDemandConstraints` per GUID | `AtlasLineageInfo` |
| `GET /api/atlas/v2/lineage/uniqueAttribute/type/{type}` | `direction`, `depth`, `attr:<name>` unique attributes | `AtlasLineageInfo` |

`aurelius_atlas_model.lineage` (`AtlasLineageInfo`, `LineageRelation`, `LineageInfoOnDemand`, `LineageOnDemandConstraints`, `LineageDirection`), `aurelius_atlas_core.entity_lineage_service` (`EntityLineageService`), the server's `routes/lineage` and three settings: `lineage_on_demand_enabled` (`atlas.lineage.on.demand.enabled`, false), `lineage_on_demand_default_node_count` (`atlas.lineage.on.demand.default.node.count`, 3) and `lineage_max_node_count` (`atlas.lineage.max.node.count`, 9,000).

Not in this increment: the Gremlin lineage (`getLineageInfoV1`, a configuration Atlas does not default to) and `getSchemaForHiveTable*` (no REST endpoint in 2.4.0 calls them).

## Semantics

| Id | Rule |
| --- | --- |
| LIN-01 | The GUID and type name are at most 4,096 characters (`INVALID_QUERY_PARAM_LENGTH`); `direction` is `INPUT`, `OUTPUT` or `BOTH` and `depth` an `int`, else `BAD_REQUEST` (DV-39). By unique attribute, an unknown type fails with `TYPE_NAME_INVALID` and no entity holding the `attr:` values with `INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND` |
| LIN-02 | The entity must exist (`INSTANCE_GUID_NOT_FOUND`) and be a `DataSet` or a `Process`, or a sub type (`INVALID_LINEAGE_ENTITY_TYPE`) |
| LIN-03 | From a data set, input lineage follows each `__Process.outputs` edge into it back to its process, and that process's `__Process.inputs` edges on to their data sets; output lineage follows `__Process.inputs` edges into it and the process's `__Process.outputs` edges. Each data set reached is followed again, `depth` times in all (0 for no end), a data set already followed in that direction not again. From a process, its own `__Process.inputs` (input) and `__Process.outputs` (output) edges lead to the data sets followed with `depth - 1`. `BOTH` follows both. Edges of every state count |
| LIN-04 | Each edge followed adds its two entities to `guidEntityMap`, as headers without classifications, and a relation from the data set to the process for an input edge, from the process to the data set for an output edge, with the relationship's GUID as `relationshipId`; an edge already added is not added again. No edge is added once there are more than `atlas.lineage.max.node.count` (at most 9,000) relations |
| LIN-05 | The answer holds `baseEntityGuid`, `lineageDirection`, `lineageDepth` as asked, `guidEntityMap`, `relations` and `relationsOnDemand` (empty but for lineage on demand); `visitedEdges` is never shown |
| LIN-06 | Lineage on demand fails with `LINEAGE_ON_DEMAND_NOT_ENABLED` unless `atlas.lineage.on.demand.enabled`. It takes constraints per GUID; the base entity's, or for none the defaults (`BOTH`, 3 relations each way, depth 3), with a missing direction `BOTH` and a 0 limit or depth the default; an entity without constraints has the defaults |
| LIN-07 | On demand, each edge is counted for the entity it leads into (inputs) and out of (outputs): once an entity reaches its limit, an edge beyond it is not followed and marks it `hasMoreInputs` or `hasMoreOutputs`, ending that entity's edges. `relationsOnDemand` holds per entity `hasMoreInputs`, `hasMoreOutputs` and the counts, only for entities with more; `lineageOnDemandPayload` the constraints taken. With lineage on demand enabled an edge is known by its two GUIDs, not its relationship |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/LineageREST.java`
- `repository/.../discovery/EntityLineageService.java`: `getAtlasLineageInfo` (both), `getLineageInfoV2`, `traverseEdges`, `getLineageInfoOnDemand`, `traverseEdgesOnDemand`, `incrementAndCheckIfRelationsLimitReached`, `addEdgeToResult`, `lineageContainsEdge`, `processEdge`, `cleanupRelationsOnDemand`, `validateEntityTypeAndCheckIfDataSet`
- `intg/.../model/lineage/AtlasLineageInfo.java`, `LineageOnDemandConstraints.java`
- `intg/.../AtlasConfiguration.java`: `LINEAGE_ON_DEMAND_ENABLED`, `LINEAGE_ON_DEMAND_DEFAULT_NODE_COUNT`, `LINEAGE_MAX_NODE_COUNT`
- Tests: `webapp/.../integration/EntityLineageJerseyResourceIT.java` (the entities and relations of each direction)

## Deviations

None of its own: `guidEntityMap` and `relations` are a map and a set in Atlas, in no order; Aurelius answers them in the order the traversal reaches them. An invalid `direction` or `depth` is DV-39.

## Acceptance

- `libs/python/aurelius-atlas-model/tests/` — the lineage models' JSON (LIN-05, LIN-07).
- `libs/python/aurelius-atlas-core/tests/` — LIN-02 to LIN-07 on the in-memory documents, with the lineages of `EntityLineageJerseyResourceIT`.
- `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/lineage/lineage.scenario.yaml` — LIN-01 to LIN-06 over HTTP.
- `uv run aurelius-atlas-trace check`.
