/**
 * The settings facade (SPL-10, DD-160): one injectable over one owner per
 * category. The rule under test is the delegation — each setter reaches
 * its owner, each signal reflects the owner's state — and the read-only
 * surface: the panel writes through the setters, never the signals.
 */
import { TestBed } from "@angular/core/testing";
import { DarkModeService } from "aurelius-atlas-ui";

import { PageSizeService } from "./page-size.service";
import { SettingsService } from "./settings.service";
import { TelemetryService } from "./telemetry.service";
import { TimezoneService } from "./timezone.service";

describe("SettingsService facade (SPL-10)", () => {
    beforeEach(() => {
        localStorage.clear();
        document.documentElement.removeAttribute("data-theme");
    });

    afterEach(() => {
        localStorage.clear();
        document.documentElement.removeAttribute("data-theme");
    });

    const facade = () => TestBed.inject(SettingsService);

    it("exposes the four stored categories with their defaults (SPL-10)", () => {
        const settings = facade();

        expect(settings.theme()).toBeNull();
        expect(settings.timezone()).toBeNull();
        expect(settings.pageSize()).toBe(10);
        expect(settings.telemetry()).toBe(true);
        expect(settings.locale.locales).toEqual(["en-US", "nl-NL"]);
    });

    it("setTheme drives DarkModeService — the theme's owner (SPL-10, SPL-03)", () => {
        const settings = facade();
        const darkMode = TestBed.inject(DarkModeService);
        TestBed.flushEffects();

        settings.setTheme("dark");
        TestBed.flushEffects();

        expect(settings.theme()).toBe("dark");
        expect(darkMode.mode()).toBe("dark");
        expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    });

    it("setTimezone drives TimezoneService (SPL-10, SPL-07)", () => {
        const settings = facade();

        settings.setTimezone("Europe/Amsterdam");

        expect(settings.timezone()).toBe("Europe/Amsterdam");
        expect(TestBed.inject(TimezoneService).timezone()).toBe("Europe/Amsterdam");
    });

    it("setPageSize drives PageSizeService (SPL-10, SPL-08)", () => {
        const settings = facade();

        settings.setPageSize(20);

        expect(settings.pageSize()).toBe(20);
        expect(TestBed.inject(PageSizeService).pageSize()).toBe(20);
    });

    it("setTelemetry drives TelemetryService (SPL-10, SPL-11)", () => {
        const settings = facade();
        const telemetry = TestBed.inject(TelemetryService);

        settings.setTelemetry(false);

        expect(settings.telemetry()).toBe(false);
        expect(telemetry.enabled()).toBe(false);
    });

    it("is a facade: it stores nothing of its own (SPL-10, DD-160)", () => {
        const settings = facade();
        settings.setTheme("light");
        TestBed.flushEffects(); // the theme owner's storage effect (SPL-04)
        settings.setTimezone("Asia/Tokyo");
        settings.setPageSize(50);
        settings.setTelemetry(false);

        // Every write landed in an owner's key — the facade adds none.
        expect(Object.keys(localStorage).sort()).toEqual([
            "aurelius-atlas.settings.pageSize",
            "aurelius-atlas.settings.telemetry",
            "aurelius-atlas.settings.timezone",
            "data-theme",
        ]);
    });
});
