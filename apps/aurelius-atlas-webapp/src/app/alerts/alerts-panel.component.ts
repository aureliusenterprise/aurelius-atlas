import { ChangeDetectionStrategy, Component, inject, signal } from "@angular/core";
import { Router } from "@angular/router";
import { AlertList, Drawer } from "aurelius-atlas-ui";

import { AlertsService } from "./alerts.service";

/**
 * The alerts panel (ALR-01, ALR-06, ALR-07): the drawer the header bell
 * opens, showing the {@link AlertsService} store through the ui-lib
 * {@link AlertList}. The panel stores nothing — dismissal (per group and
 * clear-all) writes through the service (ALR-06), the feed renders what
 * the store holds (ALR-03).
 *
 * Like the settings panel, it is a routed component in the `drawer` aux
 * outlet (SPL-14's shape, DD-078, ALR-01): the bell navigates to it,
 * dismissal navigates away, and the outlet segment rides the URL — so
 * the language switch's full-page navigation (SPL-06) reloads the same
 * page with the drawer open. The one named outlet swaps drawers: opening
 * alerts replaces the settings panel and vice versa.
 */
@Component({
    imports: [AlertList, Drawer],
    selector: "aurelius-atlas-webapp-alerts-panel",
    templateUrl: "./alerts-panel.component.html",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AlertsPanel {
    protected readonly alerts = inject(AlertsService);

    private readonly router = inject(Router);

    /**
     * The drawer's open state, two-way bound to the ui-lib drawer. True
     * for the component's whole life: the routed panel exists only while
     * open, and dismissal flips it before navigating away (the settings
     * panel's pattern, SPL-14).
     */
    readonly active = signal(true);

    /** The drawer's accessible title (SPL-02's pattern). Strings bound into inputs use `$localize` (BRW-02). */
    protected readonly title = $localize`:@@shell.alerts.title:Alerts`;

    /** Accessible name of the drawer's close control. */
    protected readonly closeLabel = $localize`:@@shell.alerts.close:Close`;

    /** Accessible name of the feed (the live region's label, ALR-09). */
    protected readonly feedLabel = $localize`:@@shell.alerts.feed:Alerts`;

    /** The line shown while the store is empty (ALR-07). */
    protected readonly emptyLabel = $localize`:@@shell.alerts.empty:No alerts`;

    /** Accessible name of each row's dismiss button (ALR-09). */
    protected readonly dismissLabel = $localize`:@@shell.alerts.dismiss:Dismiss`;

    /** The clear-all button's label (ALR-06). */
    protected readonly clearLabel = $localize`:@@shell.alerts.clear:Clear all`;

    /** The burst chip's prefix, joined to the count (ALR-07). */
    protected readonly timesPrefix = $localize`:@@shell.alerts.times:\u00d7`;

    /**
     * The drawer's dismissal (ALR-01, DD-078's pattern): navigate the
     * `drawer` outlet away.
     */
    protected close(): void {
        this.active.set(false);
        this.router.navigate([{ outlets: { drawer: null } }]);
    }
}
