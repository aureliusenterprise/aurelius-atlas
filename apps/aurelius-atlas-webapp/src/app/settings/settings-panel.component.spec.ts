/**
 * The settings panel (SPL-03, SPL-06..SPL-12): the drawer the header gear
 * opens, carrying the five sections and About. The rules under test are
 * the panel's own — the sections render, the radio drives the theme
 * through the facade, the language section computes locale hrefs, the
 * selects write their owners, About shows the config and server version.
 * The owners' storage behaviour is specced at the owner (their specs
 * above); the panel only drives the facade.
 */
import { TestBed } from "@angular/core/testing";
import { provideHttpClient } from "@angular/common/http";
import { AdminService, AtlasSession, AtlasVersion } from "aurelius-atlas-data-access";
import { of, throwError } from "rxjs";

import { AppConfig } from "../config";
import { APP_CONFIG } from "../tokens";
import { SettingsPanel } from "./settings-panel.component";
import { SettingsService } from "./settings.service";

const config: AppConfig = {
    keycloak: { clientId: "aurelius", realm: "atlas", url: "https://keycloak.example/" },
    apiBaseUrl: "/api",
    otelExporterUrl: "/otel/v1/traces",
    appName: "Aurelius Atlas Data Governance",
    appCopyright: 2022,
    appVersion: "7.14.0#abc1234",
};

const session = {
    userName: null,
    groups: [],
    timezones: ["UTC", "Europe/Amsterdam", "Asia/Tokyo"],
    _csrfToken: "",
} as AtlasSession;

const version: AtlasVersion = {
    Name: "aurelius-atlas",
    Version: "4.2.0",
    Revision: "r-deadbeef",
    Description: "Aurelius Atlas",
};

function setup() {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    // The served document declares its locale (SPL-06); jsdom's default is empty.
    document.documentElement.lang = "en-US";
    TestBed.configureTestingModule({
        imports: [SettingsPanel],
        providers: [
            provideHttpClient(),
            { provide: APP_CONFIG, useValue: config },
            {
                provide: AdminService,
                useValue: { getSession: () => of(session), getVersion: () => of(version) },
            },
        ],
    });
}

/** The rendered, open panel: open + change detection + NgModel settle, DOM returned. */
async function renderOpen() {
    const fixture = TestBed.createComponent(SettingsPanel);
    fixture.detectChanges();
    fixture.componentInstance.open();
    fixture.detectChanges();
    // NgModel writes its model value into the control on a resolved
    // promise (the ExpressionChangedAfterItHasBeenChecked guard), so the
    // checkbox/selects need one microtask flush before they are readable.
    await fixture.whenStable();

    return { fixture, compiled: fixture.nativeElement as HTMLElement };
}

/** Pick an option (by its text) in a panel select and fire the change. */
function pickOption(compiled: HTMLElement, selectIndex: number, optionText: string): void {
    const select = compiled.querySelectorAll<HTMLSelectElement>(".select select")[selectIndex];
    const option = [...select.options].find((o) => o.textContent?.trim() === optionText);
    if (!option) throw new Error(`no option "${optionText}" in select ${selectIndex}`);

    select.value = option.value;
    select.dispatchEvent(new Event("change"));
}

describe("SettingsPanel (SPL-03, SPL-06..SPL-12)", () => {
    beforeEach(setup);

    afterEach(() => {
        localStorage.clear();
        document.documentElement.removeAttribute("data-theme");
    });

    it("is closed until the gear opens it (SPL-01)", async () => {
        const fixture = TestBed.createComponent(SettingsPanel);
        fixture.detectChanges();

        expect((fixture.nativeElement as HTMLElement).querySelector(".aurelius-drawer")).toBeNull();
    });

    it("open() renders the drawer with its five sections and About (SPL-02, SPL-13)", async () => {
        const { compiled } = await renderOpen();
        const text = compiled.textContent ?? "";

        expect(compiled.querySelector(".aurelius-drawer")).toBeTruthy();
        expect(compiled.querySelector(".aurelius-drawer-title")?.textContent).toBe("Settings");
        for (const label of [
            "Appearance",
            "Language",
            "Time zone",
            "Default table page size",
            "Usage telemetry",
            "About",
        ]) {
            expect(text).toContain(label);
        }
    });

    it("the Appearance radio drives the theme through the owner (SPL-03, SPL-10)", async () => {
        const { fixture, compiled } = await renderOpen();
        const radios = [...compiled.querySelectorAll<HTMLInputElement>('input[type="radio"][name="settings-theme"]')];

        expect(radios.map((r) => r.checked)).toEqual([true, false, false]); // Auto first (SPL-03)

        radios[2].click(); // Dark
        fixture.detectChanges();

        expect(TestBed.inject(SettingsService).theme()).toBe("dark");
        expect(document.documentElement.getAttribute("data-theme")).toBe("dark");

        radios[0].click(); // Auto — the attribute goes, not empties (SPL-03)
        fixture.detectChanges();

        expect(TestBed.inject(SettingsService).theme()).toBeNull();
        expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
    });

    it("the language section carries SHC-04's locale links (SPL-06)", async () => {
        const { compiled } = await renderOpen();
        const links = [...compiled.querySelectorAll<HTMLAnchorElement>("[hreflang]")];

        expect(links.map((l) => l.getAttribute("hreflang"))).toEqual(["en-US", "nl-NL"]);
        expect(links.map((l) => l.getAttribute("href"))).toEqual(["/en-US/", "/nl-NL/"]);
        // The active locale is marked from the document's lang (SPL-06).
        expect(links[0].getAttribute("aria-current")).toBe("true");
        expect(links[1].getAttribute("aria-current")).toBeNull();
    });

    it("the time zone select offers Browser default and the server's zones (SPL-07)", async () => {
        const { fixture, compiled } = await renderOpen();
        const select = compiled.querySelectorAll<HTMLSelectElement>(".select select")[0];

        expect([...select.options].map((o) => o.textContent?.trim())).toEqual([
            "Browser default",
            "UTC",
            "Europe/Amsterdam",
            "Asia/Tokyo",
        ]);

        pickOption(compiled, 0, "Europe/Amsterdam");
        fixture.detectChanges();

        expect(TestBed.inject(SettingsService).timezone()).toBe("Europe/Amsterdam");
    });

    it("the page-size select writes the owner (SPL-08)", async () => {
        const { fixture, compiled } = await renderOpen();
        const select = compiled.querySelectorAll<HTMLSelectElement>(".select select")[1];

        expect([...select.options].map((o) => o.textContent?.trim())).toEqual(["5", "10", "20", "50"]);

        pickOption(compiled, 1, "20");
        fixture.detectChanges();

        expect(TestBed.inject(SettingsService).pageSize()).toBe(20);
    });

    it("the telemetry toggle writes the owner; the hint states the reload (SPL-11)", async () => {
        const { fixture, compiled } = await renderOpen();
        const box = compiled.querySelector<HTMLInputElement>('input[type="checkbox"]');

        expect(box?.checked).toBe(true);
        expect(compiled.textContent).toContain("takes effect after a reload");

        box?.click();
        fixture.detectChanges();

        expect(TestBed.inject(SettingsService).telemetry()).toBe(false);
    });

    it("About shows the app and the server version (SPL-12)", async () => {
        const { compiled } = await renderOpen();
        const about = [...compiled.querySelectorAll<HTMLElement>(".settings-section")].at(-1);
        const text = about?.textContent?.replace(/\s+/g, " ").trim();

        expect(text).toContain(config.appName);
        expect(text).toContain(config.appVersion);
        // ADM-01/DV-03: the server's name is "aurelius-atlas".
        expect(text).toContain("aurelius-atlas 4.2.0");
    });

    it("About degrades quietly when the server never answers (SPL-12)", async () => {
        TestBed.resetTestingModule();
        localStorage.clear();
        TestBed.configureTestingModule({
            imports: [SettingsPanel],
            providers: [
                provideHttpClient(),
                { provide: APP_CONFIG, useValue: config },
                {
                    provide: AdminService,
                    useValue: {
                        getSession: () => throwError(() => new Error("no session")),
                        getVersion: () => throwError(() => new Error("no version")),
                    },
                },
            ],
        });

        const fixture = TestBed.createComponent(SettingsPanel);
        fixture.detectChanges();
        expect(() => fixture.componentInstance.open()).not.toThrow();
        fixture.detectChanges();

        const text = (fixture.nativeElement as HTMLElement).textContent ?? "";
        expect(text).toContain("Server version unavailable");
    });
});
