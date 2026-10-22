import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from "@angular/core";
import { Router } from "@angular/router";
import { AlertInbox, AlertList, Drawer } from "aurelius-atlas-ui";
import type { AlertSeverity } from "aurelius-atlas-ui";

import { AlertsService } from "./alerts.service";

/**
 * The alerts panel (ALR-01, ALR-06, ALR-07): the drawer the header bell
 * opens, showing the {@link AlertsService} store through the ui-lib
 * {@link AlertList}, under the {@link AlertInbox} bar (ALR-11). The
 * panel stores the filter and nothing else — dismissal (per group and
 * clear-all) and read-marking write through the service (ALR-06,
 * ALR-12), the feed renders what the store holds (ALR-03).
 *
 * Like the settings panel, it is a routed component in the `drawer` aux
 * outlet (SPL-14's shape, DD-078, ALR-01): the bell navigates to it,
 * dismissal navigates away, and the outlet segment rides the URL — so
 * the language switch's full-page navigation (SPL-06) reloads the same
 * page with the drawer open. The one named outlet swaps drawers: opening
 * alerts replaces the settings panel and vice versa.
 *
 * Opening the drawer is reading it (ALR-12, DD-090): an effect marks
 * every group read while the panel lives, re-marking as a live feed
 * lands new arrivals. Which severities the bar hides is view state
 * (DD-090): the store keeps counting all of them, the chips show the
 * totals — filtering the rows must not empty the bar's own numbers.
 */
@Component({
    imports: [AlertInbox, AlertList, Drawer],
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

    /**
     * The severities the feed hides (ALR-11): chip state, empty while
     * every severity shows. A view concern — the store's counts and the
     * bell ignore it.
     */
    protected readonly hidden = signal<readonly AlertSeverity[]>([]);

    /** The rows the feed shows: the store's groups minus the hidden severities (ALR-11). */
    protected readonly visible = computed(() =>
        this.alerts.alerts().filter((g) => !this.hidden().includes(g.severity)),
    );

    constructor() {
        // Opening the drawer is reading it (ALR-12): every group is
        // marked read while the panel lives, so the bell's dot (ALR-02)
        // and the chips' dots answer what the user has not seen yet.
        // New arrivals while the drawer is open are read on landing —
        // they are on the screen. `markAllRead` is a no-op once every
        // row is read, so the effect settles.
        effect(() => {
            if (this.alerts.alerts().length > 0) this.alerts.markAllRead();
        });
    }

    /** Toggle a severity chip (ALR-11): show it when hidden, hide it when shown. */
    protected toggleSeverity(severity: AlertSeverity): void {
        this.hidden.update((hidden) =>
            hidden.includes(severity) ? hidden.filter((s) => s !== severity) : [...hidden, severity],
        );
    }

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

    /** Accessible name of the inbox bar (ALR-11). */
    protected readonly inboxLabel = $localize`:@@shell.alerts.inbox:Alert filters`;

    /** The label on the unread markers (ALR-12). */
    protected readonly unreadLabel = $localize`:@@shell.alerts.unread:Unread`;

    /** The inbox chips' severity labels (ALR-11). */
    protected readonly severityLabels: Record<AlertSeverity, string> = {
        error: $localize`:@@shell.alerts.severity.error:Errors`,
        warning: $localize`:@@shell.alerts.severity.warning:Warnings`,
        info: $localize`:@@shell.alerts.severity.info:Info`,
    };

    /**
     * The drawer's dismissal (ALR-01, DD-078's pattern): navigate the
     * `drawer` outlet away.
     */
    protected close(): void {
        this.active.set(false);
        this.router.navigate([{ outlets: { drawer: null } }]);
    }
}
