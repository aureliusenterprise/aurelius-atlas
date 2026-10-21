import { Injectable } from "@angular/core";

/** The locales the image serves (DD-039: one build per locale, locale tree in nginx). */
export const LOCALES = ["en-US", "nl-NL"] as const;

/**
 * The language owner (SPL-06, DD-072): the active locale and the full-page
 * locale navigation. There is no stored language preference to own — the
 * locale builds are separate bundles (DD-039), so switching is a
 * navigation, not a setting (SHC-04); the settings panel consumes this
 * service (SPL-01 moves the control there).
 */
@Injectable({ providedIn: "root" })
export class LocaleNavigation {
    /** The locales offered by the language section (SHC-04). */
    readonly locales: readonly string[] = LOCALES;

    /** The active locale, as the served document declares it. */
    get activeLocale(): string {
        return document.documentElement.lang;
    }

    /**
     * The full-page URL of a locale's copy of the current page: the active
     * locale prefix is stripped and the chosen one prepended (SHC-04).
     * @param locale the locale to switch to
     * @param currentPath the current path (the location, by default — a
     *   parameter so specs pin every locale pair)
     * @returns the href to navigate to
     */
    localeHref(locale: string, currentPath: string = location.pathname): string {
        const stripped = currentPath.replace(/^\/(?:en-US|nl-NL)(?=\/|$)/, "");

        return `/${locale}${stripped === "" ? "/" : stripped}`;
    }
}
