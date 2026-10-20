import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { Card } from "./card.component";

@Component({
    imports: [Card],
    template: `
        <aurelius-atlas-ui-card>
            <img card-image src="lineage.svg" alt="Lineage" />
            <p card-content>Entity content</p>
            <a card-footer href="#">Open</a>
        </aurelius-atlas-ui-card>
    `,
    // The card's own component has no template-checkable state; the host
    // exercises the content projection (UIC-01).
})
class Host {}

describe("Card", () => {
    let fixture: ComponentFixture<Host>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [Host],
        }).compileComponents();

        fixture = TestBed.createComponent(Host);
        fixture.detectChanges();
    });

    it("projects image, content and footer into the Bulma card anatomy (UIC-01)", () => {
        const card: HTMLElement = fixture.nativeElement.querySelector("aurelius-atlas-ui-card > .card");

        expect(card).toBeTruthy();
        expect(card.querySelector(".card-image img")).toBeTruthy();
        expect(card.querySelector(".card-content p")?.textContent).toContain("Entity content");
        expect(card.querySelector(".card-footer a")?.textContent).toContain("Open");
    });
});
