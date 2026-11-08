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

/**
 * The shell over the shipped chain's document (LDG-27..31, DD-391/DD-415):
 * the chrome the details page keeps after the drawing moved to
 * `aurelius-atlas-ui`'s canvas (DD-419). The fixture is the vendored 8.2
 * scenario extract — three nodes at x=0/320/640, y=0, 120x55, joined by two
 * unnamed relations — so the DOM below is that document's own, drawn by the
 * canvas the shell hosts. What the picture looks like (shapes, fills, paths,
 * zoom mechanics, the archimate tables) is pinned by the canvas's own spec
 * in the lib; this spec pins the state, the routes, the toolbar, and the
 * save seam around it.
 */

/** The vendored model, parsed (LDG-11's output feeds the canvas). */
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
    // Two passes: the first creates the view, the second lets the canvas's
    // zoom effect (a viewChild reader) run.
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

/** The shell's own style block — the chrome pixels LDG-15/LDG-28 pin. */
function styleBlock(): string {
    const def = (LineageViewer as unknown as { ɵcmp: { styles?: string[] } }).ɵcmp;
    return (def.styles ?? []).join("\n");
}

/**
 * The real jsdom window behind the test environment's patched global.
 * d3-zoom (on the canvas) attaches its drag listeners to `event.view`, and
 * jsdom's event constructors reject the patched global as a view ("not of
 * type Window"), so the pointer events below must name this window. Reached
 * the way jsdom itself crosses realms.
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
 * Pan the drawing by (40, 20) through the canvas's d3-zoom, so a test has a
 * transform in place (the LDG-16 gesture, shortened). The post-drag
 * setTimeout(0) is left to the caller to await before any further click.
 */
async function panDrawing(compiled: HTMLElement): Promise<SVGGElement> {
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
        new eventCtor("mouseup", { bubbles: true, cancelable: true, view: view as Window, clientX: 50, clientY: 30 }),
    );
    expect(zoomGroup.getAttribute("transform")).toBe("translate(40,20) scale(1)");
    // d3-drag's post-drag click guard swallows one click until its
    // setTimeout(0) runs (the LDG-16 note) — let it pass before a click.
    await new Promise((resolve) => setTimeout(resolve, 0));
    return zoomGroup;
}

describe("LineageViewer, the shell (LDG-15..LDG-18 pass-through, LDG-27..29)", () => {
    it("LDG-15: the drawing region keeps the legacy's 50vh area", () => {
        setup();
        // The area's own height rides the shell (the canvas fills it with
        // its svg's min-size, as in the legacy).
        expect(styleBlock()).toContain("50vh");
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

        // The canvas answers the click with the referenced element (the
        // legacy's `ref ?? id` — the element guid, not the view-node id);
        // the shell writes it into the shared state and paints it through
        // the selected input.
        expect(processNode.getAttribute("data-concept")).toBe(PROCESS);
        click(processNode);
        expect(state.selected()).toBe(PROCESS);
        expect(processNode.classList.contains("is-selected")).toBe(true);

        // A connection click moves the selection to its relation — the
        // shell holds ONE selected concept (the legacy's selectedEntity).
        expect(connections[0].getAttribute("data-concept")).toBe("rel-1");
        click(connections[0]);
        expect(state.selected()).toBe("rel-1");
        expect(connections[0].classList.contains("is-selected")).toBe(true);
        expect(processNode.classList.contains("is-selected")).toBe(false);

        // Clicking the same concept again clears it.
        click(connections[0]);
        expect(state.selected()).toBeNull();
        expect(connections[0].classList.contains("is-selected")).toBe(false);

        // DD-415: every click doubles as the drawer's navigation — the
        // legacy's auto-open/close, now the outlet's (the routed panel exists
        // only while its route does, so the surfaces cannot drift).
        expect(navigate.mock.calls.map((call: unknown[]) => call[0])).toEqual([
            [{ outlets: { drawer: ["lineage", "selection", PROCESS] } }],
            [{ outlets: { drawer: ["lineage", "selection", "rel-1"] } }],
            [{ outlets: { drawer: null } }],
        ]);
    });

    it("LDG-18: the page guid input highlights its node on the canvas", () => {
        const { created, compiled } = setup();

        // No highlight input: nothing highlights.
        expect(compiled.querySelectorAll("g.node.is-highlighted")).toHaveLength(0);

        // The shell forwards the input to the canvas, which paints the node
        // whose element ref equals the guid (LDG-18).
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

    it("LDG-29: the reset button restores the canvas's identity transform", async () => {
        const { created, compiled } = setup();

        // Pan the drawing so there is something to reset, then press the
        // button — the shell forwards to the canvas's resetZoom (DD-419).
        const zoomGroup = await panDrawing(compiled);

        compiled.querySelector<HTMLButtonElement>(".aurelius-lineage-reset-zoom")?.click();
        created.detectChanges();
        expect(zoomGroup.getAttribute("transform")).toBe("translate(0,0) scale(1)");
    });

    it("LDG-29/DD-407: saving captures the current transform and never moves the view", async () => {
        const { created, compiled } = setup();

        // The save seam: record what the service is handed, draw nothing.
        const save = vi.spyOn(TestBed.inject(SaveViewAsImage), "save").mockResolvedValue(undefined);

        // Pan the drawing so a transform is in place.
        const zoomGroup = await panDrawing(compiled);

        // The save flow measures the container (LDG-30), not the svg —
        // jsdom gives every element a 0x0 box, so pin the container too.
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
        // watched the view jump twice — DD-407 dropped that). The svg is
        // the canvas's own (DD-419: the shell hands it over).
        expect(save).toHaveBeenCalledTimes(1);
        const [savedSvg, width, height] = save.mock.calls[0] as unknown as [SVGSVGElement, number, number];
        expect(savedSvg).toBe(compiled.querySelector("svg.lineage-svg"));
        expect([width, height]).toEqual([800, 600]);

        // And the view did not move: the transform still reads the pan.
        expect(zoomGroup.getAttribute("transform")).toBe("translate(40,20) scale(1)");
    });
});
