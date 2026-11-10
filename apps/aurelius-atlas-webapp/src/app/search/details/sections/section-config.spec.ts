import { LAYOUTS, layoutForTypeName } from "./section-config";

/**
 * The config table (DET-16, DD-366; 7.21c's rows, DET-32/DET-33): the eight
 * layouts key for key the spec's table — anchors, titles, seed keys, People
 * box flag, stats, and nav. The table itself is the fixture; these specs pin
 * the dispatch's lookup and the shapes one renderer depends on.
 */
describe("Section config (DET-16)", () => {
    it("holds exactly the eight m4i layouts (DET-16, DET-33)", () => {
        expect(Object.keys(LAYOUTS).sort()).toEqual([
            "m4i_collection",
            "m4i_data_attribute",
            "m4i_data_domain",
            "m4i_data_entity",
            "m4i_dataset",
            "m4i_field",
            "m4i_generic_process",
            "m4i_system",
        ]);
    });

    it("maps each of the eight names to its layout (DET-15, DET-16)", () => {
        for (const name of Object.keys(LAYOUTS)) {
            expect(layoutForTypeName(name)).toBe(LAYOUTS[name as keyof typeof LAYOUTS]);
        }
    });

    it("maps every other name to no layout (DET-15)", () => {
        expect(layoutForTypeName("DataSet")).toBeUndefined();
        // The bare Atlas `Process` keeps the default: the legacy's dispatch
        // names the m4i type, not the built-in (DET-33, DD-383).
        expect(layoutForTypeName("Process")).toBeUndefined();
        expect(layoutForTypeName("m4i_person")).toBeUndefined();
        expect(layoutForTypeName("")).toBeUndefined();
    });

    it("keeps the table's section shape for each layout (DET-16)", () => {
        // Every section: an anchor, a title, at least one seed key — the
        // renderer's whole input set; a blank would draw an empty chrome.
        for (const [name, layout] of Object.entries(LAYOUTS)) {
            expect(layout.sections.length, name).toBeGreaterThan(0);
            for (const section of layout.sections) {
                expect(section.anchor, name).toMatch(/^[a-z-]+$/);
                expect(section.title, name).not.toBe("");
                expect(section.seedKeys.length, name).toBeGreaterThan(0);
            }
        }
    });

    it("carries the spec table's People-box flag (DET-16, DET-23)", () => {
        // The legacy pages with a People box: domain, entity, attribute.
        // The field carries a steward end but its page has no box.
        expect(LAYOUTS.m4i_data_domain.peopleBox).toBe(true);
        expect(LAYOUTS.m4i_data_entity.peopleBox).toBe(true);
        expect(LAYOUTS.m4i_data_attribute.peopleBox).toBe(true);
        expect(LAYOUTS.m4i_field.peopleBox).toBe(false);
        expect(LAYOUTS.m4i_dataset.peopleBox).toBe(false);
        expect(LAYOUTS.m4i_collection.peopleBox).toBe(false);
        expect(LAYOUTS.m4i_system.peopleBox).toBe(false);
        // The process page carries a `processOwner` end and no People box —
        // DET-23's `m4i_field` case (DET-33, DD-383).
        expect(LAYOUTS.m4i_generic_process.peopleBox).toBe(false);
    });

    it("lists the spec table's anchors and seed keys, in order (DET-16)", () => {
        const shape = (name: keyof typeof LAYOUTS) =>
            LAYOUTS[name].sections.map((section) => [section.anchor, [...section.seedKeys]]);

        expect(shape("m4i_data_domain")).toEqual([["related-entities", ["dataEntity"]]]);
        expect(shape("m4i_data_entity")).toEqual([
            ["related-attributes", ["attributes"]],
            ["related-entities", ["childEntity"]],
        ]);
        expect(shape("m4i_data_attribute")).toEqual([["related-fields", ["fields"]]]);
        // DET-35 (7.24, DD-434): the field's own `dataQuality` end seeds the
        // rules box, the legacy `#related-rules` place.
        expect(shape("m4i_field")).toEqual([
            ["related-attributes", ["attributes"]],
            ["related-fields", ["childField"]],
            ["related-rules", ["dataQuality"]],
        ]);
        expect(shape("m4i_dataset")).toEqual([
            ["related-fields", ["fields"]],
            ["related-datasets", ["childDataset"]],
            // DET-32, DD-382: the dataset's own lineage ends, in the legacy
            // positions after Child Datasets.
            ["related-producers", ["outputFromProcesses"]],
            ["related-consumers", ["inputToProcesses"]],
        ]);
        expect(shape("m4i_collection")).toEqual([["related-datasets", ["datasets"]]]);
        expect(shape("m4i_system")).toEqual([
            ["related-collections", ["collections"]],
            ["related-systems", ["childSystem"]],
            ["related-processes", ["processes"]],
        ]);
        // DET-33: the process row's three sections, the legacy order.
        expect(shape("m4i_generic_process")).toEqual([
            ["related-systems", ["system"]],
            ["related-inputs", ["inputs"]],
            ["related-outputs", ["outputs"]],
        ]);
    });

    it("carries the Lineage Model box position on the two layouts (LDG-09)", () => {
        // 7.22b: the box rides the layout row as `lineageAfter`, not the
        // sections list — it is the viewer, not a card section (DD-388).
        // The anchor names the card box the legacy seats it after: the
        // dataset's deferral position (DET-32's table, after Child
        // Datasets) and the process's (DET-33's, after Systems).
        expect(LAYOUTS.m4i_dataset.lineageAfter).toBe("related-datasets");
        expect(LAYOUTS.m4i_generic_process.lineageAfter).toBe("related-systems");
        // Every other legacy page draws no lineage box: no anchor, no box.
        expect(LAYOUTS.m4i_data_domain.lineageAfter).toBeUndefined();
        expect(LAYOUTS.m4i_data_entity.lineageAfter).toBeUndefined();
        expect(LAYOUTS.m4i_data_attribute.lineageAfter).toBeUndefined();
        expect(LAYOUTS.m4i_field.lineageAfter).toBeUndefined();
        expect(LAYOUTS.m4i_collection.lineageAfter).toBeUndefined();
        expect(LAYOUTS.m4i_system.lineageAfter).toBeUndefined();
    });

    it("keeps the stats and nav of 7.21c's rows in the legacy order (DET-32, DET-33, LDG-32)", () => {
        const labels = (name: keyof typeof LAYOUTS) => LAYOUTS[name].stats.map((stat) => stat.anchor);
        const nav = (name: keyof typeof LAYOUTS) => LAYOUTS[name].nav.map((entry) => entry.anchor);

        // LDG-32 (DD-383's hold-out returns): the lineage pair sits before
        // Producers on the dataset (the legacy bar, its no-Data-Entities
        // shape) and before Inputs on the process.
        expect(labels("m4i_dataset")).toEqual([
            "related-fields",
            "related-datasets",
            "lineage-model",
            "related-producers",
            "related-consumers",
            "properties-details",
        ]);
        expect(nav("m4i_dataset")).toEqual([
            "description-details",
            "related-fields",
            "related-datasets",
            "lineage-model",
            "related-producers",
            "related-consumers",
            "properties-details",
        ]);

        expect(labels("m4i_generic_process")).toEqual([
            "related-systems",
            "lineage-model",
            "related-inputs",
            "related-outputs",
            "properties-details",
        ]);
        expect(nav("m4i_generic_process")).toEqual([
            "description-details",
            "related-systems",
            "lineage-model",
            "related-inputs",
            "related-outputs",
            "properties-details",
        ]);

        // DET-36 (7.24): the rules stat returns in the legacy place — after
        // Child Fields, before Properties — and the score stat stays out
        // (DD-369: `data-quality` names it, and it is absent).
        expect(labels("m4i_field")).toEqual([
            "related-attributes",
            "related-fields",
            "related-rules",
            "properties-details",
        ]);
        expect(nav("m4i_field")).toEqual([
            "description-details",
            "related-attributes",
            "related-fields",
            "related-rules",
            "properties-details",
        ]);
    });

    it("carries the lineage stat's kind and word pair (LDG-32)", () => {
        const lineageStat = (name: "m4i_dataset" | "m4i_generic_process") =>
            LAYOUTS[name].stats.find((stat) => stat.anchor === "lineage-model");

        const dataset = lineageStat("m4i_dataset");
        expect(dataset?.source).toEqual({ kind: "lineage" });
        expect(dataset?.available).toBe("Available");
        expect(dataset?.unavailable).toBe("Unavailable");

        const process = lineageStat("m4i_generic_process");
        expect(process?.source).toEqual({ kind: "lineage" });
        expect(process?.available).toBe("Available");
        expect(process?.unavailable).toBe("Unavailable");

        // Every other layout's stat keeps its count shape: no pair, no
        // lineage kind.
        for (const layout of Object.values(LAYOUTS)) {
            for (const stat of layout.stats) {
                if (stat.anchor !== "lineage-model") {
                    expect(stat.available, stat.anchor).toBeUndefined();
                    expect(stat.unavailable, stat.anchor).toBeUndefined();
                }
            }
        }
    });

    it("lists only rendered boxes in the stats and the nav (DET-24, DET-25, DD-369, LDG-32)", () => {
        // Each layout's stats and nav name a box that layout renders: one
        // of its own sections, the lineage box the row seats (LDG-09's
        // lineageAfter), or one of the shared ids. The deferred DQ entry
        // stays absent by this rule (DD-369).
        for (const [name, layout] of Object.entries(LAYOUTS)) {
            const rendered = new Set(["description-details", "properties-details"]);
            if (layout.peopleBox) {
                rendered.add("people-details");
            }
            if (layout.lineageAfter !== undefined) {
                rendered.add("lineage-model");
            }
            for (const section of layout.sections) {
                rendered.add(section.anchor);
            }
            for (const stat of layout.stats) {
                expect(rendered.has(stat.anchor), `${name} stat ${stat.anchor}`).toBe(true);
            }
            for (const entry of layout.nav) {
                expect(rendered.has(entry.anchor), `${name} nav ${entry.anchor}`).toBe(true);
            }
        }
    });
});
