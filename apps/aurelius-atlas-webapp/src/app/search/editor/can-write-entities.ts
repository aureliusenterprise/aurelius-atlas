import { Signal, inject, signal } from "@angular/core";
import Keycloak from "keycloak-js";

import { DEFAULT_ATLAS_CLIENT_ID } from "../../config";
import { APP_CONFIG } from "../../tokens";

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
 * Call inside an injection context (a field initializer).
 *
 * @returns a signal holding whether the token holds `atlas-write`
 */
export function canWriteEntities(): Signal<boolean> {
    const keycloak = inject(Keycloak);
    const atlasClientId = inject(APP_CONFIG).atlasClientId ?? DEFAULT_ATLAS_CLIENT_ID;

    return signal(keycloak.hasResourceRole("atlas-write", atlasClientId)).asReadonly();
}
