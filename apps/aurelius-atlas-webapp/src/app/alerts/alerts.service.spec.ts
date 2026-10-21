import { TestBed } from "@angular/core/testing";

import { AlertsService, ALERT_CLOCK, GROUP_WINDOW_MS, MAX_GROUPS } from "./alerts.service";

/** A controllable clock: `at(t)` moves wall time to `t` (ALR-03). */
function setupService(start = 1_000) {
    let now = start;

    TestBed.configureTestingModule({
        providers: [AlertsService, { provide: ALERT_CLOCK, useValue: () => now }],
    });

    return {
        service: TestBed.inject(AlertsService),
        at: (t: number) => {
            now = t;
        },
    };
}

const error = { severity: "error", message: "GET /api/x 500", source: "http" } as const;

describe("AlertsService (ALR-02, ALR-03, ALR-06)", () => {
    it("adds groups newest first (ALR-03)", () => {
        const { service } = setupService();

        service.add({ severity: "info", message: "first", source: "app" });
        service.add({ severity: "warning", message: "second", source: "app" });

        expect(service.alerts().map((g) => g.message)).toEqual(["second", "first"]);
    });

    it("merges a repeat of the same key inside the window (ALR-03)", () => {
        const { service, at } = setupService(10_000);

        service.add(error);
        at(10_000 + GROUP_WINDOW_MS); // inclusive edge: at the window's end
        service.add(error);

        expect(service.alerts()).toHaveLength(1);
        expect(service.alerts()[0].count).toBe(2);
        expect(service.alerts()[0].lastSeen).toBe(10_000 + GROUP_WINDOW_MS);
    });

    it("starts a new group after the window closes (ALR-03)", () => {
        const { service, at } = setupService(10_000);

        service.add(error);
        at(10_000 + GROUP_WINDOW_MS + 1);
        service.add(error);

        expect(service.alerts()).toHaveLength(2);
        expect(service.alerts()[0].count).toBe(1);
    });

    it("does not merge across keys (ALR-03)", () => {
        const { service } = setupService();

        service.add(error);
        service.add({ ...error, message: "GET /api/y 500" }); // different message
        service.add({ ...error, severity: "warning" }); // different severity
        service.add({ ...error, source: "app" }); // different source

        expect(service.alerts()).toHaveLength(4);
    });

    it("merges only the newest group — an older burst is history (ALR-03)", () => {
        const { service } = setupService();

        service.add(error);
        service.add({ severity: "info", message: "between", source: "app" });
        service.add(error);

        expect(service.alerts()).toHaveLength(3);
        expect(service.alerts().filter((g) => g.count === 2)).toHaveLength(0);
    });

    it("caps the store, evicting the oldest (ALR-03)", () => {
        const { service, at } = setupService();

        for (let i = 0; i <= MAX_GROUPS; i++) {
            at(i * (GROUP_WINDOW_MS + 1)); // every add is its own group
            service.add({ ...error, message: `m${i}` });
        }

        expect(service.alerts()).toHaveLength(MAX_GROUPS);
        expect(service.alerts().at(-1)?.message).toBe("m1"); // m0 evicted
    });

    it("dismisses one group, the whole burst with it (ALR-06)", () => {
        const { service, at } = setupService(10_000);

        service.add(error);
        at(10_001);
        service.add(error); // merges into the first group — count 2
        at(20_000);
        service.add({ severity: "info", message: "other", source: "app" });
        const burst = service.alerts().find((g) => g.count === 2);

        service.dismiss(burst?.id ?? "");

        expect(service.alerts().map((g) => g.message)).toEqual(["other"]);
    });

    it("clearAll empties the store (ALR-06)", () => {
        const { service } = setupService();

        service.add(error);
        service.clearAll();

        expect(service.alerts()).toHaveLength(0);
        expect(service.hasAlerts()).toBe(false);
    });

    it("reports the highest severity present (ALR-02)", () => {
        const { service, at } = setupService();

        service.add({ severity: "info", message: "i", source: "app" });
        expect(service.topSeverity()).toBe("info");

        at(2 * GROUP_WINDOW_MS);
        service.add({ severity: "warning", message: "w", source: "app" });
        expect(service.topSeverity()).toBe("warning");

        at(3 * GROUP_WINDOW_MS);
        service.add(error);
        expect(service.topSeverity()).toBe("error");

        // Dismissing the error drops the top back to what remains.
        const top = service.alerts()[0];
        service.dismiss(top.id);
        expect(service.topSeverity()).toBe("warning");
    });

    it("rings once per new group, not per merged alert (ALR-02a)", () => {
        const { service, at } = setupService(10_000);

        service.add(error);
        expect(service.newGroups()).toBe(1);

        at(10_500);
        service.add(error); // merged — the window restarts at 10_500
        service.add(error); // merged
        expect(service.newGroups()).toBe(1);

        at(10_500 + GROUP_WINDOW_MS + 1);
        service.add(error); // a new burst
        expect(service.newGroups()).toBe(2);
    });

    it("flips hasAlerts with the store (ALR-02)", () => {
        const { service } = setupService();

        expect(service.hasAlerts()).toBe(false);
        service.add(error);
        expect(service.hasAlerts()).toBe(true);
        service.clearAll();
        expect(service.hasAlerts()).toBe(false);
    });

    it("arrives unread and reads all on markAllRead (ALR-12)", () => {
        const { service } = setupService();

        service.add(error);
        expect(service.alerts()[0].read).toBe(false);
        expect(service.hasUnread()).toBe(true);

        service.markAllRead();
        expect(service.alerts()[0].read).toBe(true);
        expect(service.hasUnread()).toBe(false);
    });

    it("a merge re-unreads a read burst (ALR-12)", () => {
        const { service, at } = setupService(10_000);

        service.add(error);
        service.markAllRead();
        expect(service.hasUnread()).toBe(false);

        at(10_500);
        service.add(error); // merged — the burst grew, fresh news again

        expect(service.alerts()[0].count).toBe(2);
        expect(service.hasUnread()).toBe(true);
    });

    it("marks a live feed read as it lands (ALR-12)", () => {
        const { service } = setupService();

        service.markAllRead(); // the open drawer's effect runs on an empty store too
        expect(service.hasUnread()).toBe(false);

        service.add(error); // arrives while the drawer is open…
        service.markAllRead(); // …and the effect reads it on landing
        expect(service.hasUnread()).toBe(false);
    });

    it("colours the dot by the highest unread severity (ALR-02, ALR-12)", () => {
        const { service, at } = setupService();

        service.add(error);
        service.markAllRead();
        expect(service.topUnreadSeverity()).toBe("info"); // vacuous — nothing unread

        at(2 * GROUP_WINDOW_MS);
        service.add({ severity: "warning", message: "w", source: "app" });
        // The read error no longer out-colours the new warning.
        expect(service.topSeverity()).toBe("error");
        expect(service.topUnreadSeverity()).toBe("warning");
    });

    it("counts the feed per severity, totals and unread (ALR-11, ALR-12)", () => {
        const { service } = setupService();

        service.add(error);
        service.add({ severity: "error", message: "GET /api/y 502", source: "http" });
        service.add({ severity: "info", message: "saved", source: "app" });

        expect(service.severityCounts().map((c) => `${c.severity}:${c.total}:${c.unread}`)).toEqual([
            "error:2:2",
            "warning:0:0",
            "info:1:1",
        ]);

        service.markAllRead();
        expect(service.severityCounts().map((c) => `${c.severity}:${c.total}:${c.unread}`)).toEqual([
            "error:2:0",
            "warning:0:0",
            "info:1:0",
        ]);
    });
});
