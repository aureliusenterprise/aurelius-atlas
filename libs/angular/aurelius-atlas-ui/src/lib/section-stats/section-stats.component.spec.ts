import { ComponentFixture, TestBed } from "@angular/core/testing";

import { SectionStat, SectionStats } from "./section-stats.component";

describe("SectionStats", () => {
    let component: SectionStats;
    let fixture: ComponentFixture<SectionStats>;

    const items: SectionStat[] = [
        { label: "Non-compliant", target: "related-non-compliants", count: 3 },
        { label: "Compliant", target: "related-compliants", count: 12 },
        { label: "Properties", target: "properties-details", count: 27 },
    ];

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [SectionStats],
        }).compileComponents();

        fixture = TestBed.createComponent(SectionStats);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("renders the level bar with one item per stat (UIC-19)", () => {
        fixture.componentRef.setInput("items", items);
        fixture.detectChanges();

        const nav = fixture.nativeElement.querySelector("nav.level");
        expect(nav).toBeTruthy();
        const stats = nav.querySelectorAll(".level-item.has-text-centered");
        expect(stats).toHaveLength(3);
        expect(stats[0].querySelector("p.heading a").textContent.trim()).toBe("Non-compliant");
        expect(stats[0].querySelector("p.title").textContent.trim()).toBe("3");
    });

    it("links each heading to its section id (UIC-19)", () => {
        fixture.componentRef.setInput("items", items);
        fixture.detectChanges();

        const anchors = fixture.nativeElement.querySelectorAll("p.heading a");
        expect(anchors[2].getAttribute("href")).toBe("#properties-details");
    });

    it("renders the caller's count as text (UIC-19, DD-192)", () => {
        fixture.componentRef.setInput("items", [{ label: "Properties", target: "properties-details", count: "0" }]);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("p.title").textContent.trim()).toBe("0");
    });

    it("renders the one-stat bar, as the default details screen used it (UIC-19)", () => {
        fixture.componentRef.setInput("items", [{ label: "Properties", target: "properties-details", count: 0 }]);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelectorAll(".level-item")).toHaveLength(1);
    });

    it("emits itemClicked with the target, cancelling the fragment jump (UIC-19, DD-154)", () => {
        fixture.componentRef.setInput("items", items);
        fixture.detectChanges();
        const clicked: string[] = [];
        component.itemClicked.subscribe((target) => clicked.push(target));

        const anchor: HTMLAnchorElement = fixture.nativeElement.querySelectorAll("p.heading a")[1];
        anchor.click();

        expect(clicked).toEqual(["related-compliants"]);
        expect(anchor.getAttribute("href")).toBe("#related-compliants");
    });

    it("renders an empty bar with no items, as the legacy bars did (UIC-19)", () => {
        expect(fixture.nativeElement.querySelector("nav.level")).toBeTruthy();
        expect(fixture.nativeElement.querySelectorAll(".level-item")).toHaveLength(0);
    });
});
