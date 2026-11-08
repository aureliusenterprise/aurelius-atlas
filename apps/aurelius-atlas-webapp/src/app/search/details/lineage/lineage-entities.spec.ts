import { describe, expect, it } from "vitest";

import fixture from "../../../../../tests/fixtures/lineage-graph.extract.json";

import { parseAr3Model } from "./parse-ar3";
import { buildEntitiesById, mergeProperties } from "./lineage-entities";

/**
 * LDG-19..LDG-22: the quickview's entity index and property merge, over the
 * vendored 8.2 fixture plus its metadata rows (DD-391's provenance — the
 * metadata shape is the chain's own `lineage-model.service.ts` answer, and the
 * live rows below are the fixture document's `metadata` list).
 */
describe("lineage entities (LDG-19..LDG-22)", () => {
    const model = parseAr3Model(fixture.model);
    const entities = buildEntitiesById(model);
    // The fixture document's metadata rows: the answer's `metadata` list
    // (LDG-02) with duplicate ids and the chain's own values.
    const metadata = fixture.metadata as { id: string; data: Record<string, unknown> }[];

    const elementId = "00000000-0000-4000-8000-000000000002";
    const relationId = "rel-1";
    const viewId = "lineage_view";

    it("LDG-19: every element, relation, view, node, and connection keys an entity", () => {
        const view = model.views[0];
        expect(entities.get(elementId)).toEqual({
            id: elementId,
            kind: "element",
            name: "Load Job",
            type: "lineage_process",
            humanReadableType: "Process",
            description: "",
            properties: [],
        });
        expect(entities.get(relationId)?.kind).toBe("relation");
        // The view entity carries the legacy parser's stamped type (LDG-20's
        // fourth metamodel row).
        expect(entities.get(viewId)).toMatchObject({ kind: "view", humanReadableType: "View", name: "Lineage" });
        // A node reads under its own id with its placement label, and the
        // connection under its own.
        expect(entities.get(view.nodes[0].id)).toMatchObject({ kind: "node", name: "" });
        expect(entities.get(view.connections[0].id)?.kind).toBe("connection");
        // The count: 3 elements + 2 relations + 1 view + 3 nodes + 2 connections.
        expect(entities.size).toBe(3 + 2 + 1 + 3 + 2);
    });

    it("LDG-20: the human-readable type is the metamodel's name", () => {
        expect(entities.get("00000000-0000-4000-8000-000000000001")?.humanReadableType).toBe("Dataset");
        expect(entities.get(elementId)?.humanReadableType).toBe("Process");
        expect(entities.get(relationId)?.humanReadableType).toBe("Data Lineage");
        // A node has no type of its own — the row hides (the legacy's
        // `|| type` fallback has nothing to show).
        expect(entities.get(model.views[0].nodes[0].id)?.humanReadableType).toBe("");
    });

    it("LDG-21: the merge widens the concept's properties with its metadata row", () => {
        const entity = entities.get(elementId) ?? null;
        const rows = mergeProperties(entity, metadata);
        // The fixture element has no ar3_properties, so the rows are the
        // chain's own data (the legacy's { ...properties, ...data }).
        expect(rows.map((row) => row.name)).toContain("created_by");
        expect(rows.map((row) => row.name)).toContain("m4i_original_id");
        expect(rows.find((row) => row.name === "created_by")?.value).toBe("Model Extractor API");
    });

    it("LDG-21/DD-394: a same-named metadata value replaces the property, and duplicate ids collapse last", () => {
        // A hand-built concept: the element carries owner/tier; two metadata
        // rows share the concept id (the fixture itself repeats the id
        // ...0002 — collapse-last is the store's per-id write).
        const element = model.elements.get(elementId);
        if (element === undefined) {
            throw new Error("fixture element missing");
        }
        const withProperties = {
            ...element,
            kind: "element" as const,
            humanReadableType: "Process",
            properties: [
                { name: "owner", value: "team-a" },
                { name: "tier", value: "bronze" },
            ],
        };
        const rows = mergeProperties(withProperties, [
            { id: elementId, data: { owner: "team-b", extra: 1 } },
            { id: "other", data: { ignored: true } },
            { id: elementId, data: { tier: "silver" } },
        ]);
        // The legacy's keyvalue order over the merged dictionary — names in
        // code-unit order; the row wins on a clash.
        expect(rows).toEqual([
            { name: "extra", value: "1" },
            { name: "owner", value: "team-b" },
            { name: "tier", value: "silver" },
        ]);
    });

    it("LDG-21: an empty merge shows no rows (the legacy's length condition)", () => {
        expect(mergeProperties(null, metadata)).toEqual([]);
        const bare = entities.get(viewId) ?? null;
        expect(bare).not.toBeNull();
        // The view has no ar3_properties in the fixture and no metadata row in
        // this narrow list — an empty merge.
        expect(mergeProperties(bare, [])).toEqual([]);
    });

    it("LDG-21: a metadata row's non-string value reads as the details page reads it", () => {
        const entity = entities.get(relationId);
        if (entity === undefined) {
            throw new Error("fixture relation missing");
        }
        const rows = mergeProperties(entity, [{ id: relationId, data: { depth: 3, ok: true, gone: null } }]);
        expect(rows).toEqual([
            { name: "depth", value: "3" },
            { name: "gone", value: "" },
            { name: "ok", value: "true" },
        ]);
    });
});
