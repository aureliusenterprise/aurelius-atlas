import { inject, Injectable, LOCALE_ID } from "@angular/core";

/**
 * The locales the application is deployed in, as locale code to display label.
 *
 * Keep in sync with the `i18n.locales` and `build.options.localize` entries in `project.json`.
 * Labels are intentionally untranslated: language names are shown in their own language.
 */
export const LOCALES = {
    "en-US": "English",
    "nl-NL": "Nederlands",
} as const;

/**
 * Represents a locale supported by the application.
 */
export type LocaleCode = keyof typeof LOCALES;

/**
 * The default locale of the application.
 */
export const DEFAULT_LOCALE: LocaleCode = "en-US";

/**
 * Matches a locale code at the start of a URL path (e.g. `/en-US/...`), generated
 * from {@link LOCALES} so new locales are stripped automatically.
 */
export const LOCALE_PREFIX = new RegExp(`^/(${Object.keys(LOCALES).join("|")})`);

/**
 * Exposes the application's locale information to the UI: the list of supported
 * locales for the language switcher, the locale the app is currently running in,
 * and locale-switched URLs for the current page.
 *
 * Locale switching is done with plain links (full page loads) rather than the
 * router, because each locale is a separately localized build served under its
 * own URL prefix.
 */
@Injectable({
    providedIn: "root",
})
export class LocaleService {
    /**
     * The locales the application is deployed in, for the language switcher.
     */
    readonly locales = LOCALES;

    /**
     * The locale the application is currently running in, validated against {@link LOCALES}.
     * Falls back to the default locale when the build locale is not one of {@link LOCALES}.
     */
    readonly activeLocale: LocaleCode = (() => {
        const localeId = inject(LOCALE_ID);
        return localeId in LOCALES ? (localeId as LocaleCode) : DEFAULT_LOCALE;
    })();

    /**
     * Build the URL of the given locale for the current page, preserving the path
     * and query string so users stay on the same screen after switching.
     * @param code The target locale code.
     * @returns An absolute URL to the same page in the target locale.
     */
    localeHref(code: LocaleCode): string {
        const { origin, pathname, search } = globalThis.location;
        const rest = pathname.replace(LOCALE_PREFIX, "");
        return `${origin}/${code}${rest}${search}`;
    }
}
