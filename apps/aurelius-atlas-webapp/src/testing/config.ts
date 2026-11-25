import { Provider } from "@angular/core";

import { AppConfig, DEFAULT_ATLAS_CLIENT_ID } from "../app/config";
import { NO_TENANCY, TENANCY, Tenancy } from "../app/tenancy";
import { APP_CONFIG } from "../app/tokens";

/**
 * The runtime config a test runs with (SHL-10's channel, ADR 018). Specs used
 * to inline `{ atlasClientId: "aurelius-atlas-server" }` fifteen times — an
 * object that satisfies no part of {@link AppConfig} except the one field the
 * test happened to read, so the type check never caught a screen that started
 * reading `appName` or a Keycloak setting.
 *
 * This is a whole, valid config built the way `parseAppConfig` builds the
 * real one, so a screen reading any field gets the deployed value's shape.
 */
export function fakeAppConfig(overrides: Partial<AppConfig> = {}): AppConfig {
    const { keycloak, ...rest } = overrides;
    return {
        keycloak: {
            clientId: "aurelius",
            realm: "master",
            url: "https://keycloak.localhost:8443",
            ...keycloak,
        },
        apiBaseUrl: "/api",
        otelExporterUrl: "/otel/v1/traces",
        appName: "Aurelius Atlas Data Governance",
        atlasClientId: DEFAULT_ATLAS_CLIENT_ID,
        ...rest,
    };
}

/**
 * The `APP_CONFIG` provider with a full, valid config.
 *
 * @param overrides fields this test needs to change
 * @returns the provider
 */
export function provideFakeAppConfig(overrides: Partial<AppConfig> = {}): Provider {
    return { provide: APP_CONFIG, useValue: fakeAppConfig(overrides) };
}

/**
 * The tenancy provider (TNW-02). Off by default — the same answer a
 * single-tenant deployment gives — so the write gate reads client roles;
 * pass the server's answer to exercise the tenant path (TNW-07, DD-636).
 *
 * @param tenancy the server's answer, {@link NO_TENANCY} unless given
 * @returns the provider
 */
export function provideFakeTenancy(tenancy: Tenancy = NO_TENANCY): Provider {
    return { provide: TENANCY, useValue: tenancy };
}
