import { describe, expect, it } from "vitest";

// The parity fixture (DD-391): vendored verbatim from the shipped chain's
// scenario fixture `apps/aurelius-atlas-lineage-model/scenarios/fixtures/
// graph.extract.json` — the 8.1-verified model document. The expected ids,
// positions, and names below are that document's own values.
import fixture from "../../../../../tests/fixtures/lineage-graph.extract.json";

import { connectionConceptId, nodeConceptId, nodeElement, parseAr3Model, type Ar3Model } from "./parse-ar3";

/**
 * LDG-11: the archimate3 reader, narrowed to the lineage document (DD-389).
 * The field map is the legacy's (`parse-view-node.ts`,
 * `parse-view-connection.ts`, `parse-element.ts`, `parse-relation.ts`), and
 * the values are the shipped producer's (8.2's fixed rule set) — so the pin
 * is the shipped chain's document, cited above, not a hand-written shape.
 */
describe("parseAr3Model (LDG-11)", () => {
    const model: Ar3Model = parseAr3Model(fixture.model);

    it("LDG-11: reads the elements — id, xsi type, and name", () => {
        const ids = [...model.elements.keys()];
        expect(ids).toEqual([
            "00000000-0000-4000-8000-000000000001",
            "00000000-0000-4000-8000-000000000002",
            "00000000-0000-4000-8000-000000000003",
        ]);
        expect(model.elements.get("00000000-0000-4000-8000-000000000001")).toEqual({
            id: "00000000-0000-4000-8000-000000000001",
            type: "lineage_dataset",
            name: "Ingest Topic",
            description: "",
            properties: [],
        });
        expect(model.elements.get("00000000-0000-4000-8000-000000000002")).toEqual({
            id: "00000000-0000-4000-8000-000000000002",
            type: "lineage_process",
            name: "Load Job",
            description: "",
            properties: [],
        });
    });

    it("LDG-11: reads the relations — id, source, target, type, and name", () => {
        expect([...model.relations.values()]).toEqual([
            {
                id: "rel-1",
                source: "00000000-0000-4000-8000-000000000001",
                target: "00000000-0000-4000-8000-000000000002",
                type: "lineage_relation",
                name: "",
                description: "",
                properties: [],
            },
            {
                id: "rel-2",
                source: "00000000-0000-4000-8000-000000000002",
                target: "00000000-0000-4000-8000-000000000003",
                type: "lineage_relation",
                name: "",
                description: "",
                properties: [],
            },
        ]);
    });

    it("LDG-11/LDG-12: reads the one view with its name and placed nodes", () => {
        expect(model.views).toHaveLength(1);
        const view = model.views[0];
        expect(view.name).toBe("Lineage");
        expect(
            view.nodes.map((node) => [node.id, node.ref, node.x, node.y, node.width, node.height, node.displayName]),
        ).toEqual([
            [
                "lineage_view-00000000-0000-4000-8000-000000000001--0",
                "00000000-0000-4000-8000-000000000001",
                0,
                0,
                120,
                55,
                "Ingest Topic",
            ],
            [
                "lineage_view-00000000-0000-4000-8000-000000000002--1",
                "00000000-0000-4000-8000-000000000002",
                320,
                0,
                120,
                55,
                "Load Job",
            ],
            [
                "lineage_view-00000000-0000-4000-8000-000000000003--2",
                "00000000-0000-4000-8000-000000000003",
                640,
                0,
                120,
                55,
                "Sales Table",
            ],
        ]);
    });

    it("LDG-11: reads the connections — refs, endpoint node ids, bendpoints", () => {
        const view = model.views[0];
        expect(
            view.connections.map((connection) => [
                connection.id,
                connection.ref,
                connection.source,
                connection.target,
                connection.bendpoints,
            ]),
        ).toEqual([
            [
                "lineage_view-rel-1--0",
                "rel-1",
                "lineage_view-00000000-0000-4000-8000-000000000001--0",
                "lineage_view-00000000-0000-4000-8000-000000000002--1",
                [],
            ],
            [
                "lineage_view-rel-2--1",
                "rel-2",
                "lineage_view-00000000-0000-4000-8000-000000000002--1",
                "lineage_view-00000000-0000-4000-8000-000000000003--2",
                [],
            ],
        ]);
        // The shipped relation names are empty (the rule set sends no relation
        // name), so a connection draws no label (LDG-14: "when present").
        expect(view.connections[0].displayName).toBe("");
    });

    it("LDG-11: a node's name falls back from the model element to its own label", () => {
        const document = {
            ar3_model: {
                ar3_elements: {
                    ar3_element: [
                        { "@identifier": "e1", "@xsi_type": "lineage_dataset", ar3_name: [{ value: "Model Name" }] },
                    ],
                },
                ar3_views: {
                    ar3_diagrams: {
                        ar3_view: [
                            {
                                "@identifier": "v1",
                                ar3_node: [
                                    {
                                        "@identifier": "n1",
                                        "@elementRef": "e1",
                                        "@x": "0",
                                        "@y": "0",
                                        "@w": "10",
                                        "@h": "10",
                                        ar3_label: [{ value: "View Label" }],
                                    },
                                    {
                                        "@identifier": "n2",
                                        "@elementRef": "missing",
                                        "@x": "0",
                                        "@y": "0",
                                        "@w": "10",
                                        "@h": "10",
                                        ar3_label: [{ value: "Own Label" }],
                                    },
                                    { "@identifier": "n3", "@x": "0", "@y": "0", "@w": "10", "@h": "10" },
                                ],
                            },
                        ],
                    },
                },
            },
        };
        const parsed = parseAr3Model(JSON.stringify(document));
        const [first, second, third] = parsed.views[0].nodes;
        // The model element's name wins (the legacy's `modelNode.name ?? …`).
        expect(first.displayName).toBe("Model Name");
        // A ref the model does not carry falls back to the node's own label.
        expect(second.displayName).toBe("Own Label");
        // A node without either draws nothing.
        expect(third.displayName).toBe("");
        expect(third.ref).toBeNull();
        // Coordinates arrive as strings in a hand-built document and parse
        // like the legacy's parseFloat.
        expect([third.x, third.y, third.width, third.height]).toEqual([0, 0, 10, 10]);
    });

    it("LDG-21/DD-389: reads the description and the property list", () => {
        // The shipped fixture carries neither ar3_documentation nor
        // ar3_properties (8.2's rule set emits none), so the field map is
        // pinned against a hand-built document using the legacy reader's
        // shapes (parse-element.ts, get-properties.ts).
        const document = {
            ar3_model: {
                ar3_elements: {
                    ar3_element: [
                        {
                            "@identifier": "e1",
                            "@xsi_type": "lineage_dataset",
                            ar3_name: [{ value: "Described" }],
                            ar3_documentation: { value: "What it holds" },
                            ar3_properties: {
                                ar3_property: [
                                    { "@propertyDefinitionRef": "owner", ar3_value: { value: "data-team" } },
                                    { "@propertyDefinitionRef": "tier", ar3_value: { value: "silver" } },
                                ],
                            },
                        },
                    ],
                },
                ar3_relationships: {
                    ar3_relationship: [
                        {
                            "@identifier": "r1",
                            "@source": "e1",
                            "@target": "e1",
                            "@xsi_type": "lineage_relation",
                            ar3_documentation: { value: "Why it flows" },
                        },
                    ],
                },
                ar3_views: {
                    ar3_diagrams: {
                        ar3_view: [
                            {
                                "@identifier": "v1",
                                ar3_name: [{ value: "The View" }],
                                ar3_documentation: { value: "What it shows" },
                                ar3_properties: {
                                    ar3_property: [{ "@propertyDefinitionRef": "tag", ar3_value: { value: "core" } }],
                                },
                            },
                        ],
                    },
                },
            },
        };
        const parsed = parseAr3Model(JSON.stringify(document));
        const element = parsed.elements.get("e1");
        expect(element?.description).toBe("What it holds");
        expect(element?.properties).toEqual([
            { name: "owner", value: "data-team" },
            { name: "tier", value: "silver" },
        ]);
        // Absent blocks read as empty (the legacy's optional chaining).
        expect(parsed.relations.get("r1")?.description).toBe("Why it flows");
        expect(parsed.relations.get("r1")?.properties).toEqual([]);
        expect(parsed.views[0].description).toBe("What it shows");
        expect(parsed.views[0].properties).toEqual([{ name: "tag", value: "core" }]);
    });

    it("LDG-11/DD-389: a document without ar3_model raises", () => {
        expect(() => parseAr3Model(JSON.stringify({ model: "not the shape" }))).toThrow(/ar3_model/);
        expect(() => parseAr3Model("not json at all")).toThrow();
    });

    it("LDG-17/LDG-18: concept ids and the node's element", () => {
        const view = model.views[0];
        expect(nodeConceptId(view.nodes[0])).toBe("00000000-0000-4000-8000-000000000001");
        expect(connectionConceptId(view.connections[1])).toBe("rel-2");
        expect(nodeElement(model, view.nodes[1])?.name).toBe("Load Job");

        const standAlone = { ...view.nodes[0], ref: null };
        expect(nodeConceptId(standAlone)).toBe(view.nodes[0].id);
        expect(nodeElement(model, standAlone)).toBeUndefined();
    });

    it("DD-406: reads the organization tree — the unlabeled root and its folders", () => {
        // The shipped producer emits one unlabeled root holding the Other /
        // Relations / Views folders (extract.py's _ar3_organizations).
        expect(model.organizations).toHaveLength(1);
        const root = model.organizations[0];
        expect(root.label).toBe("");
        expect(root.ref).toBeNull();
        expect(root.children.map((folder) => folder.label)).toEqual(["Other", "Relations", "Views"]);

        const other = root.children[0];
        expect(other.children.map((leaf) => leaf.ref)).toEqual([
            "00000000-0000-4000-8000-000000000001",
            "00000000-0000-4000-8000-000000000002",
            "00000000-0000-4000-8000-000000000003",
        ]);
        expect(other.children[0].children).toEqual([]);
        expect(root.children[1].children.map((leaf) => leaf.ref)).toEqual(["rel-1", "rel-2"]);
        expect(root.children[2].children.map((leaf) => leaf.ref)).toEqual(["lineage_view"]);
    });

    it("DD-406: a document without organizations parses to an empty tree", () => {
        // The 8.2 producer always writes the folders; a document that carries
        // none (or any producer that drops the block) reads as no tree, and
        // the Browse tab shows only the dropdown.
        const document = JSON.parse(fixture.model) as Record<string, unknown>;
        const ar3 = document["ar3_model"] as Record<string, unknown>;
        delete ar3["ar3_organizations"];
        expect(parseAr3Model(JSON.stringify(document)).organizations).toEqual([]);
    });
});
