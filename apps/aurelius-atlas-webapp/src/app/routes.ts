import { ActivatedRouteSnapshot, RouterStateSnapshot, Routes } from "@angular/router";
import { AuthGuardData, createAuthGuard } from "keycloak-angular";

/**
 * The app-root guard (APC-05, DD-141): an unauthenticated visit redirects to the
 * Keycloak sign-in page and returns to the requested route afterwards. The legacy
 * `Shell.childRoutes(..., requiresAuth)` guarded every feature route from the shell;
 * `createAuthGuard` on the root route guards them all from where routing is declared,
 * and no screen can forget it.
 * @param _route the activated route (unused)
 * @param state the router state — its url becomes the post-login redirect
 * @param keycloak the guard's injected Keycloak (APC-05)
 * @param keycloak.authenticated whether Keycloak's check-sso found a session
 * @param keycloak.login the Keycloak client
 * @returns whether the navigation may proceed
 */
async function rootAuthGuard(
    _route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot,
    { authenticated, keycloak }: AuthGuardData,
): Promise<boolean> {
    if (!authenticated) {
        // The auth code comes back in the URL *fragment* (response_mode=fragment);
        // when init fails to consume it (a tracking-preventing browser blocks the
        // 3rd-party-cookies check keycloak-js runs first), the guard re-fires with
        // that fragment on the url — Keycloak then rejects the exact-registered
        // redirect_uri with 400. Strip the fragment; keep query params (app state).
        const path = state.url.split("#")[0];
        await keycloak.login({ redirectUri: new URL(path.replace(/^\//, ""), document.baseURI).href });
    }
    return authenticated;
}

/**
 * The application routes, ported from the Aurelius `AppRoutingModule`.
 *
 * Aurelius (apps/atlas/src/app/app-routing.module.ts) redirects the root to
 * `/search/browse` and sends unknown paths back to the root; both behaviours
 * are kept (SHL-04, SHL-05). Scroll restoration is configured in
 * `app.config.ts`, where Aurelius had `scrollPositionRestoration: 'enabled'`
 * (SHL-06).
 *
 * Everything sits under one guarded empty-path parent (APC-05, DD-141): the
 * parent matches every navigation, so its guard runs for every screen — the
 * signal-state replacement of the Aurelius shell's per-route `requiresAuth`.
 */
export const routes: Routes = [
    {
        path: "",
        canActivate: [createAuthGuard(rootAuthGuard)],
        children: [
            { path: "", redirectTo: "search/browse", pathMatch: "full" },
            {
                path: "search",
                loadChildren: () => import("./search/search.routes").then((m) => m.SEARCH_ROUTES),
            },
            // The settings panel, in the `drawer` aux outlet (SPL-14, DD-166):
            // the gear navigates to `(drawer:settings)`, dismissal navigates
            // away, and the segment rides the URL — the language switch's
            // full-page reload (SPL-06) lands on the same page, panel open.
            {
                path: "settings",
                outlet: "drawer",
                loadComponent: () => import("./settings/settings-panel.component").then((m) => m.SettingsPanel),
            },
            // The alerts drawer, the second route in the one `drawer` outlet
            // (ALR-01, DD-166's shape): the bell navigates to `(drawer:alerts)`
            // and the outlet swaps panels — the settings panel and the alerts
            // drawer replace each other, the open state rides the URL.
            {
                path: "alerts",
                outlet: "drawer",
                loadComponent: () => import("./alerts/alerts-panel.component").then((m) => m.AlertsPanel),
            },
            // Fallback when no prior route is matched (SHL-05, as Aurelius's '**').
            // Aurelius: { path: '**', redirectTo: '' } — in the legacy app the chain
            // '**' -> '' -> '/search/browse' lands on the default destination.
            // Angular 22's router stops at '' after a wildcard redirect (the
            // empty-path redirect is not re-triggered), so the fallback redirects
            // straight to the destination: same observable end state (SHL-05), DD-132.
            { path: "**", redirectTo: "search/browse", pathMatch: "full" },
        ],
    },
];
