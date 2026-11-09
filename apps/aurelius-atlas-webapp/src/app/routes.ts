import { ActivatedRouteSnapshot, RouterStateSnapshot, Routes, UrlMatchResult, UrlSegment } from "@angular/router";
import { AuthGuardData, createAuthGuard } from "keycloak-angular";

/**
 * The create-mode editor route's matcher (DD-355): it takes `create` and
 * `create/<type>` in one config. The type is optional because Angular has no
 * optional path segments (a `?` in a path is literal, DD-330), and a second
 * entry for `create/:type` would put the two URLs in two different configs —
 * which is how the router decides whether to reuse a component. With two
 * entries, the first type pick replaced the editor and the drawer replayed
 * its slide-in. One config keeps the component, so the pick only changes the
 * `:type` parameter.
 * @param segments the unclaimed segments of the `drawer` outlet
 * @returns the consumed segments, with the type as `:type` when present
 */
export function createEntityMatcher(segments: UrlSegment[]): UrlMatchResult | null {
    const [first, second] = segments;
    if (first?.path !== "create") {
        return null;
    }

    return second ? { consumed: [first, second], posParams: { type: second } } : { consumed: [first] };
}

/** The tabs the lineage quickview's route segment may name (DD-415). */
const LINEAGE_TABS = new Set(["browse", "model", "view", "selection"]);

/**
 * The lineage quickview route's matcher (DD-415): it takes `lineage`,
 * `lineage/<tab>`, and `lineage/selection/<concept>` in one config — the
 * `createEntityMatcher` posture (DD-355): one config keeps the component
 * across tab and selection changes, so switching tabs never rebuilds the
 * drawer or replays its slide-in.
 * @param segments the unclaimed segments of the `drawer` outlet
 * @returns the consumed segments, with the tab and concept as posParams
 */
export function lineageDrawerMatcher(segments: UrlSegment[]): UrlMatchResult | null {
    const [first, second, third] = segments;
    if (first?.path !== "lineage") {
        return null;
    }
    if (second?.path === "selection" && third !== undefined) {
        return { consumed: [first, second, third], posParams: { tab: second, concept: third } };
    }
    if (second !== undefined && LINEAGE_TABS.has(second.path)) {
        return { consumed: [first, second], posParams: { tab: second } };
    }
    return { consumed: [first] };
}
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
            // The entity editor drawer, the third route in the one `drawer`
            // outlet (EDT-01, DD-322): the details pencil navigates to
            // `(drawer:edit:guid)` and the hero `+` to `(drawer:create)`.
            // The mode rides the route data (DD-355); the outlet swaps it in
            // over whatever screen is underneath. Create carries the chosen
            // type as a route parameter (DD-330): the bare segment opens the
            // picker, `create/<type>` opens the form for that type, and a
            // re-pick navigates the new type in — the type is part of the
            // path, so switching is a URL change. One matcher route, not two
            // entries (DD-355): the router reuses a component only across
            // navigations that stay in the same config, and the first pick
            // would otherwise rebuild the editor and replay the drawer's
            // slide-in.
            {
                path: "edit/:guid",
                outlet: "drawer",
                loadComponent: () => import("./search/editor/entity-editor.component").then((m) => m.EntityEditor),
                data: { editorMode: "edit" },
            },
            {
                matcher: createEntityMatcher,
                outlet: "drawer",
                loadComponent: () => import("./search/editor/entity-editor.component").then((m) => m.EntityEditor),
                data: { editorMode: "create" },
            },
            // The lineage quickview, the fourth route in the one `drawer`
            // outlet (LDG-25, DD-415): the diagram's node click navigates to
            // `(drawer:lineage:selection:<concept>)`, the tab strip
            // re-navigates the tab segment, and dismissal navigates away —
            // the editor's shape (DD-322), so the open panel rides the URL
            // and a reload reopens it on the same tab. One matcher config
            // for the tab and the concept (the DD-355 posture): switching
            // tabs stays in the config, so the drawer never rebuilds or
            // replays its slide-in.
            {
                matcher: lineageDrawerMatcher,
                outlet: "drawer",
                loadComponent: () =>
                    import("./search/details/lineage/model-browser.component").then((m) => m.LineageModelBrowser),
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
