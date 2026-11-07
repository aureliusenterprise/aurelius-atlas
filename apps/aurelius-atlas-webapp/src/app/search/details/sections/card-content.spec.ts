import { ChangeDetectionStrategy, Component, input } from "@angular/core";
import { TestBed } from "@angular/core/testing";

import type { AtlasEntity } from "aurelius-atlas-data-access";

import { CardContent } from "./card-content.component";

/**
 * The uniform card body (DET-19, DD-367): classification chips, the
 * definition-else-description markdown, the card entity's own people rows
 * (silent — no placeholder), and nothing else: the legacy's DQ column and
 * its leading column blocks have no source and stay out (the badge icon
 * lives in the card header, not the body — DD-378). These specs mount the body through a
 * host that owns the entity input; the routing emit rides the host's
 * listener. The in-screen wiring — the header badge, the card click, the
 * people links inside a live section — rides `details.component.spec.ts`.
 */

/** A minimal host: the body under test with one entity input. */
@Component({
    template: `<aurelius-atlas-webapp-card-content [entity]="entity()" (personClicked)="lastPerson = $event" />`,
    imports: [CardContent],
    changeDetection: ChangeDetectionStrategy.OnPush,
})
class Host {
    readonly entity = input.required<AtlasEntity>();
    lastPerson: string | null = null;
}

/** Collapse the markup's whitespace (the row's `:&nbsp;` renders a nbsp). */
const normalize = (text: string | undefined | null) => text?.replace(/\s+/g, " ").trim();

/** A resolved card entity: chips, both text keys, one steward end. */
function cardEntity(overrides: Partial<AtlasEntity> = {}): AtlasEntity {
    return {
        guid: "card-1",
        typeName: "m4i_data_attribute",
        attributes: { name: "gene_symbol", qualifiedName: "gene_symbol@hgnc" },
        classifications: [{ typeName: "PII" }, { typeName: "key_data" }],
        relationshipAttributes: {
            steward: [{ guid: "p-1", displayText: "Lin", relationshipStatus: "ACTIVE" }],
        },
        ...overrides,
    };
}

function mount(entity: AtlasEntity): { fixture: ReturnType<typeof TestBed.createComponent<Host>>; host: Host } {
    const fixture = TestBed.createComponent(Host);
    // setInput marks the OnPush host dirty: one detectChanges then runs the
    // body's render deterministically.
    fixture.componentRef.setInput("entity", entity);
    fixture.detectChanges();
    return { fixture, host: fixture.componentInstance };
}

describe("Card content (DET-19)", () => {
    it("renders one chip per classification (DET-19)", () => {
        const { fixture } = mount(cardEntity());
        const chips = fixture.nativeElement.querySelectorAll("aurelius-atlas-ui-classification-chip");
        expect(chips).toHaveLength(2);
        expect(chips[0].textContent).toContain("PII");
        expect(chips[1].textContent).toContain("key_data");
    });

    it("omits the chip row when the entity has none (DET-19)", () => {
        const { fixture } = mount(cardEntity({ classifications: [] }));
        expect(fixture.nativeElement.querySelector(".field.is-grouped")).toBeNull();
    });

    it("prefers definition over description (DET-19, DD-320's order)", () => {
        const { fixture } = mount(
            cardEntity({
                attributes: { definition: "The definition text.", description: "The description text." },
            }),
        );
        const body = fixture.nativeElement.querySelector(".aurelius-card-description");
        expect(body.textContent).toContain("The definition text.");
        expect(body.textContent).not.toContain("The description text.");
    });

    it("falls back to description, and renders the text as markdown (DET-19)", () => {
        const { fixture } = mount(cardEntity({ attributes: { description: "**bold** text" } }));
        const body = fixture.nativeElement.querySelector(".aurelius-card-description");
        expect(body.textContent).toContain("bold text");
        expect(body.querySelector("strong")).not.toBeNull();
    });

    it("omits the description block when neither key is text (DET-19)", () => {
        const { fixture } = mount(cardEntity({ attributes: { description: 42 } }));
        expect(fixture.nativeElement.querySelector(".aurelius-card-description")).toBeNull();
    });

    it("shows the card entity's own people rows, placeholder silent (DET-19, DET-23)", () => {
        const { fixture } = mount(cardEntity());
        const rows = fixture.nativeElement.querySelectorAll(".aurelius-people-row");
        expect(rows).toHaveLength(1);
        expect(normalize(rows[0].textContent)).toBe("Data Steward(s) : Lin");
        // The DET-19 silent shape: an entity with no people renders no box
        // and no placeholder line.
        const empty = mount(cardEntity({ relationshipAttributes: {} }));
        expect(empty.fixture.nativeElement.querySelector("aurelius-atlas-ui-people-box")).toBeNull();
    });

    it("drops a DELETED people edge (EDT-15's rule, shared with DET-23)", () => {
        const { fixture } = mount(
            cardEntity({
                relationshipAttributes: {
                    steward: [{ guid: "p-9", displayText: "Gone", relationshipStatus: "DELETED" }],
                },
            }),
        );
        expect(fixture.nativeElement.querySelector("aurelius-atlas-ui-people-box")).toBeNull();
    });

    it("emits the clicked person's guid (DET-19's routing seam)", () => {
        const { fixture, host } = mount(cardEntity());
        const link: HTMLElement = fixture.nativeElement.querySelector(".aurelius-people-row a");
        link.click();
        fixture.detectChanges();
        expect(host.lastPerson).toBe("p-1");
    });

    it("carries no quality column and no leading icon column (DET-19, DD-367)", () => {
        // The legacy body's unique columns were the DQ badges and the
        // breadcrumb trail (both without a source): neither block is here.
        // The chip's hashtag and the people row's person glyph are the parts'
        // own, not the body's; the type icon rides the header badge (DD-378).
        const { fixture } = mount(cardEntity());
        expect(fixture.nativeElement.querySelector(".quality")).toBeNull();
        expect(fixture.nativeElement.querySelector(".media-left")).toBeNull();
        expect(fixture.nativeElement.querySelector("figure.image")).toBeNull();
    });
});
