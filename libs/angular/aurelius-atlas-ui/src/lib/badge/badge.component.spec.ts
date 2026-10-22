import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { Badge } from "./badge.component";

describe("Badge (ALR-02, ALR-10)", () => {
    let fixture: ComponentFixture<Badge>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [Badge],
        }).compileComponents();

        fixture = TestBed.createComponent(Badge);
        fixture.detectChanges();
    });

    it("hides the dot while not visible (ALR-02)", () => {
        expect(fixture.nativeElement.querySelector(".aurelius-badge-dot")).toBeNull();
    });

    it("shows the dot when visible (ALR-02)", () => {
        fixture.componentRef.setInput("visible", true);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector(".aurelius-badge-dot")).toBeTruthy();
    });

    it("maps the severity to the ramp (ALR-02)", () => {
        fixture.componentRef.setInput("visible", true);
        for (const severity of ["error", "warning", "info"] as const) {
            fixture.componentRef.setInput("severity", severity);
            fixture.detectChanges();
            expect(
                fixture.nativeElement.querySelector(".aurelius-badge-dot").classList.contains(`is-${severity}`),
            ).toBe(true);
        }
    });

    it("is decorative to the accessibility tree (ALR-02)", () => {
        // The dot sits inside the bell link: a labelled element would join
        // the link's accessible name, so the dot is aria-hidden with the
        // caller's label as its tooltip.
        fixture.componentRef.setInput("visible", true);
        fixture.componentRef.setInput("label", "Meldingen");
        fixture.detectChanges();

        const dot = fixture.nativeElement.querySelector(".aurelius-badge-dot");
        expect(dot.getAttribute("aria-hidden")).toBe("true");
        expect(dot.getAttribute("title")).toBe("Meldingen");
    });

    it("projects the wrapped content (ALR-10)", () => {
        const hosted = TestBed.createComponent(HostComponent);
        hosted.detectChanges();

        expect(hosted.nativeElement.querySelector(".aurelius-badge > .button")).toBeTruthy();
    });
});

@Component({
    imports: [Badge],
    selector: "aurelius-atlas-ui-badge-host",
    template: `
        <aurelius-atlas-ui-badge [visible]="true">
            <button type="button" class="button">bell</button>
        </aurelius-atlas-ui-badge>
    `,
})
class HostComponent {}
