import { Component } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { provideRouter, Router, type Routes } from "@angular/router";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import Keycloak from "keycloak-js";

import { AppConfig } from "../config";
import { AlertsService } from "../alerts/alerts.service";
import { APP_CONFIG } from "../tokens";
import { ShellHeader } from "./header.component";
import { Session } from "./session.service";

const config: AppConfig = {
    keycloak: { clientId: "aurelius", realm: "atlas", url: "https://keycloak.example/" },
    apiBaseUrl: "/api",
    otelExporterUrl: "/otel/v1/traces",
    appName: "Aurelius Atlas Data Governance",
    appCopyright: 2022,
    appVersion: "7.11.0#abc1234",
};

const DOC_HREF = "https://aureliusenterprise.github.io/aurelius-atlas-documentation/";

// The drawer route's placeholder (SPL-14's shape): the router rejects a
// componentless named-outlet route, and the header's template has no
// drawer outlet, so this component is never rendered.
@Component({ selector: "aurelius-atlas-webapp-lib-drawer-panel", template: "" })
class DrawerPanelPlaceholder {}

function setup(identity = "aurelius-writer", routes: Routes = []) {
    const logout = vi.fn();

    // jsdom ships no matchMedia (the reduced-motion probe, ALR-02a).
    window.matchMedia = vi.fn().mockReturnValue({ matches: false });

    TestBed.configureTestingModule({
        imports: [FontAwesomeModule, ShellHeader],
        providers: [
            provideRouter(routes),
            { provide: APP_CONFIG, useValue: config },
            { provide: Keycloak, useValue: { logout } },
            { provide: Session, useValue: { identity: () => identity } },
        ],
    });

    return { logout };
}

/** The rendered header, with change detection run. */
function render() {
    const fixture = TestBed.createComponent(ShellHeader);
    fixture.detectChanges();

    return fixture.nativeElement as HTMLElement;
}

const normalize = (text: string | undefined | null) => text?.replace(/\s+/g, " ").trim();

describe("ShellHeader", () => {
    beforeEach(() => {
        setup();
    });

    it("creates", () => {
        expect(TestBed.createComponent(ShellHeader).componentInstance).toBeTruthy();
    });

    it("brands the navbar with the Aurelius logo (SHM-02)", () => {
        // The brand is the legacy navbar logo (DD-148): the Aurelius Atlas
        // mark, linking home, sized by the ui-lib's .logo rule. The app
        // name remains the accessible alt (SHC-02, superseded here).
        const brand = render().querySelector<HTMLAnchorElement>(".navbar-brand a.navbar-item");
        const img = brand?.querySelector("img");

        expect(brand?.getAttribute("routerLink")).toBe("/");
        expect(img?.getAttribute("src")).toBe("assets/aurelius-atlas-logo.png");
        expect(img?.getAttribute("alt")).toBe(config.appName);
        expect(img?.getAttribute("class")).toBe("logo");
    });

    it("carries the Documentation link with the Aurelius docs target (SHC-03)", () => {
        const link = render().querySelector<HTMLAnchorElement>('a[target="_blank"]');

        expect(link?.getAttribute("rel")).toBe("noopener noreferrer");
        expect(link?.getAttribute("href")).toBe(DOC_HREF);
        // The i18n bridge key renders its English leaf (SHC-07).
        expect(normalize(link?.textContent)).toBe("Documentation");
    });

    it("opens the settings panel from the gear (SPL-01, SPL-14, DD-166)", () => {
        // The gear replaces the language dropdown in navbar-end and opens
        // the panel by navigating the `drawer` aux outlet — the panel is a
        // routed component, no longer the header's child (SPL-14).
        const compiled = render();
        const gear = compiled.querySelector<HTMLAnchorElement>('a.navbar-item[aria-label="Settings"]');

        expect(gear).toBeTruthy();
        // RouterLink serialises the aux-outlet target into the href.
        expect(gear?.getAttribute("href")).toBe("/(drawer:settings)");
        expect(compiled.querySelector("aurelius-atlas-webapp-settings-panel")).toBeNull();
        // On the plain URL the gear is not lit.
        expect(gear?.classList.contains("is-active")).toBe(false);
    });

    it("lights the gear while the drawer route is open (SPL-01, DD-167)", async () => {
        // RouterLinkActive keys `is-active` off the drawer segment: with
        // the settings outlet in the URL, the gear carries Bulma's
        // active-navbar-item styling. The drawer route is the app's real
        // shape; the header's template has no drawer outlet, so the
        // component is never rendered. Navigating after the fixture
        // exists is what the directive listens for (NavigationEnd).
        setup("aurelius-writer", [{ path: "settings", outlet: "drawer", component: DrawerPanelPlaceholder }]);
        const fixture = TestBed.createComponent(ShellHeader);
        fixture.detectChanges();
        await TestBed.inject(Router).navigate([{ outlets: { drawer: ["settings"] } }]);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;
        const gear = compiled.querySelector<HTMLAnchorElement>('a.navbar-item[aria-label="Settings"]');

        expect(gear?.getAttribute("routerlinkactive")).toBe("is-active");
        expect(gear?.classList.contains("is-active")).toBe(true);
    });

    it("no longer carries the language dropdown (SPL-01, SPL-06)", () => {
        // The language control moved into the panel; the navbar-end set is
        // Documentation, the gear, the bell, and the account dropdown.
        const compiled = render();

        expect(compiled.querySelector("[hreflang]")).toBeNull();
        expect(normalize(compiled.textContent)).not.toContain("Your language is");
    });

    it("opens the alerts drawer from the bell (ALR-01)", () => {
        // The bell is the gear's pattern for the second drawer (ALR-01):
        // a routerLink into the one `drawer` outlet, lit while open.
        const compiled = render();
        const bell = compiled.querySelector<HTMLAnchorElement>('a.navbar-item[aria-label="Alerts"]');

        expect(bell).toBeTruthy();
        expect(bell?.getAttribute("href")).toBe("/(drawer:alerts)");
        expect(bell?.classList.contains("is-active")).toBe(false);
    });

    it("lights the bell while the alerts route is open (ALR-01)", async () => {
        setup("aurelius-writer", [{ path: "alerts", outlet: "drawer", component: DrawerPanelPlaceholder }]);
        const fixture = TestBed.createComponent(ShellHeader);
        fixture.detectChanges();
        await TestBed.inject(Router).navigate([{ outlets: { drawer: ["alerts"] } }]);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;
        const bell = compiled.querySelector<HTMLAnchorElement>('a.navbar-item[aria-label="Alerts"]');

        expect(bell?.classList.contains("is-active")).toBe(true);
    });

    it("carries the unread severity badge (ALR-02, ALR-12)", () => {
        setup();
        const fixture = TestBed.createComponent(ShellHeader);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;
        const alerts = TestBed.inject(AlertsService);

        // Presence, not a count: no dot on an empty store.
        expect(compiled.querySelector(".aurelius-badge-dot")).toBeNull();

        alerts.add({ severity: "warning", message: "slow", source: "app" });
        fixture.detectChanges();

        expect(compiled.querySelector(".aurelius-badge-dot")?.classList.contains("is-warning")).toBe(true);

        // The dot answers what has not been seen (ALR-12): opening the
        // drawer reads the feed, the dot goes with it.
        alerts.markAllRead();
        fixture.detectChanges();
        expect(compiled.querySelector(".aurelius-badge-dot")).toBeNull();

        // The colour rides the highest UNREAD severity, not the store's
        // top: a read error no longer out-colours a new warning.
        alerts.add({ severity: "error", message: "boom", source: "app" });
        alerts.markAllRead();
        alerts.add({ severity: "warning", message: "slow again", source: "app" });
        fixture.detectChanges();

        expect(compiled.querySelector(".aurelius-badge-dot")?.classList.contains("is-warning")).toBe(true);
    });

    it("rings the bell on a new alert group, once per burst (ALR-02a)", () => {
        setup();
        const fixture = TestBed.createComponent(ShellHeader);
        fixture.detectChanges();
        const alerts = TestBed.inject(AlertsService);
        const icon = (fixture.nativeElement as HTMLElement).querySelector(".aurelius-bell-icon") as HTMLElement;
        const animate = vi.fn();
        icon.animate = animate;

        alerts.add({ severity: "error", message: "boom", source: "app" });
        TestBed.flushEffects();
        expect(animate).toHaveBeenCalledTimes(1);

        // A merge into the burst (ALR-03) is not a new group: no second ring.
        alerts.add({ severity: "error", message: "boom", source: "app" });
        TestBed.flushEffects();
        expect(animate).toHaveBeenCalledTimes(1);
    });

    it("skips the ring under reduced motion (ALR-02a)", () => {
        setup();
        vi.spyOn(window, "matchMedia").mockReturnValue({ matches: true } as MediaQueryList);
        const fixture = TestBed.createComponent(ShellHeader);
        fixture.detectChanges();
        const icon = (fixture.nativeElement as HTMLElement).querySelector(".aurelius-bell-icon") as HTMLElement;
        const animate = vi.fn();
        icon.animate = animate;

        TestBed.inject(AlertsService).add({ severity: "error", message: "boom", source: "app" });
        TestBed.flushEffects();

        expect(animate).not.toHaveBeenCalled();
    });

    it("greets the signed-in identity in the account dropdown (SHC-05)", () => {
        // The account dropdown is the last navbar-link: language comes first.
        const links = [...render().querySelectorAll<HTMLElement>("a.navbar-link")];
        const welcome = normalize(links.at(-1)?.textContent);

        // "Logged in as" is the shell.header.welcome bridge leaf (SHC-07).
        expect(welcome).toBe("Logged in as aurelius-writer");
    });

    it("links Account-security to the Keycloak account console (SHC-05)", () => {
        const security = [...render().querySelectorAll<HTMLAnchorElement>("a.navbar-item")].find((item) =>
            item.getAttribute("href")?.includes("/account"),
        );

        expect(security?.getAttribute("href")).toBe("https://keycloak.example/realms/atlas/account");
        // The shell.header.security bridge leaf (SHC-07).
        expect(normalize(security?.textContent)).toBe("Account security");
    });

    it("ends the Keycloak session on Logout (SHC-05)", () => {
        const { logout } = setup();
        const compiled = render();
        // The legacy Logout is `a role="button" .navbar-item` (DD-153).
        const anchor = [...compiled.querySelectorAll<HTMLAnchorElement>("a.navbar-item")].find((item) =>
            item.textContent?.includes("Logout"),
        );

        expect(anchor?.getAttribute("role")).toBe("button");

        anchor?.click();

        expect(logout).toHaveBeenCalledOnce();
    });

    it("ends the session fire-and-forget even when logout rejects (SHC-05)", async () => {
        // logout() is `void keycloak.logout()`: the navigation starts
        // immediately, so the component attaches no catch and awaits
        // nothing — a rejection is not the click's problem. In a browser the
        // rejection lands on the global error path (window's
        // unhandledrejection → the app's AureliusTraceErrorHandler, which
        // records it). The click's contract: called once, throws never. The
        // mock consumes its own rejection (catch attached at construction)
        // so the runner does not report the component's deliberate
        // fire-and-forget as an unhandled rejection.
        setup();
        const keycloak = TestBed.inject(Keycloak) as unknown as { logout: ReturnType<typeof vi.fn> };
        keycloak.logout.mockImplementation(() => {
            const rejection = Promise.reject(new Error("Keycloak service unreachable"));
            rejection.catch(() => undefined);
            return rejection;
        });

        const compiled = render();
        const anchor = [...compiled.querySelectorAll<HTMLAnchorElement>("a.navbar-item")].find((item) =>
            item.textContent?.includes("Logout"),
        );

        expect(() => anchor?.click()).not.toThrow();
        expect(keycloak.logout).toHaveBeenCalledOnce();
        await new Promise((resolve) => setTimeout(resolve, 10));
    });
});
