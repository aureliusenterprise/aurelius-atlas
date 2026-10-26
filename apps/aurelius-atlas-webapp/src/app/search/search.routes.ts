import { Routes } from "@angular/router";

/**
 * The Aurelius search subtree, lazy-loaded from the app root. Every path
 * here is relative to `/search`, the Aurelius router's search prefix
 * (SHL-04: `'' -> /search/browse` is the app's default destination).
 *
 * Since 7.4a (DD-218) the subtree is the search layout's shell: the layout
 * carries the hero — the design's search bar (DD-145 superseded) — and the
 * `SearchState` store, scoped to the subtree so leaving search discards the
 * result set: the legacy store-reset on browse, by construction (SRH-02).
 * The screens are its children — the browse landing, the results screen
 * (7.4a), and the 7.6 details skeleton (DET-01) — and the layout's hero
 * stays mounted across them, as the legacy `search` route kept its
 * browse/search screens under one chrome.
 */
export const SEARCH_ROUTES: Routes = [
    {
        path: "",
        loadComponent: () => import("./search-layout.component").then((m) => m.SearchLayout),
        children: [
            { path: "", redirectTo: "browse", pathMatch: "full" },
            {
                path: "browse",
                loadComponent: () => import("./browse/browse.component").then((m) => m.Browse),
            },
            {
                path: "results",
                loadComponent: () => import("./results/results.component").then((m) => m.Results),
            },
            {
                path: "details/:guid",
                loadComponent: () => import("./details/details.component").then((m) => m.Details),
            },
        ],
    },
];
