import { TestBed } from "@angular/core/testing";
import { provideRouter, Routes } from "@angular/router";
import { KeycloakService } from "keycloak-angular";

import { AppConfig } from "./config";
import { APP_CONFIG } from "./tokens";
import { App } from "./app.component";

const config: AppConfig = {
    keycloak: { clientId: "aurelius", realm: "atlas", url: "https://keycloak.example/" },
    apiBaseUrl: "/api",
    otelExporterUrl: "/otel/v1/traces",
    appName: "Aurelius Atlas Data Governance",
    appCopyright: 2022,
    appVersion: "7.11.0#abc1234",
};

describe("App", () => {
    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [App],
            providers: [
                provideRouter([] as Routes),
                { provide: APP_CONFIG, useValue: config },
                // The header's session identity reads the Keycloak token; the
                // root spec keeps the chrome's plumbing out of scope.
                { provide: KeycloakService, useValue: { getKeycloakInstance: () => ({ tokenParsed: {} }) } },
            ],
        }).compileComponents();
    });

    it("creates", () => {
        expect(TestBed.createComponent(App).componentInstance).toBeTruthy();
    });

    it("renders the shell chrome around the router outlet (SHC-01)", () => {
        const fixture = TestBed.createComponent(App);
        fixture.detectChanges();

        const compiled = fixture.nativeElement as HTMLElement;

        // The Aurelius root wraps its outlet in the shell chrome: header
        // above, footer below (SHL-03's bare-outlet reading is superseded
        // here — the legacy root renders <models4insight-shell>).
        expect([...compiled.children].map((child) => child.tagName.toLowerCase())).toEqual([
            "aurelius-atlas-webapp-header",
            "router-outlet",
            "aurelius-atlas-webapp-footer",
        ]);
    });
});
