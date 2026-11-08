import { describe, expect, it } from "vitest";

import {
    AR3_ICON_FILLS,
    AR3_MARKER_DEFS,
    AR3_NODE_FILLS,
    ar3Class,
    ar3ConnectionStyle,
    ar3Icon,
    ar3NodeShape,
    nodePath,
    NO_RELATION_OPTIONS,
} from "./archimate-shapes";
import { GENERIC_ARROW, LINEAGE_ICON_PATHS } from "./lineage-shapes";

/**
 * LDG-33..LDG-36 (DD-418): the archimate3 shape language, pinned against the
 * legacy tables it ports — `archimate3.ts` (the shape, class, relation, and
 * marker tables), `archimate-icon/definitions.ts` (the glyphs), and the two
 * scss fill blocks. The legacy lives in the vendored Aurelius clone; each
 * literal below is its byte-exact copy (ADR 052's "read from the source"
 * posture — the tables are reviewed as code).
 */

/** Every relation type the legacy style table names (ar3Relations + lineage). */
const STYLED_TYPES = [
    "ar3_Access",
    "ar3_Aggregation",
    "ar3_Assignment",
    "ar3_Association",
    "ar3_Composition",
    "ar3_Flow",
    "ar3_Influence",
    "ar3_Realization",
    "ar3_Serving",
    "ar3_Specialization",
    "ar3_Triggering",
    "lineage_relation",
];

describe("archimate-shapes (LDG-33..LDG-36)", () => {
    it("LDG-33: a junction is a hidden-label ellipse, the grouping hides its icon", () => {
        expect(ar3NodeShape("ar3_AndJunction")).toEqual({ kind: "ellipse", showIcon: false, showName: false });
        expect(ar3NodeShape("ar3_OrJunction")).toEqual({ kind: "ellipse", showIcon: false, showName: false });
        expect(ar3NodeShape("ar3_Grouping")).toEqual({ kind: "grouping", showIcon: false, showName: true });
    });

    it("LDG-33: the shape families draw as the legacy compose chose them", () => {
        // A representative of each basic shape the legacy table uses.
        expect(ar3NodeShape("ar3_Goal").kind).toBe("octagon");
        expect(ar3NodeShape("ar3_Value").kind).toBe("ellipse");
        expect(ar3NodeShape("ar3_BusinessProcess").kind).toBe("rounded");
        expect(ar3NodeShape("ar3_Deliverable").kind).toBe("waved");
        expect(ar3NodeShape("ar3_ApplicationComponent").kind).toBe("rectangle");
        // The lineage pair keeps the plain rectangle it always drew.
        expect(ar3NodeShape("lineage_dataset").kind).toBe("rectangle");
        expect(ar3NodeShape("lineage_process").kind).toBe("rectangle");
    });

    it("LDG-13/LDG-33: an untabled type draws the plain rectangle, icon and name shown", () => {
        // ar3_Junction and ar3_Element carry no row in the legacy table and
        // fall back like any unknown type.
        expect(ar3NodeShape("ar3_Junction")).toEqual({ kind: "rectangle", showIcon: true, showName: true });
        expect(ar3NodeShape("ar3_Element")).toEqual({ kind: "rectangle", showIcon: true, showName: true });
        expect(ar3NodeShape("")).toEqual({ kind: "rectangle", showIcon: true, showName: true });
    });

    it("LDG-33: the basic-shape paths are the legacy basicShapes, verbatim", () => {
        // Each string is the legacy template literal evaluated at w=120, h=80
        // (basic-shapes.ts, and the archimate file's own grouping/waved).
        expect(nodePath("rectangle", 120, 80)).toBe("m0,0h120v80h-120z");
        expect(nodePath("rounded", 120, 80)).toBe(
            "m12,0h96a12,12,0,0,1,12,12v56a12,12,0,0,1,-12,12h-96a12,12,0,0,1,-12,-12v-56a12,12,0,0,1,12,-12z",
        );
        expect(nodePath("ellipse", 120, 80)).toBe("m0,0a60,40,0,0,0,120,80a60,40,0,0,0,-120,-80z");
        expect(nodePath("octagon", 120, 80)).toBe("m12,0h96l12,12v56l-12,12h-96l-12,-12v-56l12,-12z");
        expect(nodePath("grouping", 120, 80)).toBe("m0,0h60v18h-60zm0,18h120v62h-120z");
        expect(nodePath("waved", 120, 80)).toBe("m0,0v74q30,12,60,0t60,0v-74z");
    });

    it("LDG-34: the layer fill classes are the legacy ar3Classes", () => {
        expect(ar3Class("ar3_BusinessActor")).toBe("business");
        expect(ar3Class("ar3_ApplicationComponent")).toBe("application");
        expect(ar3Class("ar3_Device")).toBe("technology");
        expect(ar3Class("ar3_DistributionNetwork")).toBe("physical");
        expect(ar3Class("ar3_Goal")).toBe("motivation");
        expect(ar3Class("ar3_Capability")).toBe("strategy");
        expect(ar3Class("ar3_WorkPackage")).toBe("implementation");
        expect(ar3Class("ar3_Location")).toBe("location");
        expect(ar3Class("ar3_AndJunction")).toBe("and");
        expect(ar3Class("ar3_OrJunction")).toBe("or");
        // The lineage pair keeps the classes the viewer already paints.
        expect(ar3Class("lineage_dataset")).toBe("dataset");
        expect(ar3Class("lineage_process")).toBe("process");
    });

    it("LDG-34: the implementation & migration quirk reaches the one class that has a rule", () => {
        // The legacy value "implementation & migration" reached CSS as four
        // classes and only implementation names a rule (DD-418's recorded
        // normalisation).
        expect(ar3Class("ar3_Gap")).toBe("implementation");
        expect(ar3Class("ar3_Plateau")).toBe("implementation");
    });

    it("LDG-34: composite, the unknown layer, and an untabled type paint no fill", () => {
        expect(ar3Class("ar3_Grouping")).toBe("composite");
        expect(ar3Class("ar3_Unknown")).toBe("unknown");
        expect(ar3Class("ar3_Junction")).toBe("");
        expect(ar3Class("")).toBe("");
        // Neither rule block names composite or unknown.
        expect(AR3_NODE_FILLS).not.toContain("composite");
        expect(AR3_NODE_FILLS).not.toContain("unknown");
        expect(AR3_ICON_FILLS).not.toContain("composite");
    });

    it("LDG-34: the node fill block carries the legacy archimate3.scss colours", () => {
        expect(AR3_NODE_FILLS).toContain(".node.business .node-shape");
        expect(AR3_NODE_FILLS).toContain("fill: #ffffb5");
        expect(AR3_NODE_FILLS).toContain("fill: #b5ffff");
        expect(AR3_NODE_FILLS).toContain("fill: #c9e7b7");
        expect(AR3_NODE_FILLS).toContain("fill: #ccccff");
        expect(AR3_NODE_FILLS).toContain("fill: #ffe0e0");
        expect(AR3_NODE_FILLS).toContain("fill: #f4deaa");
        expect(AR3_NODE_FILLS).toContain("fill: #000000");
        expect(AR3_NODE_FILLS).toContain("fill: #ffffff");
        expect(AR3_NODE_FILLS).toContain("fill: #ff8c00");
    });

    it("LDG-35: a glyph is its legacy path and colour class", () => {
        expect(ar3Icon("ar3_Goal")?.path).toMatch(/^M 6\.1538 8 a/);
        expect(ar3Icon("ar3_Goal")?.color).toBe("motivation");
        expect(ar3Icon("ar3_AndJunction")?.color).toBe("and");
        expect(ar3Icon("ar3_OrJunction")?.color).toBe("or");
        expect(ar3Icon("ar3_Grouping")?.color).toBe("composite");
        // The Deliverable quirk: the node is technology green, the icon is
        // implementation pink — the two legacy tables disagree verbatim.
        expect(ar3Class("ar3_Deliverable")).toBe("technology");
        expect(ar3Icon("ar3_Deliverable")?.color).toBe("implementation");
    });

    it("LDG-35: the lineage glyphs ride the table, the unknown type draws no glyph", () => {
        expect(ar3Icon("lineage_dataset")).toEqual({ path: LINEAGE_ICON_PATHS.dataset, color: "dataset" });
        expect(ar3Icon("lineage_process")).toEqual({ path: LINEAGE_ICON_PATHS.process, color: "process" });
        // definitions.ts carries no row for the unknown type — nothing drew.
        expect(ar3Icon("ar3_Unknown")).toBeNull();
        expect(ar3Icon("ar3_Junction")).toBeNull();
        expect(ar3Icon("")).toBeNull();
    });

    it("LDG-36: the eight markers are the legacy ar3RelationDef rows", () => {
        expect(AR3_MARKER_DEFS.map((marker) => marker.id)).toEqual([
            "access-read",
            "aggregation",
            "assignment-start",
            "association",
            "block-arrow",
            "composition",
            "generic-arrow",
            "generic-arrow-open",
        ]);
        const byId = new Map(AR3_MARKER_DEFS.map((marker) => [marker.id, marker]));
        expect(byId.get("access-read")).toEqual({
            id: "access-read",
            refX: 0,
            refY: 3,
            markerWidth: 6,
            markerHeight: 7,
            path: "M7,0l-7,3l7,3",
            fill: "none",
            stroke: "#000000",
        });
        expect(byId.get("aggregation")?.path).toBe("M10,0l10,6l-10,6l-10,-6l10,-6z");
        expect(byId.get("aggregation")?.fill).toBe("#FFFFFF");
        expect(byId.get("composition")?.fill).toBe("#000000");
        expect(byId.get("block-arrow")?.path).toBe("M0,0v14l10,-7z");
        // 7.22b's single marker is the same row, so the lineage drawing is
        // unchanged by the loop that renders all eight.
        expect(byId.get("generic-arrow")).toMatchObject({
            refX: GENERIC_ARROW.refX,
            refY: GENERIC_ARROW.refY,
            markerWidth: GENERIC_ARROW.markerWidth,
            markerHeight: GENERIC_ARROW.markerHeight,
            path: GENERIC_ARROW.path,
        });
    });

    it("LDG-36: the relation styles are the legacy ar3Relations table", () => {
        const solid = { markerStart: null, markerEnd: null, dash: null };
        expect(ar3ConnectionStyle("ar3_Aggregation", NO_RELATION_OPTIONS)).toEqual({
            ...solid,
            markerStart: "aggregation",
        });
        expect(ar3ConnectionStyle("ar3_Assignment", NO_RELATION_OPTIONS)).toEqual({
            markerStart: "assignment-start",
            markerEnd: "generic-arrow",
            dash: null,
        });
        expect(ar3ConnectionStyle("ar3_Composition", NO_RELATION_OPTIONS)).toEqual({
            ...solid,
            markerStart: "composition",
        });
        expect(ar3ConnectionStyle("ar3_Flow", NO_RELATION_OPTIONS)).toEqual({
            ...solid,
            markerEnd: "generic-arrow",
            dash: "4,2",
        });
        expect(ar3ConnectionStyle("ar3_Influence", NO_RELATION_OPTIONS)).toEqual({
            ...solid,
            markerEnd: "generic-arrow-open",
            dash: "4,2",
        });
        expect(ar3ConnectionStyle("ar3_Realization", NO_RELATION_OPTIONS)).toEqual({
            ...solid,
            markerEnd: "block-arrow",
            dash: "2,2",
        });
        expect(ar3ConnectionStyle("ar3_Serving", NO_RELATION_OPTIONS)).toEqual({
            ...solid,
            markerEnd: "generic-arrow-open",
        });
        expect(ar3ConnectionStyle("ar3_Specialization", NO_RELATION_OPTIONS)).toEqual({
            ...solid,
            markerEnd: "block-arrow",
        });
        expect(ar3ConnectionStyle("ar3_Triggering", NO_RELATION_OPTIONS)).toEqual({
            ...solid,
            markerEnd: "generic-arrow",
        });
        // The lineage edge keeps the one arrow 7.22b drew.
        expect(ar3ConnectionStyle("lineage_relation", NO_RELATION_OPTIONS)).toEqual({
            ...solid,
            markerEnd: "generic-arrow",
        });
    });

    it("LDG-36: an access relation grows its markers from its accessType", () => {
        const options = (accessType: string) => ({ accessType, isDirected: "" });
        expect(ar3ConnectionStyle("ar3_Access", options("Read"))).toEqual({
            markerStart: "access-read",
            markerEnd: null,
            dash: "2,2",
        });
        expect(ar3ConnectionStyle("ar3_Access", options("Write"))).toEqual({
            markerStart: null,
            markerEnd: "generic-arrow-open",
            dash: "2,2",
        });
        expect(ar3ConnectionStyle("ar3_Access", options("ReadWrite"))).toEqual({
            markerStart: "access-read",
            markerEnd: "generic-arrow-open",
            dash: "2,2",
        });
        // Any other value (or none) draws just the dash.
        expect(ar3ConnectionStyle("ar3_Access", options(""))).toEqual({
            markerStart: null,
            markerEnd: null,
            dash: "2,2",
        });
    });

    it("LDG-36: an association is directed by truthiness, not by the word true", () => {
        // The legacy checked the option's truthiness, so any non-empty string
        // — even "false" — draws the open V (kept verbatim, DD-418).
        const directed = (isDirected: string) => ({ accessType: "", isDirected });
        expect(ar3ConnectionStyle("ar3_Association", directed("true")).markerEnd).toBe("association");
        expect(ar3ConnectionStyle("ar3_Association", directed("false")).markerEnd).toBe("association");
        expect(ar3ConnectionStyle("ar3_Association", directed("")).markerEnd).toBeNull();
    });

    it("LDG-36: every styled type is covered and an unstyled type draws a plain line", () => {
        // The switch names every legacy row exactly once (a missed type would
        // silently draw the default).
        const names = STYLED_TYPES.filter((type) => ar3ConnectionStyle(type, NO_RELATION_OPTIONS).markerEnd === null);
        expect(names).toEqual(["ar3_Access", "ar3_Aggregation", "ar3_Association", "ar3_Composition"]);
        // A view connection whose relation is missing carries ar3_Relationship
        // — the legacy style function answered no markers for it.
        expect(ar3ConnectionStyle("ar3_Relationship", NO_RELATION_OPTIONS)).toEqual({
            markerStart: null,
            markerEnd: null,
            dash: null,
        });
    });
});
