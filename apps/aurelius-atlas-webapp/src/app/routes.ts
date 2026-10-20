import { Routes } from "@angular/router";

/**
 * The application routes, ported from the Aurelius `AppRoutingModule`.
 *
 * Aurelius (apps/atlas/src/app/app-routing.module.ts) redirects the root to
 * `/search/browse` and sends unknown paths back to the root; both behaviours
 * are kept (SHL-04, SHL-05). Scroll restoration is configured in
 * `app.config.ts`, where Aurelius had `scrollPositionRestoration: 'enabled'`
 * (SHL-06).
 */
export const routes: Routes = [
    { path: "", redirectTo: "search/browse", pathMatch: "full" },
    {
        path: "search",
        loadChildren: () => import("./search/search.routes").then((m) => m.SEARCH_ROUTES),
    },
    // Fallback when no prior route is matched (SHL-05, as Aurelius's '**').
    // Aurelius: { path: '**', redirectTo: '' } — in the legacy app the chain
    // '**' -> '' -> '/search/browse' lands on the default destination.
    // Angular 22's router stops at '' after a wildcard redirect (the
    // empty-path redirect is not re-triggered), so the fallback redirects
    // straight to the destination: same observable end state (SHL-05), DD-043.
    { path: "**", redirectTo: "search/browse", pathMatch: "full" },
];
