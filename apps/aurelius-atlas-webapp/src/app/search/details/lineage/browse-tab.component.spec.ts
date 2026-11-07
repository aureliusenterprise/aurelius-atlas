import { ComponentFixture, TestBed } from "@angular/core/testing";
import { describe, expect, it } from "vitest";

import type { LineageEntity } from "./lineage-entities";
import { LineageBrowseTab } from "./browse-tab.component";

/**
 * LDG-23: the Browse tab's view dropdown over the shipped chain's one view
 * (the fixture's "Lineage" — DD-391's provenance). The tree half of the
 * legacy tab never lands here (DD-395).
 */
const VIEW: LineageEntity = {
    id: "lineage_view",
    kind: "view",
    name: "Lineage",
    type: "ar3_View",
    humanReadableType: "View",
    description: "",
    properties: [],
};
const SECOND: LineageEntity = { ...VIEW, id: "view-2", name: "Second view" };

function setup(
    views: LineageEntity[],
    drawnViewId: string | null,
): {
    tab: LineageBrowseTab;
    created: ComponentFixture<LineageBrowseTab>;
    compiled: HTMLElement;
} {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ imports: [LineageBrowseTab] });
    const created = TestBed.createComponent(LineageBrowseTab);
    created.componentRef.setInput("views", views);
    created.componentRef.setInput("drawnViewId", drawnViewId);
    created.detectChanges();
    return { tab: created.componentInstance, created, compiled: created.nativeElement as HTMLElement };
}

describe("LineageBrowseTab (LDG-23)", () => {
    it("LDG-23: the dropdown lists the model's views and the drawn one reads back", async () => {
        const { created, compiled } = setup([VIEW, SECOND], "lineage_view");
        // The select rides ngModel: its value accessor writes the native
        // control's value on a microtask.
        await created.whenStable();
        created.detectChanges();
        const select = compiled.querySelector("select");
        if (select === null) {
            throw new Error("the dropdown is missing");
        }
        // The placeholder plus the two view rows (no-data / null messages
        // ride the control's placeholder option).
        const optionTexts = [...select.querySelectorAll("option")].map((option) => option.textContent ?? "");
        expect(optionTexts.some((text) => text.includes("Lineage"))).toBe(true);
        expect(optionTexts.some((text) => text.includes("Second view"))).toBe(true);
        expect(select.getAttribute("aria-labelledby")).toBeTruthy();
        // The drawn view is the control's value: the native select carries
        // the row's index among the option rows (the legacy's viewId sync).
        expect(select.value).toBe("0");
    });

    it("LDG-23: choosing a row emits the view (LDG-25's close-and-draw rides the browser)", () => {
        const { tab, created, compiled } = setup([VIEW, SECOND], "lineage_view");
        const emitted: string[] = [];
        tab.viewChosen.subscribe((id) => emitted.push(id));
        const select = compiled.querySelector("select") as HTMLSelectElement;
        // Pick the second view: the native select carries the row index.
        select.value = "1";
        select.dispatchEvent(new Event("change"));
        created.detectChanges();
        expect(emitted).toEqual(["view-2"]);
    });

    it("LDG-23: a model with no view shows the no-data message", () => {
        const { compiled } = setup([], null);
        const optionTexts = [...compiled.querySelectorAll("option")].map((option) => option.textContent ?? "");
        expect(optionTexts.some((text) => text.includes("No views available"))).toBe(true);
    });
});
