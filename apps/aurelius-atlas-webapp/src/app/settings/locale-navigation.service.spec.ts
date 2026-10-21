/**
 * The language owner (SPL-06, SPL-10): SHC-04's semantics moved from the
 * header dropdown into the settings panel, and the locale-href computation
 * moved with it (the header spec's SHC-04 assertions live here now). The
 * locale builds are separate bundles (DD-039), so this service stores
 * nothing — it is the navigation seam.
 */
import { TestBed } from "@angular/core/testing";

import { LocaleNavigation } from "./locale-navigation.service";

describe("LocaleNavigation (SPL-06)", () => {
    const service = () => TestBed.inject(LocaleNavigation);

    it("lists the locales the image serves (SHC-04)", () => {
        expect(service().locales).toEqual(["en-US", "nl-NL"]);
    });

    it("computes locale hrefs by swapping the locale prefix (SHC-04)", () => {
        const nav = service();

        expect(nav.localeHref("nl-NL", "/en-US/search/browse")).toBe("/nl-NL/search/browse");
        expect(nav.localeHref("nl-NL", "/search/browse")).toBe("/nl-NL/search/browse");
        expect(nav.localeHref("en-US", "/nl-NL/")).toBe("/en-US/");
        expect(nav.localeHref("en-US", "/")).toBe("/en-US/");
    });

    it("reads the active locale from the served document (SHC-04, SPL-06)", () => {
        document.documentElement.lang = "nl-NL";
        try {
            expect(service().activeLocale).toBe("nl-NL");
        } finally {
            document.documentElement.lang = "en-US";
        }
    });

    it("stores no language preference (SPL-06)", () => {
        // The locale is the build that is served, not a stored setting:
        // the seam has no write path and localStorage stays empty.
        localStorage.clear();
        const nav = service();

        expect(nav.localeHref("nl-NL", "/")).toBe("/nl-NL/");
        expect(localStorage.length).toBe(0);
    });
});
