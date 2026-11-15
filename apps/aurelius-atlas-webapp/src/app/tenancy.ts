import { InjectionToken } from "@angular/core";

import { readPreference, TENANT_KEY, writePreference } from "./settings/user-preference";

/**
 * Whether the server serves tenants, as it answers `GET /api/aurelius/v1/tenancy`
 * (TNW-01, DD-636): with tenancy on, the organization whose members run the
 * platform and the realm role that marks an operator.
 */
export interface Tenancy {
    readonly enabled: boolean;
    readonly operatorOrganization?: string;
    readonly operatorRole?: string;
}

/** Tenancy off: the webapp signs in and gates as before (TNW-03). */
export const NO_TENANCY: Tenancy = { enabled: false };

/** The server's answer, provided at bootstrap (TNW-02). */
export const TENANCY = new InjectionToken<Tenancy>("TENANCY", { providedIn: "root", factory: () => NO_TENANCY });

/** The scopes a sign-in asks for: the organization scope, which lets the person choose (TNW-04, DD-582). */
export const SIGN_IN_SCOPE = "openid organization";

/** The answer's path below the API base. */
export const TENANCY_PATH = "/aurelius/v1/tenancy";

/**
 * Validate the server's answer (TNW-02).
 *
 * @param value the parsed answer
 * @returns the tenancy it states
 * @throws If the answer is not the server's shape.
 */
export function parseTenancy(value: unknown): Tenancy {
    if (typeof value !== "object" || value === null || typeof (value as Tenancy).enabled !== "boolean") {
        throw new TypeError('Invalid tenancy answer: expected {"enabled": boolean}.');
    }
    const { enabled, operatorOrganization, operatorRole } = value as Tenancy;
    if (!enabled) {
        return NO_TENANCY;
    }
    if (typeof operatorOrganization !== "string" || typeof operatorRole !== "string") {
        throw new TypeError("Invalid tenancy answer: tenancy on names its operator organization and role.");
    }
    return { enabled, operatorOrganization, operatorRole };
}

/**
 * Read the server's tenancy before signing in (TNW-02): an answer that can't be
 * read fails the start, as a bad `/config.json` does (SHL-02).
 *
 * @param apiBaseUrl the API's base, `/api`
 * @returns the tenancy the server states
 */
export async function loadTenancy(apiBaseUrl: string): Promise<Tenancy> {
    const url = `${apiBaseUrl.replace(/\/$/, "")}${TENANCY_PATH}`;
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Failed to load the tenancy (${url}): ${response.status} ${response.statusText}`);
    }
    return parseTenancy(await response.json());
}

/** The parts of a parsed token the tenant is read from. */
export interface TenantClaims {
    readonly organization?: unknown;
    readonly realm_access?: { readonly roles?: readonly string[] };
}

/**
 * The one organization a token names, as the server reads it (TEN-02): the
 * strings of a list, or the keys of an object; none, or several, is no tenant.
 *
 * @param token the parsed token
 * @returns the tenant's alias, or `undefined`
 */
export function tenantOf(token: TenantClaims | undefined): string | undefined {
    const claim = token?.organization;
    const named = Array.isArray(claim)
        ? claim.filter((entry): entry is string => typeof entry === "string")
        : typeof claim === "object" && claim !== null
          ? Object.keys(claim)
          : [];
    return named.length === 1 ? named[0] : undefined;
}

/**
 * The tenant's own groups in the token (TEN-05): the `groups` under its alias in
 * the organization claim.
 *
 * @param token the parsed token
 * @param tenant the tenant's alias
 * @returns the group paths, `[]` when there are none
 */
export function tenantGroups(token: TenantClaims | undefined, tenant: string): readonly string[] {
    const claim = token?.organization;
    if (typeof claim !== "object" || claim === null || Array.isArray(claim)) {
        return [];
    }
    const groups = (claim as Record<string, { groups?: unknown }>)[tenant]?.groups;
    return Array.isArray(groups) ? groups.filter((group): group is string => typeof group === "string") : [];
}

/**
 * The tenant this browser signed in to last (TNW-05, DD-634).
 *
 * @returns the alias, or `undefined`
 */
export function rememberedTenant(): string | undefined {
    return readPreference<string | undefined>(TENANT_KEY, undefined, (value) => typeof value === "string");
}

/**
 * Remember the tenant this browser signed in to (TNW-05).
 *
 * @param tenant the alias
 */
export function rememberTenant(tenant: string): void {
    writePreference(TENANT_KEY, tenant);
}

/**
 * The scopes the silent check at start asks for (TNW-05, TNW-10, DD-634): the
 * remembered tenant's organization, which Keycloak answers without a choice for
 * a member and refuses otherwise; else the organization scope.
 *
 * @param tenancy the server's tenancy
 * @param remembered the remembered alias
 * @returns the scopes, `undefined` with tenancy off (TNW-03)
 */
export function silentScope(tenancy: Tenancy, remembered: string | undefined): string | undefined {
    if (!tenancy.enabled) {
        return undefined;
    }
    return remembered === undefined ? SIGN_IN_SCOPE : `openid organization:${remembered}`;
}
