import { FACET_GROUP_TITLES, type M4iLayoutType, LAYOUTS, layoutForTypeName, hasGovQualityBox } from "./section-config";

/**
 * The config table (DET-16, DD-366; 7.21c's rows, DET-32/DET-33; 7.29's
 * person row, DET-39..DET-43): the ten layouts key for key the spec's
 * table — anchors, titles, seed keys, People box flag, stats, and nav. The
 * table itself is the fixture; these specs pin the dispatch's lookup and the
 * shapes one renderer depends on.
 */
describe("Section config (DET-16)", () => {
    it("holds exactly the ten m4i layouts (DET-16, DET-33, DET-38, DET-39)", () => {
        expect(Object.keys(LAYOUTS).sort()).toEqual([
            "m4i_collection",
            "m4i_data_attribute",
            "m4i_data_domain",
            "m4i_data_entity",
            "m4i_data_quality",
            "m4i_dataset",
            "m4i_field",
            "m4i_generic_process",
            "m4i_person",
            "m4i_system",
        ]);
    });

    it("maps each of the ten names to its layout (DET-15, DET-16)", () => {
        for (const name of Object.keys(LAYOUTS)) {
            expect(layoutForTypeName(name)).toBe(LAYOUTS[name as keyof typeof LAYOUTS]);
        }
    });

    it("maps every other name to no layout (DET-15)", () => {
        expect(layoutForTypeName("DataSet")).toBeUndefined();
        // The bare Atlas `Process` keeps the default: the legacy's dispatch
        // names the m4i type, not the built-in (DET-33, DD-383).
        expect(layoutForTypeName("Process")).toBeUndefined();
        expect(layoutForTypeName("")).toBeUndefined();
    });

    it("keeps the table's section shape for each layout (DET-16, DET-48)", () => {
        // Every section: an anchor, a title, at least one seed key — the
        // renderer's whole input set; a blank would draw an empty chrome.
        // The Governance Quality Rules box is the one exception (DD-841): it
        // seeds from a rule search and a verdict call, not a relationship.
        for (const [name, layout] of Object.entries(LAYOUTS)) {
            expect(layout.sections.length, name).toBeGreaterThan(0);
            for (const section of layout.sections) {
                expect(section.anchor, name).toMatch(/^[a-z-]+$/);
                expect(section.title, name).not.toBe("");
                if (section.kind !== "gov-quality") {
                    expect(section.seedKeys.length, name).toBeGreaterThan(0);
                } else {
                    expect(section.seedKeys, name).toEqual([]);
                }
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
        // DET-38 (7.27): the rule page carries no People box (the legacy has
        // no rule page at all — the anatomy is the generic one).
        expect(LAYOUTS.m4i_data_quality.peopleBox).toBe(false);
        expect(LAYOUTS.m4i_dataset.peopleBox).toBe(false);
        expect(LAYOUTS.m4i_collection.peopleBox).toBe(false);
        expect(LAYOUTS.m4i_system.peopleBox).toBe(false);
        // The process page carries a `processOwner` end and no People box —
        // DET-23's `m4i_field` case (DET-33, DD-383).
        expect(LAYOUTS.m4i_generic_process.peopleBox).toBe(false);
    });

    it("lists the spec table's anchors and seed keys, in order (DET-16, DET-48)", () => {
        const shape = (name: keyof typeof LAYOUTS) =>
            LAYOUTS[name].sections.map((section) => [section.anchor, [...section.seedKeys]]);

        // The box closes every legacy page's section list (DET-48) except the
        // rule page's, which the legacy never drew one on (DV-199).
        const box: [string, string[]] = ["gov-quality", []];

        expect(shape("m4i_data_domain")).toEqual([["related-entities", ["dataEntity"]], box]);
        expect(shape("m4i_data_entity")).toEqual([
            ["related-attributes", ["attributes"]],
            ["related-entities", ["childEntity"]],
            box,
        ]);
        expect(shape("m4i_data_attribute")).toEqual([["related-fields", ["fields"]], box]);
        // DET-38 (7.27, DD-495): the rule's own page — the `fields` end the
        // editor writes seeds its Fields box.
        expect(shape("m4i_data_quality")).toEqual([["related-fields", ["fields"]]]);
        // DET-35 (7.24, DD-444): the field's own `dataQuality` end seeds the
        // rules box, the legacy `#related-rules` place.
        expect(shape("m4i_field")).toEqual([
            ["related-attributes", ["attributes"]],
            ["related-fields", ["childField"]],
            ["related-rules", ["dataQuality"]],
            box,
        ]);
        expect(shape("m4i_dataset")).toEqual([
            ["related-fields", ["fields"]],
            ["related-datasets", ["childDataset"]],
            // DET-32, DD-382: the dataset's own lineage ends, in the legacy
            // positions after Child Datasets.
            ["related-producers", ["outputFromProcesses"]],
            ["related-consumers", ["inputToProcesses"]],
            box,
        ]);
        expect(shape("m4i_collection")).toEqual([["related-datasets", ["datasets"]], box]);
        expect(shape("m4i_system")).toEqual([
            ["related-collections", ["collections"]],
            ["related-systems", ["childSystem"]],
            ["related-processes", ["processes"]],
            box,
        ]);
        // DET-33: the process row's three sections, the legacy order.
        expect(shape("m4i_generic_process")).toEqual([
            ["related-systems", ["system"]],
            ["related-inputs", ["inputs"]],
            ["related-outputs", ["outputs"]],
            box,
        ]);
    });

    it("carries the facet group table for every section (VCF-10, VCF-18, DD-619)", () => {
        // Each legacy `*-cards` component asked its own facets; the group
        // keys ride the section row (VCF-10). One entry per section, in
        // legacy order — the empty list is the "No filters available."
        // popover (DV-168's rule sections).
        const facetShape = (name: keyof typeof LAYOUTS) =>
            LAYOUTS[name].sections.map((section) => [section.anchor, [...section.facets]]);

        // The flat people group went with the roles (VCF-18, DD-629): the
        // three role groups in the People box's order wherever 16.5e
        // carried the one flat group.
        const roles = ["domainLead", "businessOwner", "steward"];
        // DET-46 (7.25a): the box asked the two rule groups, in the legacy
        // order (the dimension menu above the type menu).
        const govFacets: [string, string[]] = ["gov-quality", ["dataqualityruledimension", "dataqualitytype"]];
        expect(facetShape("m4i_data_domain")).toEqual([["related-entities", roles], govFacets]);
        expect(facetShape("m4i_data_entity")).toEqual([
            ["related-attributes", roles],
            ["related-entities", roles],
            govFacets,
        ]);
        expect(facetShape("m4i_data_attribute")).toEqual([
            ["related-fields", ["m4i_system", "m4i_collection", "m4i_dataset"]],
            govFacets,
        ]);
        expect(facetShape("m4i_field")).toEqual([
            ["related-attributes", ["m4i_data_domain", "m4i_data_entity", ...roles]],
            ["related-fields", ["m4i_system", "m4i_collection", "m4i_dataset"]],
            // The legacy asked the rule dimension; no card field carries it (DV-168).
            ["related-rules", []],
            govFacets,
        ]);
        // DV-199: the rule page never drew the box, so it asks no rule groups.
        expect(facetShape("m4i_data_quality")).toEqual([["related-fields", []]]);
        expect(facetShape("m4i_dataset")).toEqual([
            ["related-fields", roles],
            ["related-datasets", roles],
            ["related-producers", ["typeName", "m4i_system"]],
            ["related-consumers", ["typeName", "m4i_system"]],
            govFacets,
        ]);
        expect(facetShape("m4i_collection")).toEqual([["related-datasets", roles], govFacets]);
        expect(facetShape("m4i_system")).toEqual([
            ["related-collections", roles],
            ["related-systems", roles],
            ["related-processes", ["typeName", "m4i_system"]],
            govFacets,
        ]);
        expect(facetShape("m4i_generic_process")).toEqual([
            ["related-systems", ["typeName", "m4i_system"]],
            ["related-inputs", ["typeName", "m4i_system", "m4i_collection"]],
            ["related-outputs", ["typeName", "m4i_system", "m4i_collection"]],
            govFacets,
        ]);
        // DET-39: the person's roles box asked the type, the two chain
        // groups, and the raw Name (DD-619).
        expect(facetShape("m4i_person")).toEqual([
            ["governance-roles", ["typeName", "m4i_data_domain", "m4i_data_entity", "name"]],
            govFacets,
        ]);

        // Every asked group carries a catalogue title (DD-622): the
        // dictionary keys, the People box's three role keys, and the raw
        // Name literal.
        for (const [name, layout] of Object.entries(LAYOUTS)) {
            for (const section of layout.sections) {
                for (const group of section.facets) {
                    expect(FACET_GROUP_TITLES[group], `${name}.${section.anchor}`).not.toBeUndefined();
                    expect(FACET_GROUP_TITLES[group], `${name}.${section.anchor}`).not.toBe("");
                }
            }
        }
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
        expect(LAYOUTS.m4i_data_quality.lineageAfter).toBeUndefined();
        expect(LAYOUTS.m4i_collection.lineageAfter).toBeUndefined();
        expect(LAYOUTS.m4i_system.lineageAfter).toBeUndefined();
    });

    it("keeps the stats and nav of 7.21c's rows in the legacy order (DET-32, DET-33, LDG-32, DET-48)", () => {
        const labels = (name: keyof typeof LAYOUTS) => LAYOUTS[name].stats.map((stat) => stat.anchor);
        const nav = (name: keyof typeof LAYOUTS) => LAYOUTS[name].nav.map((entry) => entry.anchor);

        // DET-48 (7.25a): the box's nav entry closes each of the nine legacy
        // pages' lists, before the properties; the box never had a stat, so
        // the count line under the title carries its number instead.
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
            "gov-quality",
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
            "gov-quality",
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
            "gov-quality",
            "properties-details",
        ]);

        // DET-38 (7.27, DD-495): the rule page's Fields stat and nav entry,
        // after the description and before the properties.
        expect(labels("m4i_data_quality")).toEqual(["related-fields", "properties-details"]);
        expect(nav("m4i_data_quality")).toEqual(["description-details", "related-fields", "properties-details"]);
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

    it("lists only rendered boxes in the stats and the nav (DET-24, DET-25, DD-369, LDG-32, DET-43)", () => {
        // Each layout's stats and nav name a box that layout renders: one
        // of its own sections, the lineage box the row seats (LDG-09's
        // lineageAfter), the rule box the row carries (DET-42), or one of
        // the shared ids. The deferred DQ entry stays absent by this rule
        // (DD-369); the person's nav names no description because its row
        // omits the box (DET-39).
        for (const [name, layout] of Object.entries(LAYOUTS)) {
            const rendered = new Set(["properties-details"]);
            if (layout.descriptionBox !== false) {
                rendered.add("description-details");
            }
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
            for (const group of layout.statsGroups ?? []) {
                for (const stat of group.items) {
                    expect(rendered.has(stat.anchor), `${name} stat ${stat.anchor}`).toBe(true);
                }
            }
            for (const entry of layout.nav) {
                expect(rendered.has(entry.anchor), `${name} nav ${entry.anchor}`).toBe(true);
            }
        }
    });

    it("carries the person row's shape (DET-39..DET-43)", () => {
        const person = LAYOUTS.m4i_person;
        // DET-39: the table's only row without the description box.
        expect(person.descriptionBox).toBe(false);
        expect(person.peopleBox).toBe(false);
        // DET-41: the one merged section, the five ends in the legacy order,
        // then the box (DET-48).
        expect(person.sections.map((section) => [section.anchor, [...section.seedKeys]])).toEqual([
            [
                "governance-roles",
                ["domainLead", "businessOwnerEntity", "businessOwnerAttribute", "stewardEntity", "stewardAttribute"],
            ],
            ["gov-quality", []],
        ]);
        // DET-40: four headed boxes, each stat counting its own end (or the
        // properties), every heading linking to its legacy target.
        expect(person.stats).toEqual([]);
        expect(
            person.statsGroups?.map((group) => [
                group.heading,
                group.items.map((item) => [item.label, item.anchor, item.source]),
            ]),
        ).toEqual([
            ["Domain Lead", [["Data Domains", "governance-roles", { kind: "end", key: "domainLead" }]]],
            [
                "Data Owner",
                [
                    ["Data Entities", "governance-roles", { kind: "end", key: "businessOwnerEntity" }],
                    ["Data Attributes", "governance-roles", { kind: "end", key: "businessOwnerAttribute" }],
                ],
            ],
            [
                "Data Steward",
                [
                    ["Data Entities", "governance-roles", { kind: "end", key: "stewardEntity" }],
                    ["Data Attributes", "governance-roles", { kind: "end", key: "stewardAttribute" }],
                ],
            ],
            ["Other", [["Properties", "properties-details", { kind: "properties" }]]],
        ]);
        // DET-42 (as amended by 7.25a): the box is the row's last section;
        // the description and stats-group flags are still this row's only
        // ones (absent means the 7.21a shape).
        expect(person.sections.at(-1)?.kind).toBe("gov-quality");
        for (const [name, layout] of Object.entries(LAYOUTS)) {
            if (name !== "m4i_person") {
                expect(layout.descriptionBox, name).toBeUndefined();
                expect(layout.statsGroups, name).toBeUndefined();
            }
        }
        // DET-43: the nav's three entries, in the legacy order.
        expect(person.nav.map((entry) => entry.anchor)).toEqual([
            "governance-roles",
            "gov-quality",
            "properties-details",
        ]);
    });

    it("carries the Governance Quality Rules box last on the nine pages (DET-48, DD-841, DV-199)", () => {
        // The nine legacy pages that drew the box carry it as their last
        // section — the legacy templates seat its div directly above the
        // properties block — and name it in the nav at the same place.
        const withBox: M4iLayoutType[] = [
            "m4i_data_domain",
            "m4i_data_entity",
            "m4i_data_attribute",
            "m4i_field",
            "m4i_dataset",
            "m4i_collection",
            "m4i_system",
            "m4i_generic_process",
            "m4i_person",
        ];
        for (const name of withBox) {
            const layout = LAYOUTS[name];
            expect(hasGovQualityBox(layout), name).toBe(true);
            expect(layout.sections.at(-1)?.anchor, name).toBe("gov-quality");
            // One box per page, and it carries the shared title.
            expect(layout.sections.filter((section) => section.kind === "gov-quality")).toHaveLength(1);
            expect(layout.sections.at(-1)?.title).toBe("Governance Quality Rules");
            const anchors = layout.nav.map((entry) => entry.anchor);
            expect(anchors.at(-2), name).toBe("gov-quality");
            expect(anchors.at(-1), name).toBe("properties-details");
            // The nav entry's label is the legacy page's own key's text.
            expect(layout.nav.at(-2)?.label, name).toBe("Governance Quality Rules");
            // The box never enters the stats bar (DET-48, the legacy's bar
            // carried no heading for it).
            expect(
                layout.stats.map((stat) => stat.anchor),
                name,
            ).not.toContain("gov-quality");
        }

        // The rule's own page is the tenth layout and the only one without
        // the box: the legacy drew no governance box there (DV-199).
        expect(hasGovQualityBox(LAYOUTS.m4i_data_quality)).toBe(false);
        expect(hasGovQualityBox(undefined)).toBe(false);
    });
});
