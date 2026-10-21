/**
 * The telemetry owner (SPL-11, DD-070, SPL-10): the stored switch gates
 * the SDK at bootstrap (`storedEnabled`, the seam app.config.ts reads).
 * The DD-070 asymmetry is the rule under test: **off** stops the running
 * exporters immediately — the providers' `shutdown` is the one clean
 * direction the SDK has; **on** only stores, the reload assembles the SDK.
 * The providers are injected optionally: off-at-bootstrap means they were
 * never registered, and the stop is a no-op exactly then.
 */
import { TestBed } from "@angular/core/testing";
import { AURELIUS_METER_PROVIDER, AURELIUS_WEB_TRACER_PROVIDER } from "aurelius-atlas-observability";

import { TELEMETRY_KEY } from "./user-preference";
import { TelemetryService } from "./telemetry.service";

describe("TelemetryService (SPL-11)", () => {
    const tracerShutdown = vi.fn(async () => undefined);
    const meterShutdown = vi.fn(async () => undefined);

    beforeEach(() => {
        localStorage.clear();
        tracerShutdown.mockClear();
        meterShutdown.mockClear();
        TestBed.configureTestingModule({
            providers: [
                { provide: AURELIUS_WEB_TRACER_PROVIDER, useValue: { shutdown: tracerShutdown } },
                { provide: AURELIUS_METER_PROVIDER, useValue: { shutdown: meterShutdown } },
            ],
        });
    });

    afterEach(() => localStorage.clear());

    const service = () => TestBed.inject(TelemetryService);

    it("defaults to on (SPL-11)", () => {
        expect(service().enabled()).toBe(true);
        expect(TelemetryService.storedEnabled()).toBe(true);
    });

    it("reads the stored switch at construction (SPL-11)", () => {
        localStorage.setItem(TELEMETRY_KEY, JSON.stringify(false));

        expect(service().enabled()).toBe(false);
        expect(TelemetryService.storedEnabled()).toBe(false);
    });

    it("off stores the choice and stops both exporters now (SPL-11, DD-070)", () => {
        const svc = service();

        svc.setEnabled(false);

        expect(svc.enabled()).toBe(false);
        expect(localStorage.getItem(TELEMETRY_KEY)).toBe(JSON.stringify(false));
        expect(tracerShutdown).toHaveBeenCalledOnce();
        expect(meterShutdown).toHaveBeenCalledOnce();
    });

    it("on stores the choice and touches no exporter — the reload assembles the SDK (SPL-11, DD-070)", () => {
        const svc = service();
        svc.setEnabled(false);
        tracerShutdown.mockClear();
        meterShutdown.mockClear();

        svc.setEnabled(true);

        expect(svc.enabled()).toBe(true);
        expect(localStorage.getItem(TELEMETRY_KEY)).toBe(JSON.stringify(true));
        expect(tracerShutdown).not.toHaveBeenCalled();
        expect(meterShutdown).not.toHaveBeenCalled();
    });

    it("a failing shutdown does not break the switch (SPL-11)", () => {
        tracerShutdown.mockRejectedValueOnce(new Error("exporter closed"));
        const svc = service();

        expect(() => svc.setEnabled(false)).not.toThrow();
        expect(svc.enabled()).toBe(false);
    });

    it("an unparseable store falls back to on (SPL-11, SPL-09)", () => {
        localStorage.setItem(TELEMETRY_KEY, "yes");

        expect(TelemetryService.storedEnabled()).toBe(true);
        expect(service().enabled()).toBe(true);
    });

    it("works when the providers were never registered (telemetry off at bootstrap)", () => {
        // The gate's off-path: app.config.ts registers no providers, the
        // optional injections are null, and switching off is a safe no-op.
        TestBed.resetTestingModule();
        localStorage.setItem(TELEMETRY_KEY, JSON.stringify(true));
        const svc = TestBed.inject(TelemetryService);

        expect(() => svc.setEnabled(false)).not.toThrow();
        expect(svc.enabled()).toBe(false);
    });
});
