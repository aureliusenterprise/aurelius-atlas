import { Injectable, inject } from "@angular/core";
import Keycloak from "keycloak-js";

import { AlertsService } from "../alerts/alerts.service";

/**
 * The sign-in again a mid-session token loss needs (ALR-13, DD-706).
 *
 * keycloak-angular refreshes the access token before it sends a bearer call
 * (APC-07), so a `401` that reaches the app means the refresh failed too: the
 * session itself is gone, and only an interactive sign-in recovers it. The
 * root guard (APC-05) signs in on navigation, but a token that dies between
 * navigations never triggers it — the user just sees failed calls. This
 * service is that missing door: a `401` becomes a warning alert and one
 * sign-in back to the page shown (SHC-05's `login` pattern).
 *
 * A dead session fails every in-flight call at once, so the sign-in fires
 * once: the first `401` redirects and later ones are ignored. It also caps a
 * misconfigured audience (which 401s forever) at a single bounce rather than
 * a redirect loop.
 */
@Injectable({ providedIn: "root" })
export class SessionExpiry {
    private readonly alerts = inject(AlertsService);

    private readonly keycloak = inject(Keycloak);

    private redirected = false;

    /**
     * Warn about the expired session and sign in again, once (ALR-13).
     *
     * The warning names what happened, not the failed call — the drawer's
     * grouping (ALR-03) already folds a burst, and the cause is the same for
     * every `401` in it. The sign-in returns to the current page.
     */
    expired(): void {
        if (this.redirected) {
            return;
        }
        this.redirected = true;
        this.alerts.add({
            severity: "warning",
            message: $localize`:@@shell.alerts.expired:Your session has expired. Signing you in again.`,
            source: "http",
        });
        // The navigation starts at once; the promise resolves on Keycloak's page.
        void this.keycloak.login({ redirectUri: globalThis.location.href });
    }
}
