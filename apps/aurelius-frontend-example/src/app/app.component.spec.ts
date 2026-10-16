/**
 * Unit tests for the {@link App} root component: header, router outlet, dark
 * mode toggle, authentication-dependent UI (log-in button, user menu), and the
 * language switcher dropdown. `AuthService` and `LocaleService` are stubbed.
 */
import { signal, WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { provideRouter, Routes } from "@angular/router";
import { KeycloakProfile } from "keycloak-js";

import { App } from "./app.component";
import { AuthService } from "./services/auth.service";
import { DEFAULT_LOCALE, LOCALES, LocaleCode, LocaleService } from "./services/locale.service";

describe("App", () => {
    let fixture: ComponentFixture<App>;
    let component: App;
    let authenticated: WritableSignal<boolean>;
    let profile: WritableSignal<KeycloakProfile | null>;
    let authService: {
        authenticated: WritableSignal<boolean>;
        profile: WritableSignal<KeycloakProfile | null>;
        login: ReturnType<typeof vi.fn>;
        logout: ReturnType<typeof vi.fn>;
        accountManagement: ReturnType<typeof vi.fn>;
    };
    let localeService: {
        locales: typeof LOCALES;
        activeLocale: LocaleCode;
        localeHref: ReturnType<typeof vi.fn>;
    };

    beforeEach(async () => {
        authenticated = signal(false);
        profile = signal(null);
        authService = {
            authenticated,
            profile,
            login: vi.fn(),
            logout: vi.fn(),
            accountManagement: vi.fn(),
        };
        localeService = {
            locales: LOCALES,
            activeLocale: DEFAULT_LOCALE,
            localeHref: vi.fn((code: string) => `http://localhost/${code}/`),
        };

        await TestBed.configureTestingModule({
            imports: [App],
            providers: [
                provideRouter([] as Routes),
                { provide: AuthService, useValue: authService },
                { provide: LocaleService, useValue: localeService },
            ],
        }).compileComponents();

        fixture = TestBed.createComponent(App);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("should create", () => {
        expect(component).toBeTruthy();
    });

    it("should render the header with the application name", () => {
        const header = fixture.debugElement.query(By.css("aurelius-ui-header"));

        expect(header).toBeTruthy();
        expect(header.attributes["name"]).toBe("Aurelius Frontend Example");
        expect(header.attributes["logo"]).toBe("favicon.ico");
    });

    it("should render the router outlet", () => {
        expect(fixture.debugElement.query(By.css("router-outlet"))).toBeTruthy();
    });

    it("should render the dark mode toggle", () => {
        expect(fixture.debugElement.query(By.css("aurelius-ui-dark-mode"))).toBeTruthy();
    });

    it("should show the log in button when unauthenticated", () => {
        const buttons = [...fixture.nativeElement.querySelectorAll("button")] as HTMLButtonElement[];
        const login = buttons.find((b) => b.textContent?.includes("Log in"));

        expect(login).toBeTruthy();
        login?.click();
        expect(authService.login).toHaveBeenCalled();
    });

    it("should hide the user menu when there is no profile", () => {
        const links = [...fixture.nativeElement.querySelectorAll("a.navbar-link")] as HTMLElement[];

        expect(links.some((l) => l.textContent?.includes("Logged in as"))).toBe(false);
    });

    it("should show the user menu with the username when authenticated", () => {
        profile.set({ username: "testuser" });
        fixture.detectChanges();

        const links = [...fixture.nativeElement.querySelectorAll("a.navbar-link")] as HTMLElement[];
        expect(links.some((l) => l.textContent?.includes("Logged in as testuser"))).toBe(true);
    });

    it("should fall back to email when the profile has no username", () => {
        profile.set({ email: "test@example.com" });
        fixture.detectChanges();

        const links = [...fixture.nativeElement.querySelectorAll("a.navbar-link")] as HTMLElement[];
        expect(links.some((l) => l.textContent?.includes("Logged in as test@example.com"))).toBe(true);
    });

    it("should call accountManagement and logout from the user menu", () => {
        profile.set({ username: "testuser" });
        fixture.detectChanges();

        const buttons = [...fixture.nativeElement.querySelectorAll("button.navbar-item")] as HTMLButtonElement[];
        const account = buttons.find((b) => b.textContent?.includes("Account Management"));
        const logout = buttons.find((b) => b.textContent?.includes("Log out"));

        expect(account).toBeTruthy();
        account?.click();
        expect(authService.accountManagement).toHaveBeenCalled();

        expect(logout).toBeTruthy();
        logout?.click();
        expect(authService.logout).toHaveBeenCalled();
    });

    it("should render a language link per locale with the active one marked", () => {
        const items = [...fixture.nativeElement.querySelectorAll("a.navbar-item")] as HTMLAnchorElement[];
        const languageLinks = items.filter((a) =>
            (Object.values(LOCALES) as string[]).includes(a.textContent?.trim() ?? ""),
        );

        expect(languageLinks.map((a) => a.textContent?.trim())).toEqual(["English", "Nederlands"]);

        const active = languageLinks.find((a) => a.getAttribute("aria-current") === "true");
        expect(active?.textContent?.trim()).toBe("English");
        expect(localeService.localeHref).toHaveBeenCalledWith("en-US");
        expect(localeService.localeHref).toHaveBeenCalledWith("nl-NL");
    });

    it("should hide the log in button once authenticated", () => {
        authenticated.set(true);
        fixture.detectChanges();

        const buttons = [...fixture.nativeElement.querySelectorAll("button")] as HTMLButtonElement[];
        expect(buttons.some((b) => b.textContent?.includes("Log in"))).toBe(false);
    });
});
