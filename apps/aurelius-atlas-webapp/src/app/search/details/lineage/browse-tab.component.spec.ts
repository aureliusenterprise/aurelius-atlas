import { ComponentFixture, TestBed } from "@angular/core/testing";
import { describe, expect, it } from "vitest";

import { buildEntitiesById } from "./lineage-entities";
import type { LineageEntity } from "./lineage-entities";
import { parseAr3Model, type Ar3Organization } from "./parse-ar3";
import { LineageBrowseTab } from "./browse-tab.component";

import entityFixture from "../../../../../tests/fixtures/lineage-graph.extract.json";

/**
 * LDG-23 / DD-406: the Browse tab over the shipped chain's document — the
 * view dropdown plus the organization navigation tree (the Other /
 * Relations / Views folders the producer emits, DD-395's superseded
 * deviation brought back by the feedback round).
 */
const VIEW: LineageEntity = {
    id: "lineage_view",
    kind: "view",
    name: "Lineage",
    type: "ar3_View",
    humanReadableType: "View",
    description: "",
    properties: [],
    sourceName: "",
    targetName: "",
    sourceType: "",
    targetType: "",
};
const SECOND: LineageEntity = { ...VIEW, id: "view-2", name: "Second view" };

/** The fixture document's organization tree and entity index (DD-406). */
const MODEL = parseAr3Model(entityFixture.model);
const ENTITIES = buildEntitiesById(MODEL);

function setup(
    views: LineageEntity[],
    drawnViewId: string | null,
    organizations: readonly Ar3Organization[] = [],
    entities: ReadonlyMap<string, LineageEntity> = new Map(),
    selectedConcept: string | null = null,
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
    created.componentRef.setInput("organizations", organizations);
    created.componentRef.setInput("entities", entities);
    created.componentRef.setInput("selectedConcept", selectedConcept);
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

    it("DD-406: the tree lists the folders open with their entity names, root not shown", () => {
        const { compiled } = setup([VIEW], "lineage_view", MODEL.organizations, ENTITIES);
        expect(compiled.textContent).toContain("Model tree");
        const folders = [...compiled.querySelectorAll(".aurelius-browse-tree-folder")].map((node) =>
            node.textContent?.trim(),
        );
        // The producer's single unlabeled root renders no row of its own.
        expect(folders).toEqual(["Other", "Relations", "Views"]);
        // The leaves read through the entity index — elements by name, the
        // unnamed relation by its id (the shipped chain names none).
        const leaves = [...compiled.querySelectorAll(".aurelius-browse-tree-leaf")].map((node) =>
            node.textContent?.trim(),
        );
        expect(leaves).toEqual(["Ingest Topic", "Load Job", "Sales Table", "rel-1", "rel-2", "Lineage"]);
    });

    it("DD-406: a closed folder hides its whole branch", () => {
        const { tab, created, compiled } = setup([VIEW], null, MODEL.organizations, ENTITIES);
        const other = compiled.querySelector(".aurelius-browse-tree-folder") as HTMLButtonElement;
        other.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        created.detectChanges();
        expect(other.getAttribute("aria-expanded")).toBe("false");
        // The Other folder's three element leaves are gone; the other folders stay.
        expect([...compiled.querySelectorAll(".aurelius-browse-tree-leaf")].map((n) => n.textContent?.trim())).toEqual([
            "rel-1",
            "rel-2",
            "Lineage",
        ]);
        // Opened again, the branch returns.
        const closed = compiled.querySelector(".aurelius-browse-tree-folder") as HTMLButtonElement;
        closed.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        created.detectChanges();
        expect(tab["treeRows"]().filter((row) => !row.folder)).toHaveLength(6);
    });

    it("DD-406: an element leaf click selects the concept; the selected one is marked", () => {
        // The selected concept is carried as the concept id (LDG-25's
        // signal), not the label — the guid of "Load Job", the fixture's
        // second element.
        const { tab, created, compiled } = setup(
            [VIEW],
            null,
            MODEL.organizations,
            ENTITIES,
            "00000000-0000-4000-8000-000000000002",
        );
        const emitted: string[] = [];
        tab.conceptChosen.subscribe((id) => emitted.push(id));
        const leaves = [...compiled.querySelectorAll<HTMLButtonElement>(".aurelius-browse-tree-leaf")];
        expect(leaves[1]?.classList.contains("is-active")).toBe(true);
        leaves[0]?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        expect(emitted).toEqual(["00000000-0000-4000-8000-000000000001"]);
    });

    it("DD-406: a view leaf click chooses the view (LDG-23's close-and-draw)", () => {
        const { tab, compiled } = setup([VIEW], null, MODEL.organizations, ENTITIES);
        const views: string[] = [];
        const concepts: string[] = [];
        tab.viewChosen.subscribe((id) => views.push(id));
        tab.conceptChosen.subscribe((id) => concepts.push(id));
        const leaves = [...compiled.querySelectorAll<HTMLButtonElement>(".aurelius-browse-tree-leaf")];
        leaves[5]?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        expect(views).toEqual(["lineage_view"]);
        expect(concepts).toEqual([]);
    });

    it("DD-406: a model without organizations shows no tree", () => {
        const { compiled } = setup([VIEW], "lineage_view", [], ENTITIES);
        expect(compiled.querySelector(".aurelius-browse-tree")).toBeNull();
        expect(compiled.textContent).not.toContain("Model tree");
    });

    it("TREEITEM-WRAPPER: every row's button is the treeitem and the wrapper is not", () => {
        const { compiled } = setup([VIEW], "lineage_view", MODEL.organizations, ENTITIES);

        // The reader lands on the focusable element: role="treeitem" rides
        // the buttons, and the <li> is role="none" layout.
        const wrappers = [...compiled.querySelectorAll(".aurelius-browse-tree > li")];
        expect(wrappers.length).toBeGreaterThan(0);
        for (const wrapper of wrappers) {
            expect(wrapper.getAttribute("role")).toBe("none");
            expect(wrapper.hasAttribute("aria-selected")).toBe(false);
        }
        const items = [...compiled.querySelectorAll(".aurelius-browse-tree button")];
        expect(items).toHaveLength(wrappers.length);
        for (const item of items) {
            expect(item.getAttribute("role")).toBe("treeitem");
        }

        // The folder keeps its fold state on the same element, and says it
        // is not selectable (a treeitem's aria-selected is required, so the
        // folder carries the literal false the old wrapper's null-equality
        // bug used to compute).
        const folder = compiled.querySelector(".aurelius-browse-tree-folder") as HTMLElement;
        expect(folder.getAttribute("aria-expanded")).toBe("true");
        expect(folder.getAttribute("aria-selected")).toBe("false");
        const unselected = compiled.querySelector(".aurelius-browse-tree-leaf") as HTMLElement;
        expect(unselected.getAttribute("aria-selected")).toBe("false");
    });

    it("TREEITEM-WRAPPER: rows carry their level and sibling position, and the selected leaf its flag", () => {
        const { compiled } = setup(
            [VIEW],
            "lineage_view",
            MODEL.organizations,
            ENTITIES,
            "00000000-0000-4000-8000-000000000002",
        );

        // The shipped tree: Other / Relations / Views at level 1 (three
        // siblings), their leaves at level 2. "Other" opens its parent's run.
        const other = [...compiled.querySelectorAll(".aurelius-browse-tree-folder")].find((node) =>
            node.textContent?.includes("Other"),
        ) as HTMLElement;
        expect(other.getAttribute("aria-level")).toBe("1");
        expect(other.getAttribute("aria-setsize")).toBe("3");
        expect(other.getAttribute("aria-posinset")).toBe("1");

        // "Load Job" — Other's second leaf — sits level 2 of a set of three,
        // and carries the selection the wrapper used to hold.
        const loadJob = [...compiled.querySelectorAll(".aurelius-browse-tree-leaf")].find((node) =>
            node.textContent?.includes("Load Job"),
        ) as HTMLElement;
        expect(loadJob.getAttribute("aria-level")).toBe("2");
        expect(loadJob.getAttribute("aria-setsize")).toBe("3");
        expect(loadJob.getAttribute("aria-posinset")).toBe("2");
        expect(loadJob.getAttribute("aria-selected")).toBe("true");

        // Closing the folder re-runs its parent's set: with Other closed, its
        // children leave the tree and Views moves to position 2 of 3.
    });
});
