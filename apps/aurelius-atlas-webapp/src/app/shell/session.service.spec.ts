import { TestBed } from "@angular/core/testing";
import Keycloak from "keycloak-js";

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
