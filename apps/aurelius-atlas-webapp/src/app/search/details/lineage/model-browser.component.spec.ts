import { ComponentFixture, TestBed } from "@angular/core/testing";
import { describe, expect, it } from "vitest";

import type { LineageModelMetadata } from "aurelius-atlas-data-access";

import fixture from "../../../../../tests/fixtures/lineage-graph.extract.json";

import type { LineageEntity } from "./lineage-entities";
import { buildEntitiesById } from "./lineage-entities";
import { buildIndexes } from "./lineage-indexes";
import { LineageModelBrowser } from "./model-browser.component";
import { parseAr3Model } from "./parse-ar3";

/**
 * LDG-19/LDG-25: the quickview drawer over the shipped chain's document
 * (DD-391) — the four tabs and their conditions, the auto-open on a concept
 * selection, the close on deselect (with the previous-tab restore), and the
 * close-and-redraw on a view choice.
 */
const MODEL = parseAr3Model(fixture.model);
const ENTITIES = buildEntitiesById(MODEL);
const INDEXES = buildIndexes(MODEL);
const METADATA = fixture.metadata as LineageModelMetadata[];

const PROCESS = "00000000-0000-4000-8000-000000000002";
const VIEW_ID = "lineage_view";

const SECOND_VIEW: LineageEntity = {
    id: "other_view",
    kind: "view",
    name: "Other View",
    type: "ar3_View",
    humanReadableType: "View",
    description: "",
    properties: [],
    sourceName: "",
    targetName: "",
    sourceType: "",
    targetType: "",
};

function setup(
    selection: string | null = null,
    activeViewId: string | null = VIEW_ID,
    entities: ReadonlyMap<string, LineageEntity> = ENTITIES,
): {
    browser: LineageModelBrowser;
    created: ComponentFixture<LineageModelBrowser>;
    compiled: HTMLElement;
} {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ imports: [LineageModelBrowser] });
    const created = TestBed.createComponent(LineageModelBrowser);
    created.componentRef.setInput("entities", entities);
    created.componentRef.setInput("indexes", INDEXES);
    created.componentRef.setInput("metadata", METADATA);
    created.componentRef.setInput("activeViewId", activeViewId);
    created.componentRef.setInput("selection", selection);
    created.detectChanges();
    created.detectChanges();
    return { browser: created.componentInstance, created, compiled: created.nativeElement as HTMLElement };
}

function tabLabels(compiled: HTMLElement): string[] {
    return [...compiled.querySelectorAll(".aurelius-model-browser-tab")].map((node) => node.textContent?.trim() ?? "");
}

function activeTab(compiled: HTMLElement): string | undefined {
    return compiled.querySelector(".aurelius-model-browser-tab.is-active")?.textContent?.trim();
}

/** The drawer's layer, rendered only while the panel is open (DD-162). */
function drawerLayer(compiled: HTMLElement): Element | null {
    return compiled.querySelector(".aurelius-drawer");
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

describe("LineageModelBrowser (LDG-19, LDG-25)", () => {
    it("LDG-19/DD-410: the open strip reads Browse, Model, View, Selection — the legacy's order", () => {
        // The strip is the drawer's (DD-180's subhead): visibleTabs is the
        // strip's source, and it drives what an open drawer shows. DD-410:
        // the legacy's keyvalue order puts View before Selection — the
        // tabs object's insertion order was browse, model, view, selection.
        const { browser, compiled } = setup(PROCESS);
        expect(browser["visibleTabs"]().map((tab) => tab.id)).toEqual(["browse", "model", "view", "selection"]);
        expect(tabLabels(compiled)).toEqual(["Browse", "Model", "View", "Selection"]);
        const { browser: empty } = setup(null);
        expect(empty["visibleTabs"]().map((tab) => tab.id)).toEqual(["browse", "model", "view"]);
    });

    it("LDG-19: with no view selected the View tab hides (the legacy's condition)", () => {
        const { browser } = setup(PROCESS, null);
        expect(browser["visibleTabs"]().map((tab) => tab.id)).toEqual(["browse", "model", "selection"]);
    });

    it("LDG-25: a concept selection opens the drawer on the Selection tab", () => {
        const { browser, created, compiled } = setup(null);
        expect(drawerLayer(compiled)).toBeNull();
        browser.selection.set(PROCESS);
        created.detectChanges();
        expect(drawerLayer(compiled)).not.toBeNull();
        expect(activeTab(compiled)).toBe("Selection");
        // The Selection tab's content: the concept's name (LDG-20).
        expect(compiled.textContent).toContain("Load Job");
    });

    it("LDG-25: clearing the selection closes the drawer and restores the previous tab", () => {
        const { browser, created, compiled } = setup(PROCESS);
        // Open on Selection, read the Model tab, then clear — the close
        // lands back on Model (the legacy's close() + selectTab(previousTab)).
        selectTab(compiled, "Model");
        created.detectChanges();
        expect(activeTab(compiled)).toBe("Model");

        browser.selection.set(null);
        created.detectChanges();
        browser.selection.set(PROCESS);
        created.detectChanges();
        expect(activeTab(compiled)).toBe("Selection");

        browser.selection.set(null);
        created.detectChanges();
        // Closed, and the reader lands back on the tab they were reading
        // (the legacy's close() + selectTab(previousTab)).
        expect(drawerLayer(compiled)).toBeNull();
        expect(browser["currentTab"]()).toBe("model");
    });

    it("LDG-25: choosing a view in the Browse dropdown closes the drawer and emits it", async () => {
        const twoViews = new Map(ENTITIES);
        twoViews.set(SECOND_VIEW.id, SECOND_VIEW);
        // No drawn view: the dropdown shows its placeholder, so picking the
        // first row is a real change for the control.
        const { browser, created, compiled } = setup(null, null, twoViews);
        const emitted: string[] = [];
        browser.viewChosen.subscribe((id) => emitted.push(id));
        // Open the panel through a selection, then switch to Browse.
        browser.selection.set(PROCESS);
        created.detectChanges();
        selectTab(compiled, "Browse");
        created.detectChanges();
        expect(drawerLayer(compiled)).not.toBeNull();

        const select = compiled.querySelector("select") as HTMLSelectElement;
        expect(select.value).toBe("");
        select.value = "0";
        select.dispatchEvent(new Event("change"));
        await created.whenStable();
        created.detectChanges();

        expect(emitted).toEqual([VIEW_ID]);
        expect(drawerLayer(compiled)).toBeNull();
    });

    it("DD-403: dismissal hides the panel and clears the selection (the box deselects)", () => {
        const { created, compiled } = setup(PROCESS);
        const close = compiled.querySelector(".aurelius-drawer-panel button.delete");
        if (close === null) {
            throw new Error("the drawer's close button is missing");
        }
        close.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        created.detectChanges();
        // The panel slides out (the layer lingers for the exit animation
        // only, DD-162) AND the selection clears — no box stays painted
        // without its panel (the deliberate departure from the legacy's
        // close, which left the node marked).
        expect(created.componentInstance["active"]()).toBe(false);
        expect(created.componentInstance.selection()).toBeNull();
        expect(compiled.querySelector(".aurelius-drawer")?.classList.contains("is-closing")).toBe(true);
        // The tab strip lost its Selection tab with the selection (LDG-19's
        // condition) — the reader lands on the tab they were reading.
        expect(created.componentInstance["currentTab"]()).not.toBe("selection");
    });

    it("DD-403: the view choice closes and deselects the same way", () => {
        const twoViews = new Map(ENTITIES);
        twoViews.set(SECOND_VIEW.id, SECOND_VIEW);
        const { browser, created } = setup(null, null, twoViews);
        // Open through a selection, then choose a view from the tab logic.
        browser.selection.set(PROCESS);
        created.detectChanges();
        browser["onViewChosen"](VIEW_ID);
        created.detectChanges();
        expect(browser["active"]()).toBe(false);
        expect(browser.selection()).toBeNull();
    });

    it("DD-410: the legacy's chrome — the header reads Details, the footer closes", () => {
        const { created, compiled } = setup(PROCESS);
        // The quickview's default name, which the legacy model browser never
        // overrode — the panel is "Details" whichever concept opened it.
        expect(compiled.querySelector(".aurelius-drawer-title")?.textContent?.trim()).toBe("Details");
        const close = compiled.querySelector("button[drawer-footer]");
        if (close === null) {
            throw new Error("the footer's Close button is missing");
        }
        expect(close.textContent?.trim()).toBe("Close");
        // It dismisses like the head's close: the panel slides out and the
        // selection clears with it (DD-403's rule, shared).
        close.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        created.detectChanges();
        expect(created.componentInstance["active"]()).toBe(false);
        expect(created.componentInstance.selection()).toBeNull();
    });

    it("DD-402: the tab strip is full width — Bulma's is-fullwidth tab nav", () => {
        const { compiled } = setup(PROCESS);
        const tabs = compiled.querySelector("nav.aurelius-model-browser-tabs");
        if (tabs === null) {
            throw new Error("the tab strip is missing");
        }
        // is-fullwidth grows every li to fill the strip (equal cells), and
        // Bulma's tab anchors center their label in the cell by default —
        // the wide, balanced row the feedback asked for.
        expect(tabs.classList.contains("is-fullwidth")).toBe(true);
    });
});
