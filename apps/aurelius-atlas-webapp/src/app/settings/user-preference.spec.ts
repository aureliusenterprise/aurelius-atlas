/**
 * The persistence seam (SPL-09, DD-072): `UserPreference` is the only code
 * touching localStorage, and it reads and writes its key with the
 * validation each owner supplies. Corruption and a denied storage
 * (private mode) fall back to the initial value — the settings never
 * brick the app (DD-073: a UX convenience, not a data store).
 */
import {
    PAGE_SIZE_KEY,
    persisted,
    readPreference,
    TELEMETRY_KEY,
    THEME_KEY,
    TIMEZONE_KEY,
    writePreference,
} from "./user-preference";

describe("user-preference (SPL-09)", () => {
    beforeEach(() => localStorage.clear());
    afterEach(() => localStorage.clear());

    it("names the browser-scoped keys the spec pins (SPL-09, DD-073)", () => {
        // The theme keeps DarkModeService's existing key; the rest share the
        // aurelius-atlas.settings. prefix. Keys carry no user identity.
        expect(THEME_KEY).toBe("data-theme");
        expect(TIMEZONE_KEY).toBe("aurelius-atlas.settings.timezone");
        expect(PAGE_SIZE_KEY).toBe("aurelius-atlas.settings.pageSize");
        expect(TELEMETRY_KEY).toBe("aurelius-atlas.settings.telemetry");
    });

    it("reads the stored value back after a write (SPL-09)", () => {
        writePreference(TIMEZONE_KEY, "Europe/Amsterdam");

        expect(readPreference(TIMEZONE_KEY, null)).toBe("Europe/Amsterdam");
    });

    it("falls back to the initial when nothing is stored (SPL-09)", () => {
        expect(readPreference(PAGE_SIZE_KEY, 10)).toBe(10);
    });

    it("falls back to the initial on unparseable JSON (SPL-09)", () => {
        localStorage.setItem(TELEMETRY_KEY, "{not json");

        expect(readPreference(TELEMETRY_KEY, true)).toBe(true);
    });

    it("falls back to the initial when validation rejects the stored value (SPL-08, SPL-09)", () => {
        localStorage.setItem(PAGE_SIZE_KEY, JSON.stringify("twelve"));
        const positive = (v: unknown): boolean => typeof v === "number" && Number.isInteger(v) && v > 0;

        expect(readPreference(PAGE_SIZE_KEY, 10, positive)).toBe(10);
    });

    it("survives a storage the browser denies (SPL-09)", () => {
        // Private mode: getItem/setItem throw — reads fall back, writes are
        // swallowed, the session keeps working.
        const original = Object.getOwnPropertyDescriptor(Storage.prototype, "getItem");
        const originalSet = Object.getOwnPropertyDescriptor(Storage.prototype, "setItem");
        Object.defineProperty(Storage.prototype, "getItem", {
            value: () => {
                throw new Error("denied");
            },
        });
        Object.defineProperty(Storage.prototype, "setItem", {
            value: () => {
                throw new Error("denied");
            },
        });
        try {
            expect(readPreference(TIMEZONE_KEY, null)).toBeNull();
            expect(() => writePreference(TIMEZONE_KEY, "Europe/Amsterdam")).not.toThrow();
        } finally {
            if (original?.value) Object.defineProperty(Storage.prototype, "getItem", original);
            if (originalSet?.value) Object.defineProperty(Storage.prototype, "setItem", originalSet);
        }
    });

    it("persisted() reads the stored value at construction and writes back on set (SPL-09)", () => {
        writePreference(PAGE_SIZE_KEY, 20);
        const pref = persisted<number>(PAGE_SIZE_KEY, 10, (v) => typeof v === "number" && v > 0);

        expect(pref.value()).toBe(20);

        pref.set(50);

        expect(pref.value()).toBe(50);
        expect(localStorage.getItem(PAGE_SIZE_KEY)).toBe(JSON.stringify(50));
    });
});
