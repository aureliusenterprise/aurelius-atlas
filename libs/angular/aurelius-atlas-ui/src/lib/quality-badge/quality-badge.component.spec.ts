import { ComponentFixture, TestBed } from "@angular/core/testing";

import { QualityBadge } from "./quality-badge.component";

describe("QualityBadge", () => {
    let fixture: ComponentFixture<QualityBadge>;

    async function setup(score: number) {
        await TestBed.configureTestingModule({ imports: [QualityBadge] }).compileComponents();
        fixture = TestBed.createComponent(QualityBadge);
        fixture.componentRef.setInput("score", score);
        fixture.detectChanges();
        return fixture.nativeElement as HTMLElement;
    }

    it("renders the pie beside the one-decimal percent (UIC-39)", async () => {
        const el = await setup(0.925);

        const pie = el.querySelector("aurelius-atlas-ui-data-quality-pie") as HTMLElement;
        expect(pie.getAttribute("title")).toBe("92.5%");
        expect(el.querySelector(".quality-score")?.textContent).toContain("92.5%");
    });

    it("renders zero honestly, not hidden (UIC-39)", async () => {
        const el = await setup(0);

        // The legacy pipe arg '1.0-1' carries min 0, max 1 decimals: whole percents print bare.
        expect(el.querySelector(".quality-score")?.textContent?.trim()).toBe("0%");
    });
});
