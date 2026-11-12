import { ChangeDetectionStrategy, Component } from "@angular/core";
import { TestBed } from "@angular/core/testing";

import { GovQualityCards } from "./gov-quality-cards.component";
import type { GovQualityRow } from "./gov-quality.state";

/**
 * The Governance Quality Rules cards (DET-42, DD-521): one card per row —
 * the rule's name as the title link, the badge of its type — and the body
 * with the description line, the verdict icon (success / warning / none),
 * and the titlecased dimension. A title click emits the rule's guid.
 * These specs mount the part through a host, the card-content spec's
 * idiom; the in-screen wiring rides `details.component.spec.ts`.
 */

/** A minimal host: the part under test with one rows input. */
@Component({
    template: `<aurelius-atlas-webapp-gov-quality-cards [rows]="rows" (ruleClicked)="lastRule = $event" />`,
    imports: [GovQualityCards],
    changeDetection: ChangeDetectionStrategy.OnPush,
})
class Host {
    rows: readonly GovQualityRow[] = [];
    lastRule: string | null = null;
}

/** Collapse the markup's whitespace. */
const normalize = (text: string | undefined | null) => text?.replace(/\s+/g, " ").trim();

/** One row of each verdict shape. */
const COMPLIANT: GovQualityRow = {
    guid: "r1",
    name: "Person has a name",
    description: "A name is stored.",
    dimension: "COMPLETENESS",
    compliant: true,
};
const BROKEN: GovQualityRow = {
    guid: "r2",
    name: "Person has an email address",
    description: "",
    dimension: "accuracy",
    compliant: false,
};
const UNVERDICTED: GovQualityRow = {
    guid: "r3",
    name: "Person has a role",
    description: "",
    dimension: "",
    compliant: null,
};

function mount(rows: readonly GovQualityRow[]): {
    fixture: ReturnType<typeof TestBed.createComponent<Host>>;
    host: Host;
} {
    const fixture = TestBed.createComponent(Host);
    fixture.componentInstance.rows = rows;
    fixture.detectChanges();
    return { fixture, host: fixture.componentInstance };
}

describe("Gov-quality cards (DET-42)", () => {
    it("renders one card per row with the rule name as its title (DET-42)", () => {
        const { fixture } = mount([COMPLIANT, BROKEN, UNVERDICTED]);
        const cards = fixture.nativeElement.querySelectorAll("aurelius-atlas-ui-entity-card");
        expect(cards).toHaveLength(3);
        const titles = [...fixture.nativeElement.querySelectorAll(".title.is-4 a")].map((link: Element) =>
            normalize(link.textContent),
        );
        expect(titles).toEqual(["Person has a name", "Person has an email address", "Person has a role"]);
        // The badge names the rule type (DET-26's resolver, applied to it).
        expect(
            normalize(cards[0].querySelector(".aurelius-type-name, aurelius-atlas-ui-type-name")?.textContent),
        ).toContain("Gov. Quality");
    });

    it("shows the description line only when the rule stores one (DET-42)", () => {
        const { fixture } = mount([COMPLIANT, BROKEN]);
        const bodies = [...fixture.nativeElement.querySelectorAll(".aurelius-gov-quality-description")];
        expect(bodies).toHaveLength(1);
        expect(normalize(bodies[0].textContent)).toBe("A name is stored.");
    });

    it("marks a compliant rule with the success icon (DET-42)", () => {
        const { fixture } = mount([COMPLIANT]);
        const icon = fixture.nativeElement.querySelector(".aurelius-gov-quality-verdict .icon");
        expect(icon.classList.contains("has-text-success")).toBe(true);
    });

    it("marks a non-compliant rule with the warning icon (DET-42)", () => {
        const { fixture } = mount([BROKEN]);
        const icon = fixture.nativeElement.querySelector(".aurelius-gov-quality-verdict .icon");
        expect(icon.classList.contains("has-text-warning")).toBe(true);
    });

    it("draws no icon at no verdict, the unread rule (DET-42, VEV-03)", () => {
        const { fixture } = mount([UNVERDICTED]);
        expect(fixture.nativeElement.querySelector(".aurelius-gov-quality-verdict .icon")).toBeNull();
    });

    it("titlecases the dimension word (DET-42, the legacy's titlecase pipe)", () => {
        const { fixture } = mount([COMPLIANT, BROKEN, UNVERDICTED]);
        const words = [...fixture.nativeElement.querySelectorAll(".aurelius-gov-quality-dimension")].map(
            (word: Element) => normalize(word.textContent),
        );
        expect(words).toEqual(["Completeness", "Accuracy"]); // the empty dimension draws no word
    });

    it("a title click emits the rule's guid (DET-42, DET-06)", () => {
        const { fixture, host } = mount([COMPLIANT, BROKEN]);
        const link = fixture.nativeElement.querySelectorAll(".title.is-4 a")[1] as HTMLElement;
        link.click();
        expect(host.lastRule).toBe("r2");
    });
});
