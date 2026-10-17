import { signal, WritableSignal } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { KEYCLOAK_EVENT_SIGNAL, KeycloakEvent, KeycloakEventType, provideKeycloak } from "keycloak-angular";
import Keycloak from "keycloak-js";
import { AuthService } from "./auth.service";

describe("AuthService", () => {
    let eventsSignal: WritableSignal<KeycloakEvent>;
    let keycloak: Keycloak;
    let service: AuthService;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [
                AuthService,
                provideKeycloak({
                    config: {
                        url: "keycloak-server-url",
                        realm: "realm-id",
                        clientId: "client-id",
                    },
                }),
                {
                    provide: KEYCLOAK_EVENT_SIGNAL,
                    useValue: signal<KeycloakEvent>({ type: KeycloakEventType.Ready, args: false }),
                },
            ],
        });
        eventsSignal = TestBed.inject(KEYCLOAK_EVENT_SIGNAL) as WritableSignal<KeycloakEvent>;
        keycloak = TestBed.inject(Keycloak);
        service = TestBed.inject(AuthService);
    });

    it("should initialize with unauthenticated state", () => {
        expect(service.authenticated()).toBe(false);
        expect(service.profile()).toBeNull();
    });

    it("should call accountManagement", async () => {
        const accountManagement = vi.spyOn(keycloak, "accountManagement").mockResolvedValueOnce();
        await service.accountManagement();

        expect(accountManagement).toHaveBeenCalled();
    });

    it("should call login", async () => {
        const login = vi.spyOn(keycloak, "login").mockResolvedValueOnce();
        await service.login();

        expect(login).toHaveBeenCalledWith({ redirectUri: globalThis.location.origin });
    });

    it("should call logout", async () => {
        const logout = vi.spyOn(keycloak, "logout").mockResolvedValueOnce();
        await service.logout();

        expect(logout).toHaveBeenCalledWith({ redirectUri: globalThis.location.origin });
    });

    // The service reacts via an Angular effect; flush it deterministically instead of
    // racing a setTimeout(50) against the 100 ms test timeout, which flaked on loaded runners.
    it("should derive the user profile from the ID token when authenticated", () => {
        keycloak.idTokenParsed = { sub: "id-1", preferred_username: "testuser" };
        eventsSignal.set({ type: KeycloakEventType.Ready, args: true });

        TestBed.flushEffects();

        expect(service.profile()).toEqual({
            id: "id-1",
            username: "testuser",
            email: undefined,
            firstName: undefined,
            lastName: undefined,
        });
    });

    it("should return a null profile when authenticated without an ID token", () => {
        eventsSignal.set({ type: KeycloakEventType.Ready, args: true });

        TestBed.flushEffects();

        expect(service.profile()).toBeNull();
    });

    it("should return null profile when not authenticated", async () => {
        expect(service.authenticated()).toBe(false);
        expect(service.profile()).toBeNull();
    });
});
