import { computed, inject, InjectionToken, Injectable, Signal, signal } from "@angular/core";
import { AlertGroup, AlertSeverity, maxSeverity } from "aurelius-atlas-ui";

/** How long a repeat may wait to merge into a burst (ALR-03). */
export const GROUP_WINDOW_MS = 60_000;

/** How many groups the store keeps, newest first (ALR-03). */
export const MAX_GROUPS = 30;

/**
 * The store's clock — a token so the window is testable without fake
 * timers; the default is wall time.
 */
export const ALERT_CLOCK = new InjectionToken<() => number>("ALERT_CLOCK", {
    factory: () => Date.now,
});

/** The public row plus the store's own merge-key source (ALR-03). */
type StoredGroup = AlertGroup & { source: string };

/** The next group id, per browser tab (`a1`, `a2`, …). */
let nextGroupId = 0;

/**
 * The alerts store (ALR-02, ALR-03, ALR-06): the in-memory collection of
 * alert groups the drawer shows and the bell badges. Every alert in the
 * app walks through {@link AlertsService.add} — the error handler
 * (ALR-04), the HTTP reporter (ALR-05), and any feature slice's own
 * notice — and grouping happens here, so no caller merges anything.
 *
 * Grouping is a quiet window (ALR-03, DD-083): an alert whose key
 * (severity + source + message) matches the newest group's merges into
 * it while the window is open (`count` +1, `lastSeen` moves); after the
 * gap the burst is history and a new group starts, so the feed shows
 * bursts as bursts. The store is capped — the oldest group is evicted —
 * and in-memory: alerts are session events, not preferences (the
 * browser-scoped stores are DD-073's lane, this is not one).
 */
@Injectable({ providedIn: "root" })
export class AlertsService {
    private readonly clock = inject(ALERT_CLOCK);

    private readonly stored = signal<readonly StoredGroup[]>([]);

    private readonly arrivals = signal(0);

    /** The groups, newest first (ALR-03) — the drawer's feed. */
    readonly alerts: Signal<readonly AlertGroup[]> = computed(() =>
        this.stored().map(({ source: _source, ...group }) => group),
    );

    /**
     * How many new groups arrived (ALR-02a): merges (ALR-03) do not
     * bump it, so a burst rings the bell once. The header watches it and
     * animates on an increase; the count itself is the header's clock,
     * never rendered.
     */
    readonly newGroups: Signal<number> = this.arrivals.asReadonly();

    /** Whether the store holds anything — the badge's visibility (ALR-02). */
    readonly hasAlerts: Signal<boolean> = computed(() => this.stored().length > 0);

    /**
     * The highest severity present, the badge's colour (ALR-02):
     * `error` > `warning` > `info`. Only meaningful while
     * {@link hasAlerts} — the badge hides on an empty store.
     */
    readonly topSeverity: Signal<AlertSeverity> = computed(() =>
        this.stored().reduce<AlertSeverity>((top, group) => maxSeverity(top, group.severity), "info"),
    );

    /**
     * Record an alert (ALR-03): merge it into the newest group while the
     * window is open and the key matches, else start a new group at the
     * front and count it as an arrival — the bell's ring.
     * @param alert the severity, the message, and the originating part
     *  (`app`, `http`, a feature name — the grouping key's source)
     */
    add(alert: { severity: AlertSeverity; message: string; source: string }): void {
        const now = this.clock();
        const groups = this.stored();
        const newest = groups[0];

        if (
            newest &&
            newest.severity === alert.severity &&
            newest.source === alert.source &&
            newest.message === alert.message &&
            now - newest.lastSeen <= GROUP_WINDOW_MS
        ) {
            this.stored.set([{ ...newest, count: newest.count + 1, lastSeen: now }, ...groups.slice(1)]);
            return;
        }

        const group: StoredGroup = {
            id: `a${++nextGroupId}`,
            severity: alert.severity,
            message: alert.message,
            count: 1,
            lastSeen: now,
            source: alert.source,
        };
        this.stored.set([group, ...groups].slice(0, MAX_GROUPS));
        this.arrivals.update((n) => n + 1);
    }

    /**
     * Drop one group — the whole burst goes with it (ALR-06).
     * @param id the group's id
     */
    dismiss(id: string): void {
        this.stored.update((groups) => groups.filter((group) => group.id !== id));
    }

    /** Empty the store (ALR-06). */
    clearAll(): void {
        this.stored.set([]);
    }
}
