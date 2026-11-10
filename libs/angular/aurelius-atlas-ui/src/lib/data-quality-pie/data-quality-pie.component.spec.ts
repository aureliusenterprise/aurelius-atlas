import { ComponentFixture, TestBed } from "@angular/core/testing";

import { DataQualityPie } from "./data-quality-pie.component";

describe("DataQualityPie", () => {
    let component: DataQualityPie;
    let fixture: ComponentFixture<DataQualityPie>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [DataQualityPie],
        }).compileComponents();

        fixture = TestBed.createComponent(DataQualityPie);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("renders the two pie layers, the ring under the arc (UIC-36)", () => {
        fixture.componentRef.setInput("value", 82);
        fixture.detectChanges();

        const pies = fixture.nativeElement.querySelectorAll(".pie.no-round.animate");
        expect(pies).toHaveLength(2);
        // jsdom normalises the static style attribute ("--p: 100; --c: …").
        expect(pies[0].getAttribute("style")).toContain("--p: 100");
        expect(pies[0].getAttribute("style")).toContain("hsl(348, 100%, 61%)");
    });

    it("drives the arc with the value and the ring with the size (UIC-36)", () => {
        fixture.componentRef.setInput("value", 42);
        fixture.componentRef.setInput("size", 6);
        fixture.detectChanges();

        const arc = fixture.nativeElement.querySelectorAll(".pie")[1] as HTMLElement;
        expect(arc.style.getPropertyValue("--p")).toBe("42");
        expect(arc.style.getPropertyValue("--b")).toBe("6px");
        expect(arc.getAttribute("style")).toContain("hsl(141, 53%, 53%)");
    });

    it("defaults to size 4, as the legacy input default (UIC-36)", () => {
        fixture.componentRef.setInput("value", 10);
        fixture.detectChanges();

        const arc = fixture.nativeElement.querySelectorAll(".pie")[1] as HTMLElement;
        expect(arc.style.getPropertyValue("--b")).toBe("4px");
    });

    it("carries the percent as the host title (UIC-36)", () => {
        fixture.componentRef.setInput("value", 73.5);
        fixture.detectChanges();

        expect((fixture.nativeElement as HTMLElement).getAttribute("title")).toBe("73.5%");
        expect(component.value()).toBe(73.5);
    });
});
