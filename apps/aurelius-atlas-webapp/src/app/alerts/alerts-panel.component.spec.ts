/**
 * The alerts panel (ALR-01, ALR-06, ALR-07): the routed drawer the header
 * bell opens, showing the store through the ui-lib AlertList. The panel
 * stores nothing, so the specs are the panel's own wiring: it renders
 * open with the feed (ALR-01), the rows come from the store (ALR-07),
 * dismissal writes through the service (ALR-06), and closing navigates
 * the `drawer` outlet away (DD-078's pattern, ALR-01). The store's own
 * grouping and the feed's rendering are specced at the owner.
 */
import { TestBed } from "@angular/core/testing";
import { Router, provideRouter } from "@angular/router";

import { AlertsService } from "./alerts.service";
import { AlertsPanel } from "./alerts-panel.component";

function setup() {
    TestBed.configureTestingModule({
        imports: [AlertsPanel],
        providers: [AlertsService, provideRouter([])],
    });

    return TestBed.inject(AlertsService);
}

/** The rendered, open panel: the routed component opens at construction (SPL-14's shape). */
async function renderOpen(alerts: AlertsService) {
    alerts.add({ severity: "error", message: "GET /api/x 500", source: "http" });
    alerts.add({ severity: "info", message: "Saved", source: "app" });

    const fixture = TestBed.createComponent(AlertsPanel);
    fixture.detectChanges();
    await fixture.whenStable();

    return { fixture, compiled: fixture.nativeElement as HTMLElement };
}

describe("AlertsPanel (ALR-01, ALR-06, ALR-07)", () => {
    it("renders open with the store's feed (ALR-01, ALR-07)", async () => {
        const alerts = setup();
        const { compiled } = await renderOpen(alerts);

        const dialog = compiled.querySelector('[role="dialog"]');
        expect(dialog?.textContent).toContain("Alerts");
        // Newest first, as the store orders them (ALR-03).
        const rows = compiled.querySelectorAll(".notification");
        expect(rows).toHaveLength(2);
        expect(rows[0].textContent).toContain("Saved");
        expect(compiled.querySelector(".aurelius-alert-list")).toBeTruthy();
    });

    it("renders the empty state on an empty store (ALR-07)", async () => {
        const alerts = setup();
        const fixture = TestBed.createComponent(AlertsPanel);
        fixture.detectChanges();
        await fixture.whenStable();

        expect((fixture.nativeElement as HTMLElement).querySelector(".aurelius-alert-empty")).toBeTruthy();
    });

    it("dismisses a row through the store (ALR-06)", async () => {
        const alerts = setup();
        const { compiled } = await renderOpen(alerts);
        const before = alerts.alerts().length;

        compiled.querySelector(".notification .delete")?.dispatchEvent(new MouseEvent("click"));

        expect(alerts.alerts()).toHaveLength(before - 1);
    });

    it("clears the store from the clear-all button in the inbox bar (ALR-06, DD-090)", async () => {
        const alerts = setup();
        const { fixture, compiled } = await renderOpen(alerts);

        // The escape hatch rides the fixed strip under the head (DD-090),
        // not the scrolling feed, and only shows while the store has alerts.
        const clear = compiled.querySelector<HTMLButtonElement>(".aurelius-alert-inbox .aurelius-alert-clear");
        expect(clear).toBeTruthy();
        clear?.click();

        expect(alerts.alerts()).toHaveLength(0);
        // With the store empty, the bar goes too (ALR-06, ALR-11).
        fixture.detectChanges();
        expect(compiled.querySelector(".aurelius-alert-inbox")).toBeNull();
    });

    it("marks the feed read while the drawer is open (ALR-12, DD-090)", async () => {
        const alerts = setup();
        alerts.add({ severity: "error", message: "GET /api/x 500", source: "http" });
        expect(alerts.hasUnread()).toBe(true); // the row arrives unread…

        const fixture = TestBed.createComponent(AlertsPanel);
        fixture.detectChanges();
        await fixture.whenStable();
        TestBed.flushEffects();

        // …and opening the drawer is reading it (ALR-12).
        expect(alerts.hasUnread()).toBe(false);
    });

    it("filters the feed by severity chip (ALR-11)", async () => {
        const alerts = setup();
        const { fixture, compiled } = await renderOpen(alerts); // one error, one info

        const chips = [...(compiled.querySelectorAll(".aurelius-alert-inbox-chip") as NodeListOf<HTMLButtonElement>)];
        expect(chips).toHaveLength(3); // one per severity, always (ALR-11)

        chips[0].click(); // hide info (inbox order: info, warning, error)
        fixture.detectChanges();
        expect(compiled.querySelectorAll(".notification")).toHaveLength(1);
        expect(compiled.querySelector(".notification")?.textContent).toContain("500");

        chips[0].click(); // show them again — the chip toggles
        fixture.detectChanges();
        expect(compiled.querySelectorAll(".notification")).toHaveLength(2);
    });

    it("keeps the chips' counts on the whole store while filtered (ALR-11)", async () => {
        const alerts = setup();
        const { fixture, compiled } = await renderOpen(alerts);

        // Hide the severities with rows: the chips still show the store's
        // totals — a filter with no results is still a filter, and the
        // bell's dot answers with the store, not the view.
        const chips = [...(compiled.querySelectorAll(".aurelius-alert-inbox-chip") as NodeListOf<HTMLButtonElement>)];
        chips[0].click(); // info off
        chips[2].click(); // errors off
        fixture.detectChanges();

        const counts = [...(compiled.querySelectorAll(".aurelius-alert-inbox-count") as NodeListOf<HTMLElement>)];
        expect(counts.map((c) => c.textContent.trim())).toEqual(["1", "0", "1"]);
        expect(compiled.querySelector(".aurelius-alert-empty")).toBeTruthy(); // the feed is empty

        // Every chip off: the show-all control appears (ALR-11).
        const showAll = compiled.querySelector<HTMLButtonElement>(".aurelius-alert-inbox-show-all");
        expect(showAll).toBeTruthy();
        showAll?.click();
        fixture.detectChanges();
        expect(compiled.querySelectorAll(".notification")).toHaveLength(2);
    });

    it("navigates the drawer outlet away on dismissal (ALR-01, DD-078)", async () => {
        const alerts = setup();
        const { compiled } = await renderOpen(alerts);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        // The drawer's close button dismisses (SPL-02's anatomy): the
        // panel flips its state and navigates the outlet away.
        compiled.querySelector(".aurelius-drawer-head .delete")?.dispatchEvent(new MouseEvent("click"));

        expect(navigate).toHaveBeenCalledWith([{ outlets: { drawer: null } }]);
    });
});
