import { ComponentFixture, TestBed } from "@angular/core/testing";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { afterEach, describe, expect, it } from "vitest";
import { DarkMode } from "./dark-mode.component";
import { DarkModeService } from "./dark-mode.service";

describe("DarkMode", () => {
    let component: DarkMode;
    let fixture: ComponentFixture<DarkMode>;
    let service: DarkModeService;

    const button = () => fixture.nativeElement.querySelector("button") as HTMLButtonElement;
    const renderedIcon = () => fixture.nativeElement.querySelector("svg")?.getAttribute("data-icon") as string | null;

    beforeEach(async () => {
        // The service is root-scoped and persists its mode in the root
        // attribute + localStorage: start every test from a clean auto mode.
        localStorage.removeItem("data-theme");
        document.documentElement.removeAttribute("data-theme");

        await TestBed.configureTestingModule({
            imports: [DarkMode, FontAwesomeModule],
        }).compileComponents();

        fixture = TestBed.createComponent(DarkMode);
        component = fixture.componentInstance;
        service = TestBed.inject(DarkModeService);
        service.setMode(null);
        fixture.detectChanges();
        await fixture.whenStable();
    });

    afterEach(() => {
        localStorage.removeItem("data-theme");
        document.documentElement.removeAttribute("data-theme");
    });

    it("should create", () => {
        expect(component).toBeTruthy();
    });

    it("names the current theme in the button title (SPL-03)", () => {
        expect(button().title).toBe("The current theme is auto");

        service.setMode("dark");
        fixture.detectChanges();
        expect(button().title).toBe("The current theme is dark");

        service.setMode("light");
        fixture.detectChanges();
        expect(button().title).toBe("The current theme is light");
    });

    it("cycles auto -> dark -> light -> auto on click (SPL-03)", async () => {
        expect(service.mode()).toBeNull();

        button().click();
        await fixture.whenStable();
        expect(service.mode()).toBe("dark");

        button().click();
        await fixture.whenStable();
        expect(service.mode()).toBe("light");

        button().click();
        await fixture.whenStable();
        expect(service.mode()).toBeNull();
    });

    it("follows the mode with its icon (SPL-03)", async () => {
        fixture.detectChanges();
        expect(renderedIcon()).toBe("circle-half-stroke");

        service.setMode("light");
        fixture.detectChanges();
        await fixture.whenStable();
        expect(renderedIcon()).toBe("circle");

        service.setMode(null);
        fixture.detectChanges();
        await fixture.whenStable();
        expect(renderedIcon()).toBe("circle-half-stroke");
    });

    it("persists the clicked mode for the next visit (SPL-04)", async () => {
        button().click();
        await fixture.whenStable();
        fixture.detectChanges();

        expect(localStorage.getItem("data-theme")).toBe("dark");
        expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    });
});
