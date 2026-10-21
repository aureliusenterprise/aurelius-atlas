import { inject, Injectable, Signal } from "@angular/core";
import { AURELIUS_METER_PROVIDER, AURELIUS_WEB_TRACER_PROVIDER } from "aurelius-atlas-observability";

import { persisted, Persisted, readPreference, TELEMETRY_KEY } from "./user-preference";

/**
 * The telemetry owner (SPL-11, DD-070, DD-072): the browser telemetry
 * switch. The stored value gates the SDK at bootstrap — `app.config.ts`
 * builds the trace/metric providers only when it is on
 * ({@link TelemetryService.storedEnabled}). Switching it **off** stops the
 * exports immediately (DD-070: the SDK's one clean direction — the
 * provider's `shutdown` flushes and closes the exporter); switching it
 * **on** stores the choice, and the SDK — assembled at startup — needs a
 * reload. The optional injections return `null` when telemetry was off at
 * bootstrap (the providers are not registered then), so the stop is a
 * no-op exactly when there is nothing to stop.
 */
@Injectable({ providedIn: "root" })
export class TelemetryService {
    private readonly pref: Persisted<boolean> = persisted<boolean>(
        TELEMETRY_KEY,
        true,
        (value): value is boolean => typeof value === "boolean",
    );

    /** Whether telemetry is on. */
    readonly enabled: Signal<boolean> = this.pref.value;

    private readonly tracerProvider = inject(AURELIUS_WEB_TRACER_PROVIDER, { optional: true });

    private readonly meterProvider = inject(AURELIUS_METER_PROVIDER, { optional: true });

    /**
     * Store the choice. Off stops the exporters now (DD-070); on is
     * effective after a reload, which the panel states (SPL-11).
     * @param enabled the new state
     */
    setEnabled(enabled: boolean): void {
        this.pref.set(enabled);
        if (!enabled) {
            void this.tracerProvider?.shutdown().catch(() => undefined);
            void this.meterProvider?.shutdown().catch(() => undefined);
        }
    }

    /**
     * The stored switch for the bootstrap gate — read synchronously,
     * before any service exists, so `app.config.ts` can skip the SDK
     * entirely when it is off (SPL-11).
     * @returns false only when the stored value is explicitly off
     */
    static storedEnabled(): boolean {
        return readPreference(TELEMETRY_KEY, true, (v) => typeof v === "boolean");
    }
}
