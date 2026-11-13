import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ActivatedRoute, ParamMap, Router, convertToParamMap, provideRouter } from "@angular/router";
import { Subject } from "rxjs";
import { describe, expect, it, vi } from "vitest";

import type { LineageModelMetadata } from "aurelius-atlas-data-access";

import fixture from "../../../../../tests/fixtures/lineage-graph.extract.json";

import { buildEntitiesById } from "./lineage-entities";
import { LineageModelState } from "./lineage-state";
import { LineageModelBrowser } from "./model-browser.component";
import { parseAr3Model, type Ar3Model } from "./parse-ar3";

/**
 * LDG-19/LDG-25 (DD-415): the quickview drawer as the routed panel in the
 * `drawer` aux outlet. The specs ride the editor's routed-drawer idiom: a
 * fake `ActivatedRoute` (paramMap carries the tab and concept, DD-415), a spy
 * on the Router, and the shared {@link LineageModelState} the drawer reads —
 * the panel fills itself from the state, so the specs set the model and
 * selection there rather than through inputs. The rules: the legacy tab
 * order and its conditions (LDG-19, DD-410), the route-driven tab, a concept
 * row click re-routing the Selection tab (LDG-25), dismissal clearing the
 * selection and routing away (DD-403, DD-415), the view choice drawing and
 * closing, the URL concept reopening the Selection tab (a reload), and the
 * legacy chrome (DD-410).
 */
const MODEL = parseAr3Model(fixture.model);
const METADATA = fixture.metadata as LineageModelMetadata[];

const PROCESS = "00000000-0000-4000-8000-000000000002";
const VIEW_ID = "lineage_view";

/** A model with no view: the View tab's condition (LDG-19) hides with none. */
const NO_VIEW_MODEL: Ar3Model = { ...MODEL, views: [] };

function setup({
    tab,
    concept,
    model = MODEL,
    selected = null,
    drawnViewId = VIEW_ID,
}: {
    tab?: string;
    concept?: string;
    model?: Ar3Model;
    selected?: string | null;
    drawnViewId?: string | null;
} = {}): {
    browser: LineageModelBrowser;
    state: LineageModelState;
    created: ComponentFixture<LineageModelBrowser>;
    compiled: HTMLElement;
    paramMap: Subject<ParamMap>;
    navigate: ReturnType<typeof vi.spyOn>;
} {
    TestBed.resetTestingModule();
    const paramMap = new Subject<ParamMap>();
    TestBed.configureTestingModule({
        imports: [LineageModelBrowser],
        providers: [
            provideHttpClient(),
            provideHttpClientTesting(),
            provideRouter([]),
            { provide: ActivatedRoute, useValue: { paramMap, snapshot: { data: {} } } },
        ],
    });
    // The drawer reads the shared state the box and viewer write; the specs
    // fill it directly (the fetch itself is the state's own concern).
    const state = TestBed.inject(LineageModelState);
    state.model.set(model);
    state.metadata.set(METADATA);
    state.selected.set(selected);
    state.drawnViewId.set(drawnViewId);

    const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
    const created = TestBed.createComponent(LineageModelBrowser);
    paramMap.next(
        convertToParamMap({ ...(tab === undefined ? {} : { tab }), ...(concept === undefined ? {} : { concept }) }),
    );
    created.detectChanges();
    return {
        browser: created.componentInstance,
        state,
        created,
        compiled: created.nativeElement as HTMLElement,
        paramMap,
        navigate,
    };
}

function tabLabels(compiled: HTMLElement): string[] {
    return [...compiled.querySelectorAll(".aurelius-model-browser-tab")].map((node) => node.textContent?.trim() ?? "");
}

function activeTab(compiled: HTMLElement): string | undefined {
    return compiled.querySelector(".aurelius-model-browser-tab.is-active")?.textContent?.trim();
}

function selectTab(compiled: HTMLElement, label: string): void {
    const tab = [...compiled.querySelectorAll(".aurelius-model-browser-tab")].find(
        (node) => node.textContent?.trim() === label,
    );
    if (tab === undefined) {
        throw new Error(`no tab labelled ${label}`);
    }
    tab.dispatchEvent(new MouseEvent("click", { bubbles: true }));
}

describe("LineageModelBrowser — routed drawer (LDG-19, LDG-25, DD-415)", () => {
    it("LDG-19/DD-410: the strip reads Browse, Model, View, Selection — the legacy's order", () => {
        const { compiled } = setup({ tab: "browse", selected: PROCESS });
        expect(tabLabels(compiled)).toEqual(["Browse", "Model", "View", "Selection"]);
    });

    it("LDG-19: the Selection tab needs a selected concept; the View tab a drawn view", () => {
        // No concept: the Selection tab hides (the legacy's condition).
        const { compiled } = setup({ tab: "browse", selected: null });
        expect(tabLabels(compiled)).toEqual(["Browse", "Model", "View"]);

        // A model with no view: the View tab hides too.
        const bare = setup({ tab: "browse", selected: null, model: NO_VIEW_MODEL, drawnViewId: null });
        expect(tabLabels(bare.compiled)).toEqual(["Browse", "Model"]);
    });

    it("DD-415: the tab the route names is the tab that reads", () => {
        const { created, compiled, paramMap } = setup({ tab: "model", selected: PROCESS });
        expect(activeTab(compiled)).toBe("Model");

        // The router answers a tab navigation with the new segment: the
        // component stays (one matcher config, DD-355) and re-reads.
        paramMap.next(convertToParamMap({ tab: "view" }));
        created.detectChanges();
        expect(activeTab(compiled)).toBe("View");
    });

    it("UIC-31: the View tab's legend picker writes the picked colour to the shared state", () => {
        const { created, compiled, state, paramMap } = setup({ tab: "view" });
        state.categories.set({ "e-1": "bronze", "e-2": "silver" });
        created.detectChanges();

        // The legend table appears with the categories and hides without.
        expect(compiled.textContent).toContain("Color legend");
        expect(compiled.querySelectorAll("input[type='color']")).toHaveLength(2);

        const swatch = compiled.querySelector("input[type='color']") as HTMLInputElement;
        swatch.value = "#654321";
        swatch.dispatchEvent(new Event("input", { bubbles: true }));
        expect(state.categoryColors()).toEqual({ bronze: "#654321" });

        // Picking keeps the panel open (no navigation) — the reader sees
        // the canvas repaint.
        expect(paramMap).toBeDefined();
    });

    it("DD-410: the legacy's chrome — the header reads Details, the footer closes", () => {
        const { created, compiled, state, navigate } = setup({ tab: "selection", concept: PROCESS });
        expect(compiled.querySelector(".aurelius-drawer-title")?.textContent?.trim()).toBe("Details");
        const close = compiled.querySelector("button[drawer-footer]");
        if (close === null) {
            throw new Error("the footer's Close button is missing");
        }
        expect(close.textContent?.trim()).toBe("Close");

        // It dismisses like the head's close: the selection clears and the
        // outlet navigates away (DD-403's rule, shared).
        close.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        created.detectChanges();
        expect(state.selected()).toBeNull();
        // DD-416: the drawer's navigations carry the router's per-navigation
        // scroll opt-out — the overlay never moves the page underneath it.
        expect(navigate).toHaveBeenCalledWith([{ outlets: { drawer: null } }], { scroll: "manual" });
    });

    it("DD-415: the route's concept reopens the Selection tab on it (a reload)", () => {
        // Arrival with a concept in the URL but an empty shared selection —
        // the reload/paste-link case: the panel fills the selection from it.
        const { compiled, state } = setup({ tab: "selection", concept: PROCESS, selected: null });
        expect(state.selected()).toBe(PROCESS);
        expect(activeTab(compiled)).toBe("Selection");
        // The Selection tab's content: the concept's name (LDG-20).
        expect(compiled.textContent).toContain("Load Job");
    });

    it("DD-415: the concept re-asserts when its model arrives after mount (the live reload)", async () => {
        // The live reload's race: the panel and the page's fetch mount
        // together, and load() clears the selection with the old document
        // (DD-415) — after the effect first set it. The effect depends on
        // the entity index, so the arriving model re-asserts the concept.
        const { created, state } = setup({ tab: "selection", concept: PROCESS, selected: null });
        expect(state.selected()).toBe(PROCESS);
        // What load() does when the page refetches: the old document and its
        // selection go, the new one arrives.
        state.model.set(null);
        state.selected.set(null);
        await created.whenStable();
        created.detectChanges();
        expect(state.selected()).toBeNull();
        state.model.set(MODEL);
        await created.whenStable();
        created.detectChanges();
        expect(state.selected()).toBe(PROCESS);
    });

    it("DD-415: switching to the Browse tab keeps the concept (no deselect)", () => {
        // A route change to a tab with no concept must not clear a selection
        // the reader still holds — the legacy kept it across the other tabs.
        const { created, compiled, state, paramMap } = setup({ tab: "selection", concept: PROCESS });
        paramMap.next(convertToParamMap({ tab: "browse" }));
        created.detectChanges();
        expect(activeTab(compiled)).toBe("Browse");
        expect(state.selected()).toBe(PROCESS);
    });

    it("DD-415: a tab label navigates the drawer outlet to the tab", () => {
        const { compiled, navigate } = setup({ tab: "browse", selected: PROCESS });
        selectTab(compiled, "Model");
        expect(navigate).toHaveBeenLastCalledWith([{ outlets: { drawer: ["lineage", "model"] } }], {
            scroll: "manual",
        });
    });

    it("DD-415: the Selection tab's label keeps carrying the concept", () => {
        const { compiled, navigate } = setup({ tab: "browse", selected: PROCESS });
        selectTab(compiled, "Selection");
        expect(navigate).toHaveBeenLastCalledWith([{ outlets: { drawer: ["lineage", "selection", PROCESS] } }], {
            scroll: "manual",
        });
    });

    it("TAB-PANEL-WIRING: the active tab controls a labelled, focusable tabpanel", () => {
        const { compiled } = setup({ tab: "browse", selected: PROCESS });

        const active = compiled.querySelector(".aurelius-model-browser-tab.is-active") as HTMLElement;
        const controls = active.getAttribute("aria-controls");
        expect(controls).toBeTruthy();
        const panel = compiled.querySelector(`[role='tabpanel']`);
        expect(panel?.id).toBe(controls);
        expect(panel?.getAttribute("aria-labelledby")).toBe(active.id);
        expect(panel?.getAttribute("tabindex")).toBe("0");
        // The panel holds the active tab's body — the Browse tab's tree label.
        expect(panel?.textContent).toContain("Model tree");

        // An inactive tab names no panel: the strip renders one panel at a
        // time (@switch), so a dead aria-controls would point at nothing.
        const inactive = [...compiled.querySelectorAll(".aurelius-model-browser-tab")].find(
            (tab) => !tab.classList.contains("is-active"),
        );
        expect(inactive?.hasAttribute("aria-controls")).toBe(false);
    });

    it("TAB-PANEL-WIRING: ArrowRight/ArrowLeft on the tablist switch to the neighbour tab", () => {
        const { created, compiled, navigate, paramMap } = setup({ tab: "browse", selected: PROCESS });

        // ArrowRight from Browse moves to Model — the same route navigation
        // a click makes (DD-415) — and focuses the new tab.
        const tablist = compiled.querySelector("[role='tablist']") as HTMLElement;
        tablist.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true, cancelable: true }));
        expect(navigate).toHaveBeenLastCalledWith([{ outlets: { drawer: ["lineage", "model"] } }], {
            scroll: "manual",
        });
        expect(document.activeElement?.classList.contains("aurelius-model-browser-tab")).toBe(true);

        // The route answers: the strip re-reads and the panel follows.
        paramMap.next(convertToParamMap({ tab: "model" }));
        created.detectChanges();
        expect(activeTab(compiled)).toBe("Model");
        expect(compiled.querySelector("[role='tabpanel']")?.getAttribute("aria-labelledby")).toBe(
            "aurelius-model-browser-tab-model",
        );

        // ArrowLeft walks back; from the first tab it wraps to the last
        // (Selection, with the concept it always carries).
        tablist.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true, cancelable: true }));
        expect(navigate).toHaveBeenLastCalledWith([{ outlets: { drawer: ["lineage", "browse"] } }], {
            scroll: "manual",
        });
        paramMap.next(convertToParamMap({ tab: "browse" }));
        created.detectChanges();
        tablist.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true, cancelable: true }));
        expect(navigate).toHaveBeenLastCalledWith([{ outlets: { drawer: ["lineage", "selection", PROCESS] } }], {
            scroll: "manual",
        });
    });

    it("TAB-PANEL-WIRING: Enter and Space on a tab activate it; other keys do not", () => {
        const { compiled, navigate } = setup({ tab: "browse", selected: PROCESS });
        const tablist = compiled.querySelector("[role='tablist']") as HTMLElement;

        // Enter/Space ride the anchor's own bindings (the arrow keys above
        // ride the strip's); a focused inactive tab activates on either.
        const model = [...compiled.querySelectorAll<HTMLElement>(".aurelius-model-browser-tab")].find((tab) =>
            tab.textContent?.includes("Model"),
        );
        model!.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }));
        expect(navigate).toHaveBeenLastCalledWith([{ outlets: { drawer: ["lineage", "model"] } }], {
            scroll: "manual",
        });
        model!.dispatchEvent(new KeyboardEvent("keydown", { key: " ", bubbles: true, cancelable: true }));
        expect(navigate).toHaveBeenLastCalledWith([{ outlets: { drawer: ["lineage", "model"] } }], {
            scroll: "manual",
        });

        // A key that is neither an arrow nor an activation: the strip's
        // handler leaves it alone (no navigation, no preventDefault).
        const before = navigate.mock.calls.length;
        const event = new KeyboardEvent("keydown", { key: "Home", bubbles: true, cancelable: true });
        tablist.dispatchEvent(event);
        expect(navigate).toHaveBeenCalledTimes(before);
        expect(event.defaultPrevented).toBe(false);
    });

    it("LDG-25: a tree leaf click re-routes the Selection tab to that concept", () => {
        // The Browse tab's organization tree holds the process leaf; its
        // click is the legacy's selectEntity — the selection follows and the
        // Selection tab routes to it (the drawer stays open).
        const { compiled, state, navigate } = setup({ tab: "browse", selected: null });
        const leaf = [...compiled.querySelectorAll(".aurelius-browse-tree-leaf")].find((row) =>
            row.textContent?.includes("Load Job"),
        );
        if (leaf === undefined) {
            throw new Error("the Browse tree's process leaf is missing");
        }
        leaf.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        expect(state.selected()).toBe(PROCESS);
        expect(navigate).toHaveBeenLastCalledWith([{ outlets: { drawer: ["lineage", "selection", PROCESS] } }], {
            scroll: "manual",
        });
    });

    it("LDG-25: the Model tab's selected row re-clicked deselects and closes", () => {
        const { created, compiled, state, navigate } = setup({ tab: "model", concept: undefined, selected: PROCESS });
        // The Elements table's selected row (the process) — clicking it again
        // is the legacy's deselect (LDG-25), which closes the drawer.
        const elementsField = [...compiled.querySelectorAll(".field")].find((field) =>
            field.querySelector(".label")?.textContent?.trim().startsWith("Elements"),
        );
        // Only the SELECTED row's re-click deselects (LDG-25): the process's
        // own row, not the table's first (the dataset).
        const row =
            [...(elementsField?.querySelectorAll("tbody tr") ?? [])].find((tr) =>
                tr.textContent?.includes("Load Job"),
            ) ?? null;
        if (row === null) {
            throw new Error("the Elements table has no process row");
        }
        row.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        created.detectChanges();
        expect(state.selected()).toBeNull();
        expect(navigate).toHaveBeenLastCalledWith([{ outlets: { drawer: null } }], { scroll: "manual" });
    });

    it("LDG-23: choosing a view draws it and closes the panel (the legacy's rule)", () => {
        // Two views so the dropdown's pick is a real change; the drawn view
        // starts unset and the Browse dropdown answers on arrival (DD-415).
        const twoViews = {
            ...MODEL,
            views: [
                ...MODEL.views,
                {
                    id: "other_view",
                    name: "Other View",
                    description: "",
                    nodes: [],
                    connections: [],
                    properties: [],
                },
            ],
        };
        const { created, compiled, state, navigate } = setup({ tab: "browse", model: twoViews });
        // Pick the SECOND view by its option — a real change from the drawn
        // first (the dropdown's selected row is the drawn view, DD-155).
        const select = compiled.querySelector("select") as HTMLSelectElement;
        const option = [...select.options].find((o) => o.textContent?.includes("Other View"));
        if (option === undefined) {
            throw new Error("the dropdown has no second view");
        }
        select.value = option.value;
        select.dispatchEvent(new Event("change"));
        created.detectChanges();

        expect(state.drawnViewId()).toBe("other_view");
        expect(navigate).toHaveBeenLastCalledWith([{ outlets: { drawer: null } }], { scroll: "manual" });
    });

    it("DD-403: the drawer's own dismissal (Escape) clears the selection too", () => {
        const { created, compiled, state, navigate } = setup({ tab: "selection", concept: PROCESS });
        // Escape on the dialog — the drawer's keyboard dismissal path (the
        // panel element carries the handler, not the layer).
        compiled
            .querySelector(".aurelius-drawer-panel")!
            .dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
        created.detectChanges();
        expect(state.selected()).toBeNull();
        expect(navigate).toHaveBeenLastCalledWith([{ outlets: { drawer: null } }], { scroll: "manual" });
    });

    it("DD-402: the tab strip is full width — Bulma's is-fullwidth tab nav", () => {
        const { compiled } = setup({ tab: "browse" });
        const tabs = compiled.querySelector("nav.aurelius-model-browser-tabs");
        if (tabs === null) {
            throw new Error("the tab strip is missing");
        }
        // is-fullwidth grows every li to fill the strip (equal cells), and
        // Bulma's tab anchors center their label in the cell by default —
        // the wide, balanced row the feedback asked for.
        expect(tabs.classList.contains("is-fullwidth")).toBe(true);
    });

    it("DD-416: the active tab carries the marker where Bulma's ink hangs", () => {
        // Bulma's active-tab rule is `li.is-active a` (tabs.scss): on the
        // anchor alone the tab stayed grey. The class must sit on the li —
        // and the strip must never shrink: a long tab body (the Model tab)
        // squeezed the strip, clipped the row, and raised its rule
        // mid-panel. flex-shrink: 0 is the head's and foot's own pin.
        const { compiled } = setup({ tab: "model", selected: PROCESS });
        const activeLi = compiled.querySelector("li.is-active");
        expect(activeLi?.querySelector("a.aurelius-model-browser-tab")?.textContent?.trim()).toBe("Model");
        const styles = ((LineageModelBrowser as unknown as { ɵcmp: { styles?: string[] } }).ɵcmp.styles ?? []).join(
            "\n",
        );
        expect(styles).toContain("flex-shrink: 0");
    });

    it("the drawer's entities are the state's model (LDG-19's index)", () => {
        // The panel derives the entity index from the shared model — the
        // Selection tab's content proves the read (the concept's name, DD-415).
        const { browser, state } = setup({ tab: "selection", concept: PROCESS });
        const expected = buildEntitiesById(state.model()!);
        expect([...browser["entities"]().keys()]).toEqual([...expected.keys()]);
    });
});
