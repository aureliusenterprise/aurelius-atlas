import { computed, Injectable, inject } from "@angular/core";
import { DarkModeService, Mode } from "aurelius-atlas-ui";

import { LocaleNavigation } from "./locale-navigation.service";
import { PageSizeService } from "./page-size.service";
import { TelemetryService } from "./telemetry.service";
import { TimezoneService } from "./timezone.service";

/**
 * The settings facade (SPL-10, DD-160): one injectable the settings panel
 * consumes, exposing each category's signal and setter and delegating to
 * exactly one owner service per category. The facade stores nothing — the
 * owners own their signals and storage; `UserPreference` is the only code
 * touching `localStorage`. Server-side persistence replaces an owner's
 * internals, not this surface.
 *
 * The bootstrap providers (the telemetry gate, `DATE_PIPE_DEFAULT_TIMEZONE`) read the
 * owners' static `stored*` seams, not the facade — DI is not up yet there.
 */
@Injectable({ providedIn: "root" })
export class SettingsService {
    private readonly darkMode = inject(DarkModeService);

    private readonly timezoneOwner = inject(TimezoneService);

    private readonly pageSizeOwner = inject(PageSizeService);

    private readonly telemetryOwner = inject(TelemetryService);

    /** The language owner: active locale, locales, locale hrefs (SPL-06). */
    readonly locale = inject(LocaleNavigation);

    /** The theme mode: `"dark"`, `"light"`, or `null` = Auto (SPL-03). Read-only — writing goes through {@link setTheme}. */
    readonly theme = computed(() => this.darkMode.mode());

    /** The chosen time zone id, `null` for the system default (SPL-07). Read-only — writing goes through {@link setTimezone}. */
    readonly timezone = computed(() => this.timezoneOwner.timezone());

    /** The default table page size (SPL-08). Read-only — writing goes through {@link setPageSize}. */
    readonly pageSize = computed(() => this.pageSizeOwner.pageSize());

    /** Whether telemetry is on (SPL-11). Read-only — writing goes through {@link setTelemetry}. */
    readonly telemetry = computed(() => this.telemetryOwner.enabled());

    /**
     * Choose the theme (the Appearance radio), through its owner —
     * `DarkModeService` writes the root attribute and the stored choice
     * (SPL-03, SPL-04).
     * @param mode `"dark"`, `"light"`, or `null` for Auto
     */
    setTheme(mode: Mode): void {
        this.darkMode.setMode(mode);
    }

    /**
     * Choose the display time zone (`null` = system default). Takes effect
     * on reload (SPL-07).
     * @param timezone the IANA zone id
     */
    setTimezone(timezone: string | null): void {
        this.timezoneOwner.set(timezone);
    }

    /**
     * Set the default table page size (SPL-08).
     * @param pageSize a positive integer
     */
    setPageSize(pageSize: number): void {
        this.pageSizeOwner.set(pageSize);
    }

    /**
     * Switch telemetry (SPL-11): off stops the exports now, on is effective
     * after a reload (DD-158).
     * @param enabled the new state
     */
    setTelemetry(enabled: boolean): void {
        this.telemetryOwner.setEnabled(enabled);
    }
}
