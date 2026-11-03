/**
 * Atlas lineage DTOs — the wire shapes of `/api/atlas/v2/lineage/**` (LIN-01..07,
 * APC-03).
 *
 * Field names are the camelCase names the server writes, mirrored from
 * `libs/python/aurelius-atlas-model` (`aurelius_atlas_model/lineage.py`, ported
 * from Apache Atlas 2.4.0 `org.apache.atlas.model.LineageREST`'s
 * `AtlasLineageInfo`): keep the two in step when the Python model changes.
 * Java's `int` and `boolean` fields are always written, an absent field is left
 * out (`to_json`, TDM-02). The Python twin of this cluster is
 * `AtlasClient.lineage` (CL-61..63); it reads the same bodies through its own
 * lenient `LineageInfo` view (CL-12), which ignores the fields the flattening
 * never reads.
 */

import type { AtlasEntityHeader } from "./atlas-search";

/** Which way a lineage graph grows (`AtlasLineageInfo.LineageDirection`). */
export type LineageDirection = "INPUT" | "OUTPUT" | "BOTH";

/**
 * `LineageRelation`: an edge of the lineage, from data set to process or
 * process to data set (LIN-04).
 */
export type LineageRelation = {
    fromEntityId?: string | null;
    toEntityId?: string | null;
    relationshipId?: string | null;
};

/**
 * `LineageInfoOnDemand`: what lineage on demand left out at an entity, and what
 * it counted (LIN-07). Atlas serializes the two flags and the two counts; its
 * limits and constraints are not shown.
 */
export type LineageInfoOnDemand = {
    hasMoreInputs?: boolean | null;
    hasMoreOutputs?: boolean | null;
    inputRelationsCount?: number | null;
    outputRelationsCount?: number | null;
};

/**
 * `LineageOnDemandConstraints`: how far lineage on demand goes from one entity
 * (LIN-06). The body of `POST /atlas/v2/lineage/{guid}` is a map of these,
 * keyed by guid.
 */
export type LineageOnDemandConstraints = {
    direction?: LineageDirection | null;
    inputRelationsLimit?: number | null;
    outputRelationsLimit?: number | null;
    depth?: number | null;
};

/**
 * `AtlasLineageInfo`: the entities and relations of an entity's lineage;
 * `visitedEdges` is not shown. `guidEntityMap` is keyed by guid and its values
 * are the entity headers of the graph.
 */
export type AtlasLineageInfo = {
    baseEntityGuid?: string | null;
    lineageDirection?: LineageDirection | null;
    lineageDepth?: number | null;
    guidEntityMap?: Record<string, AtlasEntityHeader> | null;
    relations?: LineageRelation[] | null;
    relationsOnDemand?: Record<string, LineageInfoOnDemand> | null;
};
