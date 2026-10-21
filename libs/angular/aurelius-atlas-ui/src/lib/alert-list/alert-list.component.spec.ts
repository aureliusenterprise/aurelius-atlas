import { ComponentFixture, TestBed } from "@angular/core/testing";

import type { AlertGroup } from "./alert-group";
import { AlertList } from "./alert-list.component";

const group = (over: Partial<AlertGroup> = {}): AlertGroup => ({
    id: "g1",
    severity: "error",
    message: "Request failed: GET /api/entity 500",
    count: 1,
    lastSeen: Date.UTC(2026, 9, 21, 10, 30),
    ...over,
});

describe("AlertList (ALR-07, ALR-09, ALR-10)", () => {
    let fixture: ComponentFixture<AlertList>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [AlertList],
        }).compileComponents();

        fixture = TestBed.createComponent(AlertList);
        fixture.detectChanges();
    });

    it("renders the empty state when there are no alerts (ALR-07)", () => {
        expect(fixture.nativeElement.querySelector(".aurelius-alert-empty").textContent.trim()).toBe("No alerts");
        expect(fixture.nativeElement.querySelector(".notification")).toBeNull();
    });

    it("uses the caller's empty label (ALR-08, ALR-10)", () => {
        fixture.componentRef.setInput("emptyLabel", "Geen meldingen");
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector(".aurelius-alert-empty").textContent.trim()).toBe("Geen meldingen");
    });

    it("renders one severity-coloured notification per group (ALR-07)", () => {
        fixture.componentRef.setInput("alerts", [
            group(),
            group({ id: "g2", severity: "warning", message: "Slow response" }),
            group({ id: "g3", severity: "info", message: "Saved" }),
        ]);
        fixture.detectChanges();

        const rows = [...(fixture.nativeElement.querySelectorAll(".notification") as NodeListOf<HTMLElement>)];
        expect(rows.map((r) => r.classList.contains("is-danger"))).toEqual([true, false, false]);
        expect(rows.map((r) => r.classList.contains("is-warning"))).toEqual([false, true, false]);
        expect(rows.map((r) => r.classList.contains("is-info"))).toEqual([false, false, true]);
        expect(rows[0].querySelector(".aurelius-alert-message")?.textContent.trim()).toContain("GET /api/entity 500");
    });

    it("shows the burst chip only above one (ALR-07)", () => {
        fixture.componentRef.setInput("alerts", [group({ id: "solo" }), group({ id: "burst", count: 7 })]);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelectorAll(".aurelius-alert-count")).toHaveLength(1);
        expect(fixture.nativeElement.querySelector(".aurelius-alert-count").textContent.trim()).toBe("×7");
    });

    it("renders the row's time as a <time> (ALR-07)", () => {
        fixture.componentRef.setInput("alerts", [group()]);
        fixture.detectChanges();

        const time = fixture.nativeElement.querySelector("time");
        expect(time.getAttribute("datetime")).toBe(String(Date.UTC(2026, 9, 21, 10, 30)));
        expect(time.textContent.trim()).not.toBe("");
    });

    it("is a polite live region with the caller's label (ALR-09)", () => {
        fixture.componentRef.setInput("alerts", [group()]);
        fixture.componentRef.setInput("ariaLabel", "Meldingen");
        fixture.detectChanges();

        const list = fixture.nativeElement.querySelector(".aurelius-alert-list");
        expect(list.getAttribute("role")).toBe("log");
        expect(list.getAttribute("aria-live")).toBe("polite");
        expect(list.getAttribute("aria-label")).toBe("Meldingen");
    });

    it("emits dismiss with the row's id (ALR-06, ALR-10)", () => {
        fixture.componentRef.setInput("alerts", [group({ id: "g7" })]);
        fixture.detectChanges();
        const ids: string[] = [];
        fixture.componentInstance.dismiss.subscribe((id) => ids.push(id));

        fixture.nativeElement.querySelector(".notification .delete").click();
        fixture.detectChanges();

        expect(ids).toEqual(["g7"]);
    });

    it("emits clearAll from the clear button (ALR-06, ALR-10)", () => {
        fixture.componentRef.setInput("alerts", [group()]);
        fixture.detectChanges();
        const clear = vi.fn();
        fixture.componentInstance.clearAll.subscribe(clear);

        fixture.nativeElement.querySelector(".aurelius-alert-clear").click();

        expect(clear).toHaveBeenCalled();
    });

    it("has no clear button in the empty state (ALR-06)", () => {
        expect(fixture.nativeElement.querySelector(".aurelius-alert-clear")).toBeNull();
    });

    it("names the dismiss control with the caller's label (ALR-08)", () => {
        fixture.componentRef.setInput("alerts", [group()]);
        fixture.componentRef.setInput("dismissLabel", "Sluiten");
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector(".notification .delete").getAttribute("aria-label")).toBe("Sluiten");
    });
});
