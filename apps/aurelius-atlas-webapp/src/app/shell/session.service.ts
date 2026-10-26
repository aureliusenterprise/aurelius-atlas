import { Injectable, inject, signal } from "@angular/core";
import Keycloak from "keycloak-js";

/**
 * The signed-in session's display identity (SHC-05, SHC-08).
 *
 * The Aurelius header read a `credentials$` from `libs/authentication`; the
 * port reads the Keycloak token directly — injected as the `Keycloak` client
 * instance `provideKeycloak` registers (keycloak-angular's own services
 * inject the same token; its `KeycloakService` is the deprecated v18-era
 * class, which `provideKeycloak` does not provide). The guard (APC-05) has
 * resolved before any component renders, so the parsed token is present when
 * this service is first injected. `preferred_username`, falling back to
 * `e-mail`, is what the legacy header showed.
 */
@Injectable({ providedIn: "root" })
export class Session {
    private readonly keycloak = inject(Keycloak);

    private readonly identityState = signal(Session.readIdentity(this.keycloak));

    private readonly emailState = signal(Session.readEmail(this.keycloak));

    /** The identity to greet the user by, `""` when no session is readable. */
    readonly identity = this.identityState.asReadonly();

    /**
     * The signed-in user's e-mail (SRH-08, the governance card's
     * `directToUser`): the token's `email`, the legacy
     * `credentials.email` the Aurelius service read.
     */
    readonly email = this.emailState.asReadonly();

    private static readIdentity(keycloak: Keycloak): string {
        const token = keycloak.tokenParsed;

        return token?.["preferred_username"] ?? token?.["email"] ?? "";
    }

    private static readEmail(keycloak: Keycloak): string {
        return keycloak.tokenParsed?.["email"] ?? "";
    }
}
