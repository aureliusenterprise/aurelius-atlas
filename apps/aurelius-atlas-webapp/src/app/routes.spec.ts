import { Routes } from "@angular/router";

import { routes } from "./routes";
import { SEARCH_ROUTES } from "./search/search.routes";

describe("routes", () => {
    it("redirects the root to the Aurelius default destination /search/browse (SHL-04)", () => {
        expect(routes[0]).toMatchObject({ path: "", redirectTo: "search/browse", pathMatch: "full" });
    });

    it("lazy-loads the search subtree", async () => {
        const search = routes[1];
        expect(search.path).toBe("search");

        const loadChildren = search.loadChildren as unknown as () => Promise<Routes>;
        await expect(loadChildren()).resolves.toBe(SEARCH_ROUTES);
    });

    it("redirects unknown paths to the default destination, as the Aurelius '**' fallback (SHL-05, DD-043)", () => {
        expect(routes.at(-1)).toMatchObject({ path: "**", redirectTo: "search/browse", pathMatch: "full" });
    });
});

describe("SEARCH_ROUTES", () => {
    it("redirects the empty path to browse", () => {
        expect(SEARCH_ROUTES[0]).toMatchObject({ path: "", redirectTo: "browse", pathMatch: "full" });
    });

    it("lazy-loads the browse placeholder", async () => {
        const browse = SEARCH_ROUTES[1];
        expect(browse.path).toBe("browse");

        const loadComponent = browse.loadComponent as unknown as () => Promise<unknown>;
        await expect(loadComponent()).resolves.toBeTruthy();
    });
});
