import { ComponentFixture, TestBed } from "@angular/core/testing";
import { Router } from "@angular/router";
import { describe, expect, it, vi } from "vitest";

import type { LineageModelMetadata } from "aurelius-atlas-data-access";

import { AR3_ICON_FILLS } from "./archimate-shapes";
import { buildEntitiesById, type LineageEntity } from "./lineage-entities";
import { buildIndexes } from "./lineage-indexes";
import { parseAr3Model } from "./parse-ar3";
import { LineageSelectionPanel } from "./selection-panel.component";

import fixture from "../../../../../tests/fixtures/lineage-graph.extract.json";

/**
 * LDG-20/LDG-21/LDG-22: the Selection tab over the shipped chain's document
 * plus its metadata rows (DD-391) — the merge, the metamodel Type row, the
 * three reference tables and their hide-when-empty conditions, and the ID line.
 */
const MODEL = parseAr3Model(fixture.model);
const ENTITIES = buildEntitiesById(MODEL);
const INDEXES = buildIndexes(MODEL);
const METADATA = fixture.metadata as LineageModelMetadata[];

const PROCESS = "00000000-0000-4000-8000-000000000002";
const DATASET = "00000000-0000-4000-8000-000000000001";
const RELATION = "rel-1";

function setup(id: string | null): {
    panel: LineageSelectionPanel;
    created: ComponentFixture<LineageSelectionPanel>;
    compiled: HTMLElement;
} {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
        imports: [LineageSelectionPanel],
        providers: [{ provide: Router, useValue: { navigate: vi.fn() } }],
    });
    const created = TestBed.createComponent(LineageSelectionPanel);
    created.componentRef.setInput("entity", id === null ? null : (ENTITIES.get(id) ?? null));
    created.componentRef.setInput("metadata", METADATA);
    created.componentRef.setInput("indexes", INDEXES);
    created.componentRef.setInput("entities", ENTITIES);
    created.componentRef.setInput("drawnViewId", "lineage_view");
    created.detectChanges();
    return { panel: created.componentInstance, created, compiled: created.nativeElement as HTMLElement };
}

function labels(compiled: HTMLElement): string[] {
    return [...compiled.querySelectorAll(".label")].map((node) => node.textContent?.trim() ?? "");
}

describe("LineageSelectionPanel (LDG-20..22)", () => {
    it("LDG-20: shows Name, Type (metamodel name), and the ID line for a process", () => {
        const { compiled } = setup(PROCESS);
        expect(labels(compiled)).toContain("Name");
        expect(compiled.textContent).toContain("Load Job");
        expect(labels(compiled)).toContain("Type");
        expect(compiled.textContent).toContain("Process");
        // The chain's metadata carries no description — the row hides.
        expect(labels(compiled)).not.toContain("Description");
        // The grey ID line: the legacy's "ID: <guid>".
        expect(compiled.querySelector(".aurelius-selection-id")?.textContent).toContain(PROCESS);
    });

    it("LDG-21: the Properties table is the merge with the metadata row's own values", () => {
        const { compiled } = setup(PROCESS);
        expect(labels(compiled)).toContain("Properties");
        const text = compiled.textContent ?? "";
        // The fixture chain's own rows: created_by, m4i_original_id (LDG-21).
        expect(text).toContain("created_by");
        expect(text).toContain("Model Extractor API");
        expect(text).toContain("m4i_original_id");
    });

    it("LDG-22: a selected relation shows its two ends under Referenced concepts", () => {
        const { compiled } = setup(RELATION);
        expect(labels(compiled)).toContain("Referenced concepts");
        // The relation's ends are the dataset and the process — both names list.
        const text = compiled.textContent ?? "";
        expect(text).toContain("Ingest Topic");
        expect(text).toContain("Load Job");
        // A relation touches nothing (no relation-of-a-relation) — hidden.
        expect(labels(compiled)).not.toContain("Referencing concepts");
    });

    it("LDG-22: a selected concept shows its relations and its containing view", () => {
        const { compiled } = setup(PROCESS);
        expect(labels(compiled)).toContain("Referencing concepts");
        expect(labels(compiled)).toContain("Referencing views");
        // The process is the end of both relations; the one view contains it.
        expect(labels(compiled)).not.toContain("Referenced concepts");
    });

    it("LDG-22: an entity with no metadata row shows no Properties table", () => {
        // A hand-built entity with no matching row and no own properties.
        const orphan: LineageEntity = {
            id: "ghost",
            kind: "element",
            name: "Ghost",
            type: "lineage_dataset",
            humanReadableType: "Dataset",
            description: "",
            properties: [],
            sourceName: "",
            targetName: "",
            sourceType: "",
            targetType: "",
        };
        TestBed.resetTestingModule();
        TestBed.configureTestingModule({ imports: [LineageSelectionPanel] });
        const created = TestBed.createComponent(LineageSelectionPanel);
        created.componentRef.setInput("entity", orphan);
        created.componentRef.setInput("metadata", []);
        created.componentRef.setInput("indexes", INDEXES);
        created.componentRef.setInput("entities", ENTITIES);
        created.detectChanges();
        const compiled = created.nativeElement as HTMLElement;
        expect(labels(compiled)).not.toContain("Properties");
    });

    it("DD-405: a selected element shows the search card; its title opens the details page", () => {
        const { compiled } = setup(PROCESS);
        const card = compiled.querySelector("aurelius-atlas-ui-entity-card");
        if (card === null) {
            throw new Error("the selection card is missing");
        }
        // The card is the results-screen's: the entity's name as the title.
        expect(card.textContent).toContain("Load Job");
        const title = card.querySelector(".title.is-4 a") as HTMLAnchorElement;
        title.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        // The results screen's rule: /search/details/<guid> — the shipped
        // chain's element id is the Atlas guid.
        expect(TestBed.inject(Router).navigate).toHaveBeenCalledWith(["/search/details", PROCESS]);
    });

    it("DD-405: a relation, node, or view selection shows no card (no details page to open)", () => {
        expect(setup(RELATION).compiled.querySelector("aurelius-atlas-ui-entity-card")).toBeNull();
        expect(setup("lineage_view").compiled.querySelector("aurelius-atlas-ui-entity-card")).toBeNull();
    });

    it("DD-414: the card sits under the Type field, where the demo's panel reads it", () => {
        const { compiled } = setup(PROCESS);
        const typeField = [...compiled.querySelectorAll(".field")].find(
            (node) => node.querySelector(".label")?.textContent?.trim() === "Type",
        );
        const card = compiled.querySelector("aurelius-atlas-ui-entity-card");
        if (typeField === undefined || card === null) {
            throw new Error("the Type field or the card is missing");
        }
        expect(typeField.compareDocumentPosition(card) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it("LDG-35/DD-418: the Type row inks an archimate glyph; its card badge stays plain", () => {
        // The full definitions table (DD-418): a Goal now answers the goal
        // glyph inked motivation under the Type row, while the card's badge
        // stays plain — the legacy's iconsByType carried no archimate entry.
        TestBed.resetTestingModule();
        TestBed.configureTestingModule({ imports: [LineageSelectionPanel] });
        const created = TestBed.createComponent(LineageSelectionPanel);
        const goal: LineageEntity = {
            id: "goal",
            kind: "element",
            name: "Reduce Cost",
            type: "ar3_Goal",
            humanReadableType: "Goal",
            description: "",
            properties: [],
            sourceName: "",
            targetName: "",
            sourceType: "",
            targetType: "",
        };
        created.componentRef.setInput("entity", goal);
        created.componentRef.setInput("metadata", []);
        created.componentRef.setInput("indexes", INDEXES);
        created.componentRef.setInput("entities", new Map([["goal", goal]]));
        created.componentRef.setInput("drawnViewId", null);
        created.detectChanges();
        const compiled = created.nativeElement as HTMLElement;

        const typePath = compiled.querySelector(".aurelius-selection-type .icon svg path");
        expect(typePath?.getAttribute("d")).toMatch(/^M 6\.1538 8 a/);
        expect(typePath?.classList.contains("motivation")).toBe(true);
        expect(compiled.textContent).toContain("Goal");
        // The badge: no glyph for an archimate type (DD-405's family stays
        // lineage-only — ar3BadgeClass answers none).
        expect(compiled.querySelector(".media-right .icon svg")).toBeNull();
    });

    it("LDG-35/DD-418: the shipped icon fills carry every AR3_ICON_FILLS rule", () => {
        // The panel's styles hold a literal copy of the glyph fills (the
        // builder drops an imported constant interpolated into a component's
        // styles, DD-418) — this pins every declaration, so the copy cannot
        // drift from the data the lookup answers.
        const def = (LineageSelectionPanel as unknown as { ɵcmp: { styles?: string[] } }).ɵcmp;
        const styles = (def.styles ?? []).join("\n");
        // The builder stamps a _ngcontent attribute after each selector part
        // and widens the descendant combinator, so every part may carry
        // attributes and the parts join on any whitespace.
        const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, (char) => `\\${char}`);
        for (const tableRule of AR3_ICON_FILLS.match(/\.[\w.-]+\s*\{[^}]*\}/g) ?? []) {
            const selector = `.aurelius-selection-type .icon ${tableRule.slice(0, tableRule.indexOf("{")).trim()}`;
            const declaration = tableRule.slice(tableRule.indexOf("{") + 1, tableRule.lastIndexOf("}")).trim();
            const property = declaration.slice(0, declaration.indexOf(":")).trim();
            const value = declaration
                .slice(declaration.indexOf(":") + 1)
                .replace(/;\s*$/, "")
                .trim();
            const selectorPattern = selector
                .split(/\s+/)
                .map((part) => escape(part) + "(?:\\[[^\\]]*\\])?")
                .join("\\s+");
            const pattern = new RegExp(
                `${selectorPattern}[^{]*\\{[^}]*${escape(property)}\\s*:\\s*${escape(value)}\\b`,
            );
            expect(styles, `the style block carries ${selector} { ${declaration} }`).toMatch(pattern);
        }
    });

    it("DD-414: the card's badge carries the lineage glyph in the type's ink", () => {
        // A process: the gear glyph, the process's teal (the badge's
        // technical-process family — #00d1b2, the diagram's own fill).
        const process = setup(PROCESS).compiled.querySelector("aurelius-atlas-ui-entity-card");
        const processIcon = process?.querySelector(".media-right .icon");
        expect(processIcon?.querySelector("svg")).toBeTruthy();
        expect(processIcon?.classList.contains("technical-process")).toBe(true);
        // A dataset: the table glyph in the dataset's blue.
        const dataset = setup(DATASET).compiled.querySelector("aurelius-atlas-ui-entity-card");
        const datasetIcon = dataset?.querySelector(".media-right .icon");
        expect(datasetIcon?.querySelector("svg")).toBeTruthy();
        expect(datasetIcon?.classList.contains("technical")).toBe(true);
        expect(datasetIcon?.classList.contains("technical-process")).toBe(false);
    });

    it("LDG-20: the Open-this-view button shows only for a view entity", () => {
        const { compiled } = setup("lineage_view");
        expect(compiled.querySelector(".aurelius-selection-open-view")).not.toBeNull();
        const { compiled: concept } = setup(DATASET);
        expect(concept.querySelector(".aurelius-selection-open-view")).toBeNull();
    });

    it("LDG-25: a reference-table row click emits the concept", () => {
        const { panel, created, compiled } = setup(PROCESS);
        const emitted: string[] = [];
        panel.conceptChosen.subscribe((id) => emitted.push(id));
        // The Referencing-concepts section (the first one after Properties):
        // its first row is a relation. Scope the click to that field — the
        // Properties table above it also holds rows.
        const field = [...compiled.querySelectorAll(".field")].find(
            (node) => node.querySelector(".label")?.textContent?.trim() === "Referencing concepts",
        );
        const row = field?.querySelector("tbody tr");
        row?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        created.detectChanges();
        expect(emitted).toEqual(["rel-1"]);
    });

    it("DD-412: the Referencing views table is the legacy's Name | Description shape", () => {
        const { created, compiled } = setup(PROCESS);
        const field = [...compiled.querySelectorAll(".field")].find(
            (node) => node.querySelector(".label")?.textContent?.trim() === "Referencing views",
        );
        if (field === undefined) {
            throw new Error("the Referencing views field is missing");
        }
        // The legacy's viewsTableConfig headers (raw, never translated) and
        // the row's th-scope-row name with the description cell beside it.
        const headers = [...field.querySelectorAll("thead th")].map((th) => th.textContent?.trim());
        expect(headers).toEqual(["Name", "Description"]);
        const viewRow = field.querySelector("tbody tr");
        expect(viewRow?.querySelector("th[scope='row']")?.textContent?.trim()).toBe("Lineage");
        // Not the entities table — no narrow Type column here.
        expect(field.querySelector("td.is-narrow")).toBeNull();
        // The drawn view is the selected row (the legacy's selectedView$).
        expect(viewRow?.classList.contains("is-selected")).toBe(true);
        // The drawn view is already the selected row: clicking it toggles to
        // a deselect, which emits nothing here — the shipped chain always
        // draws a view (LDG-12), so there is no "no view" to return to (the
        // deviation from the legacy's deselectView, recorded in the spec).
        const emitted: string[] = [];
        created.componentInstance.viewChosen.subscribe((id) => emitted.push(id));
        viewRow?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        created.detectChanges();
        expect(emitted).toEqual([]);
    });

    it("DD-412: with no drawn view, a Referencing views row click draws it", () => {
        TestBed.resetTestingModule();
        TestBed.configureTestingModule({
            imports: [LineageSelectionPanel],
            providers: [{ provide: Router, useValue: { navigate: vi.fn() } }],
        });
        const created = TestBed.createComponent(LineageSelectionPanel);
        created.componentRef.setInput("entity", ENTITIES.get(PROCESS) ?? null);
        created.componentRef.setInput("metadata", METADATA);
        created.componentRef.setInput("indexes", INDEXES);
        created.componentRef.setInput("entities", ENTITIES);
        created.componentRef.setInput("drawnViewId", null);
        created.detectChanges();
        const compiled = created.nativeElement as HTMLElement;
        const field = [...compiled.querySelectorAll(".field")].find(
            (node) => node.querySelector(".label")?.textContent?.trim() === "Referencing views",
        );
        const emitted: string[] = [];
        created.componentInstance.viewChosen.subscribe((id) => emitted.push(id));
        field?.querySelector("tbody tr")?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        created.detectChanges();
        expect(emitted).toEqual(["lineage_view"]);
    });
});
