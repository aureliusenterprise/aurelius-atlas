import { EnvironmentProviders, Provider } from "@angular/core";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideRouter } from "@angular/router";

import { Tenancy } from "../app/tenancy";

import { provideFakeKeycloak, FakeKeycloakOptions } from "./auth";
import { provideFakeAppConfig, provideFakeTenancy } from "./config";

/**
 * The provider set every routed screen spec configures by hand: real HTTP with
 * the testing controller, an empty router, a valid config, a Keycloak double,
 * and tenancy off (TNW-03 — the single-tenant answer the write gate reads).
 *
 * Twenty-nine specs hand-rolled a variant of these five providers, each
 * missing one piece, so a screen that started reading a second config field or
 * a Keycloak member broke in the next increment rather than the one that added
 * it. Pass what the screen also needs (a fake `ActivatedRoute`, a
 * `VersionService`) in the spec's own `providers` array.
 *
 * @param options the Keycloak grants and the tenancy answer
 * @returns providers for `TestBed.configureTestingModule`
 */
export function provideScreenTest(
    options: { keycloak?: FakeKeycloakOptions; tenancy?: Tenancy } = {},
): (Provider | EnvironmentProviders)[] {
    return [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        provideFakeAppConfig(),
        provideFakeKeycloak(options.keycloak),
        provideFakeTenancy(options.tenancy),
    ];
}
