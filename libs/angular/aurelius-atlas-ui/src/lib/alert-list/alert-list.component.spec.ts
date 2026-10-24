import { ComponentFixture, TestBed } from "@angular/core/testing";

import type { AlertGroup } from "./alert-group";
import { AlertList } from "./alert-list.component";

const group = (over: Partial<AlertGroup> = {}): AlertGroup => ({
    id: "g1",
    severity: "error",
    message: "Request failed: GET /api/entity 500",
    count: 1,
    lastSeen: Date.UTC(2026, 9, 21, 10, 30),
    read: true,
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

    it("carries no clear-all button (ALR-06, DD-176)", () => {
        fixture.componentRef.setInput("alerts", [group()]);
        fixture.detectChanges();

        // Clearing the feed is the caller's action, placed in the
        // drawer's head slot (DD-176) — the list is only the rows, so
        // it has no clear control to bury in a long feed.
        expect(fixture.nativeElement.querySelector(".aurelius-alert-clear")).toBeNull();
        expect(fixture.nativeElement.querySelector("button:not(.delete)")).toBeNull();
    });

    it("pins the count chip's pair, not Bulma's scheme-following is-light (ALR-07, DD-176)", () => {
        fixture.componentRef.setInput("alerts", [group({ id: "burst", count: 3 })]);
        fixture.detectChanges();

        const chip = fixture.nativeElement.querySelector(".aurelius-alert-count");
        // `is-light` is a scheme trap: the brand pins the light plate,
        // Bulma re-pins its ink — white-on-white in dark mode.
        expect(chip.classList.contains("is-light")).toBe(false);
    });

    it("marks an unread row, read rows carry no marker (ALR-12)", () => {
        fixture.componentRef.setInput("alerts", [group({ id: "u1", read: false }), group({ id: "r1", read: true })]);
        fixture.detectChanges();

        const rows = [...(fixture.nativeElement.querySelectorAll(".notification") as NodeListOf<HTMLElement>)];
        expect(rows[0].classList.contains("aurelius-alert-unread")).toBe(true);
        expect(rows[1].classList.contains("aurelius-alert-unread")).toBe(false);
        expect(rows[0].querySelector(".aurelius-alert-unread-dot")).toBeTruthy();
        expect(rows[1].querySelector(".aurelius-alert-unread-dot")).toBeNull();
        // The dot is decorative; the sr-only label carries the meaning.
        expect(rows[0].querySelector(".aurelius-alert-unread-dot")?.getAttribute("aria-hidden")).toBe("true");
        expect(rows[0].textContent).toContain("Unread");
    });

    it("names the unread marker with the caller's label (ALR-08, ALR-12)", () => {
        fixture.componentRef.setInput("alerts", [group({ read: false })]);
        fixture.componentRef.setInput("unreadLabel", "Ongelezen");
        fixture.detectChanges();

        expect(fixture.nativeElement.textContent).toContain("Ongelezen");
    });

    it("names the dismiss control with the caller's label (ALR-08)", () => {
        fixture.componentRef.setInput("alerts", [group()]);
        fixture.componentRef.setInput("dismissLabel", "Sluiten");
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector(".notification .delete").getAttribute("aria-label")).toBe("Sluiten");
    });
});
