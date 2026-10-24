/**
 * The time zone owner (SPL-07, SPL-10): stores the chosen IANA id, null
 * for "Browser default". The store is browser-scoped (DD-161); the
 * bootstrap read (`storedTimezone`) is the same synchronous read the
 * `DATE_PIPE_DEFAULT_TIMEZONE` provider factory performs, so the provider and the
 * panel agree from the first frame.
 */
import { TestBed } from "@angular/core/testing";

import { TimezoneService } from "./timezone.service";
import { TIMEZONE_KEY } from "./user-preference";

describe("TimezoneService (SPL-07)", () => {
    beforeEach(() => localStorage.clear());
    afterEach(() => localStorage.clear());

    const service = () => TestBed.inject(TimezoneService);

    it("defaults to null — the system zone, no choice made (SPL-07)", () => {
        expect(service().timezone()).toBeNull();
    });

    it("stores the chosen zone id under the browser-scoped key (SPL-07, SPL-09)", () => {
        const svc = service();

        svc.set("Europe/Amsterdam");

        expect(svc.timezone()).toBe("Europe/Amsterdam");
        expect(localStorage.getItem(TIMEZONE_KEY)).toBe(JSON.stringify("Europe/Amsterdam"));
    });

    it("null restores the system default (SPL-07)", () => {
        const svc = service();
        svc.set("Asia/Tokyo");
        svc.set(null);

        expect(svc.timezone()).toBeNull();
        expect(localStorage.getItem(TIMEZONE_KEY)).toBe("null");
    });

    it("reads the stored zone at construction — the bootstrap seam (SPL-07)", () => {
        localStorage.setItem(TIMEZONE_KEY, JSON.stringify("America/New_York"));
        expect(service().timezone()).toBe("America/New_York");
        expect(TimezoneService.storedTimezone()).toBe("America/New_York");
    });

    it("a corrupt store falls back to null (SPL-07, SPL-09)", () => {
        localStorage.setItem(TIMEZONE_KEY, JSON.stringify(42));

        expect(service().timezone()).toBeNull();
        expect(TimezoneService.storedTimezone()).toBeNull();
    });
});
