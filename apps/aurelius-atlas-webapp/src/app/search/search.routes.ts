import { Routes } from "@angular/router";

/**
 * The `/search` route subtree, the first half of the Aurelius
 * `SearchRoutingModule`.
 *
 * 7.1 delivers the browse placeholder only: the real browse screen arrives with
 * 7.5, and results/details/editor with 7.4 and 7.6-7.7, replacing this
 * subtree route by route.
 */
export const SEARCH_ROUTES: Routes = [
    { path: "", redirectTo: "browse", pathMatch: "full" },
    {
        path: "browse",
        loadComponent: () => import("./browse/browse.component").then((m) => m.Browse),
    },
];
