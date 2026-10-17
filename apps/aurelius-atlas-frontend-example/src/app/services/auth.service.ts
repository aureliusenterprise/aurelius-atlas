import { computed, effect, inject, Injectable, signal } from "@angular/core";
import { KEYCLOAK_EVENT_SIGNAL, KeycloakEventType, ReadyArgs, typeEventArgs } from "keycloak-angular";
import Keycloak, { KeycloakProfile } from "keycloak-js";

@Injectable({
    providedIn: "root",
})
export class AuthService {
    /**
     * A signal that indicates whether the user is authenticated.
     */
    readonly authenticated = signal<boolean>(false);

    /**
     * A signal that returns the Keycloak profile if the user is authenticated.
     */
    readonly profile = computed(() => this.profileFor(this.authenticated()));

    /**
     * The Keycloak instance used for authentication.
     */
    private readonly keycloak = inject(Keycloak);

    /**
     * A signal that listens to Keycloak events.
     */
    private readonly keycloakEvents = inject(KEYCLOAK_EVENT_SIGNAL);

    /**
     * Initializes the AuthService and sets up an effect to handle Keycloak events.
     */
    constructor() {
        effect(() => {
            const keycloakEvent = this.keycloakEvents();

            if (keycloakEvent.type === KeycloakEventType.Ready) {
                this.authenticated.set(typeEventArgs<ReadyArgs>(keycloakEvent.args));
            }

            if (keycloakEvent.type === KeycloakEventType.AuthLogout) {
                this.authenticated.set(false);
            }
        });
    }

    /**
     * Open the account management page.
     */
    accountManagement(): Promise<void> {
        return this.keycloak.accountManagement();
    }

    /**
     * Log in the user.
     */
    login(): Promise<void> {
        return this.keycloak.login({ redirectUri: globalThis.location.origin });
    }

    /**
     * Log out the user.
     */
    logout(): Promise<void> {
        return this.keycloak.logout({ redirectUri: globalThis.location.origin });
    }

    /**
     * Returns the user profile for authenticated users, derived from the ID-token claims.
     *
     * Deliberately NOT {@link Keycloak.loadUserProfile}: that calls the Account REST API,
     * which requires the {@code account} audience. The {@code aurelius} client runs with
     * {@code fullScopeAllowed: false} (least privilege), so its tokens never carry that
     * audience and the call would fail with an opaque CORS error.
     */
    private profileFor(authenticated: boolean): KeycloakProfile | null {
        if (!authenticated) {
            return null;
        }

        const claims = this.keycloak.idTokenParsed;

        if (!claims) {
            return null;
        }

        return {
            id: claims.sub,
            username: claims["preferred_username"],
            email: claims["email"],
            firstName: claims["given_name"],
            lastName: claims["family_name"],
        };
    }
}
