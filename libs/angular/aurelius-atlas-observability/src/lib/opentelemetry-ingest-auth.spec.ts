/**
 * The OTLP ingest-credential seam (7.17, DD-193): the exporter headers
 * factory attaches the signed-in user's Keycloak token to every OTLP push
 * (the collector's OIDC receiver, CIA-02); a signed-out tab sends nothing
 * and the collector answers 401 (the accepted pre-login telemetry loss).
 *
 * The seam is a plain closure — no DI, no Keycloak client construction:
 * these tests drive it with the stub keycloak-angular's interceptor seam
 * documents (authenticated / updateToken / token).
 */
import { describe, expect, it, vi, type Mock } from "vitest";

import { createAureliusOtelIngestAuth, type OtelIngestAuthClient } from "./opentelemetry-ingest-auth";

type KeycloakStub = Omit<OtelIngestAuthClient, "updateToken"> & {
    updateToken: Mock<(minValidity: number) => Promise<boolean>>;
};

function makeKeycloakStub(): KeycloakStub {
    return {
        authenticated: true,
        token: "test-token",
        updateToken: vi.fn(async () => true),
    };
}

describe("createAureliusOtelIngestAuth (7.17, DD-193)", () => {
    it("sends the bearer token of an authenticated session (CIA-02)", async () => {
        const keycloak = makeKeycloakStub();
        const auth = createAureliusOtelIngestAuth();
        auth.attach(keycloak);

        await expect(auth.headers()).resolves.toEqual({ Authorization: "Bearer test-token" });
        expect(keycloak.updateToken).toHaveBeenCalledWith(30);
    });

    it("sends nothing for a signed-out session (DD-193)", async () => {
        const keycloak = { ...makeKeycloakStub(), authenticated: false };
        const auth = createAureliusOtelIngestAuth();
        auth.attach(keycloak);

        await expect(auth.headers()).resolves.toEqual({});
        expect(keycloak.updateToken).not.toHaveBeenCalled();
    });

    it("sends nothing before the client attaches (DD-193)", async () => {
        const auth = createAureliusOtelIngestAuth();

        await expect(auth.headers()).resolves.toEqual({});
    });

    it("sends the current token when refresh fails (DD-193)", async () => {
        const keycloak = makeKeycloakStub();
        keycloak.updateToken = vi.fn(async () => {
            throw new Error("session gone");
        });
        const auth = createAureliusOtelIngestAuth();
        auth.attach(keycloak);

        await expect(auth.headers()).resolves.toEqual({ Authorization: "Bearer test-token" });
    });

    it("sends nothing for an authenticated session without a token (DD-193)", async () => {
        const keycloak = { ...makeKeycloakStub(), token: undefined };
        const auth = createAureliusOtelIngestAuth();
        auth.attach(keycloak);

        await expect(auth.headers()).resolves.toEqual({});
        expect(keycloak.updateToken).toHaveBeenCalledWith(30);
    });
});
