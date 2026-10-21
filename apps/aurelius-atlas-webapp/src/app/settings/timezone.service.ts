import { Injectable, Signal } from "@angular/core";

import { persisted, Persisted, readPreference, TIMEZONE_KEY } from "./user-preference";

/**
 * The time zone owner (SPL-07, DD-072): the display zone for dates, stored
 * in the browser. `null` means "no choice made" — Angular's `DATE_PIPE_DEFAULT_TIMEZONE`
 * provider (the replacement of the removed `DATE_TIME_ZONE`) then falls back to the system zone, the app's behaviour before
 * the setting existed. The ids come from the server's session
 * (`GET /atlas/admin/session`, ADM-05); the store keeps any IANA id.
 */
@Injectable({ providedIn: "root" })
export class TimezoneService {
    private readonly pref: Persisted<string | null> = persisted<string | null>(
        TIMEZONE_KEY,
        null,
        (value): value is string | null => value === null || typeof value === "string",
    );

    /** The chosen zone id, `null` for the system default. */
    readonly timezone: Signal<string | null> = this.pref.value;

    /**
     * Store the chosen zone id (`null` restores the system default). A
     * change applies on the next reload — the `DATE_PIPE_DEFAULT_TIMEZONE`
     * provider is
     * read at bootstrap (DD-073, SPL-07).
     * @param timezone the IANA zone id, or `null`
     */
    set(timezone: string | null): void {
        this.pref.set(timezone);
    }

    /**
     * The zone to apply at bootstrap — the same synchronous read the
     * provider factory uses, so the app and the panel agree.
     * @returns the stored zone id, or `null`
     */
    static storedTimezone(): string | null {
        return readPreference<string | null>(TIMEZONE_KEY, null, (v) => v === null || typeof v === "string");
    }
}
