import { signal } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";

import { AppConfig } from "../config";
import { APP_CONFIG } from "../tokens";
import { VersionService } from "./version.service";
import { ShellFooter } from "./footer.component";

const config: AppConfig = {
    keycloak: { clientId: "aurelius", realm: "atlas", url: "https://keycloak.example/" },
    apiBaseUrl: "/api",
    otelExporterUrl: "/otel/v1/traces",
    appName: "Aurelius Atlas Data Governance",
};

function setup(version: string) {
    TestBed.configureTestingModule({
        imports: [FontAwesomeModule, ShellFooter],
        providers: [
            { provide: APP_CONFIG, useValue: config },
            // The version is the server's answer, stubbed here so the footer's
            // print is what this spec pins (VER-01's read is its service's spec).
            { provide: VersionService, useValue: { version: signal(version) } },
        ],
    });
}

describe("ShellFooter", () => {
    beforeEach(() => {
        setup("7.11.0#abc1234");
    });

    it("creates", () => {
        expect(TestBed.createComponent(ShellFooter).componentInstance).toBeTruthy();
    });

    it("renders the Aurelius footer anatomy (SHC-06)", () => {
        const fixture = TestBed.createComponent(ShellFooter);
        fixture.detectChanges();

        const compiled = fixture.nativeElement as HTMLElement;
        const normalize = (text: string | undefined | null) => text?.replace(/\s+/g, " ").trim();

        // The footer is Bulma `level`: copyright left, app name centre, version right.
        // The year is the browser's own (VER-04, DD-726), never a configured value.
        expect(normalize(compiled.querySelector(".level-left")?.textContent)).toBe(
            `Copyright ${new Date().getFullYear()}`,
        );
        // "Copyright" is the shell.footer.copyright bridge leaf (SHC-07).
        expect(compiled.querySelector(".level-left svg")).toBeTruthy(); // faCopyright icon

        expect(normalize(compiled.querySelector(".level > .level-item")?.textContent)).toBe(config.appName);
        expect(normalize(compiled.querySelector(".level-right")?.textContent)).toBe("7.11.0#abc1234");
    });

    it("VER-03: an unanswered version leaves the footer's right side blank", () => {
        TestBed.resetTestingModule();
        setup("");
        const fixture = TestBed.createComponent(ShellFooter);
        fixture.detectChanges();

        const compiled = fixture.nativeElement as HTMLElement;

        expect(compiled.querySelector(".level-right")?.textContent?.trim()).toBe("");
        // The name and the year still print.
        expect(compiled.querySelector(".level > .level-item")?.textContent?.trim()).toBe(config.appName);
    });
});
