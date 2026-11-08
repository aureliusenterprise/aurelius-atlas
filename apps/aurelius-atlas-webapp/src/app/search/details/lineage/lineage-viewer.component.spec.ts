import { ComponentFixture, TestBed } from "@angular/core/testing";
import { Router } from "@angular/router";
import Keycloak from "keycloak-js";
import { describe, expect, it, vi } from "vitest";

import fixture from "../../../../../tests/fixtures/lineage-graph.extract.json";
import { APP_CONFIG } from "../../../tokens";
import { LineageModelState } from "./lineage-state";
import { parseAr3Model, type Ar3Model } from "./parse-ar3";
import { SaveViewAsImage } from "./save-view-as-image";
import { LineageViewer } from "./lineage-viewer.component";
import { AR3_ICON_FILLS, AR3_NODE_FILLS } from "./archimate-shapes";
import { BOUNDS_INSET, ZOOM_SCALE_EXTENT } from "./lineage-shapes";

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

/**
 * The viewer over the shared state (DD-415): the specs fill the state's
 * model directly — the fetch is the box's and the state's own specs — and a
 * Router spy watches the clicks' navigation (LDG-17's click now doubles as
 * the drawer's open, the legacy's auto-open turned route).
 */
function setup(model: Ar3Model = MODEL): {
    viewer: LineageViewer;
    state: LineageModelState;
    created: ComponentFixture<LineageViewer>;
    compiled: HTMLElement;
    navigate: ReturnType<typeof vi.spyOn>;
} {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
        imports: [LineageViewer],
        // The toolbar's save flow injects the session (Keycloak) and the
        // runtime config (LDG-31's fields) — the save itself is the save
        // spec's; here the viewer only needs the injections to resolve.
        providers: [
            { provide: Keycloak, useValue: { tokenParsed: {} } },
            { provide: APP_CONFIG, useValue: { appName: "Aurelius Atlas", appVersion: "0.0.0" } },
        ],
    });
    const state = TestBed.inject(LineageModelState);
    state.model.set(model);
    const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
    const created = TestBed.createComponent(LineageViewer);
    // Two passes: the first creates the view, the second lets the zoom
    // effect (a viewChild reader) run.
    created.detectChanges();
    created.detectChanges();
    return {
        viewer: created.componentInstance,
        state,
        created,
        compiled: created.nativeElement as HTMLElement,
        navigate,
    };
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

/**
 * An archimate document, hand-built in the shipped writer's shape (the
 * model-extraction's contract — DV-68/DTM-11): a motivation Goal (octagon,
 * icon), an And Junction (hidden icon and name), a Data Object joined to the
 * Goal by a Flow, an Access Read/Write, and a connection whose relation the
 * model does not carry (the plain line).
 */
function archimateModel(): Ar3Model {
    const document = {
        ar3_model: {
            "@identifier": "m",
            ar3_name: [{ value: "The Architecture" }],
            ar3_elements: {
                ar3_element: [
                    { "@identifier": "goal", "@xsi_type": "ar3_Goal", ar3_name: [{ value: "Reduce Cost" }] },
                    { "@identifier": "junction", "@xsi_type": "ar3_AndJunction" },
                    { "@identifier": "data", "@xsi_type": "ar3_DataObject", ar3_name: [{ value: "Invoices" }] },
                ],
            },
            ar3_relationships: {
                ar3_relationship: [
                    {
                        "@identifier": "flow",
                        "@source": "data",
                        "@target": "goal",
                        "@xsi_type": "ar3_Flow",
                    },
                    {
                        "@identifier": "access",
                        "@source": "data",
                        "@target": "junction",
                        "@xsi_type": "ar3_Access",
                        "@accessType": "ReadWrite",
                    },
                ],
            },
            ar3_views: {
                ar3_diagrams: {
                    ar3_view: [
                        {
                            "@identifier": "v1",
                            ar3_name: [{ value: "The View" }],
                            ar3_node: [
                                {
                                    "@identifier": "n-goal",
                                    "@elementRef": "goal",
                                    "@x": 320,
                                    "@y": 0,
                                    "@w": 120,
                                    "@h": 80,
                                    "@xsi_type": "ar3_Element",
                                },
                                {
                                    "@identifier": "n-junction",
                                    "@elementRef": "junction",
                                    "@x": 0,
                                    "@y": 200,
                                    "@w": 14,
                                    "@h": 14,
                                    "@xsi_type": "ar3_Element",
                                },
                                {
                                    "@identifier": "n-data",
                                    "@elementRef": "data",
                                    "@x": 0,
                                    "@y": 0,
                                    "@w": 120,
                                    "@h": 80,
                                    "@xsi_type": "ar3_Element",
                                },
                            ],
                            ar3_connection: [
                                {
                                    "@identifier": "c-flow",
                                    "@relationshipRef": "flow",
                                    "@source": "n-data",
                                    "@target": "n-goal",
                                    "@xsi_type": "ar3_Relationship",
                                },
                                {
                                    "@identifier": "c-access",
                                    "@relationshipRef": "access",
                                    "@source": "n-data",
                                    "@target": "n-junction",
                                    "@xsi_type": "ar3_Relationship",
                                },
                                {
                                    "@identifier": "c-lost",
                                    "@source": "n-junction",
                                    "@target": "n-goal",
                                    "@xsi_type": "ar3_Relationship",
                                },
                            ],
                        },
                    ],
                },
            },
        },
    };
    return parseAr3Model(JSON.stringify(document));
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
        // ModelviewService) plus the default inset (DD-417); the fixture
        // starts at 0,0, and each node rides its raw model coordinate — the
        // group's shift seats them a BOUNDS_INSET off the corner.
        expect(compiled.querySelector("svg > g > g")?.getAttribute("transform")).toBe("translate(20, 20)");
        expect([...compiled.querySelectorAll("g.node")].map((node) => node.getAttribute("transform"))).toEqual([
            "translate(0, 0)",
            "translate(320, 0)",
            "translate(640, 0)",
        ]);

        // A model laid out at any origin fits its container: shifted by
        // (1000, 500) the group takes the negated minimum plus the inset and
        // the nodes (raw coordinates, so they keep aligning with the
        // connection paths) render back at 20/340/660 on screen.
        const shifted = setup(shiftModel(1000, 500));
        expect(shifted.compiled.querySelector("svg > g > g")?.getAttribute("transform")).toBe("translate(-980, -480)");
        expect([...shifted.compiled.querySelectorAll("g.node")].map((node) => node.getAttribute("transform"))).toEqual([
            "translate(1000, 500)",
            "translate(1320, 500)",
            "translate(1640, 500)",
        ]);

        // The legacy's 50vh drawing area.
        expect(styleBlock()).toContain("50vh");
    });

    it("DD-417: the drawing sits off the top-left corner by default", () => {
        const { viewer, created, compiled } = setup();

        // The inset rides the bounds group, so the reader sees air between
        // the corner and the first node's stroke.
        const bounds = compiled.querySelector("svg.lineage-svg > g > g") as SVGGElement;
        expect(bounds.getAttribute("transform")).toBe(`translate(${BOUNDS_INSET}, ${BOUNDS_INSET})`);

        // The inset is not part of the zoom transform: panning and
        // resetting the zoom leave it in place (LDG-16's reset restores the
        // zoom group's identity, the bounds group keeps its seating).
        const svg = compiled.querySelector("svg.lineage-svg") as SVGSVGElement;
        stubSvgExtent(svg);
        const view = eventWindow();
        const eventCtor = (view as unknown as { MouseEvent: typeof MouseEvent }).MouseEvent;
        svg.dispatchEvent(
            new eventCtor("mousedown", {
                bubbles: true,
                cancelable: true,
                view: view as Window,
                clientX: 400,
                clientY: 300,
            }),
        );
        view.dispatchEvent(
            new eventCtor("mousemove", {
                bubbles: true,
                cancelable: true,
                view: view as Window,
                clientX: 460,
                clientY: 340,
            }),
        );
        view.dispatchEvent(new eventCtor("mouseup", { bubbles: true, cancelable: true, view: view as Window }));
        created.detectChanges();
        const zoomGroup = svg.querySelector("g.lineage-zoom") as SVGGElement;
        expect(zoomGroup.getAttribute("transform")).not.toBe("translate(0,0) scale(1)");

        viewer.resetZoom();
        expect(zoomGroup.getAttribute("transform")).toBe("translate(0,0) scale(1)");
        expect(bounds.getAttribute("transform")).toBe(`translate(${BOUNDS_INSET}, ${BOUNDS_INSET})`);
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

        // Every connection ends in the generic-arrow marker; the defs set
        // carries it among the legacy's eight (LDG-36).
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

    it("DD-409: every connection carries a wide transparent hit path", () => {
        const { compiled } = setup();
        // The clickable twin: same geometry as the visible path, so the
        // whole edge — not its ~1 px stroke — answers a click.
        const hits = [...compiled.querySelectorAll("g.connection path.connection-hit")];
        expect(hits.map((path) => path.getAttribute("d"))).toEqual(["M120,27.5L320,27.5", "M440,27.5L640,27.5"]);
        // It rides inside the click handler's group (the group's (click)
        // selects the relation — LDG-17's rule, unchanged).
        expect(hits[0]?.closest("g.connection")?.getAttribute("data-concept")).toBe("rel-1");
        // Transparent, wide, stroke-only — the style block's rule (the
        // legacy never had this; DD-409 fixes its nearly-unhittable edge).
        expect(styleBlock()).toMatch(/\.connection-hit[^{]*\{[^}]*stroke:\s*transparent/);
        expect(styleBlock()).toMatch(/\.connection-hit[^{]*\{[^}]*stroke-width:\s*10px/);
        expect(styleBlock()).toMatch(/\.connection-hit[^{]*\{[^}]*pointer-events:\s*stroke/);
    });

    it("DD-408: the drawing carries no font-family of its own — the app font rules", () => {
        const { compiled } = setup();
        // The legacy pinned "Segoe UI" on the svg, which set the diagram
        // apart from the rest of the app; the svg now inherits the body's
        // stack (the brand's --bulma-family-primary).
        expect(styleBlock()).not.toMatch(/font-family/);
        // The 12 px size stays — the legacy's own text scale for the drawing.
        expect(styleBlock()).toMatch(/\.lineage-svg[^{]*\{[^}]*font-size:\s*12px/);
        // Nothing on the drawing element carries a family either.
        expect(compiled.querySelector("svg.lineage-svg")?.getAttribute("style")).toBeNull();
    });

    it("LDG-16: pan and zoom ride d3-zoom at [0.5, 3]; resetZoom restores", async () => {
        const { viewer, compiled } = setup();

        // The legacy SVGZoomDirective's extent, verbatim.
        expect(ZOOM_SCALE_EXTENT).toEqual([0.5, 3]);

        // The lineage svg by class — the toolbar's fa-icon svgs are earlier
        // in the DOM now (LDG-27).
        const svg = compiled.querySelector("svg.lineage-svg") as SVGSVGElement;
        const zoomGroup = compiled.querySelector("svg.lineage-svg > g") as SVGGElement;

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

    it("LDG-17/DD-415: a click selects the concept and opens the drawer; the same click clears it", () => {
        const { state, created, compiled, navigate } = setup();

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

        expect(state.selected()).toBeNull();
        // DD-415: every click doubles as the drawer's navigation — the
        // legacy's auto-open/close, now the outlet's (the routed panel exists
        // only while its route does, so the surfaces cannot drift).
        expect(navigate.mock.calls.map((call: unknown[]) => call[0])).toEqual([
            [{ outlets: { drawer: ["lineage", "selection", PROCESS] } }],
            [{ outlets: { drawer: ["lineage", "selection", "rel-1"] } }],
            [{ outlets: { drawer: null } }],
        ]);

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

    it("LDG-27: the control column carries the named tooltips", () => {
        const { compiled } = setup();

        // The legacy's column, in order (the Browse copy is fullscreen-only,
        // LDG-28 — so four buttons ride it at rest). The header's Browse is
        // the box's (LDG-27's level-right — the box spec pins it).
        const buttons = [...compiled.querySelectorAll(".controls button")];
        expect(buttons.map((button) => button.getAttribute("title"))).toEqual([
            "View info",
            "Toggle fullscreen",
            "Reset zoom and pan",
            "Save view as image",
        ]);
        // Each is an icon button (the legacy's span.icon) — DD-397's title
        // tooltips, not the ported tooltip directive.
        for (const button of buttons) {
            expect(button.querySelector("span.icon fa-icon")).toBeTruthy();
        }
    });

    it("LDG-28: the fullscreen toggle fixes and frees the drawing region", () => {
        const { created, compiled } = setup();
        const drawing = compiled.querySelector(".lineage-drawing") as HTMLElement;

        expect(drawing.classList.contains("is-fullscreen")).toBe(false);
        // At rest the column has no Browse button (the fullscreen-only copy).
        expect(compiled.querySelector(".aurelius-lineage-browse")).toBeNull();

        compiled.querySelector<HTMLButtonElement>(".aurelius-lineage-fullscreen")?.click();
        created.detectChanges();
        expect(drawing.classList.contains("is-fullscreen")).toBe(true);
        // Fullscreen gains the Browse button (the legacy's fullscreen copy).
        expect(compiled.querySelector(".aurelius-lineage-browse")?.getAttribute("title")).toBe("Browse the model");

        compiled.querySelector<HTMLButtonElement>(".aurelius-lineage-fullscreen")?.click();
        created.detectChanges();
        expect(drawing.classList.contains("is-fullscreen")).toBe(false);

        // The legacy's fixed block, measured on this navbar (68 px).
        const styles = styleBlock();
        expect(styles).toContain("position: fixed");
        expect(styles).toContain("top: 68px");
        expect(styles).toContain("height: 100vh");

        // The overlay is opaque because of the legacy's backdrop rect (the
        // modelview-background): the white ground sits under the drawing,
        // painted before it and excluded from the html2canvas fallback.
        const backdrop = compiled.querySelector("svg.lineage-svg > rect.background");
        expect(backdrop?.getAttribute("width")).toBe("100%");
        expect(backdrop?.hasAttribute("data-html2canvas-ignore")).toBe(true);
        expect(styles).toMatch(/\.background[^{]*\{[^}]*fill:\s*white/);
    });

    it("LDG-27/DD-415: View-info routes the quickview open on the View tab", () => {
        const { created, compiled, navigate } = setup();

        compiled.querySelector<HTMLButtonElement>(".aurelius-lineage-view-info")?.click();
        created.detectChanges();

        expect(navigate).toHaveBeenLastCalledWith([{ outlets: { drawer: ["lineage", "view"] } }], { scroll: "manual" });
    });

    it("LDG-27/DD-415: the fullscreen Browse routes the quickview open on the Browse tab", () => {
        const { created, compiled, navigate } = setup();

        compiled.querySelector<HTMLButtonElement>(".aurelius-lineage-fullscreen")?.click();
        created.detectChanges();
        compiled.querySelector<HTMLButtonElement>(".aurelius-lineage-browse")?.click();
        created.detectChanges();

        expect(navigate).toHaveBeenLastCalledWith([{ outlets: { drawer: ["lineage", "browse"] } }], {
            scroll: "manual",
        });
    });

    it("LDG-29: the reset button restores the identity transform", async () => {
        const { created, compiled } = setup();

        // Pan the diagram (the LDG-16 gesture) so there is something to reset.
        const svg = compiled.querySelector("svg.lineage-svg") as SVGSVGElement;
        const zoomGroup = compiled.querySelector("svg.lineage-svg > g") as SVGGElement;
        stubSvgExtent(svg);
        Object.defineProperty(svg, "getBoundingClientRect", {
            value: () => ({ left: 0, top: 0, right: 800, bottom: 600, width: 800, height: 600, x: 0, y: 0 }),
        });
        const view = eventWindow();
        const eventCtor = (view as unknown as { MouseEvent: typeof MouseEvent }).MouseEvent;
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

        // d3-drag's post-drag click guard swallows one click until its
        // setTimeout(0) runs (the LDG-16 note) — let it pass before the
        // button's click.
        await new Promise((resolve) => setTimeout(resolve, 0));

        compiled.querySelector<HTMLButtonElement>(".aurelius-lineage-reset-zoom")?.click();
        created.detectChanges();
        expect(zoomGroup.getAttribute("transform")).toBe("translate(0,0) scale(1)");
    });

    it("LDG-29/DD-407: saving captures the current transform and never moves the view", async () => {
        const { created, compiled } = setup();

        // The save seam: record what the service is handed, draw nothing.
        const save = vi.spyOn(TestBed.inject(SaveViewAsImage), "save").mockResolvedValue(undefined);

        // Pan the diagram so a transform is in place.
        const svg = compiled.querySelector("svg.lineage-svg") as SVGSVGElement;
        const zoomGroup = compiled.querySelector("svg.lineage-svg > g") as SVGGElement;
        stubSvgExtent(svg);
        Object.defineProperty(svg, "getBoundingClientRect", {
            value: () => ({ left: 0, top: 0, right: 800, bottom: 600, width: 800, height: 600, x: 0, y: 0 }),
        });
        const view = eventWindow();
        const eventCtor = (view as unknown as { MouseEvent: typeof MouseEvent }).MouseEvent;
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
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(zoomGroup.getAttribute("transform")).toBe("translate(40,20) scale(1)");

        // The save flow measures the container (LDG-30), not the svg —
        // jsdom gives every element a 0×0 box, so pin the container too.
        const container = compiled.querySelector(".screenshot-container") as HTMLElement;
        Object.defineProperty(container, "getBoundingClientRect", {
            value: () => ({ left: 0, top: 0, right: 800, bottom: 600, width: 800, height: 600, x: 0, y: 0 }),
        });

        // The toolbar's save button (LDG-27's column).
        const saveButton = compiled.querySelector("button.aurelius-lineage-save") as HTMLButtonElement;
        saveButton.click();
        await created.whenStable();
        created.detectChanges();

        // The service converts the live svg at the container's size — the
        // clone it serializes carries the CURRENT transform (the legacy
        // reset to identity around the save and restored after; the reader
        // watched the view jump twice — DD-407 dropped that).
        expect(save).toHaveBeenCalledTimes(1);
        const [savedSvg, width, height] = save.mock.calls[0] as unknown as [SVGSVGElement, number, number];
        expect(savedSvg).toBe(svg);
        expect([width, height]).toEqual([800, 600]);

        // And the view did not move: the transform still reads the pan.
        expect(zoomGroup.getAttribute("transform")).toBe("translate(40,20) scale(1)");
    });
});

describe("LineageViewer over an archimate document (LDG-33..LDG-36, DD-418)", () => {
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
        // The legacy's stroke-dasharray="999" rides every marker path so a
        // dashed connection never dashes its own arrowhead, and the fill
        // rides as a style — the open arrows carry none, the closed one black.
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

        // The Goal: the legacy octagon over its 120x80, the motivation
        // class on the group (the fill rule reads it), the goal glyph inked
        // motivation.
        const goal = compiled.querySelector("g.node[data-concept='goal']") as SVGGElement;
        expect(goal.classList.contains("motivation")).toBe(true);
        expect(goal.querySelector("path.node-shape")?.getAttribute("d")).toBe(
            "m12,0h96l12,12v56l-12,12h-96l-12,-12v-56l12,-12z",
        );
        expect(goal.querySelector(".node-icon path")?.getAttribute("d")).toMatch(/^M 6\.1538 8 a/);
        expect(goal.querySelector(".node-icon path")?.classList.contains("motivation")).toBe(true);
        expect(goal.querySelector(".node-text")?.textContent?.trim()).toBe("Reduce Cost");

        // The Data Object: application class, plain rectangle, object glyph.
        const data = compiled.querySelector("g.node[data-concept='data']") as SVGGElement;
        expect(data.classList.contains("application")).toBe(true);
        expect(data.querySelector("path.node-shape")?.getAttribute("d")).toBe("m0,0h120v80h-120z");
        expect(data.querySelector(".node-icon path")?.classList.contains("application")).toBe(true);
    });

    it("LDG-33: a junction is an unlabelled, uninked ellipse", () => {
        const { compiled } = setup(archimateModel());
        const junction = compiled.querySelector("g.node[data-concept='junction']") as SVGGElement;
        // The And class (black fill), the ellipse over the writer's 14x14.
        expect(junction.classList.contains("and")).toBe(true);
        expect(junction.querySelector("path.node-shape")?.getAttribute("d")).toBe(
            "m0,0a7,7,0,0,0,14,14a7,7,0,0,0,-14,-14z",
        );
        // The legacy compose hid both the icon and the name (showIcon:
        // false, showName: false).
        expect(junction.querySelector(".node-icon")).toBeNull();
        expect(junction.querySelector(".node-text")).toBeNull();
    });

    it("LDG-36: each connection rides its relation type's markers and dash", () => {
        const { compiled } = setup(archimateModel());
        const pathFor = (concept: string) =>
            compiled.querySelector(`g.connection[data-concept='${concept}'] path.connection-path`) as SVGPathElement;

        // The Flow: the filled arrow at the end, the legacy's 4,2 dash.
        const flow = pathFor("flow");
        expect(flow.getAttribute("marker-end")).toBe("url(#generic-arrow)");
        expect(flow.getAttribute("marker-start")).toBeNull();
        expect(flow.style.strokeDasharray).toBe("4,2");

        // The Access Read/Write: the open access hook at the start, the
        // open arrow at the end, dashed 2,2.
        const access = pathFor("access");
        expect(access.getAttribute("marker-start")).toBe("url(#access-read)");
        expect(access.getAttribute("marker-end")).toBe("url(#generic-arrow-open)");
        expect(access.style.strokeDasharray).toBe("2,2");

        // A connection whose relation the model does not carry: the plain
        // line, no markers, no dash (the legacy's no-style answer). Its
        // concept is its own id (LDG-17's `ref ?? id`).
        const lost = pathFor("c-lost");
        expect(lost.getAttribute("marker-start")).toBeNull();
        expect(lost.getAttribute("marker-end")).toBeNull();
        expect(lost.style.strokeDasharray).toBe("");
    });

    it("LDG-34/LDG-35: the shipped style block carries every fill of the tables", () => {
        const styles = styleBlock();
        // The lineage fills the shipped chain still uses stay (7.22b's pin).
        expect(styles).toContain("fill: hsl(240, 100%, 95%)");
        // The builder drops an imported constant interpolated into a
        // component's styles, so the archimate blocks ship as a literal copy
        // (DD-418). This pins every declaration of the AR3_NODE_FILLS and
        // AR3_ICON_FILLS tables into the shipped block, so the copy cannot
        // drift from the data the tables answer.
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
                    const value = declaration.slice(declaration.indexOf(":") + 1).trim();
                    // The builder stamps a _ngcontent attribute into each
                    // selector part and may reformat spacing, so each part
                    // matches with an optional attribute after it, and the
                    // declaration by property and value inside the rule.
                    const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, (char) => `\\${char}`);
                    // The leading lookbehind keeps a bare glyph selector like
                    // .motivation from matching inside .node.motivation.
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
