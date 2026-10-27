import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { Header } from "./header.component";

describe("Header", () => {
    let component: Header;
    let fixture: ComponentFixture<Header>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [Header],
        }).compileComponents();

        fixture = TestBed.createComponent(Header);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("should create", () => {
        expect(component).toBeTruthy();
    });

    it("renders the brand as a logo image when one is given", () => {
        fixture.componentRef.setInput("logo", "assets/aurelius-atlas-logo.png");
        fixture.componentRef.setInput("name", "Aurelius Atlas Data Governance");
        fixture.detectChanges();

        const link = fixture.nativeElement.querySelector(".navbar-brand a.navbar-item");
        const img = link?.querySelector("img");

        expect(link.getAttribute("routerLink")).toBe("/");
        expect(img.getAttribute("src")).toBe("assets/aurelius-atlas-logo.png");
        expect(img.getAttribute("alt")).toBe("Aurelius Atlas Data Governance");
    });

    it("puts the logo css class on the brand image (SHM-02)", () => {
        // The Aurelius chrome sizes the mark through the `.logo` rule; the
        // ui-lib applies it by default and forwards a custom class.
        fixture.componentRef.setInput("logo", "assets/aurelius-atlas-logo.png");
        fixture.detectChanges();

        const img = fixture.nativeElement.querySelector(".navbar-brand img");

        expect(img.getAttribute("class")).toBe("logo");
    });

    it("forwards a custom logo css class (SHM-02)", () => {
        fixture.componentRef.setInput("logo", "assets/aurelius-atlas-logo.png");
        fixture.componentRef.setInput("logoCssClass", "my-logo");
        fixture.detectChanges();

        const img = fixture.nativeElement.querySelector(".navbar-brand img");

        expect(img.getAttribute("class")).toBe("my-logo");
    });

    it("pins the navbar when fixed (SHM-05)", () => {
        fixture.componentRef.setInput("fixed", true);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("nav.navbar").classList.contains("is-fixed-top")).toBe(true);
    });

    it("wraps the navbar content in a container (SHM-05)", () => {
        // The legacy navbar anatomy: `navbar > container > navbar-brand`,
        // so the chrome aligns with the page's container below.
        fixture.detectChanges();

        const container = fixture.nativeElement.querySelector("nav.navbar > div.container");

        expect(container).toBeTruthy();
        expect(container.querySelector(".navbar-brand")).toBeTruthy();
        expect(container.querySelector("nav.navbar-menu")).toBeTruthy();
    });
});

describe("Header with projected content (mobile burger)", () => {
    // The burger only renders when the navbar has content (DD-223): the
    // webapp e2e's mobile-logout flow rides this toggle; the computed-style
    // pins of DD-153 left e2e and the behaviour is guarded here.
    @Component({
        imports: [Header],
        template: `
            <aurelius-atlas-ui-header>
                <a navbar-start class="navbar-item">Start</a>
                <a navbar-end class="navbar-item">Logout</a>
            </aurelius-atlas-ui-header>
        `,
    })
    class HostComponent {}

    let hostFixture: ComponentFixture<HostComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();

        hostFixture = TestBed.createComponent(HostComponent);
        hostFixture.detectChanges();
    });

    function burger(): HTMLButtonElement {
        return hostFixture.nativeElement.querySelector("button.navbar-burger");
    }

    function menu(): HTMLElement {
        return hostFixture.nativeElement.querySelector("nav.navbar-menu");
    }

    it("renders the burger when the navbar has content", () => {
        expect(burger()).toBeTruthy();
        expect(burger().getAttribute("aria-expanded")).toBe("false");
    });

    it("opens the menu on burger click, closes on the second (SHM-04, DD-153, DD-223)", () => {
        burger().click();
        hostFixture.detectChanges();

        expect(burger().getAttribute("aria-expanded")).toBe("true");
        expect(burger().classList.contains("is-active")).toBe(true);
        expect(menu().classList.contains("is-active")).toBe(true);
        const items = [...menu().querySelectorAll("a.navbar-item")].map((item) => item.textContent?.trim());

        expect(items).toEqual(["Start", "Logout"]);

        burger().click();
        hostFixture.detectChanges();

        expect(burger().getAttribute("aria-expanded")).toBe("false");
        expect(menu().classList.contains("is-active")).toBe(false);
    });

    it("the expanded model drives the burger state", () => {
        const header = hostFixture.debugElement.query(By.directive(Header)).componentInstance as Header;

        header.expanded.set(true);
        hostFixture.detectChanges();

        expect(burger().getAttribute("aria-expanded")).toBe("true");
        expect(menu().classList.contains("is-active")).toBe(true);
    });
});
