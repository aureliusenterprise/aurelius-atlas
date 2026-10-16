/**
 * Unit tests for {@link LocaleService}: locale exposure, active-locale detection
 * from `LOCALE_ID` (including the unknown-locale fallback), and locale-switched
 * URL generation.
 */
import { LOCALE_ID } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { DEFAULT_LOCALE, LocaleService } from "./locale.service";

describe("LocaleService", () => {
    function createService(localeId?: string) {
        TestBed.configureTestingModule({
            providers: [{ provide: LOCALE_ID, useValue: localeId ?? DEFAULT_LOCALE }],
        });

        return TestBed.inject(LocaleService);
    }

    it("should expose the supported locale labels", () => {
        const service = createService(DEFAULT_LOCALE);

        expect(service.locales).toEqual({ "en-US": "English", "nl-NL": "Nederlands" });
    });

    it("should select the active locale from the build locale", () => {
        const service = createService("nl-NL");

        expect(service.activeLocale).toBe("nl-NL");
    });

    it("should fall back to the default locale for an unknown build locale", () => {
        const service = createService("de-DE");

        expect(service.activeLocale).toBe(DEFAULT_LOCALE);
    });

    it("should preserve the current path and query string when building a locale link", () => {
        const service = createService(DEFAULT_LOCALE);

        window.history.pushState({}, "", "/en-US/search?query=foo");

        expect(service.localeHref("nl-NL")).toBe(`${window.location.origin}/nl-NL/search?query=foo`);
    });
});
