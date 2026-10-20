import { ChangeDetectionStrategy, Component, inject } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faBook } from "@fortawesome/free-solid-svg-icons";
import { Header } from "aurelius-atlas-ui";
import Keycloak from "keycloak-js";

import { APP_CONFIG } from "../tokens";
import { Session } from "./session.service";

/** The locales the image serves (DD-039: one build per locale, locale tree in nginx). */
const LOCALES = ["en-US", "nl-NL"] as const;

/** The Aurelius Atlas documentation site, the legacy header's Documentation link. */
const DOCUMENTATION_URL = "https://aureliusenterprise.github.io/aurelius-atlas-documentation/";

/**
 * The Aurelius shell header (SHC-02..SHC-05): the 7.2 ui-lib header with the
 * app name brand, and on the right the Documentation link, the language
 * dropdown, and the account dropdown.
 *
 * The navbar is search-free by design (DD-056): the global search bar and
 * nav buttons join 7.4. The login button the legacy navbar shows when signed
 * out is not ported — the root guard (APC-05) makes that state unreachable
 * (SHC-05). Switching language is a full-page navigation into the locale
 * tree: the locale builds are separate bundles (DD-039), so there is no
 * runtime string swap, only `location` URLs (SHC-04).
 */
@Component({
    imports: [FontAwesomeModule, Header],
    selector: "aurelius-atlas-webapp-header",
    templateUrl: "./header.component.html",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShellHeader {
    private readonly config = inject(APP_CONFIG);

    protected readonly appName = this.config.appName;

    protected readonly session = inject(Session);

    protected readonly locales: readonly string[] = LOCALES;

    protected readonly faBook = faBook;

    protected readonly documentationUrl = DOCUMENTATION_URL;

    private readonly keycloak = inject(Keycloak);

    /**
     * The full-page URL of a locale's copy of the current page: the active
     * locale prefix is stripped and the chosen one prepended (SHC-04).
     * @param locale the locale to switch to
     * @param currentPath the current path (the location, by default — a
     *   parameter so specs pin every locale pair)
     * @returns the href to navigate to
     */
    protected localeHref(locale: string, currentPath: string = location.pathname): string {
        const stripped = currentPath.replace(/^\/(?:en-US|nl-NL)(?=\/|$)/, "");

        return `/${locale}${stripped === "" ? "/" : stripped}`;
    }

    /**
     * Keycloak's account console for the configured realm — the legacy
     * `accountManagement()` (keycloak-js dropped its `accountManager`, so the
     * port composes the URL from the runtime config, SHC-05).
     */
    protected get accountUrl(): string {
        const { url, realm } = this.config.keycloak;

        return new URL(`realms/${realm}/account`, url).href;
    }

    /** End the Keycloak session (SHC-05), returning to the sign-in page. */
    protected logout(): void {
        this.keycloak.logout();
    }

    /** The active locale, as the served document declares it. */
    protected get activeLocale(): string {
        return document.documentElement.lang;
    }
}
