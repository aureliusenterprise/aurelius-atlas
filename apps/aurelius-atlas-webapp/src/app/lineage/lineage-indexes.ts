import type { Ar3Model } from "./parse-ar3";

/**
 * The three maps the Selection tab reads (LDG-22): the legacy
 * `ModelExplorerService`'s `buildConceptRelationMap` and
 * `buildEntityViewMap` (model-explorer.service.ts), whose
 * `BidirectionalMultiMap` collapses to two plain maps each — only the listed
 * directions are ever read here.
 *
 * Every map lists ids; the caller resolves them through
 * {@link buildEntitiesById} (the legacy's `selectEntitiesById`).
 */
export interface LineageIndexes {
    /** relation id → its source and target concept ids (the relation's ends). */
    readonly conceptsByRelationId: ReadonlyMap<string, readonly string[]>;
    /** concept id → the relation ids touching it. */
    readonly relationsByConceptId: ReadonlyMap<string, readonly string[]>;
    /** entity (or view-node/connection) id → the view ids that contain it. */
    readonly viewsByEntityId: ReadonlyMap<string, readonly string[]>;
}

/**
 * Build the index maps over the parsed model (LDG-22).
 * @param model the parsed model
 */
export function buildIndexes(model: Ar3Model): LineageIndexes {
    const conceptsByRelationId = new Map<string, string[]>();
    const relationsByConceptId = new Map<string, string[]>();
    for (const relation of model.relations.values()) {
        conceptsByRelationId.set(relation.id, [relation.source, relation.target]);
        push(relationsByConceptId, relation.source, relation.id);
        push(relationsByConceptId, relation.target, relation.id);
    }

    const viewsByEntityId = new Map<string, string[]>();
    for (const view of model.views) {
        // The legacy's findReferencedConcepts: every node and connection
        // counts under both its own id and its reference, so selecting either
        // finds the view.
        const seen = new Set<string>();
        for (const { id, ref } of [...view.nodes, ...view.connections]) {
            for (const key of ref === null ? [id] : [id, ref]) {
                if (!seen.has(key)) {
                    seen.add(key);
                    push(viewsByEntityId, key, view.id);
                }
            }
        }
    }

    return { conceptsByRelationId, relationsByConceptId, viewsByEntityId };
}

/** Append to the list under `key`, creating it (the multimap's `set`). */
function push(map: Map<string, string[]>, key: string, value: string): void {
    const list = map.get(key);
    if (list === undefined) {
        map.set(key, [value]);
    } else {
        list.push(value);
    }
}
