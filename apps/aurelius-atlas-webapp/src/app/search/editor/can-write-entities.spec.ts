import { TestBed } from "@angular/core/testing";
import Keycloak from "keycloak-js";

import { AppConfig } from "../../config";
import { APP_CONFIG } from "../../tokens";
import { canWriteEntities } from "./can-write-entities";

/**
 * The gate's inputs: the Keycloak client's role check (the seam the token
 * feeds, EDT-09) and the config's `atlasClientId`.
 */
function configure(options: {
    hasResourceRole?: (role: string, resource?: string) => boolean;
    atlasClientId?: string;
}): void {
    const config = {
        keycloak: { clientId: "aurelius", realm: "master", url: "https://keycloak.localhost:8443" },
        apiBaseUrl: "/api",
        otelExporterUrl: "/otel/v1/traces",
        appName: "Aurelius Atlas Data Governance",
        appCopyright: 2022,
        appVersion: "0.0.0",
        ...(options.atlasClientId === undefined ? {} : { atlasClientId: options.atlasClientId }),
    } as AppConfig;

    TestBed.configureTestingModule({
        providers: [
            { provide: APP_CONFIG, useValue: config },
            {
                provide: Keycloak,
                useValue: { hasResourceRole: options.hasResourceRole ?? (() => false) },
            },
        ],
    });
}

describe("canWriteEntities (EDT-09)", () => {
    it("grants when the configured client's roles hold atlas-write", () => {
        const hasResourceRole = vi.fn(() => true);
        configure({ hasResourceRole, atlasClientId: "aurelius-atlas-server" });

        const canWrite = TestBed.runInInjectionContext(() => canWriteEntities());

        expect(canWrite()).toBe(true);
        expect(hasResourceRole).toHaveBeenCalledWith("atlas-write", "aurelius-atlas-server");
    });

    it("denies when the roles answer for no such client entry", () => {
        const hasResourceRole = vi.fn(() => false);
        configure({ hasResourceRole });

        const canWrite = TestBed.runInInjectionContext(() => canWriteEntities());

        expect(canWrite()).toBe(false);
    });

    it("asks the client the config names (DD-324)", () => {
        const hasResourceRole = vi.fn(() => true);
        configure({ hasResourceRole, atlasClientId: "atlas-prod" });

        TestBed.runInInjectionContext(() => canWriteEntities());

        expect(hasResourceRole).toHaveBeenCalledWith("atlas-write", "atlas-prod");
    });

    it("falls back to the server's client id when the config omits it (DD-324)", () => {
        const hasResourceRole = vi.fn(() => true);
        configure({ hasResourceRole });

        TestBed.runInInjectionContext(() => canWriteEntities());

        expect(hasResourceRole).toHaveBeenCalledWith("atlas-write", "aurelius-atlas-server");
    });

    it("reads the roles once, at page load (EDT-09)", () => {
        const hasResourceRole = vi.fn(() => true);
        configure({ hasResourceRole });

        const canWrite = TestBed.runInInjectionContext(() => canWriteEntities());
        canWrite();
        canWrite();

        expect(hasResourceRole).toHaveBeenCalledTimes(1);
    });
});
