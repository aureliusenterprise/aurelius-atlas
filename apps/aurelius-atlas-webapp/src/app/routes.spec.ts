import { ActivatedRouteSnapshot, RouterStateSnapshot, Routes } from "@angular/router";

const createAuthGuardMock = vi.hoisted(() => vi.fn((guard: unknown) => guard));

vi.mock("keycloak-angular", () => ({
    createAuthGuard: createAuthGuardMock,
}));

import { routes } from "./routes";
import { SEARCH_ROUTES } from "./search/search.routes";
import { SettingsPanel } from "./settings/settings-panel.component";

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

    it("routes the settings panel into the drawer aux outlet (SPL-14, DD-078)", async () => {
        const settings = routes[0].children?.find((route) => route.outlet === "drawer");
        expect(settings?.path).toBe("settings");

        const loadComponent = settings?.loadComponent as unknown as () => Promise<unknown>;
        await expect(loadComponent()).resolves.toBe(SettingsPanel);
    });

    it("routes the alerts panel into the drawer aux outlet (ALR-01)", async () => {
        // The one named outlet carries both drawers (ALR-01): the bell
        // navigates to `(drawer:alerts)`, and the outlet swaps the panels.
        const alerts = routes[0].children?.find((route) => route.path === "alerts");
        expect(alerts?.outlet).toBe("drawer");

        const loadComponent = alerts?.loadComponent as unknown as () => Promise<unknown>;
        const { AlertsPanel } = await import("./alerts/alerts-panel.component");
        await expect(loadComponent()).resolves.toBe(AlertsPanel);
    });

    it("routes the details skeleton at search/details/:guid (DET-01)", async () => {
        // The Aurelius `details` module's `:id` child (DET-01): the deep
        // link is the screen's whole state until the 2.3 wiring increment
        // feeds it (DD-096).
        const details = SEARCH_ROUTES.find((route) => route.path === "details/:guid");
        expect(details).toBeDefined();

        const loadComponent = details?.loadComponent as unknown as () => Promise<unknown>;
        const { Details } = await import("./search/details/details.component");
        await expect(loadComponent()).resolves.toBe(Details);
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

    it("strips the auth-response fragment from the re-login redirect_uri (APC-05)", async () => {
        // Keycloak answers with the code in the URL fragment; when init cannot
        // consume it (a tracking-preventing browser blocks keycloak-js's
        // 3rd-party-cookies check), the guard re-fires — and the exact-registered
        // redirect_uri must not carry the fragment, which Keycloak answers 400.
        const guard = routes[0].canActivate?.[0] as GuardFn;

        const login = vi.fn().mockResolvedValue(undefined);
        const state = { url: "/search/browse#state=abc&session_state=xyz&code=123" } as RouterStateSnapshot;

        const result = await guard({} as ActivatedRouteSnapshot, state, {
            authenticated: false,
            keycloak: { login },
        });

        expect(result).toBe(false);
        expect(login).toHaveBeenCalledWith({
            redirectUri: `${globalThis.location.origin}/search/browse`,
        });
    });

    it("keeps query parameters on the re-login redirect_uri (APC-05)", async () => {
        const guard = routes[0].canActivate?.[0] as GuardFn;

        const login = vi.fn().mockResolvedValue(undefined);
        const state = { url: "/search/browse?q=gene%20expression" } as RouterStateSnapshot;

        await guard({} as ActivatedRouteSnapshot, state, { authenticated: false, keycloak: { login } });

        expect(login).toHaveBeenCalledWith({
            redirectUri: `${globalThis.location.origin}/search/browse?q=gene%20expression`,
        });
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
