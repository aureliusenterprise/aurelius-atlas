import { ComponentFixture, TestBed } from "@angular/core/testing";
import { describe, expect, it } from "vitest";

import { LineageDiagram } from "./lineage-diagram.component";
import { AR3_ICON_FILLS, AR3_NODE_FILLS, NO_RELATION_OPTIONS } from "./archimate-shapes";
import { BOUNDS_INSET, GENERIC_ARROW, LINEAGE_ICON_PATHS } from "./lineage-shapes";
import type { Ar3DiagramModel, Ar3View } from "./ar3-types";

/**
 * The canvas over hand-built documents (LDG-12..18, LDG-33..36): the
 * components in `aurelius-atlas-ui` carry no reader, so the models below are
 * the canvas's own input shape (`Ar3DiagramModel`/`Ar3View`) — the shipped
 * chain's geometry (three nodes at x=0/320/640, 120x55, two unnamed
 * relations) and an archimate document, both stated literally so every
 * expected position below is the fixture's own.
 */

const DATASET_ONE = "ds-1";
const PROCESS = "pr-1";

/** The shipped lineage chain as the canvas reads it (LDG-11's output shape). */
function lineageModel(dx = 0, dy = 0): Ar3DiagramModel {
    const view: Ar3View = {
        id: "v1",
        name: "Lineage",
        nodes: [
            {
                id: "n1",
                ref: DATASET_ONE,
                label: "",
                displayName: "Ingest Topic",
                x: 0 + dx,
                y: 0 + dy,
                width: 120,
                height: 55,
            },
            {
                id: "n2",
                ref: PROCESS,
                label: "",
                displayName: "Load Job",
                x: 320 + dx,
                y: 0 + dy,
                width: 120,
                height: 55,
            },
            {
                id: "n3",
                ref: "ds-2",
                label: "",
                displayName: "Sales Table",
                x: 640 + dx,
                y: 0 + dy,
                width: 120,
                height: 55,
            },
        ],
        connections: [
            { id: "c1", ref: "rel-1", source: "n1", target: "n2", displayName: "", bendpoints: [] },
            { id: "c2", ref: "rel-2", source: "n2", target: "n3", displayName: "", bendpoints: [] },
        ],
    };
    return {
        elements: new Map([
            [DATASET_ONE, { type: "lineage_dataset" }],
            [PROCESS, { type: "lineage_process" }],
            ["ds-2", { type: "lineage_dataset" }],
        ]),
        relations: new Map([
            ["rel-1", { id: "rel-1", type: "lineage_relation", options: NO_RELATION_OPTIONS }],
            ["rel-2", { id: "rel-2", type: "lineage_relation", options: NO_RELATION_OPTIONS }],
        ]),
        views: [view],
    };
}

/** An archimate document (the shape a model-extraction produces, DD-418). */
function archimateModel(): Ar3DiagramModel {
    const view: Ar3View = {
        id: "v1",
        name: "The View",
        nodes: [
            { id: "n-goal", ref: "goal", label: "", displayName: "Reduce Cost", x: 320, y: 0, width: 120, height: 80 },
            { id: "n-junction", ref: "junction", label: "", displayName: "", x: 0, y: 200, width: 14, height: 14 },
            { id: "n-data", ref: "data", label: "", displayName: "Invoices", x: 0, y: 0, width: 120, height: 80 },
        ],
        connections: [
            { id: "c-flow", ref: "flow", source: "n-data", target: "n-goal", displayName: "", bendpoints: [] },
            { id: "c-access", ref: "access", source: "n-data", target: "n-junction", displayName: "", bendpoints: [] },
            { id: "c-lost", ref: null, source: "n-junction", target: "n-goal", displayName: "", bendpoints: [] },
        ],
    };
    return {
        elements: new Map([
            ["goal", { type: "ar3_Goal" }],
            ["junction", { type: "ar3_AndJunction" }],
            ["data", { type: "ar3_DataObject" }],
        ]),
        relations: new Map([
            ["flow", { id: "flow", type: "ar3_Flow", options: NO_RELATION_OPTIONS }],
            ["access", { id: "access", type: "ar3_Access", options: { accessType: "ReadWrite", isDirected: "" } }],
        ]),
        views: [view],
    };
}

/** Mount the canvas with the given model/view (the caller reads the DOM). */
function setup(
    model: Ar3DiagramModel,
    view?: Ar3View,
): {
    diagram: LineageDiagram;
    created: ComponentFixture<LineageDiagram>;
    compiled: HTMLElement;
} {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ imports: [LineageDiagram] });
    const created = TestBed.createComponent(LineageDiagram);
    created.componentRef.setInput("model", model);
    created.componentRef.setInput("view", view ?? model.views[0] ?? null);
    // Two passes: the first creates the view, the second runs the zoom effect.
    created.detectChanges();
    created.detectChanges();
    return { diagram: created.componentInstance, created, compiled: created.nativeElement as HTMLElement };
}

/** The canvas's own style block — the pixels LDG-13/14/34/35/36 pin. */
function styleBlock(): string {
    const def = (LineageDiagram as unknown as { ɵcmp: { styles?: string[] } }).ɵcmp;
    return (def.styles ?? []).join("\n");
}

/**
 * The real jsdom window behind the test environment's patched global.
 * d3-zoom attaches its drag listeners to `event.view`, and jsdom's event
 * constructors reject the patched global as a view, so the pointer events
 * below name this window.
 */
function eventWindow(): EventTarget {
    const implSymbol = Object.getOwnPropertySymbols(document).find((symbol) => String(symbol) === "Symbol(impl)");
    const impl = implSymbol
        ? (document as unknown as Record<symbol, { _defaultView?: { _globalProxy?: unknown } }>)[implSymbol]
        : undefined;
    const realWindow = impl?._defaultView?._globalProxy;
    if (typeof (realWindow as EventTarget | undefined)?.addEventListener !== "function") {
        throw new Error("the jsdom window behind the test environment is not reachable");
    }
    return realWindow as EventTarget;
}

/** jsdom never implements the SVG width/height baseVal d3 reads — hand them over. */
function stubSvgExtent(svg: SVGSVGElement): void {
    Object.defineProperty(svg, "width", { value: { baseVal: { value: 800 } } });
    Object.defineProperty(svg, "height", { value: { baseVal: { value: 600 } } });
    Object.defineProperty(svg, "getBoundingClientRect", {
        value: () => ({ left: 0, top: 0, right: 800, bottom: 600, width: 800, height: 600, x: 0, y: 0 }),
    });
}

describe("LineageDiagram (LDG-12..LDG-18)", () => {
    it("LDG-12: the view draws — every node before every connection", () => {
        const { compiled } = setup(lineageModel());

        const nodes = [...compiled.querySelectorAll("svg > g > g > g.node")];
        const connections = [...compiled.querySelectorAll("svg > g > g > g.connection")];
        expect(nodes).toHaveLength(3);
        expect(connections).toHaveLength(2);

        // Nodes render first, connections on top (LDG-12).
        const drawn = [...compiled.querySelectorAll("svg > g > g > g")];
        const nodeIndices = nodes.map((node) => drawn.indexOf(node));
        const connectionIndices = connections.map((connection) => drawn.indexOf(connection));
        expect(Math.max(...nodeIndices)).toBeLessThan(Math.min(...connectionIndices));

        const shapes = [...compiled.querySelectorAll("g.node > path.node-shape")];
        expect(shapes.map((shape) => shape.getAttribute("d"))).toEqual([
            "m0,0h120v55h-120z",
            "m0,0h120v55h-120z",
            "m0,0h120v55h-120z",
        ]);
    });

    it("LDG-15/DD-417: the group normalises to the bounds plus the inset", () => {
        const { compiled } = setup(lineageModel());
        expect(compiled.querySelector("svg > g > g")?.getAttribute("transform")).toBe("translate(20, 20)");
        expect([...compiled.querySelectorAll("g.node")].map((node) => node.getAttribute("transform"))).toEqual([
            "translate(0, 0)",
            "translate(320, 0)",
            "translate(640, 0)",
        ]);

        // A shifted model: the group re-seats it at the inset, the nodes ride
        // their raw coordinates.
        const shifted = setup(lineageModel(-1000, -500));
        expect(shifted.compiled.querySelector("svg > g > g")?.getAttribute("transform")).toBe(
            `translate(${BOUNDS_INSET + 1000}, ${BOUNDS_INSET + 500})`,
        );
    });

    it("LDG-13: fills, classes, and the vendored icons per type", () => {
        const { compiled } = setup(lineageModel());
        const styles = styleBlock();

        expect(styles).toContain("fill: hsl(240, 100%, 95%)");
        expect(styles).toContain("fill: hsl(171, 100%, 95%)");
        expect(styles).toContain("stroke: #a0a0a0");

        expect(
            [...compiled.querySelectorAll("g.node")].map((node) =>
                node.classList.contains("dataset") ? "dataset" : node.classList.contains("process") ? "process" : "",
            ),
        ).toEqual(["dataset", "process", "dataset"]);

        const iconPaths = [...compiled.querySelectorAll("g.node .node-icon path")];
        expect(iconPaths).toHaveLength(3);
        expect(iconPaths[0].getAttribute("d")).toBe(LINEAGE_ICON_PATHS.dataset);
        expect(iconPaths[1].getAttribute("d")).toBe(LINEAGE_ICON_PATHS.process);
        expect(styles).toContain("float: right");
        expect(styles).toContain("fill: blue");
        expect(styles).toContain("fill: #00d1b2");

        expect([...compiled.querySelectorAll("g.node .node-text")].map((text) => text.textContent?.trim())).toEqual([
            "Ingest Topic",
            "Load Job",
            "Sales Table",
        ]);
    });

    it("LDG-14: the connection path and the arrow marker", () => {
        const { compiled } = setup(lineageModel());
        const paths = [...compiled.querySelectorAll("g.connection path.connection-path")];
        expect(paths.map((path) => path.getAttribute("d"))).toEqual(["M120,27.5L320,27.5", "M440,27.5L640,27.5"]);

        expect(paths[0].getAttribute("marker-end")).toBe("url(#generic-arrow)");
        const marker = compiled.querySelector("defs marker[id='generic-arrow']");
        expect(marker?.getAttribute("refX")).toBe(String(GENERIC_ARROW.refX));
        expect(marker?.getAttribute("refY")).toBe(String(GENERIC_ARROW.refY));
        expect(marker?.querySelector("path")?.getAttribute("d")).toBe(GENERIC_ARROW.path);
        expect(compiled.querySelectorAll("textPath")).toHaveLength(0);
    });

    it("DD-409: every connection carries a wide transparent hit path", () => {
        const { compiled } = setup(lineageModel());
        const hits = [...compiled.querySelectorAll("g.connection path.connection-hit")];
        expect(hits.map((path) => path.getAttribute("d"))).toEqual(["M120,27.5L320,27.5", "M440,27.5L640,27.5"]);
        expect(hits[0]?.closest("g.connection")?.getAttribute("data-concept")).toBe("rel-1");
        expect(styleBlock()).toMatch(/\.connection-hit[^{]*\{[^}]*stroke:\s*transparent/);
        expect(styleBlock()).toMatch(/\.connection-hit[^{]*\{[^}]*pointer-events:\s*stroke/);
    });

    it("DD-408: the drawing carries no font-family of its own", () => {
        const { compiled } = setup(lineageModel());
        expect(styleBlock()).not.toMatch(/font-family/);
        expect(styleBlock()).toMatch(/\.lineage-svg[^{]*\{[^}]*font-size:\s*12px/);
        expect(compiled.querySelector("svg.lineage-svg")?.getAttribute("style")).toBeNull();
    });

    it("LDG-16: pan and zoom ride d3-zoom at [0.5, 3]; resetZoom restores", async () => {
        const { diagram, compiled } = setup(lineageModel());

        const svg = compiled.querySelector("svg.lineage-svg") as SVGSVGElement;
        const zoomGroup = compiled.querySelector("svg.lineage-svg > g") as SVGGElement;
        stubSvgExtent(svg);

        const view = eventWindow();
        const eventCtor = (view as unknown as { MouseEvent: typeof MouseEvent }).MouseEvent;
        const wheelCtor = (view as unknown as { WheelEvent: typeof WheelEvent }).WheelEvent;

        svg.dispatchEvent(
            new eventCtor("mousedown", {
                bubbles: true,
                cancelable: true,
                view: view as Window,
                clientX: 10,
                clientY: 10,
            }),
        );
        view.dispatchEvent(
            new eventCtor("mousemove", {
                bubbles: true,
                cancelable: true,
                view: view as Window,
                clientX: 50,
                clientY: 30,
            }),
        );
        view.dispatchEvent(
            new eventCtor("mouseup", {
                bubbles: true,
                cancelable: true,
                view: view as Window,
                clientX: 50,
                clientY: 30,
            }),
        );
        expect(zoomGroup.getAttribute("transform")).toBe("translate(40,20) scale(1)");

        const previous = diagram.resetZoom();
        expect(previous.k).toBe(1);
        expect(zoomGroup.getAttribute("transform")).toBe("translate(0,0) scale(1)");

        svg.dispatchEvent(
            new wheelCtor("wheel", {
                deltaY: -10000,
                clientX: 0,
                clientY: 0,
                bubbles: true,
                cancelable: true,
                view: view as Window,
            }),
        );
        expect(zoomGroup.getAttribute("transform")).toBe("translate(0,0) scale(3)");

        await new Promise((resolve) => setTimeout(resolve, 0));
    });

    it("LDG-17: a click emits the concept; the selected input paints it", () => {
        const { created, compiled } = setup(lineageModel());
        const emits: string[] = [];
        created.componentInstance.conceptSelected.subscribe((concept) => emits.push(concept));

        const nodes = [...compiled.querySelectorAll<SVGGElement>("g.node")];
        const connections = [...compiled.querySelectorAll<SVGGElement>("g.connection")];
        const processNode = nodes[1];

        // A click reports the concept (`ref ?? id`) — the element guid, not
        // the view-node id. The canvas owns no state; the caller answers.
        expect(processNode.getAttribute("data-concept")).toBe(PROCESS);
        processNode.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        expect(emits).toEqual([PROCESS]);

        // The selected input styles the concept (LDG-17's stroke, both a node
        // and a connection).
        created.componentRef.setInput("selected", "rel-1");
        created.detectChanges();
        expect(connections[0].classList.contains("is-selected")).toBe(true);
        expect(processNode.classList.contains("is-selected")).toBe(false);
        expect(styleBlock()).toContain("stroke: #40e0d0");
    });

    it("LDG-18: the highlighted guid's node carries the highlight", () => {
        const { created, compiled } = setup(lineageModel());
        expect(compiled.querySelectorAll("g.node.is-highlighted")).toHaveLength(0);

        created.componentRef.setInput("highlightedGuid", PROCESS);
        created.detectChanges();
        const highlighted = [...compiled.querySelectorAll("g.node.is-highlighted")];
        expect(highlighted).toHaveLength(1);
        expect(highlighted[0].classList.contains("process")).toBe(true);

        created.componentRef.setInput("highlightedGuid", "no-such-guid");
        created.detectChanges();
        expect(compiled.querySelectorAll("g.node.is-highlighted")).toHaveLength(0);

        expect(styleBlock()).toContain("stroke: hsl(141, 53%, 53%)");
    });

    it("LDG-14/LDG-36: the background rect is the save-excluded ground", () => {
        const { compiled } = setup(lineageModel());
        const backdrop = compiled.querySelector("svg.lineage-svg > rect.background");
        expect(backdrop?.getAttribute("width")).toBe("100%");
        expect(backdrop?.hasAttribute("data-html2canvas-ignore")).toBe(true);
        expect(styleBlock()).toMatch(/\.background[^{]*\{[^}]*fill:\s*white/);
    });
});

describe("LineageDiagram over an archimate document (LDG-33..LDG-36, DD-418)", () => {
    it("LDG-36: the defs carry all eight legacy markers, dash-proof", () => {
        const { compiled } = setup(archimateModel());
        const markers = [...compiled.querySelectorAll("defs marker")];
        expect(markers.map((marker) => marker.id)).toEqual([
            "access-read",
            "aggregation",
            "assignment-start",
            "association",
            "block-arrow",
            "composition",
            "generic-arrow",
            "generic-arrow-open",
        ]);
        const closed = markers.find((marker) => marker.id === "generic-arrow");
        expect(closed?.querySelector("path")?.getAttribute("stroke-dasharray")).toBe("999");
        expect(closed?.querySelector("path")?.style.fill).toBe("#000000");
        expect(closed?.querySelector("path")?.style.stroke).toBe("");
        const open = markers.find((marker) => marker.id === "generic-arrow-open");
        expect(open?.querySelector("path")?.style.fill).toBe("none");
        expect(open?.querySelector("path")?.style.stroke).toBe("#000000");
    });

    it("LDG-33/LDG-34/LDG-35: an archimate node draws its shape, fill class, and glyph", () => {
        const { compiled } = setup(archimateModel());
        const goal = compiled.querySelector("g.node[data-concept='goal']") as SVGGElement;
        expect(goal.classList.contains("motivation")).toBe(true);
        expect(goal.querySelector("path.node-shape")?.getAttribute("d")).toBe(
            "m12,0h96l12,12v56l-12,12h-96l-12,-12v-56l12,-12z",
        );
        expect(goal.querySelector(".node-icon path")?.getAttribute("d")).toMatch(/^M 6\.1538 8 a/);
        expect(goal.querySelector(".node-icon path")?.classList.contains("motivation")).toBe(true);
        expect(goal.querySelector(".node-text")?.textContent?.trim()).toBe("Reduce Cost");

        const data = compiled.querySelector("g.node[data-concept='data']") as SVGGElement;
        expect(data.classList.contains("application")).toBe(true);
        expect(data.querySelector("path.node-shape")?.getAttribute("d")).toBe("m0,0h120v80h-120z");
        expect(data.querySelector(".node-icon path")?.classList.contains("application")).toBe(true);
    });

    it("LDG-33: a junction is an unlabelled, uninked ellipse", () => {
        const { compiled } = setup(archimateModel());
        const junction = compiled.querySelector("g.node[data-concept='junction']") as SVGGElement;
        expect(junction.classList.contains("and")).toBe(true);
        expect(junction.querySelector("path.node-shape")?.getAttribute("d")).toBe(
            "m0,0a7,7,0,0,0,14,14a7,7,0,0,0,-14,-14z",
        );
        expect(junction.querySelector(".node-icon")).toBeNull();
        expect(junction.querySelector(".node-text")).toBeNull();
    });

    it("LDG-36: each connection rides its relation type's markers and dash", () => {
        const { compiled } = setup(archimateModel());
        const pathFor = (concept: string) =>
            compiled.querySelector(`g.connection[data-concept='${concept}'] path.connection-path`) as SVGPathElement;

        const flow = pathFor("flow");
        expect(flow.getAttribute("marker-end")).toBe("url(#generic-arrow)");
        expect(flow.getAttribute("marker-start")).toBeNull();
        expect(flow.style.strokeDasharray).toBe("4,2");

        const access = pathFor("access");
        expect(access.getAttribute("marker-start")).toBe("url(#access-read)");
        expect(access.getAttribute("marker-end")).toBe("url(#generic-arrow-open)");
        expect(access.style.strokeDasharray).toBe("2,2");

        const lost = pathFor("c-lost");
        expect(lost.getAttribute("marker-start")).toBeNull();
        expect(lost.getAttribute("marker-end")).toBeNull();
        expect(lost.style.strokeDasharray).toBe("");
    });

    it("LDG-34/LDG-35: the shipped style block carries every fill of the tables", () => {
        const styles = styleBlock();
        expect(styles).toContain("fill: hsl(240, 100%, 95%)");
        const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, (char) => `\\${char}`);
        for (const table of [AR3_NODE_FILLS, AR3_ICON_FILLS]) {
            for (const rule of table.match(/\.[\w.-]+[^{]*\{[^}]*\}/g) ?? []) {
                const selector = rule.slice(0, rule.indexOf("{")).trim();
                const declarations = rule
                    .slice(rule.indexOf("{") + 1, rule.lastIndexOf("}"))
                    .split(";")
                    .map((declaration) => declaration.trim())
                    .filter((declaration) => declaration !== "");
                for (const declaration of declarations) {
                    const property = declaration.slice(0, declaration.indexOf(":")).trim();
                    const value = declaration
                        .slice(declaration.indexOf(":") + 1)
                        .trim()
                        .replace(/;$/, "");
                    const selectorPattern =
                        "(?<![\\w-])" +
                        selector
                            .split(/\s+/)
                            .map((part) => `${escape(part)}(?:\\[[^\\]]*\\])?`)
                            .join("\\s+");
                    const pattern = new RegExp(
                        `${selectorPattern}[^{]*\\{[^}]*${escape(property)}\\s*:\\s*${escape(value)}\\b`,
                    );
                    expect(styles, `the style block carries ${selector} { ${declaration} }`).toMatch(pattern);
                }
            }
        }
    });
});
