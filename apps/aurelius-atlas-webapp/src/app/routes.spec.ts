import { ActivatedRouteSnapshot, RouterStateSnapshot, Routes } from "@angular/router";

const createAuthGuardMock = vi.hoisted(() => vi.fn((guard: unknown) => guard));

vi.mock("keycloak-angular", () => ({
    createAuthGuard: createAuthGuardMock,
}));

import { routes } from "./routes";
import { SEARCH_ROUTES } from "./search/search.routes";

// The guard is registered once, at import time. Copy the calls now: Vitest clears mock history before each test.
const createAuthGuardCalls = [...createAuthGuardMock.mock.calls];

type GuardFn = (
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot,
    authData: { authenticated: boolean; keycloak: { login: (options: { redirectUri: string }) => Promise<void> } },
) => Promise<boolean>;

describe("routes", () => {
    it("guards every route from the app root (APC-05, DD-052)", () => {
        expect(routes).toHaveLength(1);
        expect(routes[0]).toMatchObject({ path: "" });
        expect(routes[0].canActivate).toHaveLength(1);
    });

    it("redirects the root to the Aurelius default destination /search/browse (SHL-04)", () => {
        expect(routes[0].children?.[0]).toMatchObject({ path: "", redirectTo: "search/browse", pathMatch: "full" });
    });

    it("lazy-loads the search subtree", async () => {
        const search = routes[0].children?.[1];
        expect(search?.path).toBe("search");

        const loadChildren = search?.loadChildren as unknown as () => Promise<Routes>;
        await expect(loadChildren()).resolves.toBe(SEARCH_ROUTES);
    });

    it("redirects unknown paths to the default destination, as the Aurelius '**' fallback (SHL-05, DD-043)", () => {
        expect(routes[0].children?.at(-1)).toMatchObject({
            path: "**",
            redirectTo: "search/browse",
            pathMatch: "full",
        });
    });

    it.each(["/", "/en-US/", "/nl-NL/"])(
        "sends an unauthenticated visit to sign-in, returning to %s's route (APC-05)",
        async (baseHref) => {
            const baseUri = vi
                .spyOn(document, "baseURI", "get")
                .mockReturnValue(`${globalThis.location.origin}${baseHref}`);
            const guard = routes[0].canActivate?.[0] as GuardFn;

            const login = vi.fn().mockResolvedValue(undefined);
            const state = { url: "/search/browse" } as RouterStateSnapshot;

            const result = await guard({} as ActivatedRouteSnapshot, state, {
                authenticated: false,
                keycloak: { login },
            });

            expect(result).toBe(false);
            expect(login).toHaveBeenCalledWith({
                redirectUri: `${globalThis.location.origin}${baseHref}search/browse`,
            });
            baseUri.mockRestore();
        },
    );

    it("lets an authenticated visit through without a login round-trip (APC-05)", async () => {
        const guard = routes[0].canActivate?.[0] as GuardFn;

        const login = vi.fn().mockResolvedValue(undefined);
        const state = { url: "/search/browse" } as RouterStateSnapshot;

        const result = await guard({} as ActivatedRouteSnapshot, state, { authenticated: true, keycloak: { login } });

        expect(result).toBe(true);
        expect(login).not.toHaveBeenCalled();
    });

    it("registers the root guard with createAuthGuard, once (DD-052)", () => {
        expect(createAuthGuardCalls).toHaveLength(1);
        expect(typeof createAuthGuardCalls[0][0]).toBe("function");
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
