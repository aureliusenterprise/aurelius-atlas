import { describe, expect, it } from "vitest";

import fixture from "../../../../../tests/fixtures/lineage-graph.extract.json";

import { parseAr3Model } from "./parse-ar3";
import { buildIndexes } from "./lineage-indexes";

/**
 * LDG-22: the Selection tab's index maps, ported from the legacy
 * `ModelExplorerService` (buildConceptRelationMap / buildEntityViewMap). The
 * fixture is the shipped chain's document (DD-391) — the ids below are its
 * own (the same ones 7.22b's viewer spec pins).
 */
describe("buildIndexes (LDG-22)", () => {
    const model = parseAr3Model(fixture.model);
    const indexes = buildIndexes(model);
    const view = model.views[0];
    const [topic, job, table] = [...model.elements.keys()];

    it("LDG-22: a relation maps to its two concept ends", () => {
        expect(indexes.conceptsByRelationId.get("rel-1")).toEqual([topic, job]);
        expect(indexes.conceptsByRelationId.get("rel-2")).toEqual([job, table]);
        expect(indexes.conceptsByRelationId.size).toBe(2);
    });

    it("LDG-22: a concept maps to the relations touching it", () => {
        // The process sits between the two relations (source of one, target
        // of the other) — both list, in document order.
        expect(indexes.relationsByConceptId.get(job)).toEqual(["rel-1", "rel-2"]);
        expect(indexes.relationsByConceptId.get(topic)).toEqual(["rel-1"]);
        expect(indexes.relationsByConceptId.get(table)).toEqual(["rel-2"]);
    });

    it("LDG-22: a concept or placement maps to the views containing it", () => {
        // findReferencedConcepts: the node's own id AND its reference both
        // key the view, and the relation and its connection id likewise.
        expect(indexes.viewsByEntityId.get(topic)).toEqual([view.id]);
        expect(indexes.viewsByEntityId.get(view.nodes[0].id)).toEqual([view.id]);
        expect(indexes.viewsByEntityId.get("rel-1")).toEqual([view.id]);
        expect(indexes.viewsByEntityId.get(view.connections[0].id)).toEqual([view.id]);
        // The view itself is not its own container (the legacy's map holds
        // only node/connection keys).
        expect(indexes.viewsByEntityId.get(view.id)).toBeUndefined();
    });

    it("LDG-22: an entity no view places maps to nothing", () => {
        expect(indexes.viewsByEntityId.get("00000000-0000-4000-8000-000000009999")).toBeUndefined();
        expect(indexes.relationsByConceptId.get(view.id)).toBeUndefined();
    });
});
