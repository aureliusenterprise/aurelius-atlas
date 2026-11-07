import { ComponentFixture, TestBed } from "@angular/core/testing";
import { describe, expect, it } from "vitest";

import type { LineageEntity } from "./lineage-entities";
import { LineageModelTab } from "./model-tab.component";

/**
 * LDG-23: the Model tab's two tables and its keyword filter (DD-396: the
 * substring match, not the legacy fuzzy index). Hand-built entities — the
 * tables list the model's kinds, and the filter's behaviour is the rule.
 */
const ELEMENTS: LineageEntity[] = [
    {
        id: "e1",
        kind: "element",
        name: "Ingest Topic",
        type: "lineage_dataset",
        humanReadableType: "Dataset",
        description: "",
        properties: [],
        sourceName: "",
        targetName: "",
    },
    {
        id: "e2",
        kind: "element",
        name: "Sales Table",
        type: "lineage_dataset",
        humanReadableType: "Dataset",
        description: "",
        properties: [],
        sourceName: "",
        targetName: "",
    },
    {
        id: "e3",
        kind: "element",
        name: "Load Job",
        type: "lineage_process",
        humanReadableType: "Process",
        description: "",
        properties: [],
        sourceName: "",
        targetName: "",
    },
];
const RELATIONS: LineageEntity[] = [
    {
        id: "r1",
        kind: "relation",
        name: "feeds",
        type: "lineage_relation",
        humanReadableType: "Data Lineage",
        description: "",
        properties: [],
        sourceName: "Ingest Topic",
        targetName: "Sales Table",
    },
];

function setup(): {
    tab: LineageModelTab;
    setQuery: (query: string | null) => void;
    compiled: HTMLElement;
} {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ imports: [LineageModelTab] });
    const created = TestBed.createComponent(LineageModelTab);
    created.componentRef.setInput("elements", ELEMENTS);
    created.componentRef.setInput("relations", RELATIONS);
    created.detectChanges();
    const compiled = created.nativeElement as HTMLElement;
    const setQuery = (query: string | null) => {
        const input = compiled.querySelector("input[type='search']") as HTMLInputElement;
        input.value = query ?? "";
        input.dispatchEvent(new Event("input"));
        created.detectChanges();
    };
    return { tab: created.componentInstance, setQuery, compiled };
}

function bodyRows(compiled: HTMLElement): number {
    return compiled.querySelectorAll("table tbody tr").length;
}

/** The second table's rows — the Relationships table. */
function relationRows(compiled: HTMLElement): HTMLTableRowElement[] {
    const tables = [...compiled.querySelectorAll("table")];
    return [...(tables[1]?.querySelectorAll<HTMLTableRowElement>("tbody tr") ?? [])];
}

describe("LineageModelTab (LDG-23)", () => {
    it("LDG-23: the two tables list elements and relationships under their headings", () => {
        const { compiled } = setup();
        const labels = [...compiled.querySelectorAll(".label")].map((node) => node.textContent?.trim());
        expect(labels).toEqual(["Elements", "Relationships"]);
        expect(bodyRows(compiled)).toBe(4);
    });

    it("LDG-23: the keyword narrows both tables as typed, on name and type (DET-20 idiom)", () => {
        const { setQuery, compiled } = setup();
        setQuery("dataset");
        // Only the two datasets remain in the elements table; the relation's
        // "Data Lineage" does not contain "dataset" — both tables narrow.
        expect(bodyRows(compiled)).toBe(2);
        setQuery("lineage");
        // "Data Lineage" matches the relation; no dataset/process name or type
        // contains it — only the relation row stays.
        expect(bodyRows(compiled)).toBe(1);
        setQuery("LOAD");
        // Case-insensitive on name.
        expect(bodyRows(compiled)).toBe(1);
    });

    it("LDG-23: clearing the box restores both tables", () => {
        const { setQuery, compiled } = setup();
        setQuery("zzz-nothing");
        expect(bodyRows(compiled)).toBe(0);
        setQuery("");
        expect(bodyRows(compiled)).toBe(4);
    });

    it("LDG-25: a row click selects the concept", () => {
        const { tab, compiled } = setup();
        const emitted: string[] = [];
        tab.conceptChosen.subscribe((id) => emitted.push(id));
        const row = compiled.querySelector("table tbody tr");
        row?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        // The tables sort by the legacy's default (unsorted = source order):
        // the first element row is e1.
        expect(emitted).toEqual(["e1"]);
    });

    it("DD-404: a relationship row reads its ends — source → target", () => {
        const { compiled } = setup();
        const [row] = relationRows(compiled);
        expect(row?.textContent).toContain("Ingest Topic");
        expect(row?.textContent).toContain("→");
        expect(row?.textContent).toContain("Sales Table");
        // An element row keeps the plain name (no arrow).
        const elementRow = compiled.querySelector("table tbody tr");
        expect(elementRow?.textContent).toContain("Ingest Topic");
        expect(elementRow?.textContent).not.toContain("→");
    });

    it("DD-404: the keyword matches a relationship's displayed ends", () => {
        const { setQuery, compiled } = setup();
        // "Topic" names the relation's source — a word neither the relation's
        // name ("feeds") nor its type ("Data Lineage") carries.
        setQuery("Topic");
        expect(relationRows(compiled)).toHaveLength(1);
    });
});
