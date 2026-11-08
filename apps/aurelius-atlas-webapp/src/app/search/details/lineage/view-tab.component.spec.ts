import { TestBed } from "@angular/core/testing";
import { describe, expect, it } from "vitest";

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
};

function setup(view: LineageEntity | null): HTMLElement {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ imports: [LineageViewTab] });
    const created = TestBed.createComponent(LineageViewTab);
    created.componentRef.setInput("view", view);
    created.componentRef.setInput("metadata", METADATA);
    created.detectChanges();
    return created.nativeElement as HTMLElement;
}

describe("LineageViewTab (LDG-24)", () => {
    it("LDG-24: the view's Name and merged Properties show; no Description, no view tables", () => {
        const compiled = setup(VIEW);
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
        const compiled = setup(null);
        // Only the @if's container comment stays; no section renders.
        expect(compiled.querySelector(".field")).toBeNull();
    });
});
