/**
 * The settings panel (SPL-03, SPL-06..SPL-14): the routed drawer the
 * header gear opens, carrying the five sections and About. The rules under
 * test are the panel's own — the sections render, the Appearance select
 * drives the theme through the facade, the language section computes locale
 * hrefs, the selects write their owners, About shows the build (SPL-12's
 * app==server version, DD-077), dismissal navigates the outlet away
 * (SPL-14, DD-078). The owners' storage behaviour is specced at the owner
 * (their specs above); the panel only drives the facade.
 */
import { TestBed } from "@angular/core/testing";
import { provideHttpClient } from "@angular/common/http";
import { Router, provideRouter } from "@angular/router";
import { AdminService, AtlasSession } from "aurelius-atlas-data-access";
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

function setup() {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    // The served document declares its locale (SPL-06); jsdom's default is empty.
    document.documentElement.lang = "en-US";
    TestBed.configureTestingModule({
        imports: [SettingsPanel],
        providers: [
            provideHttpClient(),
            provideRouter([]),
            { provide: APP_CONFIG, useValue: config },
            { provide: AdminService, useValue: { getSession: () => of(session) } },
        ],
    });
}

/** The rendered, open panel: the routed component opens at construction (SPL-14). */
async function renderOpen() {
    const fixture = TestBed.createComponent(SettingsPanel);
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

describe("SettingsPanel (SPL-03, SPL-06..SPL-14)", () => {
    beforeEach(setup);

    afterEach(() => {
        localStorage.clear();
        document.documentElement.removeAttribute("data-theme");
    });

    it("renders open: the routed panel exists only while open (SPL-14, DD-078)", async () => {
        const { fixture, compiled } = await renderOpen();

        expect(compiled.querySelector(".aurelius-drawer")).toBeTruthy();
        expect(fixture.componentInstance.active()).toBe(true);
    });

    it("renders the drawer with its five sections and About (SPL-02, SPL-13)", async () => {
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

    it("dismissal flips the drawer and navigates the outlet away (SPL-14, DD-078)", async () => {
        const { fixture, compiled } = await renderOpen();
        const router = TestBed.inject(Router);
        const navigate = vi.spyOn(router, "navigate").mockResolvedValue(true);

        compiled.querySelector<HTMLButtonElement>(".aurelius-drawer-head .delete")?.click();
        fixture.detectChanges();

        expect(fixture.componentInstance.active()).toBe(false);
        // The dismissal clears the `drawer` outlet segment (DD-078).
        expect(navigate).toHaveBeenCalledWith([{ outlets: { drawer: null } }]);
    });

    it("the Appearance select drives the theme through the owner (SPL-03, SPL-10, DD-076)", async () => {
        const { fixture, compiled } = await renderOpen();
        const select = compiled.querySelectorAll<HTMLSelectElement>(".select select")[0];

        // The ui-lib Select, no search button (searchVisible off); the
        // rows are the modes, Auto first and selected by default (SPL-03).
        // The placeholder's &nbsp; normalizes like the ui-lib spec's.
        expect(compiled.querySelector("aurelius-atlas-ui-select button.button")).toBeNull();
        expect([...select.options].map((o) => (o.textContent?.trim() ?? "").replace(/\u00a0/g, " "))).toEqual([
            "-- Please select a value --",
            "Auto",
            "Light",
            "Dark",
        ]);
        expect(select.options[select.selectedIndex].textContent?.trim()).toBe("Auto");

        pickOption(compiled, 0, "Dark");
        fixture.detectChanges();
        await fixture.whenStable();

        expect(TestBed.inject(SettingsService).theme()).toBe("dark");
        expect(document.documentElement.getAttribute("data-theme")).toBe("dark");

        pickOption(compiled, 0, "Auto"); // Auto — the attribute goes, not empties (SPL-03)
        fixture.detectChanges();
        await fixture.whenStable();

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
        // Index 1: the Appearance select (DD-076) comes first.
        const select = compiled.querySelectorAll<HTMLSelectElement>(".select select")[1];

        expect([...select.options].map((o) => o.textContent?.trim())).toEqual([
            "Browser default",
            "UTC",
            "Europe/Amsterdam",
            "Asia/Tokyo",
        ]);

        pickOption(compiled, 1, "Europe/Amsterdam");
        fixture.detectChanges();

        expect(TestBed.inject(SettingsService).timezone()).toBe("Europe/Amsterdam");
    });

    it("the page-size select writes the owner (SPL-08)", async () => {
        const { fixture, compiled } = await renderOpen();
        const select = compiled.querySelectorAll<HTMLSelectElement>(".select select")[2];

        expect([...select.options].map((o) => o.textContent?.trim())).toEqual(["5", "10", "20", "50"]);

        pickOption(compiled, 2, "20");
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

    it("About shows the build's one version (SPL-12, DD-077)", async () => {
        const { compiled } = await renderOpen();
        const about = [...compiled.querySelectorAll<HTMLElement>(".settings-section")].at(-1);
        const text = about?.textContent?.replace(/\s+/g, " ").trim();

        expect(text).toContain(config.appName);
        expect(text).toContain(config.appVersion);
        // One release, one number: app and server share it (DD-077) — the
        // server is not fetched and not listed.
        expect(text).not.toContain("Server");
    });

    it("the panel survives a session that never answers (SPL-07)", async () => {
        TestBed.resetTestingModule();
        localStorage.clear();
        TestBed.configureTestingModule({
            imports: [SettingsPanel],
            providers: [
                provideHttpClient(),
                provideRouter([]),
                { provide: APP_CONFIG, useValue: config },
                { provide: AdminService, useValue: { getSession: () => throwError(() => new Error("no session")) } },
            ],
        });

        const fixture = TestBed.createComponent(SettingsPanel);
        expect(() => fixture.detectChanges()).not.toThrow();

        // The zone list stays empty; the select keeps its Browser default.
        const compiled = fixture.nativeElement as HTMLElement;
        const select = compiled.querySelectorAll<HTMLSelectElement>(".select select")[1];
        expect([...select.options].map((o) => o.textContent?.trim())).toEqual(["Browser default"]);
    });
});
