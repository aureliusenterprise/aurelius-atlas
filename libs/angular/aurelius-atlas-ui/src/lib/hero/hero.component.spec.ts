import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { Hero } from "./hero.component";

@Component({
    imports: [Hero],
    template: `
        <aurelius-atlas-ui-hero title="Atlas" subtitle="Data catalogue">
            <button before-title type="button">Editor</button>
            <div after-title>search box</div>
            <li navigation><a>Technical context</a></li>
        </aurelius-atlas-ui-hero>
    `,
})
class Host {}

describe("Hero", () => {
    let fixture: ComponentFixture<Host>;

    function root(): HTMLElement {
        return fixture.nativeElement as HTMLElement;
    }

    beforeEach(async () => {
        await TestBed.configureTestingModule({ imports: [Host, Hero] }).compileComponents();
        fixture = TestBed.createComponent(Host);
        fixture.detectChanges();
    });

    it("renders the Bulma hero anatomy (UIC-01)", () => {
        expect(root().querySelector("section.hero.is-primary.is-bold")).toBeTruthy();
        expect(root().querySelector(".hero-body .container")).toBeTruthy();
        expect(root().querySelector(".hero-foot nav.tabs.is-boxed")).toBeTruthy();
    });

    it("renders title and subtitle (UIC-01)", () => {
        expect(root().querySelector("h1.title")?.textContent?.trim()).toBe("Atlas");
        expect(root().querySelector("h2.subtitle")?.textContent?.trim()).toBe("Data catalogue");
    });

    it("omits the heading elements when unset (UIC-01)", () => {
        const bare = TestBed.createComponent(Hero);
        bare.detectChanges();

        expect(bare.nativeElement.querySelector("h1")).toBeNull();
        expect(bare.nativeElement.querySelector("h2")).toBeNull();
    });

    it("projects the action, after-title, and navigation slots (UIC-01)", () => {
        expect(root().querySelector(".buttons button[before-title]")).toBeTruthy();
        expect(root().querySelector(".column div[after-title]")).toBeTruthy();
        expect(root().querySelector(".tabs ul li a")?.textContent?.trim()).toBe("Technical context");
    });

    it("stretches to full height on request (UIC-01)", () => {
        const stretched = TestBed.createComponent(Hero);
        stretched.componentRef.setInput("fullHeight", true);
        stretched.detectChanges();

        expect(stretched.nativeElement.querySelector("section").classList.contains("is-fullheight-with-navbar")).toBe(
            true,
        );
    });
});
