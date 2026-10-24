/**
 * The example app's boot pair (DD-125, mirrors the webapp's 7.19 spec):
 * `initialize()` assembles its providers from a served `/config.json`, and a
 * non-2xx answer fails the boot loudly — an unreachable config is an
 * operator-visible failure, never a silently half-configured UI.
 */
import { ApplicationConfig } from "@angular/core";
import { afterEach, describe, expect, it, vi } from "vitest";
import { initialize } from "./app.config";

const configPayload = {
    keycloak: { clientId: "aurelius", realm: "master", url: "https://keycloak.localhost:8443" },
    apiBaseUrl: "/api",
    otelExporterUrl: "/otel/v1/traces",
};

describe("example app boot (DD-125)", () => {
    afterEach(() => vi.unstubAllGlobals());

    it("assembles the provider set from a served /config.json", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn(async () => new Response(JSON.stringify(configPayload), { status: 200 })),
        );

        const appConfig: ApplicationConfig = await initialize();

        expect(appConfig.providers.length).toBeGreaterThan(0);
    });

    it("initialize fails loudly when /config.json answers 500 (SHL-02)", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn(async () => new Response("upstream exploded", { status: 500, statusText: "Server Error" })),
        );

        await expect(initialize()).rejects.toThrow(/Failed to load app config \(\/config\.json\): 500 Server Error/);
    });
});
