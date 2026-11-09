import { TestBed } from "@angular/core/testing";
import { describe, expect, it } from "vitest";

import type { CategoryMap } from "aurelius-atlas-ui";
import type { LineageModelMetadata } from "aurelius-atlas-data-access";

import fixture from "../../../../../tests/fixtures/lineage-graph.extract.json";

import type { LineageEntity } from "./lineage-entities";
import { parseAr3Model } from "./parse-ar3";
import { LineageViewTab } from "./view-tab.component";

/**
 * LDG-24: the View tab over the shipped chain's view — Name, no Description
 * (the document carries none), and the Properties table from the LDG-21
 * merge over the view's metadata row. The referenced/referencing-views
 * tables are deliberately absent (the component's note).
 */
const MODEL = parseAr3Model(fixture.model);
const METADATA = fixture.metadata as LineageModelMetadata[];

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

function setup(
    view: LineageEntity | null,
    categories: CategoryMap | null = null,
    categoryColors: CategoryMap | null = null,
): {
    compiled: HTMLElement;
    picks: { category: string; color: string }[];
} {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ imports: [LineageViewTab] });
    const created = TestBed.createComponent(LineageViewTab);
    const picks: { category: string; color: string }[] = [];
    created.componentRef.setInput("view", view);
    created.componentRef.setInput("metadata", METADATA);
    created.componentRef.setInput("categories", categories);
    created.componentRef.setInput("categoryColors", categoryColors);
    created.componentInstance.colorPicked.subscribe((picked) => picks.push(picked));
    created.detectChanges();
    return { compiled: created.nativeElement as HTMLElement, picks };
}

describe("LineageViewTab (LDG-24, UIC-31)", () => {
    it("LDG-24: the view's Name and merged Properties show; no Description, no view tables", () => {
        const { compiled } = setup(VIEW);
        const labels = [...compiled.querySelectorAll(".label")].map((node) => node.textContent?.trim());
        expect(labels).toEqual(["Name", "Properties"]);
        expect(compiled.textContent).toContain("Lineage");
        // The view's metadata row (LDG-21's merge) — key-sorted, as the
        // legacy's keyvalue pipe rendered it. The name cell is a row header
        // (th), the value a data cell (td).
        const values = [...compiled.querySelectorAll("table tbody tr")].map((row) => {
            const name = row.querySelector("th")?.textContent?.trim();
            const value = row.querySelector("td")?.textContent?.trim();
            return `${name}=${value}`;
        });
        expect(values).toEqual([
            "created_by=Model Extractor API",
            "m4i_id_prefix=",
            "m4i_id_type=static",
            "m4i_original_id=lineage_view",
        ]);
    });

    it("LDG-24: with no view selected the tab renders nothing", () => {
        const { compiled } = setup(null);
        // Only the @if's container comment stays; no section renders.
        expect(compiled.querySelector(".field")).toBeNull();
    });

    it("UIC-31: no categories keep the legend hidden (the legacy's null legend)", () => {
        const { compiled } = setup(VIEW);
        expect(compiled.textContent).not.toContain("Color legend");
    });

    it("UIC-31: categories draw the legend rows, overrides repaint one", () => {
        const categories = { "e-1": "bronze", "e-2": "silver", "e-3": "bronze" };
        const { compiled } = setup(VIEW, categories, { silver: "#123456" });

        expect(compiled.textContent).toContain("Color legend");
        // The legend is the table whose rows carry the colour swatch.
        const rows = [...compiled.querySelectorAll("tbody tr")]
            .filter((row) => row.querySelector(".legend-color") !== null)
            .map((row) => {
                const category = row.querySelector("th")?.textContent?.trim();
                const color = (row.querySelector("input[type='color']") as HTMLInputElement).value;
                return `${category}=${color}`;
            });
        // First-seen order, the palette for the untouched category, the
        // override for the picked one — the same join the canvas fills read.
        expect(rows).toEqual(["bronze=#3366cc", "silver=#123456"]);
    });

    it("UIC-31: a picked swatch emits its category and hex", () => {
        const { compiled, picks } = setup(VIEW, { "e-1": "bronze" });
        const swatch = compiled.querySelector("input[type='color']") as HTMLInputElement;
        expect(swatch.value).toBe("#3366cc");

        swatch.value = "#abcdef";
        swatch.dispatchEvent(new Event("input", { bubbles: true }));
        expect(picks).toEqual([{ category: "bronze", color: "#abcdef" }]);
    });
});
