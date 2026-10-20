import { TestBed } from "@angular/core/testing";
import { KeycloakService } from "keycloak-angular";

import { Session } from "./session.service";

/**
 * A KeycloakService stand-in exposing only what {@link Session} reads: the
 * parsed token. The guard (APC-05) has resolved before any component renders,
 * so the token is present when the service is constructed.
 */
function provideKeycloak(tokenParsed: Record<string, unknown> | undefined) {
    const keycloak = { getKeycloakInstance: () => ({ tokenParsed }) };

    TestBed.configureTestingModule({ providers: [{ provide: KeycloakService, useValue: keycloak }] });
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
