import { DatePipe } from "@angular/common";
import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";

import type { AlertGroup } from "./alert-group";

/**
 * The alert feed (ALR-07, ALR-09, ALR-10): one Bulma notification per
 * group, severity-coloured, newest first as the caller ordered them. The
 * component is presentational — it stores nothing and owns no clock: the
 * caller's store groups the alerts (ALR-03) and passes the rows; the list
 * renders them and emits `dismiss`.
 *
 * The feed is a live region (`role="log"`, `aria-live="polite"`): an
 * alert arriving while the drawer is open is announced without
 * interrupting. The list labels itself with the caller's `ariaLabel`.
 *
 * Clearing the whole feed lives outside the list (DD-088): the caller
 * places a clear-all action in the {@link Drawer}'s head slot, where a
 * long feed cannot bury it. The list stays the rows.
 *
 * An unread group (ALR-12) reads as a row: its message is bolder and its
 * meta line carries a ring dot with the caller's `unreadLabel` for
 * screen readers. Read groups show neither — the list only renders the
 * flag its store set on each row.
 *
 * Labels are caller inputs with English defaults (the {@link Drawer}'s
 * `ariaLabel` pattern), so the lib keeps no translation dependency —
 * the app passes localised strings and the XLIFF gate stays app-side
 * (ALR-08).
 */
@Component({
    selector: "aurelius-atlas-ui-alert-list",
    imports: [DatePipe],
    templateUrl: "./alert-list.component.html",
    styleUrl: "./alert-list.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AlertList {
    /**
     * The groups to render, in display order (the caller's newest-first
     * ordering, ALR-03). An empty array renders the empty state.
     */
    readonly alerts = input<readonly AlertGroup[]>([]);

    /**
     * Accessible name of the feed (the live region's label). The caller
     * localises it.
     */
    readonly ariaLabel = input("Alerts");

    /**
     * The line shown when there are no alerts. The caller localises it.
     */
    readonly emptyLabel = input("No alerts");

    /**
     * The accessible name of each row's dismiss button. The caller
     * localises it.
     */
    readonly dismissLabel = input("Dismiss");

    /**
     * The prefix of the burst-count chip, joined to the count (ALR-07).
     * A prefix rather than a full plural string, so the chip stays a
     * single localised word per locale.
     */
    readonly timesPrefix = input("\u00d7");

    /**
     * The label announced on an unread row's dot (ALR-12). The caller
     * localises it.
     */
    readonly unreadLabel = input("Unread");

    /** Emits the id of a row's dismiss button (ALR-06). */
    readonly dismiss = output<string>();
}
