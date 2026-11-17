import { TestBed } from "@angular/core/testing";
import Keycloak from "keycloak-js";

import { AccountLanguage } from "../settings/account-language.service";
import { TENANT_KEY } from "../settings/user-preference";
import { TENANCY } from "../tenancy";
import { Session } from "./session.service";

/**
 * A Keycloak client stand-in exposing only what {@link Session} reads: the
 * parsed token. The guard (APC-05) has resolved before any component renders,
 * so the token is present when the service is constructed.
 */
function provideKeycloak(tokenParsed: Record<string, unknown> | undefined) {
    const keycloak = { tokenParsed };

    TestBed.configureTestingModule({ providers: [{ provide: Keycloak, useValue: keycloak }] });
}

describe("Session", () => {
    it("prefers the token's preferred_username (SHC-05)", () => {
        provideKeycloak({ preferred_username: "aurelius-writer", email: "writer@aurelius.example" });

        expect(TestBed.inject(Session).identity()).toBe("aurelius-writer");
    });

    it("falls back to the token's e-mail (SHC-05)", () => {
        provideKeycloak({ email: "writer@aurelius.example" });

        expect(TestBed.inject(Session).identity()).toBe("writer@aurelius.example");
    });

    it("is the empty string when no token is readable (SHC-05)", () => {
        provideKeycloak(undefined);

        expect(TestBed.inject(Session).identity()).toBe("");
    });
});

describe("Session's language (SHC-10, DD-665)", () => {
    it("saves the webapp's language with the user once the session exists", () => {
        const accountLanguage = { save: vi.fn().mockResolvedValue(false) };
        TestBed.configureTestingModule({
            providers: [
                { provide: Keycloak, useValue: { tokenParsed: { preferred_username: "aurelius-writer" } } },
                { provide: AccountLanguage, useValue: accountLanguage },
            ],
        });

        TestBed.inject(Session);

        expect(accountLanguage.save).toHaveBeenCalledTimes(1);
    });
});

describe("Session's tenant (TNW-05, TNW-06)", () => {
    afterEach(() => localStorage.clear());

    const ON = { enabled: true, operatorOrganization: "operators", operatorRole: "atlas-operator" };

    it("reads the token's one organization and remembers it for the next silent check", () => {
        TestBed.configureTestingModule({
            providers: [
                { provide: Keycloak, useValue: { tokenParsed: { organization: { acme: { groups: [] } } } } },
                { provide: TENANCY, useValue: ON },
            ],
        });

        expect(TestBed.inject(Session).tenant()).toBe("acme");
        expect(localStorage.getItem(TENANT_KEY)).toBe(JSON.stringify("acme"));
    });

    it("has none with tenancy off, or when the token names none", () => {
        provideKeycloak({ organization: { acme: {} } });

        expect(TestBed.inject(Session).tenant()).toBeUndefined();

        TestBed.resetTestingModule();
        TestBed.configureTestingModule({
            providers: [
                { provide: Keycloak, useValue: { tokenParsed: {} } },
                { provide: TENANCY, useValue: ON },
            ],
        });

        expect(TestBed.inject(Session).tenant()).toBeUndefined();
        expect(localStorage.getItem(TENANT_KEY)).toBeNull();
    });
});
