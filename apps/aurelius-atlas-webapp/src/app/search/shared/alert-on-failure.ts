import { effect, inject } from "@angular/core";
import type { Signal } from "@angular/core";
import type { AlertSeverity } from "aurelius-atlas-ui";

import { AlertsService } from "../../alerts/alerts.service";

/**
 * A failure a store holds until the screen that shows it drains it (DD-871):
 * the store records *what went wrong* without reaching into the alerts store,
 * and the screen's relay turns it into an alert. The shape is an alert minus
 * its `source`, which the relay supplies.
 */
export interface AlertNotice {
    readonly severity: AlertSeverity;
    readonly message: string;
}

/**
 * The seam a store implements to park its failures (DD-871): {@link failures}
 * holds every failure awaiting the screen's {@link alertOnFailure} relay, and
 * {@link handled} drains the list so a shown failure never re-alerts.
 *
 * A store owns this instead of injecting {@link AlertsService} directly so the
 * store stays a description of state — what a screen would show — not a side
 * effect. The alerts store is a UI concern, and a state service that writes to
 * it can fire an alert behind a screen that has already navigated away.
 *
 * It is a list, not one slot, because one user action can fail more than once
 * before the screen reacts — a section's resolve fires several cards chunks and
 * each failed chunk alerts (DET-18) — and each must surface, exactly as it does
 * today when the store calls {@link AlertsService.add} per failure.
 */
export interface FailureHolder {
    /** The failures awaiting the relay, oldest first; empty when none is pending. */
    readonly failures: Signal<readonly AlertNotice[]>;

    /** Mark every held failure shown, so the relay does not fire them again. */
    handled(): void;
}

/**
 * The one relay that turns a store's held failures into alerts (DD-871): call
 * it once from the component that owns the store (the one that lists it in its
 * `providers`), and each failure the store records surfaces as an alert, once.
 *
 * The relay, not the store, owns the alert because the alert is a screen event:
 * it fires on the screen that is showing the failure, and never a second time
 * for the same failure. It runs in an `effect` so it stays a screen-side
 * reaction to store state, and it re-arms after draining so a later failure
 * fires again. Each alert carries the store's exact severity and message with
 * the passed `source` — the message must stay byte-identical to the pre-refactor
 * call, because {@link AlertsService} groups repeats on the exact
 * severity+source+message triple within its window (ALR-03).
 * @param store the store whose held failures the screen shows
 * @param source the alert's source, `search` for every search screen
 */
export function alertOnFailure(store: FailureHolder, source = "search"): void {
    const alerts = inject(AlertsService);
    effect(() => {
        const failures = store.failures();
        if (failures.length === 0) {
            return;
        }
        for (const failure of failures) {
            alerts.add({ severity: failure.severity, message: failure.message, source });
        }
        store.handled();
    });
}
