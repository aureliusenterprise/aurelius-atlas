import { TestBed } from "@angular/core/testing";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { AdminService } from "aurelius-atlas-data-access";
import { NEVER } from "rxjs";
import Keycloak from "keycloak-js";

import { AppConfig } from "../config";
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

function setup(identity = "aurelius-writer") {
    const logout = vi.fn();

    TestBed.configureTestingModule({
        imports: [FontAwesomeModule, ShellHeader],
        providers: [
            { provide: APP_CONFIG, useValue: config },
            { provide: Keycloak, useValue: { logout } },
            { provide: Session, useValue: { identity: () => identity } },
            // The settings panel the header carries loads timezones/version
            // lazily on open — no open happens in these tests, the stub stays silent.
            { provide: AdminService, useValue: { getSession: () => NEVER, getVersion: () => NEVER } },
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
        // The brand is the legacy navbar logo (DD-059): the Aurelius Atlas
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

    it("opens the settings panel from the gear (SPL-01)", () => {
        // The gear replaces the language dropdown in navbar-end; the panel
        // is the header's own element, closed until the gear opens it.
        const fixture = TestBed.createComponent(ShellHeader);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;
        const gear = compiled.querySelector<HTMLButtonElement>('button.navbar-item[aria-label="Settings"]');
        const panel = compiled.querySelector("aurelius-atlas-webapp-settings-panel");

        expect(gear).toBeTruthy();
        expect(panel).toBeTruthy();
        expect(compiled.querySelector(".aurelius-drawer")).toBeNull();

        gear?.click();
        fixture.detectChanges();

        expect(compiled.querySelector(".aurelius-drawer")).toBeTruthy();
    });

    it("no longer carries the language dropdown (SPL-01, SPL-06)", () => {
        // The language control moved into the panel; the navbar-end set is
        // Documentation, the gear, and the account dropdown.
        const compiled = render();

        expect(compiled.querySelector("[hreflang]")).toBeNull();
        expect(normalize(compiled.textContent)).not.toContain("Your language is");
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
        // The legacy Logout is `a role="button" .navbar-item` (DD-064).
        const anchor = [...compiled.querySelectorAll<HTMLAnchorElement>("a.navbar-item")].find((item) =>
            item.textContent?.includes("Logout"),
        );

        expect(anchor?.getAttribute("role")).toBe("button");

        anchor?.click();

        expect(logout).toHaveBeenCalledOnce();
    });
});
