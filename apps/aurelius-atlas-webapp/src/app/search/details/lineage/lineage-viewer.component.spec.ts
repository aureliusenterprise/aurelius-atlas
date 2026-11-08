import { ComponentFixture, TestBed } from "@angular/core/testing";
import { describe, expect, it } from "vitest";

import fixture from "../../../../../tests/fixtures/lineage-graph.extract.json";
import { parseAr3Model, type Ar3Model } from "./parse-ar3";
import { LineageViewer } from "./lineage-viewer.component";
import { ZOOM_SCALE_EXTENT } from "./lineage-shapes";

/**
 * The viewer over the shipped chain's document (LDG-12..LDG-18, DD-391):
 * the fixture is the vendored 8.2 scenario extract — three nodes at
 * x=0/320/640, y=0, 120x55, joined by two unnamed relations — so every
 * expected geometry below is that document's own.
 */

/** The vendored model, parsed (LDG-11's output feeds the viewer). */
const MODEL: Ar3Model = parseAr3Model(fixture.model);

/** The fixture's element ids (the fake guids of the 8.2 document). */
const DATASET_ONE = "00000000-0000-4000-8000-000000000001";
const PROCESS = "00000000-0000-4000-8000-000000000002";

function setup(model: Ar3Model = MODEL): {
    viewer: LineageViewer;
    created: ComponentFixture<LineageViewer>;
    compiled: HTMLElement;
} {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ imports: [LineageViewer] });
    const created = TestBed.createComponent(LineageViewer);
    created.componentRef.setInput("model", model);
    // Two passes: the first creates the view, the second lets the zoom
    // effect (a viewChild reader) run.
    created.detectChanges();
    created.detectChanges();
    return { viewer: created.componentInstance, created, compiled: created.nativeElement as HTMLElement };
}

/** The component's own style block — the pixels LDG-13/14/17/18 pin. */
function styleBlock(): string {
    const def = (LineageViewer as unknown as { ɵcmp: { styles?: string[] } }).ɵcmp;
    return (def.styles ?? []).join("\n");
}

/** A shifted copy of the fixture: every node moved by (dx, dy). */
function shiftModel(dx: number, dy: number): Ar3Model {
    const document = JSON.parse(fixture.model) as Record<string, unknown>;
    const ar3 = document["ar3_model"] as Record<string, unknown>;
    const views = ar3["ar3_views"] as Record<string, unknown>;
    const diagrams = views["ar3_diagrams"] as Record<string, unknown[]>;
    const view = diagrams["ar3_view"][0] as Record<string, unknown>;
    const nodes = view["ar3_node"] as Record<string, unknown>[];
    for (const node of nodes) {
        node["@x"] = Number(node["@x"]) + dx;
        node["@y"] = Number(node["@y"]) + dy;
    }
    return parseAr3Model(JSON.stringify(document));
}

/**
 * The real jsdom window behind the test environment's patched global.
 * d3-zoom attaches its drag listeners to `event.view`, and jsdom's event
 * constructors reject the patched global as a view ("not of type Window"),
 * so the pointer events below must name this window — dispatches through
 * the patched `window` still reach listeners bound here (it forwards them).
 * Reached the way jsdom itself crosses realms: the document's impl object
 * holds its global, whose global proxy passes jsdom's window check.
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

/**
 * d3-zoom reads the non-viewBox SVG's width/height (baseVal) for its
 * default extent; jsdom never implements those SVG properties, so hand the
 * element what d3 expects before the first gesture.
 */
function stubSvgExtent(svg: SVGSVGElement): void {
    Object.defineProperty(svg, "width", { value: { baseVal: { value: 800 } } });
    Object.defineProperty(svg, "height", { value: { baseVal: { value: 600 } } });
}

describe("LineageViewer (LDG-12..LDG-18)", () => {
    it("LDG-12: the first view draws — every node before every connection", () => {
        const { compiled } = setup();

        const nodes = [...compiled.querySelectorAll("svg > g > g > g.node")];
        const connections = [...compiled.querySelectorAll("svg > g > g > g.connection")];
        expect(nodes).toHaveLength(3);
        expect(connections).toHaveLength(2);

        // Nodes render first, connections on top (LDG-12): in the one
        // drawing group, the last node precedes the first connection.
        const drawn = [...compiled.querySelectorAll("svg > g > g > g")];
        const nodeIndices = nodes.map((node) => drawn.indexOf(node));
        const connectionIndices = connections.map((connection) => drawn.indexOf(connection));
        expect(Math.max(...nodeIndices)).toBeLessThan(Math.min(...connectionIndices));

        // Each node is the rectangle path from its x,y,w,h — the legacy
        // basicShapes.rectangle over the fixture's 120x55.
        const shapes = [...compiled.querySelectorAll("g.node > path.node-shape")];
        expect(shapes.map((shape) => shape.getAttribute("d"))).toEqual([
            "m0,0h120v55h-120z",
            "m0,0h120v55h-120z",
            "m0,0h120v55h-120z",
        ]);
    });

    it("LDG-15: the group normalises to the view's bounds", () => {
        const { compiled } = setup();

        // The bounds group: -minX/-minY over all node positions (the legacy
        // ModelviewService); the fixture starts at 0,0, and each node rides
        // its raw model coordinate — the group's shift seats them at the
        // origin.
        expect(compiled.querySelector("svg > g > g")?.getAttribute("transform")).toBe("translate(0, 0)");
        expect([...compiled.querySelectorAll("g.node")].map((node) => node.getAttribute("transform"))).toEqual([
            "translate(0, 0)",
            "translate(320, 0)",
            "translate(640, 0)",
        ]);

        // A model laid out at any origin fits its container: shifted by
        // (1000, 500) the group takes the negated minimum and the nodes
        // (raw coordinates, so they keep aligning with the connection
        // paths) render back at 0/320/640 on screen.
        const shifted = setup(shiftModel(1000, 500));
        expect(shifted.compiled.querySelector("svg > g > g")?.getAttribute("transform")).toBe("translate(-1000, -500)");
        expect([...shifted.compiled.querySelectorAll("g.node")].map((node) => node.getAttribute("transform"))).toEqual([
            "translate(1000, 500)",
            "translate(1320, 500)",
            "translate(1640, 500)",
        ]);

        // The legacy's 50vh drawing area.
        expect(styleBlock()).toContain("50vh");
    });

    it("LDG-13: fills, classes, and the vendored icons per type", () => {
        const { compiled } = setup();
        const styles = styleBlock();

        // The two lineage fills and the node stroke, verbatim from the
        // legacy lineage.scss / modelview-node.component.scss.
        expect(styles).toContain("fill: hsl(240, 100%, 95%)");
        expect(styles).toContain("fill: hsl(171, 100%, 95%)");
        expect(styles).toContain("stroke: #a0a0a0");
        expect(styles).toContain("stroke-width: 2px");

        // The type classes ride the node groups — the referenced element's
        // type (dataset, process, dataset).
        expect(
            [...compiled.querySelectorAll("g.node")].map((node) =>
                node.classList.contains("dataset") ? "dataset" : node.classList.contains("process") ? "process" : "",
            ),
        ).toEqual(["dataset", "process", "dataset"]);

        // Each node carries its 16x16 icon — the legacy archimate-icon
        // paths (the database card and the gear), floated right, the icon
        // fills blue for a dataset and #00d1b2 for a process (LDG-13).
        const iconPaths = [...compiled.querySelectorAll("g.node .node-icon path")];
        expect(iconPaths).toHaveLength(3);
        expect(iconPaths[0].getAttribute("d")).toContain("M 14.492 1");
        expect(iconPaths[1].getAttribute("d")).toContain("M 15.4545 10.0102");
        expect(styles).toContain("float: right");
        expect(styles).toContain("fill: blue");
        expect(styles).toContain("fill: #00d1b2");

        // The names inside the rectangles (LDG-11's display name).
        expect([...compiled.querySelectorAll("g.node .node-text")].map((text) => text.textContent?.trim())).toEqual([
            "Ingest Topic",
            "Load Job",
            "Sales Table",
        ]);
    });

    it("LDG-14: the connection path and the arrow marker", () => {
        const { compiled } = setup();

        // The edge-anchored straightest line: the dataset's right edge
        // (x=120, centre y=27.5) to the process's left edge (x=320) — the
        // fixture's two rectangles with no bendpoints.
        const paths = [...compiled.querySelectorAll("g.connection path.connection-path")];
        expect(paths.map((path) => path.getAttribute("d"))).toEqual(["M120,27.5L320,27.5", "M440,27.5L640,27.5"]);

        // Every connection ends in the generic-arrow marker; the one defs
        // marker is the legacy's ported geometry.
        expect(paths[0].getAttribute("marker-end")).toBe("url(#generic-arrow)");
        const marker = compiled.querySelector("defs marker[id='generic-arrow']");
        expect(marker?.getAttribute("refX")).toBe("7");
        expect(marker?.getAttribute("refY")).toBe("3");
        expect(marker?.querySelector("path")?.getAttribute("d")).toBe("M0,0l7,3l-7,3z");

        // The shipped relation names are empty, so no label draws (LDG-14's
        // "when present").
        expect(compiled.querySelectorAll("textPath")).toHaveLength(0);

        // The path style: none-fill black (the legacy's .connection-path).
        expect(styleBlock()).toContain("fill: none;");
        expect(styleBlock()).toContain("stroke: black;");
    });

    it("LDG-16: pan and zoom ride d3-zoom at [0.5, 3]; resetZoom restores", async () => {
        const { viewer, compiled } = setup();

        // The legacy SVGZoomDirective's extent, verbatim.
        expect(ZOOM_SCALE_EXTENT).toEqual([0.5, 3]);

        const svg = compiled.querySelector("svg") as SVGSVGElement;
        const zoomGroup = compiled.querySelector("svg > g") as SVGGElement;

        // jsdom lacks the SVG geometry d3 reads (the default extent's
        // width/height baseVal, getScreenCTM), so hand it a fixed drawing
        // box and origin — pointer coordinates then equal clientX/clientY.
        stubSvgExtent(svg);
        Object.defineProperty(svg, "getBoundingClientRect", {
            value: () => ({ left: 0, top: 0, right: 800, bottom: 600, width: 800, height: 600, x: 0, y: 0 }),
        });

        // d3 attaches the drag's move/up listeners to event.view and jsdom
        // rejects the patched test window as a view: build the pointer
        // events through the real jsdom window (see eventWindow()).
        const view = eventWindow();
        const eventCtor = (view as unknown as { MouseEvent: typeof MouseEvent }).MouseEvent;
        const wheelCtor = (view as unknown as { WheelEvent: typeof WheelEvent }).WheelEvent;

        // Drag pans: a mouse drag translates the zoom group (the transform
        // d3 hands out, applied to the group as in the legacy directive).
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

        // resetZoom() restores the identity — the seam 7.22d's toolbar calls.
        const previous = viewer.resetZoom();
        expect(previous.k).toBe(1);
        expect(zoomGroup.getAttribute("transform")).toBe("translate(0,0) scale(1)");

        // The wheel zooms, and the extent clamps: one huge wheel-in stops
        // at the ceiling of 3.
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

        // d3-drag clears its post-drag click guard on a setTimeout(0); let
        // it run so a later test's dispatched clicks are not swallowed.
        await new Promise((resolve) => setTimeout(resolve, 0));
    });

    it("LDG-17: a click selects the concept, the same click clears it", () => {
        const { viewer, created, compiled } = setup();
        const emitted: (string | null)[] = [];
        viewer.selectedConcept.subscribe((concept) => emitted.push(concept));

        // A bare dispatched click needs a change-detection pass for the
        // class bindings to follow the signal.
        const click = (element: Element) => {
            element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
            created.detectChanges();
        };

        const nodes = [...compiled.querySelectorAll<SVGGElement>("g.node")];
        const connections = [...compiled.querySelectorAll<SVGGElement>("g.connection")];
        const processNode = nodes[1];

        // The click selects the referenced element (the legacy's `ref ?? id`
        // — the element guid, not the view-node id).
        expect(processNode.getAttribute("data-concept")).toBe(PROCESS);
        click(processNode);
        expect(processNode.classList.contains("is-selected")).toBe(true);

        // A connection click moves the selection to its relation — the
        // viewer holds ONE selected concept (the legacy's selectedEntity).
        expect(connections[0].getAttribute("data-concept")).toBe("rel-1");
        click(connections[0]);
        expect(connections[0].classList.contains("is-selected")).toBe(true);
        expect(processNode.classList.contains("is-selected")).toBe(false);

        // Clicking the same concept again clears it.
        click(connections[0]);
        expect(connections[0].classList.contains("is-selected")).toBe(false);

        expect(emitted).toEqual([PROCESS, "rel-1", null]);

        // The selection stroke (LDG-17): the legacy's #40e0d0, on both the
        // node and the connection.
        expect(styleBlock()).toContain("stroke: #40e0d0");
    });

    it("LDG-18: the opened guid's node carries the highlight", () => {
        const { created, compiled } = setup();

        // No highlight input: nothing highlights.
        expect(compiled.querySelectorAll("g.node.is-highlighted")).toHaveLength(0);

        // The process guid highlights its node — by the element id the view
        // node references (LDG-18).
        created.componentRef.setInput("highlightedGuid", PROCESS);
        created.detectChanges();
        const highlighted = [...compiled.querySelectorAll("g.node.is-highlighted")];
        expect(highlighted).toHaveLength(1);
        expect(highlighted[0].classList.contains("process")).toBe(true);

        // The first dataset's guid highlights the first node.
        created.componentRef.setInput("highlightedGuid", DATASET_ONE);
        created.detectChanges();
        expect(compiled.querySelectorAll("g.node.is-highlighted")).toHaveLength(1);
        expect(compiled.querySelector("g.node.is-highlighted.dataset")).toBeTruthy();

        // A guid the view does not carry highlights nothing.
        created.componentRef.setInput("highlightedGuid", "no-such-guid");
        created.detectChanges();
        expect(compiled.querySelectorAll("g.node.is-highlighted")).toHaveLength(0);

        // The highlight stroke (LDG-18): the legacy's hsl(141, 53%, 53%).
        expect(styleBlock()).toContain("stroke: hsl(141, 53%, 53%)");
    });
});
