import { Signal, inject, signal } from "@angular/core";
import Keycloak from "keycloak-js";

import { DEFAULT_ATLAS_CLIENT_ID } from "../../config";
import { type Tenancy, TENANCY, type TenantClaims, tenantGroups, tenantOf } from "../../tenancy";
import { APP_CONFIG } from "../../tokens";

/** The tenant's group that grants writing entities (TEN-05). */
const WRITE_GROUP = "/atlas-write";

/**
 * Whether the signed-in token may write entities (EDT-09).
 *
 * The legacy app gated the editor affordances with a `DATA_STEWARD`
 * `*appHasRole` directive over a realm role the Aurelius deployment granted;
 * this product's realm has no such role (DD-324). The gate reads the claim
 * the server itself enforces instead: `atlas-write` in the
 * `resource_access.<atlasClientId>.roles` of the browser's token — the four
 * Atlas client roles of the server's Keycloak client (DD-300, AUZ-01/02),
 * with `atlasClientId` from the runtime config (`config.ts`, paired with the
 * server's `auth_client_id`). The roles are read once, when the helper is
 * first injected: the route guard has resolved the sign-in by then, and the
 * token's roles do not change within the session (EDT-09's "at page load").
 *
 * The gate covers the affordances only. The routes are not guarded (EDT-09):
 * a deep link opens the drawer and the server's 403 answers through its
 * failure path (EDT-08) — the server is the real gate.
 *
 * With tenancy on, the server reads the roles from the tenant's own groups, and
 * holds an operator at read access outside the operator organization (TEN-05,
 * TEN-06), so the gate reads them so too, and the client roles count for nothing
 * (TNW-07, DD-636).
 *
 * Call inside an injection context (a field initializer).
 *
 * @returns a signal holding whether the token holds `atlas-write`
 */
export function canWriteEntities(): Signal<boolean> {
    const keycloak = inject(Keycloak);
    const tenancy = inject(TENANCY);
    if (tenancy.enabled) {
        return signal(writesInTenant(tenancy, keycloak.tokenParsed)).asReadonly();
    }
    const atlasClientId = inject(APP_CONFIG).atlasClientId ?? DEFAULT_ATLAS_CLIENT_ID;

    return signal(keycloak.hasResourceRole("atlas-write", atlasClientId)).asReadonly();
}

/**
 * Whether a token may write in its tenant (TNW-07): the tenant's groups hold
 * `/atlas-write`, and an operator writes only in the operator organization.
 *
 * @param tenancy the server's tenancy, on
 * @param token the parsed token
 * @returns whether the write controls show
 */
export function writesInTenant(tenancy: Tenancy, token: TenantClaims | undefined): boolean {
    const tenant = tenantOf(token);
    if (tenant === undefined || !tenantGroups(token, tenant).includes(WRITE_GROUP)) {
        return false;
    }
    const operator =
        tenancy.operatorRole !== undefined && (token?.realm_access?.roles ?? []).includes(tenancy.operatorRole);

    return !operator || tenant === tenancy.operatorOrganization;
}
