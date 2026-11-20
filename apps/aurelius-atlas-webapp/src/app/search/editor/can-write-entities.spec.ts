import { TestBed } from "@angular/core/testing";
import Keycloak from "keycloak-js";

import { AppConfig } from "../../config";
import { APP_CONFIG } from "../../tokens";
import { type Tenancy, TENANCY } from "../../tenancy";
import { canWriteEntities, writesInTenant } from "./can-write-entities";

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

describe("canWriteEntities with tenancy on (TNW-07, DD-636)", () => {
    const tenancy: Tenancy = { enabled: true, operatorOrganization: "operators", operatorRole: "atlas-operator" };
    const token = (tenant: string, groups: string[], roles: string[] = []) => ({
        organization: { [tenant]: { groups } },
        realm_access: { roles },
    });

    it("grants by the tenant's /atlas-write group, never by the client roles", () => {
        TestBed.configureTestingModule({
            providers: [
                { provide: TENANCY, useValue: tenancy },
                {
                    provide: Keycloak,
                    useValue: { tokenParsed: token("acme", ["/atlas-read"]), hasResourceRole: () => true },
                },
            ],
        });

        expect(TestBed.runInInjectionContext(() => canWriteEntities())()).toBe(false);
        expect(writesInTenant(tenancy, token("acme", ["/atlas-read", "/atlas-write"]))).toBe(true);
    });

    it("holds an operator at read outside the operator organization, as the server does (TEN-06)", () => {
        expect(writesInTenant(tenancy, token("acme", ["/atlas-write"], ["atlas-operator"]))).toBe(false);
        expect(writesInTenant(tenancy, token("operators", ["/atlas-write"], ["atlas-operator"]))).toBe(true);
    });

    it("denies a token that names no tenant, or several", () => {
        expect(writesInTenant(tenancy, {})).toBe(false);
        expect(
            writesInTenant(tenancy, {
                organization: { acme: { groups: ["/atlas-write"] }, globex: { groups: ["/atlas-write"] } },
            }),
        ).toBe(false);
    });
});
