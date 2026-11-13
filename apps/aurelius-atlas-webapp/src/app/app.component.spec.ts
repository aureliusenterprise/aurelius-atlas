import { TestBed } from "@angular/core/testing";
import { provideRouter, Routes } from "@angular/router";
import Keycloak from "keycloak-js";

import { AlertsService } from "./alerts/alerts.service";
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
                { provide: Keycloak, useValue: { tokenParsed: {} } },
            ],
        }).compileComponents();
    });

    it("creates", () => {
        expect(TestBed.createComponent(App).componentInstance).toBeTruthy();
    });

    it("LR-003: the announcer names the newest alert, and says nothing without one", () => {
        const fixture = TestBed.createComponent(App);
        const app = fixture.componentInstance;
        const alerts = TestBed.inject(AlertsService);

        // The empty store: the persistent region rests silent.
        expect(app["alertAnnouncement"]()).toBe("");

        // An arrival enters the store once per new group (ALR-03 merges do
        // not re-announce): the line carries its severity and message.
        alerts.add({ severity: "error", message: "Search failed", source: "search" });
        expect(app["alertAnnouncement"]()).toBe("New error alert - Search failed");

        // A different alert becomes the newest; the line follows it.
        alerts.add({ severity: "warning", message: "Slow response", source: "http" });
        expect(app["alertAnnouncement"]()).toBe("New warning alert - Slow response");
    });

    it("renders the shell chrome around the router outlet (SHC-01)", () => {
        const fixture = TestBed.createComponent(App);
        fixture.detectChanges();

        const compiled = fixture.nativeElement as HTMLElement;

        // The Aurelius root wraps its outlet in the shell chrome: the skip
        // link first (LANDMARK-002), header above, the sticky loading bar
        // (SRH-09), footer below (SHL-03's bare-outlet reading is superseded
        // here — the legacy root renders <models4insight-shell>). The outlet
        // band is the main landmark (LANDMARK-001) wearing the legacy
        // .is-tall-container (flex + 100vh), so the footer begins below the
        // fold (SHM-05, SHM-07, DD-150). The named `drawer` outlet (SPL-14,
        // DD-166) is the root's last child.
        expect([...compiled.children].map((child) => child.tagName.toLowerCase())).toEqual([
            "a",
            "aurelius-atlas-webapp-header",
            "aurelius-atlas-webapp-nav-loading-bar",
            "main",
            "aurelius-atlas-webapp-footer",
            "output",
            "router-outlet",
        ]);

        const band = compiled.querySelector(":scope > main");

        expect(band?.className).toBe("is-tall-container has-background");
        expect(band?.getAttribute("id")).toBe("main");
        expect(band?.querySelector("router-outlet")).toBeTruthy();
        expect(compiled.querySelector(":scope > router-outlet")?.getAttribute("name")).toBe("drawer");
        // The skip link targets the landmark (LANDMARK-002).
        expect(compiled.querySelector("a.skip-link")?.getAttribute("href")).toBe("#main");
    });
});
