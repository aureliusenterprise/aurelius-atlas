import { ComponentFixture, TestBed } from "@angular/core/testing";

import { QualityDimensionList, QualityDimensionRow } from "./quality-dimension-list.component";

/** The legacy's five-dimension set, as an entity's App Search document carried it. */
const dimensions: QualityDimensionRow[] = [
    { dimension: "accuracy", score: 0.92, count: 34 },
    { dimension: "completeness", score: 0.66, count: 12 },
    { dimension: "timeliness", score: 0.5, count: 3 },
];

describe("QualityDimensionList", () => {
    let fixture: ComponentFixture<QualityDimensionList>;

    async function setup(rows: QualityDimensionRow[], notAvailable = "No data quality results available") {
        await TestBed.configureTestingModule({ imports: [QualityDimensionList] }).compileComponents();
        fixture = TestBed.createComponent(QualityDimensionList);
        fixture.componentRef.setInput("dimensions", rows);
        fixture.componentRef.setInput("notAvailable", notAvailable);
        fixture.detectChanges();
        return fixture.nativeElement as HTMLElement;
    }

    it("renders one row per dimension, in order (UIC-37)", async () => {
        const el = await setup(dimensions);

        const rows = el.querySelectorAll(".control .quality-dimension");
        expect(rows).toHaveLength(3);
        expect(rows[0].textContent).toContain("accuracy");
        expect(rows[0].textContent).toContain("(34)");
        expect(rows[1].textContent).toContain("completeness");
    });

    it("renders the score in the legacy's percent form, up to one decimal (UIC-37)", async () => {
        const el = await setup([
            { dimension: "accuracy", score: 0.92, count: 34 },
            { dimension: "validity", score: 0.925, count: 2 },
        ]);

        // The legacy pipe arg '1.0-1' carries min 0, max 1 decimals. The
        // legacy's separators are &nbsp; (U+00A0), which jsdom keeps.
        const scores = el.querySelectorAll(".quality-score");
        expect(scores[0]?.textContent).toBe("92%\u00a0accuracy\u00a0(34)");
        expect(scores[1]?.textContent).toBe("92.5%\u00a0validity\u00a0(2)");
    });

    it("drives the pie with the scaled score (UIC-37)", async () => {
        const el = await setup([{ dimension: "validity", score: 0.75, count: 5 }]);

        const pie = el.querySelector("aurelius-atlas-ui-data-quality-pie") as HTMLElement;
        expect(pie.getAttribute("title")).toBe("75%");
    });

    it("shows the placeholder for the empty list (UIC-37)", async () => {
        const el = await setup([]);

        expect(el.querySelector(".quality-dimension")).toBeNull();
        expect(el.querySelector(".aurelius-quality-not-available")?.textContent).toBe(
            "No data quality results available",
        );
    });

    it("renders nothing when the placeholder is empty, the legacy's showPlaceholder off (UIC-37)", async () => {
        const el = await setup([], "");

        expect(el.querySelector(".aurelius-quality-not-available")).toBeNull();
        expect(el.querySelector(".field.is-grouped")).toBeNull();
    });
});
