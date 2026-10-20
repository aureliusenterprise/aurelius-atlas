import { Injectable, inject, signal } from "@angular/core";
import { KeycloakService } from "keycloak-angular";

/**
 * The signed-in session's display identity (SHC-05, SHC-08).
 *
 * The Aurelius header read a `credentials$` from `libs/authentication`; the
 * port reads the Keycloak token directly — the guard (APC-05) has resolved
 * before any component renders, so the parsed token is present when this
 * service is first injected. `preferred_username`, falling back to `e-mail`,
 * is what the legacy header showed.
 */
@Injectable({ providedIn: "root" })
export class Session {
    private readonly keycloak = inject(KeycloakService);

    private readonly identityState = signal(Session.readIdentity(this.keycloak));

    /** The identity to greet the user by, `""` when no session is readable. */
    readonly identity = this.identityState.asReadonly();

    private static readIdentity(keycloak: KeycloakService): string {
        const token = keycloak.getKeycloakInstance().tokenParsed;

        return token?.["preferred_username"] ?? token?.["email"] ?? "";
    }
}
