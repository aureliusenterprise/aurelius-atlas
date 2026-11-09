/**
 * The archimate3 shape language (LDG-33..LDG-36, DD-418): the legacy
 * `libs/modelview2/src/lib/shapes/languages/archimate3.ts` ported whole —
 * the node-shape table (`ar3Elements`), the fill-class table (`ar3Classes`),
 * the relation-style table (`ar3Relations`), and the marker set
 * (`ar3RelationDef`) — with the glyph table of
 * `libs/components/src/lib/archimate-icon/` (`shapes.ts` + `definitions.ts`)
 * and the two fill blocks of `archimate3.scss` and
 * `archimate-icon.component.scss`. The legacy assembled these through
 * `compose(basicShapes.X)` closures over a `Dictionary`; the tables below are
 * plain data (the shapes are named kinds drawn by {@link nodePath}), which is
 * what the signal-rendered viewer and the drawer's tables read.
 *
 * The shipped producer (8.2) emits only the two lineage types, so today every
 * row here renders only archimate documents a model-extraction produces —
 * the drawing's parity with the legacy renderer, which drew any ar3 document
 * with these same tables. A type the tables do not name draws the plain
 * rectangle with no fill and no icon (the LDG-13 rule, unchanged).
 *
 * The legacy carried three deliberate quirks kept verbatim: the Deliverable's
 * node fill is the technology green while its icon is the implementation pink
 * (the two tables disagree in the legacy too); the `isDirected` check is
 * truthiness, not `=== "true"`; and the class value
 * `implementation & migration` reached CSS as four classes (only
 * `implementation` has a rule), normalised to that one here.
 */

import { LINEAGE_ICON_PATHS } from "./lineage-shapes";

import type { Ar3RelationOptions } from "./ar3-types";

/** The marker a connection style names (the legacy `RelationDef` keys). */
export type Ar3Marker =
    | "access-read"
    | "aggregation"
    | "assignment-start"
    | "association"
    | "block-arrow"
    | "composition"
    | "generic-arrow"
    | "generic-arrow-open";

/**
 * A node's basic shape (the legacy `basicShapes` plus the archimate file's
 * own `grouping` and `wavedRectangle`). A junction is an ellipse whose icon
 * and name are hidden (the legacy's `compose` options); the And/Or pair
 * tells itself apart by its fill class.
 */
export type Ar3ShapeKind = "rectangle" | "rounded" | "ellipse" | "octagon" | "grouping" | "waved";

/** One row of the node-shape table (the legacy `compose` result). */
export interface Ar3NodeShape {
    /** The basic shape to draw. */
    readonly kind: Ar3ShapeKind;
    /** Whether the type icon shows (false for a junction and the grouping). */
    readonly showIcon: boolean;
    /** Whether the name shows (false for a junction). */
    readonly showName: boolean;
}

/** The layer fills of `archimate3.scss` (the node block). */
export const AR3_NODE_FILLS = `
    .node.business .node-shape {
        fill: #ffffb5;
    }
    .node.application .node-shape {
        fill: #b5ffff;
    }
    .node.technology .node-shape {
        fill: #c9e7b7;
    }
    .node.physical .node-shape {
        fill: #c9e7b7;
    }
    .node.motivation .node-shape {
        fill: #ccccff;
    }
    .node.implementation .node-shape {
        fill: #ffe0e0;
    }
    .node.strategy .node-shape {
        fill: #f4deaa;
    }
    .node.and .node-shape {
        fill: #000000;
    }
    .node.or .node-shape {
        fill: #ffffff;
    }
    .node.location .node-shape {
        fill: #ff8c00;
    }
`;

/**
 * The icon fills of `archimate-icon.component.scss`, bare class rules the
 * drawing and the drawer's two icon sites each append to their styles. The
 * lineage pair rides the rules the components already carry. `composite` and
 * the unknown layer carry no rule — the glyph stays uninked, as in the legacy.
 */
export const AR3_ICON_FILLS = `
    .business {
        fill: #ffffb5;
    }
    .application {
        fill: #b5ffff;
    }
    .technology {
        fill: #c9e7b7;
    }
    .physical {
        fill: #c9e7b7;
    }
    .motivation {
        fill: #ccccff;
    }
    .implementation {
        fill: #ffe0e0;
    }
    .strategy {
        fill: #f4deaa;
    }
    .and {
        fill: #000000;
    }
    .or {
        fill: #ffffff;
    }
    .location {
        fill: #ff8c00;
    }
`;

/**
 * The node-shape table (the legacy `ar3Elements`, verbatim). `ar3_Junction`
 * and `ar3_Element` carry no row — the legacy table had none either, and the
 * unknown-type rule of LDG-13 draws them plain.
 */
const AR3_SHAPES: Readonly<Record<string, Ar3NodeShape>> = {
    ar3_AndJunction: { kind: "ellipse", showIcon: false, showName: false },
    ar3_ApplicationCollaboration: { kind: "rounded", showIcon: true, showName: true },
    ar3_ApplicationComponent: { kind: "rectangle", showIcon: true, showName: true },
    ar3_ApplicationEvent: { kind: "rounded", showIcon: true, showName: true },
    ar3_ApplicationFunction: { kind: "rounded", showIcon: true, showName: true },
    ar3_ApplicationInteraction: { kind: "rectangle", showIcon: true, showName: true },
    ar3_ApplicationInterface: { kind: "rectangle", showIcon: true, showName: true },
    ar3_ApplicationProcess: { kind: "rounded", showIcon: true, showName: true },
    ar3_ApplicationService: { kind: "rounded", showIcon: true, showName: true },
    ar3_Artifact: { kind: "rectangle", showIcon: true, showName: true },
    ar3_Assessment: { kind: "octagon", showIcon: true, showName: true },
    ar3_BusinessActor: { kind: "rectangle", showIcon: true, showName: true },
    ar3_BusinessCollaboration: { kind: "rounded", showIcon: true, showName: true },
    ar3_BusinessEvent: { kind: "rounded", showIcon: true, showName: true },
    ar3_BusinessFunction: { kind: "rounded", showIcon: true, showName: true },
    ar3_BusinessInteraction: { kind: "rounded", showIcon: true, showName: true },
    ar3_BusinessInterface: { kind: "rectangle", showIcon: true, showName: true },
    ar3_BusinessObject: { kind: "rectangle", showIcon: true, showName: true },
    ar3_BusinessProcess: { kind: "rounded", showIcon: true, showName: true },
    ar3_BusinessRole: { kind: "rectangle", showIcon: true, showName: true },
    ar3_BusinessService: { kind: "rounded", showIcon: true, showName: true },
    ar3_Capability: { kind: "rounded", showIcon: true, showName: true },
    ar3_CommunicationNetwork: { kind: "rectangle", showIcon: true, showName: true },
    ar3_Constraint: { kind: "octagon", showIcon: true, showName: true },
    ar3_Contract: { kind: "rectangle", showIcon: true, showName: true },
    ar3_CourseOfAction: { kind: "rounded", showIcon: true, showName: true },
    ar3_DataObject: { kind: "rectangle", showIcon: true, showName: true },
    ar3_Deliverable: { kind: "waved", showIcon: true, showName: true },
    ar3_Device: { kind: "rectangle", showIcon: true, showName: true },
    ar3_DistributionNetwork: { kind: "rectangle", showIcon: true, showName: true },
    ar3_Driver: { kind: "octagon", showIcon: true, showName: true },
    ar3_Equipment: { kind: "rectangle", showIcon: true, showName: true },
    ar3_Facility: { kind: "rectangle", showIcon: true, showName: true },
    ar3_Gap: { kind: "rectangle", showIcon: true, showName: true },
    ar3_Goal: { kind: "octagon", showIcon: true, showName: true },
    ar3_Grouping: { kind: "grouping", showIcon: false, showName: true },
    ar3_ImplementationEvent: { kind: "rounded", showIcon: true, showName: true },
    ar3_Location: { kind: "rectangle", showIcon: true, showName: true },
    ar3_Material: { kind: "rectangle", showIcon: true, showName: true },
    ar3_Meaning: { kind: "octagon", showIcon: true, showName: true },
    ar3_Node: { kind: "rectangle", showIcon: true, showName: true },
    ar3_OrJunction: { kind: "ellipse", showIcon: false, showName: false },
    ar3_Outcome: { kind: "octagon", showIcon: true, showName: true },
    ar3_Path: { kind: "rectangle", showIcon: true, showName: true },
    ar3_Plateau: { kind: "rectangle", showIcon: true, showName: true },
    ar3_Principle: { kind: "octagon", showIcon: true, showName: true },
    ar3_Product: { kind: "rectangle", showIcon: true, showName: true },
    ar3_Representation: { kind: "waved", showIcon: true, showName: true },
    ar3_Requirement: { kind: "octagon", showIcon: true, showName: true },
    ar3_Resource: { kind: "rectangle", showIcon: true, showName: true },
    ar3_Stakeholder: { kind: "octagon", showIcon: true, showName: true },
    ar3_SystemSoftware: { kind: "rectangle", showIcon: true, showName: true },
    ar3_TechnologyCollaboration: { kind: "rounded", showIcon: true, showName: true },
    ar3_TechnologyEvent: { kind: "rounded", showIcon: true, showName: true },
    ar3_TechnologyFunction: { kind: "rounded", showIcon: true, showName: true },
    ar3_TechnologyInteraction: { kind: "rounded", showIcon: true, showName: true },
    ar3_TechnologyInterface: { kind: "rectangle", showIcon: true, showName: true },
    ar3_TechnologyProcess: { kind: "rounded", showIcon: true, showName: true },
    ar3_TechnologyService: { kind: "rounded", showIcon: true, showName: true },
    ar3_Unknown: { kind: "rectangle", showIcon: true, showName: true },
    ar3_Value: { kind: "ellipse", showIcon: true, showName: true },
    ar3_ValueStream: { kind: "rounded", showIcon: true, showName: true },
    ar3_WorkPackage: { kind: "rounded", showIcon: true, showName: true },
    lineage_dataset: { kind: "rectangle", showIcon: true, showName: true },
    lineage_process: { kind: "rectangle", showIcon: true, showName: true },
};

/**
 * The fill-class table (the legacy `ar3Classes` + `lineageClasses`, verbatim
 * but for `implementation & migration`, which the legacy reached CSS as the
 * classes `implementation`, `&`, and `migration` — only the first names a
 * rule. `composite` and `unknown` name no rule: those nodes stay uninked.
 */
const AR3_CLASSES: Readonly<Record<string, string>> = {
    ar3_AndJunction: "and",
    ar3_ApplicationCollaboration: "application",
    ar3_ApplicationComponent: "application",
    ar3_ApplicationEvent: "application",
    ar3_ApplicationFunction: "application",
    ar3_ApplicationInteraction: "application",
    ar3_ApplicationInterface: "application",
    ar3_ApplicationProcess: "application",
    ar3_ApplicationService: "application",
    ar3_Artifact: "technology",
    ar3_Assessment: "motivation",
    ar3_BusinessActor: "business",
    ar3_BusinessCollaboration: "business",
    ar3_BusinessEvent: "business",
    ar3_BusinessFunction: "business",
    ar3_BusinessInteraction: "business",
    ar3_BusinessInterface: "business",
    ar3_BusinessObject: "business",
    ar3_BusinessProcess: "business",
    ar3_BusinessRole: "business",
    ar3_BusinessService: "business",
    ar3_Capability: "strategy",
    ar3_CommunicationNetwork: "technology",
    ar3_Constraint: "motivation",
    ar3_Contract: "business",
    ar3_CourseOfAction: "strategy",
    ar3_DataObject: "application",
    ar3_Deliverable: "technology",
    ar3_Device: "technology",
    ar3_DistributionNetwork: "physical",
    ar3_Driver: "motivation",
    ar3_Equipment: "physical",
    ar3_Facility: "physical",
    ar3_Gap: "implementation",
    ar3_Goal: "motivation",
    ar3_Grouping: "composite",
    ar3_ImplementationEvent: "implementation",
    ar3_Location: "location",
    ar3_Material: "physical",
    ar3_Meaning: "motivation",
    ar3_Node: "technology",
    ar3_OrJunction: "or",
    ar3_Outcome: "motivation",
    ar3_Path: "technology",
    ar3_Plateau: "implementation",
    ar3_Principle: "motivation",
    ar3_Product: "business",
    ar3_Representation: "business",
    ar3_Requirement: "motivation",
    ar3_Resource: "strategy",
    ar3_Stakeholder: "motivation",
    ar3_SystemSoftware: "technology",
    ar3_TechnologyCollaboration: "technology",
    ar3_TechnologyEvent: "technology",
    ar3_TechnologyFunction: "technology",
    ar3_TechnologyInteraction: "technology",
    ar3_TechnologyInterface: "technology",
    ar3_TechnologyProcess: "technology",
    ar3_TechnologyService: "technology",
    ar3_Unknown: "unknown",
    ar3_Value: "motivation",
    ar3_ValueStream: "strategy",
    ar3_WorkPackage: "implementation",
    lineage_dataset: "dataset",
    lineage_process: "process",
};

/** The 16x16 glyph paths (the archimate-icon `shapes.ts`, verbatim). */
const AR3_ICON_PATHS = {
    actor: "M 8 5.6471 l 0 5.6471 m -3.7647 -2.8235 l 7.5294 0 m -3.7647 2.8235 l -3.7647 4.7059 m 3.7647 -4.7059 l 3.7647 4.7059 m -6.5882 -13.1765 a 2.8235 2.8235 90 1 0 5.6471 0 a 2.8235 2.8235 90 1 0 -5.6471 0F",
    applicationComponent:
        "M 3.3846 16 l 0 -4.3077 M 3.3846 8.6154 l 0 -3.0769 M 3.3846 2.4615 l 0 -2.4615 l 12.3077 0 l 0 16 l -12.3077 0 M 0.3077 2.4615 l 7.3846 0 l 0 3.0769 l -7.3846 0 z M 0.3077 8.6154 l 7.3846 0 l 0 3.0769 l -7.3846 0 z",
    artifact: "M 2 0 l 8 0 l 4 4 l 0 12 l -12 0 z M 10 0 l 0 4 l 4 0",
    assessment:
        "M 4.6667 5.3333 a 5.3333 5.3333 90 1 0 10.6667 0 a 5.3333 5.3333 90 1 0 -10.6667 0 M 0.6667 16 L 7.3333 9.3333",
    capability:
        "M 10.6667 0 l 5.3333 0 l 0 5.3333 l -5.3333 0 z M 10.6667 5.3333 l 5.3333 0 l 0 5.3333 l -5.3333 0 z M 5.3333 5.3333 l 5.3333 0 l 0 5.3333 l -5.3333 0 z M 10.6667 10.6667 l 5.3333 0 l 0 5.3333 l -5.3333 0 z M 5.3333 10.6667 l 5.3333 0 l 0 5.3333 l -5.3333 0 z M 0 10.6667 l 5.3333 0 l 0 5.3333 l -5.3333 0 z",
    collaboration:
        "M 0 8 a 5.7143 5.7143 90 1 0 11.4286 0 a 5.7143 5.7143 90 1 0 -11.4286 0 m 4.5714 0 a 5.7143 5.7143 90 1 0 11.4286 0 a 5.7143 5.7143 90 1 0 -11.4286 0",
    communicationNetwork:
        "M 2.1333 3.6668 a 2.6667 2.6667 90 1 0 5.3333 0 a 2.6667 2.6667 90 1 0 -5.3333 0 m 8.5333 0 a 2.6667 2.6667 90 1 0 5.3333 0 a 2.6667 2.6667 90 1 0 -5.3333 0 m -10.6667 8.5333 a 2.6667 2.6667 90 1 0 5.3333 0 a 2.6667 2.6667 90 1 0 -5.3333 0 m 8.5333 0 a 2.6667 2.6667 90 1 0 5.3333 0 a 2.6667 2.6667 90 1 0 -5.3333 0 m -5.3333 -2.6667 l 1.0667 -3.2 m 7.4667 3.2 l 1.0667 -3.2 m -7.4667 5.8667 l 3.2 0 m -1.0667 -8.5333 l 3.2 0",
    constraint: "M4,0l12,0l-4,9l-12,0l4,-9zM8,0L4,9",
    contract: "M0,3l16,0l0,10l-16,0zM0,6L16,6M0,10L16,10",
    courseOfAction:
        "M 9.7255 6.7717 a 1.1765 1.1765 90 1 0 2.3529 0 a 1.1765 1.1765 90 1 0 -2.3529 0 m 6.2745 0 c 0 -2.8157 -2.2824 -5.098 -5.098 -5.098 c -2.8157 0 -5.098 2.2824 -5.098 5.098 c 0 2.8157 2.2824 5.098 5.098 5.098 c 2.8157 0 5.098 -2.2824 5.098 -5.098 z m -1.9608 0 c 0 -1.7325 -1.4047 -3.1373 -3.1373 -3.1373 c -1.7325 0 -3.1373 1.4047 -3.1373 3.1373 c 0 1.7325 1.4047 3.1373 3.1373 3.1373 c 1.7325 0 3.1373 -1.4047 3.1373 -3.1373 z m -10.1961 4.3137 c -1.9027 0 -3.5318 1.3663 -3.862 3.2408 m 1.5875 -5.5937 l 4.7059 0.7843 l -2.3529 4.0784",
    deliverable: "M 0 3 l 0 9 q 4 2 8 0 t 8 0 l 0 -9 z",
    device: "M 1.7143 1.1428 h 12.5714 a 1.7143 1.7143 90 0 1 1.7143 1.7143 v 9.1429 a 1.7143 1.7143 90 0 1 -1.7143 1.7143 h -12.5714 a 1.7143 1.7143 90 0 1 -1.7143 -1.7143 v -9.1429 a 1.7143 1.7143 90 0 1 1.7143 -1.7143 z M 0.5714 14.8571 l 3.4286 -4.5714 l 8 0 l 3.4286 4.5714 l -14.8571 0 z",
    distributionNetwork: "M 2 3 l 13 0 M 2 7 l 13 0 M 5 0 l -5 5 l 5 5 M 12 0 l 5 5 l -5 5",
    driver: "M 1.8824 8 a 6.1176 6.1176 90 1 0 12.2353 0 a 6.1176 6.1176 90 1 0 -12.2353 0 M 0 8 l 16 0 m -8 -8 l 0 16 m -5.6471 -13.6471 l 11.2941 11.2941 m -11.2941 0 l 11.2941 -11.2941 z",
    equipment:
        "M 5.3333 10.6667 a 2 2 90 1 0 4 0 a 2 2 90 1 0 -4 0 M 9.3333 3.3333 a 1.3333 1.3333 90 1 0 2.6667 0 a 1.3333 1.3333 90 1 0 -2.6667 0 M 11.3333 11.3333 l 1.3333 0 l 0 -1.3333 l -1.3333 0 l -0.6667 -1.3333 l 0.6667 -1.3333 l -0.6667 -0.6667 l -1.3333 0.6667 l -1.3333 -0.6667 l 0 -1.3333 l -1.3333 0 l 0 1.3333 l -1.3333 0.6667 l -1.3333 -0.6667 l -0.6667 0.6667 l 0.6667 1.3333 l -0.6667 1.3333 l -1.3333 0 l 0 1.3333 l 1.3333 0 l 0.6667 1.3333 l -0.6667 1.3333 l 0.6667 0.6667 l 1.3333 -0.6667 l 1.3333 0.6667 l 0 1.3333 l 1.3333 0 l 0 -1.3333 l 1.3333 -0.6667 l 1.3333 0.6667 l 0.6667 -0.6667 l -0.6667 -1.3333 l 0.6667 -1.3333 z M 13.3333 4 l 0.6667 0 l 0 -1.3333 l -0.6667 0 l -0.6667 -1.3333 l 0 -0.6667 l -0.6667 -0.6667 l -0.6667 0.6667 l -1.3333 0 l -0.6667 -0.6667 l -0.6667 0.6667 l 0 0.6667 l -0.6667 1.3333 l -0.6667 0 l 0 1.3333 l 0.6667 0 l 0.6667 1.3333 l 0 0.6667 l 0.6667 0.6667 l 0.6667 -0.6667 l 1.3333 0 l 0.6667 0.6667 l 0.6667 -0.6667 l 0 -0.6667 l 0.6667 -1.3333 z",
    event: "M 0 3.5 c 2 0 4 2 4 4.5 c 0 2.5 -2 4.5 -4 4.5 h 12 c 2 0 4 -2 4 -4.5 c 0 -2.5 -2 -4.5 -4 -4.5 h -12 z",
    facility: "M 0 15 l 15 0 l 0 -6 l -4 3 l 0 -3 l -4 3 l 0 -3 l -4 3 l 0 -12 l -3 0 l 0 15",
    function:
        "M 1.1429 16 l 0 -10.2857 l 6.8571 -5.7143 l 6.8571 5.7143 l 0 10.2857 l -6.8571 -6.8571 l -6.8571 6.8571 z",
    gap: "M 1.8824 8 a 6.1176 6.1176 90 1 0 12.2353 0 a 6.1176 6.1176 90 1 0 -12.2353 0 M 0 6.5882 l 16 0 M 0 9.4118 l 16 0",
    goal: "M 6.1538 8 a 1.8462 1.8462 90 1 0 3.6923 0 a 1.8462 1.8462 90 1 0 -3.6923 0 M 16 8 c 0 -4.4185 -3.5815 -8 -8 -8 c -4.4185 0 -8 3.5815 -8 8 c 0 4.4185 3.5815 8 8 8 c 4.4185 0 8 -3.5815 8 -8 z m -3.0769 0 c 0 -2.7188 -2.2043 -4.9231 -4.9231 -4.9231 c -2.7188 0 -4.9231 2.2043 -4.9231 4.9231 c 0 2.7188 2.2043 4.9231 4.9231 4.9231 c 2.7188 0 4.9231 -2.2043 4.9231 -4.9231 z",
    grouping: "M0,3l10,0l0,3l-10,0zM0,6l16,0l0,7l-16,0z",
    interaction:
        "M 6.6667 0 c 0 0 -6.6667 0 -6.6667 8 c 0 0 0 8 6.6667 8 l 0 -16 m 2.6667 16 c 0 0 6.6667 0 6.6667 -8 c 0 0 0 -8 -6.6667 -8 c 0 0 0 0 0 0 l 0 16",
    interface: "M 6.5882 8 a 4.7059 4.7059 90 1 0 9.4118 0 a 4.7059 4.7059 90 1 0 -9.4118 0 M 0 8 l 6.5882 0",
    junction: "M0,8a8,8,0,1,0,16,0a8,8,0,1,0,-16,0",
    location:
        "M 13 7.1467 c 1.0069 -2.768 -0.4203 -5.8283 -3.1872 -6.8363 c -2.768 -1.0069 -5.8283 0.4203 -6.8363 3.1883 c -0.4288 1.1776 -0.4288 2.4693 0 3.648 l 5.0123 8.8427 l 5.12 -9.0667",
    material: "M 12 1 l -8 0 l -4 7 l 3 7 l 9 0 l 4 -7 l -4 -7 z m -6 2 l -3.3 5.5 m 1.6 4 l 6.7 0 m 2 -4 l -3 -5.5",
    meaning:
        "M 5.3559 4.427 a 5.3559 2.3729 0 1 0 0.1356 0 m 5.1525 0 a 5.3559 2.3729 0 1 0 0.1356 0 m -5.9661 2.4407 a 4.8136 2.3729 0 1 0 0.1356 0 m 5.2881 -0.678 a 4.8136 2.3729 0 1 0 0.1356 0",
    node: "M 0 3.4286 l 12.5714 0 l 0 12.5714 l -12.5714 0 z M 0 3.4286 l 3.4286 -3.4286 l 12.5714 0 l -3.4286 3.4286 M 12.5714 16 l 3.4286 -3.4286 l 0 -12.5714 l -3.4286 3.4286",
    object: "M0,3l16,0l0,10l-16,0zM0,6L16,6",
    outcome:
        "M 4.3243 10.1639 a 1.2973 1.2973 90 1 0 2.5946 0 a 1.2973 1.2973 90 1 0 -2.5946 0 m 6.9189 0 c 0 -3.1049 -2.5168 -5.6216 -5.6216 -5.6216 c -3.1049 0 -5.6216 2.5168 -5.6216 5.6216 c 0 3.1049 2.5168 5.6216 5.6216 5.6216 c 3.1049 0 5.6216 -2.5168 5.6216 -5.6216 z m -2.1622 0 c 0 -1.9105 -1.549 -3.4595 -3.4595 -3.4595 c -1.9105 0 -3.4595 1.549 -3.4595 3.4595 c 0 1.9105 1.549 3.4595 3.4595 3.4595 c 1.9105 0 3.4595 -1.549 3.4595 -3.4595 z m -3.4595 0.4324 l 8.2162 -8.2162 m -2.1622 2.1622 l 0.8649 -4.3243 m -0.8649 4.3243 l 4.3243 -0.8649",
    path: "M 4.7059 3.2941 l -4.7059 4.7059 l 4.7059 4.7059 m 6.5882 -9.4118 l 4.7059 4.7059 l -4.7059 4.7059 m -8 -4.7059 l 1.8824 0 m 1.8824 0 l 1.8824 0 m 1.8824 0 l 1.8824 0",
    plateau: "M 0 11 l 12 0 m -10 -3 l 12 0 m -10 -3 l 12 0",
    principle:
        "M 2 0 h 12 a 2 2 0 0 1 2 2 v 12 a 2 2 0 0 1 -2 2 h -12 a 2 2 0 0 1 -2 -2 v -12 a 2 2 0 0 1 2 -2 z M 8.5 2.75 l 0 7 l -1 0 l 0 -7 z m 0 8.5 l 0 2 l -1 0 l 0 -2 z",
    process: "M 0 5.7143 l 9.1429 0 l 0 -3.4286 l 6.8571 5.7143 l -6.8571 5.7143 l 0 -3.4286 l -9.1429 0 l 0 -4.5714 z",
    product: "M0,3l16,0l0,10l-16,0zM0,6L8,6L8,3",
    representation: "M 0 3 l 0 9 q 4 2 8 0 t 8 0 l 0 -9 z M 0 6 l 16 0",
    requirement: "M 4 3.5 l 12 0 l -4 9 l -12 0 l 4 -9 z",
    resource:
        "M 1.3333 3.5556 h 10.6667 a 1.3333 1.3333 90 0 1 1.3333 1.3333 v 6.2222 a 1.3333 1.3333 90 0 1 -1.3333 1.3333 h -10.6667 a 1.3333 1.3333 90 0 1 -1.3333 -1.3333 v -6.2222 a 1.3333 1.3333 90 0 1 1.3333 -1.3333 z M 13.7778 5.7778 h 1.7778 a 0.4444 0.4444 90 0 1 0.4444 0.4444 v 3.5556 a 0.4444 0.4444 90 0 1 -0.4444 0.4444 h -1.7778 a 0.4444 0.4444 90 0 1 -0.4444 -0.4444 v -3.5556 a 0.4444 0.4444 90 0 1 0.4444 -0.4444 z M 2.6667 5.3334 l 0 5.3333 m 2.6667 -5.3333 l 0 5.3333 m 2.6667 -5.3333 l 0 5.3333",
    role: "M 13.2414 3.5862 l -10.4828 0 c -1.5239 0 -2.7586 1.9763 -2.7586 4.4138 c 0 2.4375 1.2348 4.4138 2.7586 4.4138 l 10.4828 0 c 1.5239 0 2.7586 -1.9763 2.7586 -4.4138 c 0 -2.4375 -1.3142 -4.4138 -2.7586 -4.4138 m 0 0 c -1.5239 0 -2.7586 1.9763 -2.7586 4.4138 c 0 2.4375 1.2348 4.4138 2.7586 4.4138",
    service: "M 4 3.5 h 8 a 4 4 0 0 1 4 4 v1 a 4 4 0 0 1 -4 4 h -8 a 4 4 0 0 1 -4 -4 v-1 a 4 4 0 0 1 4 -4 z",
    systemSoftware:
        "M 1.3333 7.3333 a 7.3333 7.3333 90 1 0 14.6667 0 a 7.3333 7.3333 90 1 0 -14.6667 0 M 0 8.6667 a 7.3333 7.3333 90 1 0 14.6667 0 a 7.3333 7.3333 90 1 0 -14.6667 0",
    value: "M 8 4 a 8 4 0 1 0 0.2 0 z",
    valueStream: "M 0 2.6667 l 10.6667 0 l 5.3333 5.3333 l -5.3333 5.3333 l -10.6667 0 l 5.3333 -5.3333 z",
    workPackage:
        "M 1.7778 4.5 h 12.4444 a 1.7778 1.7778 90 0 1 1.7778 1.7778 v 4.1481 a 1.7778 1.7778 90 0 1 -1.7778 1.7778 h -12.4444 a 1.7778 1.7778 90 0 1 -1.7778 -1.7778 v -4.1481 a 1.7778 1.7778 90 0 1 1.7778 -1.7778 z",
} as const;

/** One row of the glyph table (the legacy `IconDefinition`). */
export interface Ar3Icon {
    /** The 16x16 glyph path. */
    readonly path: string;
    /** The fill class of `archimate-icon.component.scss`. */
    readonly color: string;
}

/**
 * The glyph table (the archimate-icon `definitions.ts`, verbatim): the type
 * icon the drawing and the drawer's Type row ink, with its colour class. The
 * view-reference row is left out — this page parses no view reference
 * (DD-389). The unknown type carries no row, as in the legacy table.
 */
const AR3_ICONS: Readonly<Record<string, Ar3Icon>> = {
    ar3_AndJunction: { path: AR3_ICON_PATHS.junction, color: "and" },
    ar3_ApplicationCollaboration: { path: AR3_ICON_PATHS.collaboration, color: "application" },
    ar3_ApplicationComponent: { path: AR3_ICON_PATHS.applicationComponent, color: "application" },
    ar3_ApplicationEvent: { path: AR3_ICON_PATHS.event, color: "application" },
    ar3_ApplicationFunction: { path: AR3_ICON_PATHS.function, color: "application" },
    ar3_ApplicationInteraction: { path: AR3_ICON_PATHS.interaction, color: "application" },
    ar3_ApplicationInterface: { path: AR3_ICON_PATHS.interface, color: "application" },
    ar3_ApplicationProcess: { path: AR3_ICON_PATHS.process, color: "application" },
    ar3_ApplicationService: { path: AR3_ICON_PATHS.service, color: "application" },
    ar3_Artifact: { path: AR3_ICON_PATHS.artifact, color: "technology" },
    ar3_Assessment: { path: AR3_ICON_PATHS.assessment, color: "motivation" },
    ar3_BusinessActor: { path: AR3_ICON_PATHS.actor, color: "business" },
    ar3_BusinessCollaboration: { path: AR3_ICON_PATHS.collaboration, color: "business" },
    ar3_BusinessEvent: { path: AR3_ICON_PATHS.event, color: "business" },
    ar3_BusinessFunction: { path: AR3_ICON_PATHS.function, color: "business" },
    ar3_BusinessInteraction: { path: AR3_ICON_PATHS.interaction, color: "business" },
    ar3_BusinessInterface: { path: AR3_ICON_PATHS.interface, color: "business" },
    ar3_BusinessObject: { path: AR3_ICON_PATHS.object, color: "business" },
    ar3_BusinessProcess: { path: AR3_ICON_PATHS.process, color: "business" },
    ar3_BusinessRole: { path: AR3_ICON_PATHS.role, color: "business" },
    ar3_BusinessService: { path: AR3_ICON_PATHS.service, color: "business" },
    ar3_Capability: { path: AR3_ICON_PATHS.capability, color: "strategy" },
    ar3_CommunicationNetwork: { path: AR3_ICON_PATHS.communicationNetwork, color: "technology" },
    ar3_Constraint: { path: AR3_ICON_PATHS.constraint, color: "motivation" },
    ar3_Contract: { path: AR3_ICON_PATHS.contract, color: "business" },
    ar3_CourseOfAction: { path: AR3_ICON_PATHS.courseOfAction, color: "strategy" },
    ar3_DataObject: { path: AR3_ICON_PATHS.object, color: "application" },
    ar3_Deliverable: { path: AR3_ICON_PATHS.deliverable, color: "implementation" },
    ar3_Device: { path: AR3_ICON_PATHS.device, color: "technology" },
    ar3_DistributionNetwork: { path: AR3_ICON_PATHS.distributionNetwork, color: "physical" },
    ar3_Driver: { path: AR3_ICON_PATHS.driver, color: "motivation" },
    ar3_Equipment: { path: AR3_ICON_PATHS.equipment, color: "physical" },
    ar3_Facility: { path: AR3_ICON_PATHS.facility, color: "physical" },
    ar3_Gap: { path: AR3_ICON_PATHS.gap, color: "implementation" },
    ar3_Goal: { path: AR3_ICON_PATHS.goal, color: "motivation" },
    ar3_Grouping: { path: AR3_ICON_PATHS.grouping, color: "composite" },
    ar3_ImplementationEvent: { path: AR3_ICON_PATHS.event, color: "implementation" },
    ar3_Location: { path: AR3_ICON_PATHS.location, color: "location" },
    ar3_Material: { path: AR3_ICON_PATHS.material, color: "physical" },
    ar3_Meaning: { path: AR3_ICON_PATHS.meaning, color: "motivation" },
    ar3_Node: { path: AR3_ICON_PATHS.node, color: "technology" },
    ar3_OrJunction: { path: AR3_ICON_PATHS.junction, color: "or" },
    ar3_Outcome: { path: AR3_ICON_PATHS.outcome, color: "motivation" },
    ar3_Path: { path: AR3_ICON_PATHS.path, color: "technology" },
    ar3_Plateau: { path: AR3_ICON_PATHS.plateau, color: "implementation" },
    ar3_Principle: { path: AR3_ICON_PATHS.principle, color: "motivation" },
    ar3_Product: { path: AR3_ICON_PATHS.product, color: "business" },
    ar3_Representation: { path: AR3_ICON_PATHS.representation, color: "business" },
    ar3_Requirement: { path: AR3_ICON_PATHS.requirement, color: "motivation" },
    ar3_Resource: { path: AR3_ICON_PATHS.resource, color: "strategy" },
    ar3_Stakeholder: { path: AR3_ICON_PATHS.role, color: "motivation" },
    ar3_SystemSoftware: { path: AR3_ICON_PATHS.systemSoftware, color: "technology" },
    ar3_TechnologyCollaboration: { path: AR3_ICON_PATHS.collaboration, color: "technology" },
    ar3_TechnologyEvent: { path: AR3_ICON_PATHS.event, color: "technology" },
    ar3_TechnologyFunction: { path: AR3_ICON_PATHS.function, color: "technology" },
    ar3_TechnologyInteraction: { path: AR3_ICON_PATHS.interaction, color: "technology" },
    ar3_TechnologyInterface: { path: AR3_ICON_PATHS.interface, color: "technology" },
    ar3_TechnologyProcess: { path: AR3_ICON_PATHS.process, color: "technology" },
    ar3_TechnologyService: { path: AR3_ICON_PATHS.service, color: "technology" },
    ar3_Value: { path: AR3_ICON_PATHS.value, color: "motivation" },
    ar3_ValueStream: { path: AR3_ICON_PATHS.valueStream, color: "strategy" },
    ar3_WorkPackage: { path: AR3_ICON_PATHS.workPackage, color: "implementation" },
    lineage_dataset: { path: LINEAGE_ICON_PATHS.dataset, color: "dataset" },
    lineage_process: { path: LINEAGE_ICON_PATHS.process, color: "process" },
};

/**
 * Every type the glyph table knows — the archimate `@xsi_type`s plus the two
 * lineage ones (the keys of {@link ar3Icon}). The "All Types" story draws one
 * node per entry so each shape, fill, and glyph can be checked with an eye.
 */
export const AR3_ICON_TYPES: readonly string[] = Object.keys(AR3_ICONS);

/** One marker of the defs block (the legacy `ar3RelationDef` row). */
export interface Ar3MarkerDef {
    /** The marker id the style names. */
    readonly id: Ar3Marker;
    readonly refX: number;
    readonly refY: number;
    readonly markerWidth: number;
    readonly markerHeight: number;
    /** The marker path (the legacy's, verbatim). */
    readonly path: string;
    /** The marker fill (the legacy `fill`, kept as a style value). */
    readonly fill: string;
    /** The marker stroke, empty for the filled arrows. */
    readonly stroke: string;
}

/**
 * The marker set (the legacy `ar3RelationDef`, verbatim — the
 * `generic-arrow` row equals 7.22b's `GENERIC_ARROW`). The path keeps the
 * legacy's `stroke-dasharray: 999`, which keeps a dashed connection from
 * dashing its own arrowhead.
 */
export const AR3_MARKER_DEFS: readonly Ar3MarkerDef[] = [
    {
        id: "access-read",
        refX: 0,
        refY: 3,
        markerWidth: 6,
        markerHeight: 7,
        path: "M7,0l-7,3l7,3",
        fill: "none",
        stroke: "#000000",
    },
    {
        id: "aggregation",
        refX: 0,
        refY: 6,
        markerWidth: 20,
        markerHeight: 12,
        path: "M10,0l10,6l-10,6l-10,-6l10,-6z",
        fill: "#FFFFFF",
        stroke: "#000000",
    },
    {
        id: "assignment-start",
        refX: 0,
        refY: 3,
        markerWidth: 6,
        markerHeight: 6,
        path: "M0,0a3,3,0,0,0,6,6a3,3,0,0,0,-6,-6z",
        fill: "#000000",
        stroke: "",
    },
    {
        id: "association",
        refX: 10,
        refY: 6,
        markerWidth: 10,
        markerHeight: 10,
        path: "M0,0L10,6",
        fill: "none",
        stroke: "#000000",
    },
    {
        id: "block-arrow",
        refX: 10,
        refY: 7,
        markerWidth: 10,
        markerHeight: 14,
        path: "M0,0v14l10,-7z",
        fill: "#FFFFFF",
        stroke: "#000000",
    },
    {
        id: "composition",
        refX: 0,
        refY: 6,
        markerWidth: 20,
        markerHeight: 12,
        path: "M10,0l10,6l-10,6l-10,-6l10,-6z",
        fill: "#000000",
        stroke: "",
    },
    {
        id: "generic-arrow",
        refX: 7,
        refY: 3,
        markerWidth: 6,
        markerHeight: 7,
        path: "M0,0l7,3l-7,3z",
        fill: "#000000",
        stroke: "",
    },
    {
        id: "generic-arrow-open",
        refX: 7,
        refY: 3,
        markerWidth: 6,
        markerHeight: 7,
        path: "M0,0l7,3l-7,3",
        fill: "none",
        stroke: "#000000",
    },
];

/** The stroke a connection's relation type asks for (the legacy style). */
export interface Ar3ConnectionStyle {
    /** The start marker, or null for none. */
    readonly markerStart: Ar3Marker | null;
    /** The end marker, or null for none (an unstyled type draws a plain line). */
    readonly markerEnd: Ar3Marker | null;
    /** The dash pattern, or null for a solid line. */
    readonly dash: string | null;
}

/** No options, for a call site with no relation to read. */
export const NO_RELATION_OPTIONS: Ar3RelationOptions = { accessType: "", isDirected: "" };

const EMPTY_STYLE: Ar3ConnectionStyle = { markerStart: null, markerEnd: null, dash: null };

/**
 * The connection style of a relation type (the legacy `ar3Relations`,
 * verbatim, with `lineage_relation` from `lineage.ts`). An unstyled type —
 * the generic `ar3_Relationship` a view connection carries when its relation
 * is missing — draws the plain line: the legacy style function answered no
 * markers.
 * @param type the relation's `@xsi_type` (the model relation wins over the
 *     view connection's, the legacy's precedence)
 * @param options the relation's type attributes
 */
export function ar3ConnectionStyle(type: string, options: Ar3RelationOptions): Ar3ConnectionStyle {
    switch (type) {
        case "ar3_Access":
            return {
                markerStart: options.accessType === "Read" || options.accessType === "ReadWrite" ? "access-read" : null,
                markerEnd:
                    options.accessType === "Write" || options.accessType === "ReadWrite" ? "generic-arrow-open" : null,
                dash: "2,2",
            };
        case "ar3_Aggregation":
            return { ...EMPTY_STYLE, markerStart: "aggregation" };
        case "ar3_Assignment":
            return { markerStart: "assignment-start", markerEnd: "generic-arrow", dash: null };
        case "ar3_Association":
            return { ...EMPTY_STYLE, markerEnd: options.isDirected ? "association" : null };
        case "ar3_Composition":
            return { ...EMPTY_STYLE, markerStart: "composition" };
        case "ar3_Flow":
            return { ...EMPTY_STYLE, markerEnd: "generic-arrow", dash: "4,2" };
        case "ar3_Influence":
            return { ...EMPTY_STYLE, markerEnd: "generic-arrow-open", dash: "4,2" };
        case "ar3_Realization":
            return { ...EMPTY_STYLE, markerEnd: "block-arrow", dash: "2,2" };
        case "ar3_Serving":
            return { ...EMPTY_STYLE, markerEnd: "generic-arrow-open" };
        case "ar3_Specialization":
            return { ...EMPTY_STYLE, markerEnd: "block-arrow" };
        case "ar3_Triggering":
            return { ...EMPTY_STYLE, markerEnd: "generic-arrow" };
        case "lineage_relation":
            return { ...EMPTY_STYLE, markerEnd: "generic-arrow" };
        default:
            return EMPTY_STYLE;
    }
}

/**
 * The node's basic shape (LDG-33), or the plain rectangle for a type the
 * table does not name (the LDG-13 fallback, unchanged).
 * @param type the element's `@xsi_type`, or the view node's own when it
 *     references no element
 */
export function ar3NodeShape(type: string): Ar3NodeShape {
    return AR3_SHAPES[type] ?? { kind: "rectangle", showIcon: true, showName: true };
}

/**
 * The node's fill class (LDG-34): the layer of `archimate3.scss`, the lineage
 * fill of `lineage.scss`, or the empty string for a type neither table names.
 * @param type the element's `@xsi_type`
 */
export function ar3Class(type: string): string {
    return AR3_CLASSES[type] ?? "";
}

/**
 * The type's glyph (LDG-35), or null when no table names it — the legacy's
 * icon component drew nothing for a missing `definitions` entry.
 * @param type the element's `@xsi_type`
 */
export function ar3Icon(type: string): Ar3Icon | null {
    return AR3_ICONS[type] ?? null;
}

/**
 * The node path of a basic shape, the legacy `basicShapes` and the archimate
 * file's two own functions, verbatim.
 * @param kind the shape kind
 * @param width the node's `@w`
 * @param height the node's `@h`
 */
export function nodePath(kind: Ar3ShapeKind, width: number, height: number): string {
    switch (kind) {
        case "rounded":
            return `m12,0h${width - 24}a12,12,0,0,1,12,12v${height - 24}a12,12,0,0,1,-12,12h-${
                width - 24
            }a12,12,0,0,1,-12,-12v-${height - 24}a12,12,0,0,1,12,-12z`;
        case "ellipse":
            return `m0,0a${width / 2},${height / 2},0,0,0,${width},${height}a${width / 2},${height / 2},0,0,0,-${width},-${height}z`;
        case "octagon":
            return `m12,0h${width - 24}l12,12v${height - 24}l-12,12h-${width - 24}l-12,-12v-${height - 24}l12,-12z`;
        case "grouping":
            return `m0,0h${width / 2}v18h-${width / 2}z` + `m0,18h${width}v${height - 18}h-${width}z`;
        case "waved":
            return `m0,0v${height - 6}q${width / 4},12,${width / 2},0t${width / 2},0v-${height - 6}z`;
        case "rectangle":
        default:
            return `m0,0h${width}v${height}h-${width}z`;
    }
}
