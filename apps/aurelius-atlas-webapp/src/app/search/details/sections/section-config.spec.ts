import { LAYOUTS, layoutForTypeName } from "./section-config";

/**
 * The config table (DET-16, DD-366): the seven layouts key for key the
 * spec's table — anchors, titles, seed keys, People box flag, stats, and
 * nav. The table itself is the fixture; these specs pin the dispatch's
 * lookup and the shapes one renderer depends on.
 */
describe("Section config (DET-16)", () => {
    it("holds exactly the seven m4i layouts (DET-16)", () => {
        expect(Object.keys(LAYOUTS).sort()).toEqual([
            "m4i_collection",
            "m4i_data_attribute",
            "m4i_data_domain",
            "m4i_data_entity",
            "m4i_dataset",
            "m4i_field",
            "m4i_system",
        ]);
    });

    it("maps each of the seven names to its layout (DET-15, DET-16)", () => {
        for (const name of Object.keys(LAYOUTS)) {
            expect(layoutForTypeName(name)).toBe(LAYOUTS[name as keyof typeof LAYOUTS]);
        }
    });

    it("maps every other name to no layout (DET-15)", () => {
        expect(layoutForTypeName("DataSet")).toBeUndefined();
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
        expect(shape("m4i_field")).toEqual([
            ["related-attributes", ["attributes"]],
            ["related-fields", ["childField"]],
        ]);
        expect(shape("m4i_dataset")).toEqual([
            ["related-fields", ["fields"]],
            ["related-datasets", ["childDataset"]],
        ]);
        expect(shape("m4i_collection")).toEqual([["related-datasets", ["datasets"]]]);
        expect(shape("m4i_system")).toEqual([
            ["related-collections", ["collections"]],
            ["related-systems", ["childSystem"]],
            ["related-processes", ["processes"]],
        ]);
    });

    it("lists only rendered boxes in the stats and the nav (DET-24, DET-25, DD-369)", () => {
        // Each layout's stats and nav name a box that layout renders: one
        // of its own sections, or one of the shared ids. The deferred DQ
        // and lineage entries are absent by this rule.
        for (const [name, layout] of Object.entries(LAYOUTS)) {
            const rendered = new Set(["description-details", "properties-details"]);
            if (layout.peopleBox) {
                rendered.add("people-details");
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
