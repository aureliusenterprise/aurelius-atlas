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

    it("clears the store from the clear-all button (ALR-06)", async () => {
        const alerts = setup();
        const { compiled } = await renderOpen(alerts);

        compiled.querySelector<HTMLButtonElement>(".aurelius-alert-clear")?.click();

        expect(alerts.alerts()).toHaveLength(0);
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
