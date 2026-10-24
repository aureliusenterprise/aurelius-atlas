import { ChangeDetectionStrategy, Component, computed, input } from "@angular/core";

import type { AlertSeverity } from "../alert-list/alert-group";

/**
 * A presence dot pinned to the top-right of wrapped content (ALR-02,
 * ALR-10): a small severity-coloured marker, hidden when not visible.
 * The dot carries a ring in the surrounding ink so it keeps a visible
 * edge on any band — Bulma's navbar-scoped `--bulma-navbar-item-color`
 * when the badge sits inside a navbar item (black on DD-168's slate,
 * the legacy grey on the light band), `currentColor` everywhere else.
 *
 * The colours are the brand ramp DD-152 pinned (danger, warning,
 * info), fixed in both schemes — like the footer's pair (SHM-07), a
 * severity marker must not shift with the theme.
 */
@Component({
    selector: "aurelius-atlas-ui-badge",
    imports: [],
    templateUrl: "./badge.component.html",
    styleUrl: "./badge.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Badge {
    /**
     * The dot's severity: `error` (danger), `warning`, or `info` —
     * DD-152's ramp (ALR-02).
     */
    readonly severity = input<AlertSeverity>("error");

    /**
     * Whether the dot shows. Presence, not a count: the caller hides it
     * when there is nothing to signal.
     */
    readonly visible = input(false);

    /**
     * Accessible name of the dot — the caller localises it (the
     * {@link Drawer}'s `ariaLabel` pattern).
     */
    readonly label = input("Notifications");

    /** The dot's severity class. */
    protected readonly severityClass = computed(() => `is-${this.severity()}`);
}
