import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";

import type { AlertGroup } from "../alert-list/alert-group";
import { AlertInbox } from "./alert-inbox.component";

const group = (over: Partial<AlertGroup> = {}): AlertGroup => ({
    id: "g1",
    severity: "error",
    message: "Request failed: GET /api/entity 500",
    count: 1,
    lastSeen: Date.UTC(2026, 9, 21, 10, 30),
    read: true,
    ...over,
});

const feed = (): AlertGroup[] => [
    group({ id: "e1", severity: "error", message: "GET /api/x 500" }),
    group({ id: "e2", severity: "error", message: "GET /api/y 502", read: false }),
    group({ id: "w1", severity: "warning", message: "Slow query", read: false }),
    group({ id: "i1", severity: "info", message: "Saved", count: 3 }),
];

describe("AlertInbox (ALR-11, ALR-12)", () => {
    let fixture: ComponentFixture<AlertInbox>;

    const chips = () => [
        ...(fixture.nativeElement.querySelectorAll(".aurelius-alert-inbox-chip") as NodeListOf<HTMLButtonElement>),
    ];

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [AlertInbox],
        }).compileComponents();

        fixture = TestBed.createComponent(AlertInbox);
        fixture.detectChanges();
    });

    it("renders one chip per severity, inbox order (ALR-11)", () => {
        fixture.componentRef.setInput("alerts", feed());
        fixture.detectChanges();

        // The chip's parts: its label, its total tag (ALR-11). The
        // unread dot's sr-only label is the chip's fourth part, tested
        // on its own below. The ramp order is calm to urgent (DD-092).
        const labels = chips().map((c) => c.querySelector("span")?.textContent.trim());
        expect(labels.join(", ")).toMatchInlineSnapshot('"Info, Warnings, Errors"');
        const totals = chips().map((c) => c.querySelector(".aurelius-alert-inbox-count")?.textContent.trim());
        expect(totals.join(", ")).toMatchInlineSnapshot('"1, 1, 2"');
    });

    it("rides each chip in its severity's class (ALR-11, DD-092)", () => {
        fixture.componentRef.setInput("alerts", feed());
        fixture.detectChanges();

        // The fill is the severity's (the scss pins the pressed fills);
        // an unpressed chip stays a plain Bulma button — `is-selected`
        // gates the colour, the severity class only names it.
        expect(chips().map((c) => [...c.classList].find((k) => k.startsWith("is-sev-")))).toEqual([
            "is-sev-info",
            "is-sev-warning",
            "is-sev-error",
        ]);
        expect(chips().every((c) => c.classList.contains("is-selected"))).toBe(true);

        fixture.componentRef.setInput("hidden", ["warning"]);
        fixture.detectChanges();
        expect(chips()[1].classList.contains("is-selected")).toBe(false);
    });

    it("shows each severity's total, not its unread count (ALR-11)", () => {
        fixture.componentRef.setInput("alerts", feed());
        fixture.detectChanges();

        const counts = [
            ...(fixture.nativeElement.querySelectorAll(".aurelius-alert-inbox-count") as NodeListOf<HTMLElement>),
        ];
        // e2 (error) and w1 (warning) are unread; the totals stay the
        // feed's coverage, in inbox order.
        expect(counts.map((c) => c.textContent.trim())).toEqual(["1", "1", "2"]);
    });

    it("dots a severity with unread groups and names the dot (ALR-12)", () => {
        fixture.componentRef.setInput("alerts", feed());
        fixture.detectChanges();

        const dots = [
            ...(fixture.nativeElement.querySelectorAll(".aurelius-alert-inbox-unread") as NodeListOf<HTMLElement>),
        ];
        expect(dots).toHaveLength(2); // warning (w1) and error (e2), inbox order
        // The dot rides the chip's ink (the scss) — the chip's face is
        // the severity's colour now (DD-092), a ramp-coloured dot would
        // ride its own colour. The dot is decorative; the sr-only label
        // carries the meaning.
        expect(dots[0].closest("button")?.textContent).toContain("Warnings");
        expect(dots[1].closest("button")?.textContent).toContain("Errors");
        expect(dots[0].getAttribute("aria-hidden")).toBe("true");
        expect(fixture.nativeElement.textContent).toContain("Unread");
    });

    it("shows every chip pressed on the default empty filter (ALR-11)", () => {
        fixture.componentRef.setInput("alerts", feed());
        fixture.detectChanges();

        expect(chips().map((c) => c.getAttribute("aria-pressed"))).toEqual(["true", "true", "true"]);
        expect(chips().every((c) => c.classList.contains("is-selected"))).toBe(true);
    });

    it("un-presses a hidden severity's chip (ALR-11)", () => {
        fixture.componentRef.setInput("alerts", feed());
        fixture.componentRef.setInput("hidden", ["warning"]);
        fixture.detectChanges();

        expect(chips().map((c) => c.getAttribute("aria-pressed"))).toEqual(["true", "false", "true"]);
        expect(chips()[1].classList.contains("is-selected")).toBe(false);
    });

    it("emits the severity on a chip click (ALR-11)", () => {
        fixture.componentRef.setInput("alerts", feed());
        fixture.detectChanges();
        const severities: string[] = [];
        fixture.componentInstance.toggleSeverity.subscribe((s) => severities.push(s));

        chips()[1].click();

        expect(severities).toEqual(["warning"]);
    });

    it("shows the show-all control only when every severity is hidden (ALR-11)", () => {
        fixture.componentRef.setInput("alerts", feed());
        fixture.detectChanges();
        expect(fixture.nativeElement.querySelector(".aurelius-alert-inbox-show-all")).toBeNull();

        fixture.componentRef.setInput("hidden", ["error", "warning", "info"]);
        fixture.detectChanges();
        const showAll = fixture.nativeElement.querySelector(".aurelius-alert-inbox-show-all") as HTMLButtonElement;
        expect(showAll.textContent.trim()).toBe("Show all");

        const calls: number[] = [];
        fixture.componentInstance.showAll.subscribe(() => calls.push(1));
        showAll.click();
        expect(calls).toEqual([1]);
    });

    it("joins show-all and the projected action into the addons group (DD-092)", () => {
        fixture.componentRef.setInput("alerts", feed());
        fixture.componentRef.setInput("hidden", ["error", "warning", "info"]);
        fixture.detectChanges();

        // One joined bar: every segment is an expanded member of the
        // same `buttons has-addons` group.
        const group = fixture.nativeElement.querySelector(".aurelius-alert-inbox-group");
        const showAll = group.querySelector(".aurelius-alert-inbox-show-all");
        expect(showAll.classList.contains("is-expanded")).toBe(true);
        expect(showAll.parentElement).toBe(group);
    });

    it("uses the caller's labels (ALR-08)", () => {
        fixture.componentRef.setInput("alerts", feed());
        fixture.componentRef.setInput("severityLabels", { error: "Fouten", warning: "Waarschuwingen", info: "Info" });
        fixture.componentRef.setInput("unreadLabel", "Ongelezen");
        fixture.componentRef.setInput("ariaLabel", "Meldingsfilters");
        fixture.detectChanges();

        expect(chips()[2].textContent).toContain("Fouten");
        expect(chips()[1].textContent).toContain("Waarschuwingen");
        expect(fixture.nativeElement.textContent).toContain("Ongelezen");
        expect(fixture.nativeElement.querySelector(".aurelius-alert-inbox").getAttribute("aria-label")).toBe(
            "Meldingsfilters",
        );
    });

    it("counts an empty feed as three empty severities (ALR-11)", () => {
        fixture.componentRef.setInput("alerts", []);
        fixture.detectChanges();

        // A filter with no results is still a filter: the bar keeps its
        // shape, the counts read zero.
        expect(chips()).toHaveLength(3);
        const counts = [
            ...(fixture.nativeElement.querySelectorAll(".aurelius-alert-inbox-count") as NodeListOf<HTMLElement>),
        ];
        expect(counts.map((c) => c.textContent.trim())).toEqual(["0", "0", "0"]);
    });

    it("projects the caller's action into the strip (DD-090)", async () => {
        @Component({
            imports: [AlertInbox],
            template: `<aurelius-atlas-ui-alert-inbox>
                <button type="button" class="button is-small is-expanded aurelius-alert-clear">Clear all</button>
            </aurelius-atlas-ui-alert-inbox>`,
        })
        class Host {}

        await TestBed.compileComponents();
        const hostFixture = TestBed.createComponent(Host);
        hostFixture.detectChanges();

        const group = hostFixture.nativeElement.querySelector(".aurelius-alert-inbox-group");
        const clear = group.querySelector(".aurelius-alert-clear");
        expect(clear?.textContent.trim()).toBe("Clear all");
        // The caller's contract: the action joins the bar as an expanded
        // member of the addons group, the strip's last segment (DD-092).
        expect(clear?.classList.contains("is-expanded")).toBe(true);
    });
});
