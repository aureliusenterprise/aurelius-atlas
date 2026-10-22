import { ChangeDetectionStrategy, Component, computed, input, output } from "@angular/core";

import { countSeverities } from "../alert-list/alert-group";
import type { AlertGroup, AlertSeverity, AlertSeverityCount } from "../alert-list/alert-group";

/**
 * The inbox bar above the alert feed (ALR-11): a full-width Bulma
 * button group with one chip per severity, in inbox order — `info`,
 * `warning`, `error`, the ramp calm to urgent (DD-092) — each showing
 * how many groups of that severity the feed holds, beside the caller's
 * clear-all action, every segment an expanded member of the joined
 * group (DD-090, DD-092). A chip toggles its severity in
 * the feed and rides that severity's pinned fill while shown (an
 * unpressed chip is plain, "off" needs no colour); it carries a dot
 * while that severity has unread groups (ALR-12), so the bar answers
 * "what's new" at a glance.
 *
 * The component is presentational: the caller passes the feed, the
 * component derives the counts, and the caller applies the filter —
 * which severities are visible is a view concern of the panel that
 * embeds the bar (the list stays the rows, DD-088's boundary).
 *
 * A severity with no alerts greys out: its chip is disabled, unpressed,
 * and takes no fill — there is nothing to show and nothing to toggle
 * (DD-094).
 *
 * With every severity hidden the chips are all "off" and the feed
 * shows its empty state; there is no show-all control (DD-095) — the
 * way back is a chip, which stays clickable while hidden. Labels are
 * caller inputs with English defaults (the {@link Drawer}'s
 * `ariaLabel` pattern) — the lib keeps no translation dependency and
 * the XLIFF gate stays app-side (ALR-08).
 */
@Component({
    selector: "aurelius-atlas-ui-alert-inbox",
    imports: [],
    templateUrl: "./alert-inbox.component.html",
    styleUrl: "./alert-inbox.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AlertInbox {
    /** The feed to count — the same rows the {@link AlertList} shows. */
    readonly alerts = input<readonly AlertGroup[]>([]);

    /**
     * The severities the feed hides. A chip whose severity is listed is
     * `aria-pressed="false"` and visually flat; an empty array shows
     * every severity (all chips pressed).
     */
    readonly hidden = input<readonly AlertSeverity[]>([]);

    /**
     * The chip labels, per severity. The caller localises them; the
     * defaults are the English words.
     */
    readonly severityLabels = input<Readonly<Record<AlertSeverity, string>>>({
        error: "Errors",
        warning: "Warnings",
        info: "Info",
    });

    /**
     * Accessible name of the bar (the button group's label). The caller
     * localises it.
     */
    readonly ariaLabel = input("Alert filters");

    /**
     * The label announced on a chip's unread dot (ALR-12), so the dot
     * is not colour-only information. The caller localises it.
     */
    readonly unreadLabel = input("Unread");

    /** Emits the severity whose chip was clicked (ALR-11). */
    readonly toggleSeverity = output<AlertSeverity>();

    /** The feed counted by severity — totals and unread, inbox order. */
    protected readonly counts = computed(() => countSeverities(this.alerts()));

    /**
     * Whether a severity's chip is on: it has alerts and the feed does
     * not hide it. An empty severity is never on (DD-094) — a filter
     * with nothing to show is not showing it, so the chip takes no
     * severity fill and reads grey (the {@link isVoid} state).
     * @param count one severity's counts
     * @returns whether the chip is pressed
     */
    protected isOn(count: AlertSeverityCount): boolean {
        return count.total > 0 && !this.hidden().includes(count.severity);
    }

    /**
     * Whether a severity's chip is void: the feed holds no alert of it,
     * so the chip is disabled — greyed, and inert, since filtering
     * nothing has nothing to toggle (DD-094).
     * @param count one severity's counts
     * @returns whether the chip is disabled
     */
    protected isVoid(count: AlertSeverityCount): boolean {
        return count.total === 0;
    }
}
