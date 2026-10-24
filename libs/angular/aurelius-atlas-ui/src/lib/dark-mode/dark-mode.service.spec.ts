import { TestBed } from "@angular/core/testing";

import { DarkModeService } from "./dark-mode.service";

describe("DarkModeService", () => {
    let service: DarkModeService;

    const root = () => document.documentElement;

    /** Flush the service's effects (attribute + storage writes). */
    const settle = () => TestBed.flushEffects();

    beforeEach(() => {
        localStorage.clear();
        root().removeAttribute("data-theme");
        service = TestBed.inject(DarkModeService);
        settle();
    });

    afterEach(() => {
        localStorage.clear();
        root().removeAttribute("data-theme");
    });

    it("starts in auto with nothing stored (SPL-05)", () => {
        expect(service.mode()).toBeNull();
        // Auto renders light by default (the app's script/service default,
        // SHM-01's promise) — the service itself writes no attribute.
        expect(root().hasAttribute("data-theme")).toBe(false);
    });

    it("reads the root attribute as the explicit choice (SPL-04)", () => {
        root().setAttribute("data-theme", "dark");

        const injected = TestBed.runInInjectionContext(() => new DarkModeService());
        expect(injected.mode()).toBe("dark");
    });

    it("the attribute wins over storage, and storage fills a missing attribute (SPL-04)", () => {
        root().setAttribute("data-theme", "light");
        localStorage.setItem("data-theme", "dark");
        expect(TestBed.runInInjectionContext(() => new DarkModeService()).mode()).toBe("light");

        root().removeAttribute("data-theme");
        expect(TestBed.runInInjectionContext(() => new DarkModeService()).mode()).toBe("dark");
    });

    it("setMode writes data-theme for light and dark (SPL-03)", () => {
        service.setMode("dark");
        settle();
        expect(root().getAttribute("data-theme")).toBe("dark");

        service.setMode("light");
        settle();
        expect(root().getAttribute("data-theme")).toBe("light");
    });

    it("setMode(null) REMOVES the attribute — Auto is no attribute, not an empty one (SPL-03, DD-159)", () => {
        service.setMode("dark");
        settle();
        service.setMode(null);
        settle();

        expect(root().hasAttribute("data-theme")).toBe(false);
    });

    it("persists the choice to the data-theme key and removes it on auto (SPL-04)", () => {
        service.setMode("dark");
        settle();
        expect(localStorage.getItem("data-theme")).toBe("dark");

        service.setMode("light");
        settle();
        expect(localStorage.getItem("data-theme")).toBe("light");

        service.setMode(null);
        settle();
        expect(localStorage.getItem("data-theme")).toBeNull();
    });

    it("next() cycles auto to dark to light to auto", () => {
        expect(service.mode()).toBeNull();

        service.next();
        expect(service.mode()).toBe("dark");
        service.next();
        expect(service.mode()).toBe("light");
        service.next();
        expect(service.mode()).toBeNull();
    });
});
