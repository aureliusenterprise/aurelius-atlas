import { TestBed } from "@angular/core/testing";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";

import { AppConfig } from "../config";
import { APP_CONFIG } from "../tokens";
import { ShellFooter } from "./footer.component";

const config: AppConfig = {
    keycloak: { clientId: "aurelius", realm: "atlas", url: "https://keycloak.example/" },
    apiBaseUrl: "/api",
    otelExporterUrl: "/otel/v1/traces",
    appName: "Aurelius Atlas Data Governance",
    appCopyright: 2022,
    appVersion: "7.11.0#abc1234",
};

describe("ShellFooter", () => {
    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [FontAwesomeModule, ShellFooter],
            providers: [{ provide: APP_CONFIG, useValue: config }],
        }).compileComponents();
    });

    it("creates", () => {
        expect(TestBed.createComponent(ShellFooter).componentInstance).toBeTruthy();
    });

    it("renders the Aurelius footer anatomy from the runtime config (SHC-06)", () => {
        const fixture = TestBed.createComponent(ShellFooter);
        fixture.detectChanges();

        const compiled = fixture.nativeElement as HTMLElement;
        const normalize = (text: string | undefined | null) => text?.replace(/\s+/g, " ").trim();

        // The footer is Bulma `level`: copyright left, app name centre, version right.
        const left = compiled.querySelector(".level-left")?.textContent;
        expect(normalize(left)).toBe("Copyright 2022");
        // "Copyright" is the shell.footer.copyright bridge leaf (SHC-07).
        expect(compiled.querySelector(".level-left svg")).toBeTruthy(); // faCopyright icon

        expect(normalize(compiled.querySelector(".level > .level-item")?.textContent)).toBe(config.appName);
        expect(normalize(compiled.querySelector(".level-right")?.textContent)).toBe(config.appVersion);
    });
});
