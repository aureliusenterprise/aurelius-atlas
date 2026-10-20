/**
 * The auth wiring {@link initialize} assembles (7.3): the Keycloak init options
 * (APC-05), the bearer-token interceptor config (APC-06), and the API base URL
 * (APC-01) — plus the absence of a hand-written token-refresh loop (APC-07).
 *
 * The wiring is tested at its seams: the two config decisions are exported from
 * `app.config.ts` and asserted directly, and the provider list is inspected for the
 * bearer config. The interceptor itself is driven end-to-end with the *real*
 * `includeBearerTokenInterceptor` from keycloak-angular and a stubbed `Keycloak`
 * instance — the seam keycloak-angular itself documents (`authenticated` /
 * `updateToken` / `getToken`). The real `keycloak-js` client is constructed by
 * `provideKeycloak` (its constructor validates the config — the APC-05 plumbing), and
 * its `init` is never called here: jsdom cannot run the SSO round-trip; that flow is
 * the e2e suite's (APC-10). `aurelius-atlas-observability` is mocked so no OTel SDK
 * starts in the unit environment.
 */
import { HttpClient, HttpHandlerFn, HttpRequest } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { ApplicationConfig, Provider } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { API_BASE_URL } from "aurelius-atlas-data-access";
import Keycloak from "keycloak-js";
import { INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG } from "keycloak-angular";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { bearerTokenConfig, initialize, keycloakInitOptions } from "./app.config";

const configPayload = {
    keycloak: { clientId: "aurelius", realm: "master", url: "https://keycloak.localhost:8443" },
    apiBaseUrl: "/api",
    otelExporterUrl: "/otel/v1/traces",
};

vi.mock("aurelius-atlas-observability", () => ({
    AureliusTraceErrorHandler: class {},
    aureliusOpenTelemetryHttpInterceptor: (req: HttpRequest<unknown>, next: HttpHandlerFn) => next(req),
    createAureliusSessionResource: () => ({}),
    provideAureliusOpenTelemetry: () => [],
    provideAureliusOpenTelemetryMetrics: () => [],
}));

/**
 * The Keycloak seams `includeBearerTokenInterceptor` reads: `updateToken()` before
 * adding the header (keycloak-angular's `conditionallyUpdateToken`) and the `token`
 * property it writes into the header (its `addAuthorizationHeader`).
 */
type KeycloakStub = {
    authenticated: boolean;
    token: string;
    updateToken: ReturnType<typeof vi.fn>;
};

function makeKeycloakStub(): KeycloakStub {
    return {
        authenticated: true,
        token: "test-token",
        updateToken: vi.fn(async () => true),
    };
}

/**
 * Run {@link initialize} against a stubbed `/config.json` and configure TestBed with
 * its providers plus HTTP testing and the Keycloak stub (the last provider wins for
 * the `Keycloak` token, so the real client `provideKeycloak` built is never consulted;
 * its `init` app-initializer never runs — TestBed initializers run at component
 * creation, which these tests never do).
 * @returns the provider list, for inspection
 */
async function bootstrap(keycloak: KeycloakStub): Promise<Provider[]> {
    vi.stubGlobal(
        "fetch",
        vi.fn(async () => new Response(JSON.stringify(configPayload), { status: 200 })),
    );
    const appConfig: ApplicationConfig = await initialize();
    vi.unstubAllGlobals();

    TestBed.configureTestingModule({
        providers: [...appConfig.providers, provideHttpClientTesting(), { provide: Keycloak, useValue: keycloak }],
    });
    return appConfig.providers as Provider[];
}

describe("app providers (7.3)", () => {
    afterEach(() => TestBed.resetTestingModule());

    it("keycloakInitOptions is check-sso with the silent-SSO redirect (APC-05)", () => {
        expect(keycloakInitOptions()).toEqual({
            onLoad: "check-sso",
            silentCheckSsoRedirectUri: `${globalThis.location.origin}/silent-check-sso.html`,
        });
    });

    it("bearerTokenConfig covers /api calls only (APC-06)", () => {
        expect(bearerTokenConfig).toHaveLength(1);
        const { urlPattern } = bearerTokenConfig[0];
        expect(urlPattern.test("/api/atlas/admin/version")).toBe(true);
        expect(urlPattern.test("/api/atlas/v2/types/typedefs")).toBe(true);
        expect(urlPattern.test("/otel/v1/traces")).toBe(false);
        expect(urlPattern.test("/config.json")).toBe(false);
    });

    it("assembles the bearer config into the provider set (APC-06)", async () => {
        const providers = await bootstrap(makeKeycloakStub());

        const bearerProvider = providers
            .filter(
                (p): p is { provide: unknown; useValue: unknown } =>
                    typeof p == "object" && p != null && "provide" in p,
            )
            .find((p) => p.provide === INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG);

        expect(bearerProvider?.useValue).toBe(bearerTokenConfig);
    });

    it("provides the API base URL from the runtime config (APC-01)", async () => {
        await bootstrap(makeKeycloakStub());
        expect(TestBed.inject(API_BASE_URL)).toBe("/api");
    });

    it("the bearer interceptor signs /api calls (APC-06)", async () => {
        await bootstrap(makeKeycloakStub());

        TestBed.inject(HttpClient).get("/api/atlas/admin/version").subscribe();
        // The interceptor resolves updateToken/getToken asynchronously; flush microtasks.
        await new Promise((resolve) => setTimeout(resolve));

        const req = TestBed.inject(HttpTestingController).expectOne("/api/atlas/admin/version");
        expect(req.request.headers.get("Authorization")).toBe("Bearer test-token");
        req.flush({});
    });

    it("the bearer interceptor leaves non-/api calls alone (APC-06)", async () => {
        const keycloak = makeKeycloakStub();
        await bootstrap(keycloak);

        TestBed.inject(HttpClient).get("/other/thing").subscribe();
        await new Promise((resolve) => setTimeout(resolve));

        const req = TestBed.inject(HttpTestingController).expectOne("/other/thing");
        expect(req.request.headers.has("Authorization")).toBe(false);
        expect(keycloak.updateToken).not.toHaveBeenCalled();
        req.flush({});
    });

    it("ships no hand-written updateToken scheduler (APC-07)", () => {
        // Anchored at process.cwd(): Vitest virtualises import.meta.url to
        // <workspace-root>/spec-app-*.js, and __dirname is the Vite root — either
        // recursive walk would scan node_modules (keycloak-js declares updateToken
        // in its own typings).
        const appDir = join(process.cwd(), "apps/aurelius-atlas-webapp/src/app");
        const sources = readdirSync(appDir, { recursive: true })
            .filter((entry): entry is string => typeof entry == "string")
            .filter((entry) => entry.endsWith(".ts") && !entry.endsWith(".spec.ts"))
            .map((entry) => readFileSync(join(appDir, entry), "utf8"));

        expect(sources.length).toBeGreaterThan(0);
        expect(sources.some((source) => source.includes("updateToken("))).toBe(false);
    });
});
