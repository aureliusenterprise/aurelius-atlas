import { Provider } from "@angular/core";
import Keycloak from "keycloak-js";

/**
 * The Keycloak test double (APC-07's surface): a bare object, never the real
 * client. Specs used to hand-roll one of these seventeen times, each with a
 * different subset of the API — {@link fakeKeycloak} carries the whole subset
 * so one provider serves a role gate, a session read, and a sign-in probe.
 *
 * Only what a component actually calls matters; unstubbed members are absent,
 * so a component reaching for something new fails loudly instead of silently
 * reading `undefined`.
 */
export type FakeKeycloak = {
    authenticated: boolean;
    token: string | undefined;
    tokenParsed: Record<string, unknown>;
    hasResourceRole: (role: string, clientId?: string) => boolean;
    hasRealmRole: (role: string) => boolean;
    login: () => Promise<void>;
    logout: () => Promise<void>;
    updateToken: (minValidity: number) => Promise<boolean>;
};

/** What a spec may override; anything omitted keeps the default. */
export type FakeKeycloakOptions = Partial<Pick<FakeKeycloak, "authenticated" | "token" | "tokenParsed">> & {
    /** Grant `atlas-write` (the write affordances' gate, EDT-09, DD-324). */
    atlasWrite?: boolean;
    /** Realm roles the token holds (TEN-05's operator check). */
    realmRoles?: readonly string[];
    /** A token whose `resource_access` names the given client's roles. */
    resourceRoles?: Record<string, readonly string[]>;
    /** A pre-parsed token to use verbatim instead of the generated one. */
    parsed?: Record<string, unknown>;
};

/**
 * Build the double. With `atlasWrite` the `hasResourceRole` answer follows it;
 * with `resourceRoles` the answer follows the token's own claims, so a spec
 * testing the gate itself (can-write-entities) exercises the real path.
 *
 * @param options what to grant or stub
 * @returns the double, cast to `Keycloak` for the provider
 */
export function fakeKeycloak(options: FakeKeycloakOptions = {}): FakeKeycloak {
    const { atlasWrite = true, realmRoles = [], resourceRoles, parsed } = options;

    const rolesByClient: Record<string, readonly string[]> = resourceRoles ?? {
        "aurelius-atlas-server": atlasWrite ? ["atlas-write"] : [],
    };

    const tokenParsed: Record<string, unknown> = parsed ?? {
        realm_access: { roles: [...realmRoles] },
        resource_access: Object.fromEntries(
            Object.entries(rolesByClient).map(([client, roles]) => [client, { roles: [...roles] }]),
        ),
    };

    return {
        authenticated: options.authenticated ?? true,
        token: options.token ?? "test-token",
        tokenParsed,
        hasResourceRole: (role, clientId) => (rolesByClient[clientId ?? ""] ?? []).includes(role),
        hasRealmRole: (role) => realmRoles.includes(role),
        login: () => Promise.resolve(),
        logout: () => Promise.resolve(),
        updateToken: () => Promise.resolve(true),
    };
}

/**
 * The provider pair a screen test needs: the double, and the write gate's
 * client id (the same default `config.ts` gives, DD-300). Pair it with
 * {@link fakeAppConfig} — the gate reads the client id from the config.
 *
 * @param options what to grant or stub
 * @returns providers for `TestBed.configureTestingModule`
 */
export function provideFakeKeycloak(options: FakeKeycloakOptions = {}): Provider {
    return { provide: Keycloak, useValue: fakeKeycloak(options) };
}
