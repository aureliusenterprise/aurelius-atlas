import { ChangeDetectionStrategy, Component } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import type { EntityCard } from "aurelius-atlas-data-access";

import { CatalogueCard } from "./catalogue-card.component";

/**
 * The one rich card of both screens (VCF-01, VCF-06, DD-616, DD-617): the
 * shell's title and badge, the breadcrumb trail (the stored crumb array
 * plus the card's own active crumb), the classification chips, the
 * description markdown, and the people rows: one labelled row per role —
 * Domain Lead(s), Data Owner(s), Data Steward(s) — from the door's role
 * relations (VCF-15, AVS-10), the flat "People" row of the derived
 * `m4i_person` relations kept as the fallback for a document still
 * awaiting its re-derive round (VCF-16). Every click — title, crumb,
 * person — emits the guid on `cardClicked`; routing is the screen's
 * (DD-154). These specs mount the part through a host, the gov-quality
 * cards spec's idiom.
 */

/** A minimal host: the part under test with one card input. */
@Component({
    template: `
        <aurelius-atlas-webapp-catalogue-card [card]="card" [pageGuid]="pageGuid" (cardClicked)="last = $event" />
    `,
    imports: [CatalogueCard],
    changeDetection: ChangeDetectionStrategy.OnPush,
})
class Host {
    card: EntityCard = CARD;
    pageGuid: string | undefined = undefined;
    last: string | null = null;
}

/** Collapse the markup's whitespace. */
const normalize = (text: string | undefined | null) => text?.replace(/\s+/g, " ").trim();

/** A card carrying every body field. */
const CARD: EntityCard = {
    guid: "e1",
    typeName: "m4i_data_attribute",
    name: "cost_centre_code",
    qualifiedName: "cost_centre_code@finance",
    displayText: "cost_centre_code",
    definition: "The **code** of the cost centre.",
    status: "ACTIVE",
    stale: false,
    classificationNames: ["PII"],
    breadcrumb: [
        { guid: "d1", name: "Finance", typeName: "m4i_data_domain" },
        { guid: "n1", name: "Cost Centre", typeName: "m4i_data_entity" },
    ],
    relations: [
        {
            attribute: "m4i_person",
            entities: [
                { guid: "p1", name: "Gerrit Lorenz", typeName: "m4i_person" },
                { guid: "p2", name: "Ava Ross", typeName: "m4i_person" },
                { guid: "p1", name: "Gerrit Lorenz", typeName: "m4i_person" }, // the duplicate drops
            ],
        },
        {
            attribute: "m4i_data_entity",
            entities: [{ guid: "n1", name: "Cost Centre", typeName: "m4i_data_entity" }],
        },
    ],
};

function mount(
    card: EntityCard,
    pageGuid?: string,
): { fixture: ReturnType<typeof TestBed.createComponent<Host>>; host: Host } {
    const fixture = TestBed.createComponent(Host);
    fixture.componentInstance.card = card;
    fixture.componentInstance.pageGuid = pageGuid;
    fixture.detectChanges();
    return { fixture, host: fixture.componentInstance };
}

describe("The shared rich card (VCF-01, VCF-06)", () => {
    it("renders the title, the badge, and their click emits the guid (VCF-01)", () => {
        const { fixture, host } = mount(CARD);
        const title = fixture.nativeElement.querySelector(".title.is-4 a");
        expect(normalize(title?.textContent)).toBe("cost_centre_code");
        title.click();
        expect(host.last).toBe("e1");
        // The badge carries the dictionary name and icon, no alias (DV-167).
        const badge = fixture.nativeElement.querySelector("aurelius-atlas-ui-type-name");
        expect(normalize(badge?.textContent)).toContain("Data Attribute");
    });

    it("renders the trail with the card's own crumb active (VCF-01, VDR-06)", () => {
        const { fixture, host } = mount(CARD);
        const crumbs = [...fixture.nativeElement.querySelectorAll(".aurelius-card-trail li")];
        expect(crumbs.map((crumb: Element) => normalize(crumb.textContent))).toEqual([
            "Finance",
            "Cost Centre",
            "cost_centre_code",
        ]);
        // With no viewed entity (a results row), the card's own crumb is
        // the active one (VCF-02).
        expect(crumbs[2].classList.contains("is-active")).toBe(true);
        crumbs[0].querySelector("a")?.click();
        expect(host.last).toBe("d1");
    });

    it("the viewed entity's crumb is the plain-text one, the card's own stays a link (DD-625)", () => {
        // The details sections pass the page's guid: the entity you are
        // already at is the non-clickable crumb, the legacy card's
        // parentId$ as activeGuid (DD-625).
        const { fixture, host } = mount(CARD, "n1");
        const crumbs = [...fixture.nativeElement.querySelectorAll(".aurelius-card-trail li")];
        expect(crumbs[1].classList.contains("is-active")).toBe(true);
        expect(crumbs[1].querySelector("a")).toBeNull();
        expect(crumbs[2].classList.contains("is-active")).toBe(false);
        // The card's own crumb is a link: clicking it routes to the card.
        crumbs[2].querySelector("a")?.click();
        expect(host.last).toBe("e1");
    });

    it("a crumb without a name rides its type, then its guid (VDR-06, ASU-02)", () => {
        const { fixture } = mount({
            ...CARD,
            breadcrumb: [
                { guid: "x1", name: null, typeName: "m4i_data_domain" },
                { guid: "x2", name: "", typeName: null },
            ],
        });
        const crumbs = [...fixture.nativeElement.querySelectorAll(".aurelius-card-trail li")];
        expect(normalize(crumbs[0].textContent)).toContain("m4i_data_domain");
        expect(normalize(crumbs[1].textContent)).toContain("x2");
    });

    it("a card without a stored parent draws no trail (VDR-11, DD-630)", () => {
        // The shared rule: the one crumb would repeat the card's own title,
        // so the legacy guard's shape leaves no trail (results rows ride
        // this too, VCF-04).
        const { fixture, host } = mount({ ...CARD, breadcrumb: [] });
        expect(fixture.nativeElement.querySelector(".aurelius-card-trail nav")).toBeNull();
        // The card still routes by its title (VCF-01).
        fixture.nativeElement.querySelector(".title.is-4 a").click();
        expect(host.last).toBe("e1");
    });

    it("renders the classification chips by display name (DD-379)", () => {
        const { fixture } = mount(CARD);
        const chips = [...fixture.nativeElement.querySelectorAll("aurelius-atlas-ui-classification-chip")];
        expect(chips.map((chip: Element) => normalize(chip.textContent))).toEqual(["Has PII"]);
    });

    it("renders the description as markdown, omitted at none (VCF-01, VCF-03)", () => {
        const { fixture } = mount(CARD);
        const body = fixture.nativeElement.querySelector(".aurelius-card-description");
        expect(body.querySelector("strong")?.textContent).toBe("code");

        const { fixture: bare } = mount({ ...CARD, definition: null });
        expect(bare.nativeElement.querySelector(".aurelius-card-description")).toBeNull();
    });

    it("renders one labelled row per role, in legacy order, deduped (VCF-15, AVS-10)", () => {
        const { fixture, host } = mount({
            ...CARD,
            relations: [
                { attribute: "steward", entities: [{ guid: "p2", name: "Ava Ross", typeName: "m4i_person" }] },
                {
                    attribute: "businessOwner",
                    entities: [
                        { guid: "p1", name: "Gerrit Lorenz", typeName: "m4i_person" },
                        { guid: "p1", name: "Gerrit Lorenz", typeName: "m4i_person" }, // the duplicate drops
                    ],
                },
                { attribute: "domainLead", entities: [{ guid: "p3", name: "Ida Lang", typeName: "m4i_person" }] },
            ],
        });
        const rows = [...fixture.nativeElement.querySelectorAll(".aurelius-people-row")];
        // the legacy order — lead, owner, steward — whatever order the relations arrived in
        expect(rows.map((row: Element) => normalize(row.textContent))).toEqual([
            "Domain Lead(s) : Ida Lang",
            "Data Owner(s) : Gerrit Lorenz",
            "Data Steward(s) : Ava Ross",
        ]);
        rows[1].querySelector("a")?.click();
        expect(host.last).toBe("p1");
    });

    it("a role with no people draws no row, and the role rows replace the flat one (VCF-15, VCF-16)", () => {
        const { fixture } = mount({
            ...CARD,
            relations: [
                { attribute: "m4i_person", entities: [{ guid: "p1", name: "Gerrit Lorenz", typeName: "m4i_person" }] },
                { attribute: "steward", entities: [{ guid: "p2", name: "Ava Ross", typeName: "m4i_person" }] },
            ],
        });
        const rows = [...fixture.nativeElement.querySelectorAll(".aurelius-people-row")];
        // domainLead and businessOwner have none: no row for them, and the flat m4i_person row is
        // gone — a card never draws both kinds (VCF-16).
        expect(rows.map((row: Element) => normalize(row.textContent))).toEqual(["Data Steward(s) : Ava Ross"]);
    });

    it("keeps the flat People row of a document awaiting its re-derive round (VCF-16, DD-628)", () => {
        const { fixture, host } = mount(CARD);
        const rows = [...fixture.nativeElement.querySelectorAll(".aurelius-people-row")];
        expect(rows).toHaveLength(1);
        expect(normalize(rows[0].textContent)).toBe("People : Gerrit Lorenz, Ava Ross");
        rows[0].querySelector("a")?.click();
        expect(host.last).toBe("p1");
    });

    it("omits the people rows at none and keeps the rest (VCF-06)", () => {
        const { fixture } = mount({ ...CARD, relations: [] });
        expect(fixture.nativeElement.querySelector(".aurelius-people-row")).toBeNull();
        expect(fixture.nativeElement.querySelector(".title.is-4 a")?.textContent).toBe("cost_centre_code");
    });

    it("a person without a name rides its guid (a link needs a label)", () => {
        const { fixture } = mount({
            ...CARD,
            relations: [{ attribute: "steward", entities: [{ guid: "p9", name: null, typeName: "m4i_person" }] }],
        });
        expect(normalize(fixture.nativeElement.querySelector(".aurelius-people-row")?.textContent)).toContain("p9");
    });

    it("an unmapped type answers a raw badge name and no icon (DD-378)", () => {
        const { fixture } = mount({ ...CARD, typeName: "spark_application" });
        const badge = fixture.nativeElement.querySelector("aurelius-atlas-ui-type-name");
        expect(normalize(badge?.textContent)).toContain("spark_application");
    });
});
