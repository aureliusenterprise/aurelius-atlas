import { Injectable, inject } from "@angular/core";
import Keycloak from "keycloak-js";

import { AppConfig } from "../config";
import { APP_CONFIG } from "../tokens";

/**
 * Keycloak's language for a webapp locale: `nl` for `nl-NL`, `en` for every
 * other, the realm's two languages (SHC-10).
 * @param locale the webapp locale, as the served document declares it
 * @returns the realm's language code
 */
export function keycloakLanguage(locale: string): string {
    return locale.toLowerCase().startsWith("nl") ? "nl" : "en";
}

/**
 * An address below the configured realm. Keycloak's URL may sit below a path,
 * as the standalone stack's `/auth`: it is read as a folder, or the relative
 * path would replace its last segment (SHC-05).
 * @param config the runtime configuration's Keycloak section
 * @param path the path below `realms/<realm>/`
 * @returns the absolute URL
 */
export function realmUrl({ url, realm }: AppConfig["keycloak"], path: string): string {
    const base = url.endsWith("/") ? url : `${url}/`;

    return new URL(`realms/${realm}/${path}`, base).href;
}

/** The account API's user, as far as the language needs it. */
interface AccountUser {
    attributes?: Record<string, string[] | undefined>;
    [field: string]: unknown;
}

/**
 * Saves the webapp's language as the user's language in Keycloak (SHC-10,
 * DD-665), so Keycloak's account console and sign-in pages speak it too: they
 * take the user's saved `locale`, not the webapp's. The save goes through
 * Keycloak's account API with the user's own token, only when the token's
 * `locale` differs, and is best effort: a realm that grants the webapp's
 * client no account rights, or an unreachable Keycloak, leaves the language
 * as it was, without an alert.
 */
@Injectable({ providedIn: "root" })
export class AccountLanguage {
    private readonly keycloak = inject(Keycloak);

    /** The runtime configuration; absent only where no app is bootstrapped (component specs). */
    private readonly config = inject(APP_CONFIG, { optional: true });

    /**
     * Save the language of `locale` unless the user already has it.
     * @param locale the webapp locale (the served document's, by default)
     * @returns whether the language was saved
     */
    async save(locale: string = document.documentElement.lang): Promise<boolean> {
        const language = keycloakLanguage(locale);
        const token = this.keycloak.token;
        if (this.config === null || token === undefined || this.keycloak.tokenParsed?.["locale"] === language) {
            return false;
        }
        const account = realmUrl(this.config.keycloak, "account/");
        const headers = { Authorization: `Bearer ${token}`, Accept: "application/json" };
        try {
            const read = await fetch(account, { headers });
            if (!read.ok) {
                return false;
            }
            const user = (await read.json()) as AccountUser;
            if (user.attributes?.["locale"]?.[0] === language) {
                return false;
            }
            const saved = await fetch(account, {
                method: "POST",
                headers: { ...headers, "Content-Type": "application/json" },
                body: JSON.stringify({ ...user, attributes: { ...user.attributes, locale: [language] } }),
            });

            return saved.ok;
        } catch {
            // Best effort: Keycloak unreachable, or no CORS for this origin.
            return false;
        }
    }
}
