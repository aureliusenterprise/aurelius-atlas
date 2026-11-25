import { ChangeDetectionStrategy, Component } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import type { EntityCard, RuleScore } from "aurelius-atlas-data-access";

import { CatalogueCard } from "./catalogue-card.component";

import { normalize } from "../../../testing/dom";

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
        <aurelius-atlas-webapp-catalogue-card
            [card]="card"
            [ruleScore]="ruleScore"
            [pageGuid]="pageGuid"
            (cardClicked)="last = $event"
        />
    `,
    imports: [CatalogueCard],
    changeDetection: ChangeDetectionStrategy.OnPush,
})
class Host {
    card: EntityCard = CARD;
    ruleScore: RuleScore | undefined = undefined;
    pageGuid: string | undefined = undefined;
    last: string | null = null;
}

/** A card carrying every body field. */
const CARD: EntityCard = {
    guid: "e1",
    typeName: "m4i_data_attribute",
    name: "cost_centre_code",
    qualifiedName: "cost_centre_code@finance",
    displayText: "cost_centre_code",
    typeAlias: "Cost Code",
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
    ruleScore?: RuleScore,
): { fixture: ReturnType<typeof TestBed.createComponent<Host>>; host: Host } {
    const fixture = TestBed.createComponent(Host);
    fixture.componentInstance.card = card;
    fixture.componentInstance.pageGuid = pageGuid;
    fixture.componentInstance.ruleScore = ruleScore;
    fixture.detectChanges();
    return { fixture, host: fixture.componentInstance };
}

describe("The shared rich card (VCF-01, VCF-06, VCF-19, VCF-20)", () => {
    it("renders the title, the badge, and their click emits the guid (VCF-01)", () => {
        const { fixture, host } = mount(CARD);
        const title = fixture.nativeElement.querySelector(".title.is-4 a");
        expect(normalize(title?.textContent)).toBe("cost_centre_code");
        title.click();
        expect(host.last).toBe("e1");
        // The badge carries the card's alias alone, with no base-type
        // suffix — the legacy card's shape (7-21a), on the field the card
        // shape gained in 18.1 (MMS-09, DD-721).
        const badge = fixture.nativeElement.querySelector("aurelius-atlas-ui-type-name");
        expect(normalize(badge?.textContent)).toContain("Cost Code");
        expect(normalize(badge?.textContent)).not.toContain("Data Attribute");
    });

    it("a card without an alias badges the dictionary type name (MMS-09)", () => {
        const { fixture } = mount({ ...CARD, typeAlias: undefined });
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

    it("marks a propagated tag on the card and names its sources (VDR-12, DD-836)", () => {
        const { fixture, host } = mount({
            ...CARD,
            propagatedClassifications: [
                {
                    typeName: "PII",
                    entities: [
                        {
                            guid: "src-1",
                            name: "source_table",
                            typeName: "m4i_dataset",
                            breadcrumb: [{ guid: "d0", name: "Genomics", typeName: "m4i_data_domain" }],
                        },
                    ],
                },
            ],
        });
        // The propagated chip rides the card's own chip row, marked by the
        // chip's trigger — the same control the header of the entity shows.
        const chips = [...fixture.nativeElement.querySelectorAll("aurelius-atlas-ui-classification-chip")];
        expect(chips).toHaveLength(2);
        const marker = chips[1].querySelector(".tag.is-primary.dropdown.is-hoverable");
        expect(marker?.getAttribute("title")).toBe("Is propagated");
        // A source row shows a card line: the type icon, the name, and the
        // path it sits on in place of the type name (DD-836). The row is a
        // div — a button cannot hold the trail's links — and its name keeps
        // a button, so the source stays keyboard-reachable (VDR-12).
        const row = fixture.nativeElement.querySelector(".aurelius-details-source");
        expect(row.tagName).toBe("DIV");
        expect(normalize(row.querySelector(".aurelius-details-source-name")?.textContent)).toBe("source_table");
        expect(row.querySelector("button.aurelius-details-source-name")).toBeTruthy();
        expect(row.querySelector(".aurelius-details-source-icon fa-icon")).toBeTruthy();
        expect(normalize(row.querySelector(".aurelius-details-source-path")?.textContent)).toBe("Genomics");
        expect(fixture.nativeElement.querySelector(".aurelius-details-source-type")).toBeNull();
        // The name button opens the source — and only the source: it stops
        // bubbling, so no ancestor can also route (DD-836).
        const name = row.querySelector("button.aurelius-details-source-name") as HTMLButtonElement;
        expect(name.querySelector(".aurelius-details-source-icon fa-icon")).toBeTruthy();
        name.click();
        expect(host.last).toBe("src-1");
        // The trail rides with its links on (the review asked for clickable
        // crumbs): a crumb click names its own entity, never the source or
        // the card.
        const crumb = row.querySelector(".aurelius-details-source-path .breadcrumb a") as HTMLAnchorElement;
        expect(crumb).toBeTruthy();
        crumb.click();
        expect(host.last).toBe("d0");
    });

    it("a card whose door answered no propagated field draws no propagated chip (DD-836)", () => {
        const { fixture } = mount({ ...CARD, propagatedClassifications: undefined });
        expect(fixture.nativeElement.querySelector(".tag.is-primary.dropdown.is-hoverable")).toBeNull();
        // The own chip row is untouched.
        expect(fixture.nativeElement.querySelectorAll("aurelius-atlas-ui-classification-chip")).toHaveLength(1);
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
        const { fixture } = mount({ ...CARD, typeName: "spark_application", typeAlias: undefined });
        const badge = fixture.nativeElement.querySelector("aurelius-atlas-ui-type-name");
        expect(normalize(badge?.textContent)).toContain("spark_application");
    });

    it("a judged card draws the governance mark from the door's joined verdicts (VCF-19, AVS-11)", () => {
        // 16.5h: the door joins the refusals (VDR-13) and the card paints the
        // mark with them — no fetch, no loading state (DD-838, DV-198).
        const { fixture } = mount({
            ...CARD,
            governed: true,
            verdicts: [
                { rule: "r-a", name: "Alpha rule", message: "the record does not carry the attribute" },
                { rule: "r-z", name: "Zeta rule", message: "the attribute holds no value to show" },
            ],
        });
        // The quality column opened (VCF-01 as amended) and the mark bottom-right.
        const column = fixture.nativeElement.querySelector(".quality");
        expect(column).toBeTruthy();
        const trigger = column.querySelector(".aurelius-gov-quality-trigger");
        expect(normalize(trigger?.textContent)).toBe("2x"); // the count, UIC-38's trigger
        // The dropdown rows, in the card's order: each its one message
        // and nothing under it (DD-839 keeps the rule name for the box).
        const rows = [...column.querySelectorAll(".dropdown-item")];
        expect(rows.map((row: Element) => normalize(row.querySelector("h6")?.textContent))).toEqual([
            "the record does not carry the attribute",
            "the attribute holds no value to show",
        ]);
        expect(column.querySelectorAll(".dropdown-item p")).toHaveLength(0);
        // Nothing else on the card moved (VCF-21): trail, chips, description, people.
        expect(fixture.nativeElement.querySelectorAll(".aurelius-card-trail li")).toHaveLength(3);
        expect(fixture.nativeElement.querySelectorAll("aurelius-atlas-ui-classification-chip")).toHaveLength(1);
        expect(fixture.nativeElement.querySelector(".aurelius-card-description strong")?.textContent).toBe("code");
        expect(fixture.nativeElement.querySelectorAll(".aurelius-people-row")).toHaveLength(1);
    });

    it("a judged card with no refusal draws the success check (VCF-20, UIC-38)", () => {
        const { fixture } = mount({ ...CARD, governed: true, verdicts: [] });
        expect(fixture.nativeElement.querySelector(".quality .aurelius-gov-quality-success")).toBeTruthy();
        expect(fixture.nativeElement.querySelector(".quality .aurelius-gov-quality-trigger")).toBeNull();
    });

    it("an unjudged card draws no mark and no quality column at all (VCF-20, DD-840, DV-198)", () => {
        // The legacy drew its green check for every card; an entity whose
        // type has no governance rules is unjudged, not compliant, so the
        // column stays shut whatever the verdicts field holds.
        for (const governed of [false, null, undefined]) {
            const { fixture } = mount({
                ...CARD,
                governed,
                verdicts: [{ rule: "r-a", name: "Alpha rule", message: "the record does not carry the attribute" }],
            });
            expect(fixture.nativeElement.querySelector(".quality")).toBeNull();
            expect(fixture.nativeElement.querySelector("aurelius-atlas-ui-gov-quality-list")).toBeNull();
        }
    });

    describe("the score block (DET-60, DET-61, DET-63, DET-64)", () => {
        /** Score rows as the door's roll-up writes them (AVS-01): a held
         *  0-count completeness row beside three scored dimensions. */
        const SCORES: NonNullable<EntityCard["quality"]> = [
            { dimension: "overall", score: 0.9, count: 5, total: 5 },
            { dimension: "timeliness", score: 0.4, count: 1, total: 5 },
            { dimension: "validity", score: 0.5, count: 2, total: 5 },
            { dimension: "accuracy", score: 0.75, count: 1, total: 5 },
            { dimension: "completeness", score: 0.25, count: 0, total: 5 },
        ];

        it("a scored card prints the block after the chips, above the description (DET-60, DET-64)", () => {
            const { fixture } = mount({ ...CARD, quality: SCORES });
            const block = fixture.nativeElement.querySelector(".aurelius-card-scores");
            expect(block).toBeTruthy();
            // The same list the details box draws: fixed order, `overall`
            // left out, and DET-64's gate — a dimension the roll-up counts 0
            // prints no row, the legacy's own count gate (LAS-12's zeros).
            const rows = [...block.querySelectorAll(".quality-dimension")];
            expect(rows.map((row: Element) => normalize(row.textContent))).toEqual([
                "75% Accuracy (1)",
                "40% Timeliness (1)",
                "50% Validity (2)",
            ]);
            expect(block.querySelector("aurelius-atlas-ui-data-quality-pie")).toBeTruthy();
            // The legacy place: after the trail and the chips, above the
            // description and the people rows.
            const content = [...fixture.nativeElement.querySelectorAll("[card-content] > *")];
            const at = (selector: string) => content.indexOf(fixture.nativeElement.querySelector(selector));
            expect(at(".aurelius-card-scores")).toBeGreaterThan(at(".aurelius-card-trail"));
            expect(at(".aurelius-card-scores")).toBeGreaterThan(at(".field.is-grouped"));
            expect(at(".aurelius-card-scores")).toBeLessThan(at(".aurelius-card-description"));
            expect(at(".aurelius-card-scores")).toBeLessThan(at("aurelius-atlas-ui-people-box"));
        });

        it("a partial set prints only the dimensions it scored (DET-60)", () => {
            const { fixture } = mount({
                ...CARD,
                quality: [
                    { dimension: "overall", score: 0.5, count: 1, total: 2 },
                    { dimension: "uniqueness", score: 0.5, count: 1, total: 2 },
                ],
            });
            const rows = [...fixture.nativeElement.querySelectorAll(".aurelius-card-scores .quality-dimension")];
            expect(rows.map((row: Element) => normalize(row.textContent))).toEqual(["50% Uniqueness (1)"]);
        });

        it("a card whose dimensions all count 0 prints no block (DET-64, DET-63's card half)", () => {
            // ASQ-05 sums the five dimensions into `overall`, so a roll-up
            // cannot write this — but the card's rule is the row builder's
            // (DET-60): no scored row, no block, no placeholder.
            const { fixture } = mount({
                ...CARD,
                quality: [
                    { dimension: "overall", score: 0, count: 1, total: 1 },
                    { dimension: "timeliness", score: 0, count: 0, total: 1 },
                ],
            });
            expect(fixture.nativeElement.querySelector(".aurelius-card-scores")).toBeNull();
            expect(fixture.nativeElement.querySelector(".aurelius-quality-not-available")).toBeNull();
        });

        it("a card with no score rows prints no block and no placeholder (DET-60, DET-63)", () => {
            for (const quality of [
                undefined, // no rows at all
                [], // the empty answer
                [{ dimension: "overall", score: 0, count: 0, total: 0 }], // sourceless: overall count 0
                [{ dimension: "accuracy", score: -1, count: 1, total: 1 }], // DET-63: a score that never renders
            ]) {
                const { fixture } = mount({ ...CARD, quality });
                expect(fixture.nativeElement.querySelector(".aurelius-card-scores")).toBeNull();
                // The card's `showPlaceholder` is off (DET-60): not even the
                // placeholder text the details box prints.
                expect(fixture.nativeElement.querySelector(".aurelius-quality-not-available")).toBeNull();
                // The rest of the card is untouched.
                expect(fixture.nativeElement.querySelector(".aurelius-card-description strong")?.textContent).toBe(
                    "code",
                );
            }
        });

        it("both screens print the block: the data decides, not the mount site (DET-61 as amended, DD-860)", () => {
            // 7.25d retires the mount-site switch: the same scored card draws
            // its block on a results row (the default mount here, no pageGuid)
            // and inside a details section (the next mount, with one).
            const { fixture: results } = mount({ ...CARD, quality: SCORES });
            expect(results.nativeElement.querySelectorAll(".aurelius-card-scores .quality-dimension")).toHaveLength(3);
            const { fixture: section } = mount({ ...CARD, quality: SCORES }, "n1");
            expect(section.nativeElement.querySelectorAll(".aurelius-card-scores .quality-dimension")).toHaveLength(3);
            // The card reads no setting of its own (DV-202 as corrected): an
            // un-scored card prints nothing on either screen.
            const { fixture: bare } = mount({ ...CARD }, "n1");
            expect(bare.nativeElement.querySelector(".aurelius-card-scores")).toBeNull();
        });

        it("a card carrying both prints both, in their own corners (DET-61 as amended)", () => {
            const { fixture } = mount({
                ...CARD,
                quality: SCORES,
                governed: true,
                verdicts: [{ rule: "r-a", name: "Alpha rule", message: "the attribute holds no value" }],
            });
            // The governance mark keeps its quality column (VCF-19, UIC-38)…
            const column = fixture.nativeElement.querySelector(".quality");
            expect(normalize(column.querySelector(".aurelius-gov-quality-trigger")?.textContent)).toBe("1x");
            // …and the score list sits in the content blocks — separate
            // rules, separate places, both printed.
            expect(fixture.nativeElement.querySelectorAll(".aurelius-card-scores .quality-dimension")).toHaveLength(3);
            expect(column.querySelector(".aurelius-card-scores")).toBeNull();
        });
    });

    describe("the rule card's own score row (DET-65, AVS-13, DD-866)", () => {
        /** One of the field's rule score rows (AVS-13): a rule card's own score. */
        function score(dimension: string, score: number): RuleScore {
            return { rule: "r-1", name: "Not null", dimension, score };
        }

        /** DET-60's roll-up, so a test can prove the two never both print. */
        const ROLL_UP: NonNullable<EntityCard["quality"]> = [
            { dimension: "overall", score: 0.9, count: 5, total: 5 },
            { dimension: "accuracy", score: 0.75, count: 1, total: 5 },
            { dimension: "completeness", score: 0.25, count: 2, total: 5 },
        ];

        it("a rule card with a row prints pie, percent, dimension, no count (DET-65)", () => {
            const { fixture } = mount(CARD, undefined, score("Accuracy", 0.892));
            const rows = [...fixture.nativeElement.querySelectorAll(".aurelius-card-scores .quality-dimension")];
            expect(rows).toHaveLength(1);
            // The legacy rule card's shape: the percent at `percent: '1.0-1'`,
            // the dimension lowercased, and the count the roll-up prints stays
            // away (DET-65, DD-866).
            expect(normalize(rows[0].textContent)).toBe("89.2% accuracy");
            expect(rows[0].textContent).toContain("\u00a0");
            expect(rows[0].textContent).not.toContain("(");
            expect(rows[0].querySelector("aurelius-atlas-ui-data-quality-pie")).toBeTruthy();
            // DET-60's place: after the trail and the chips, above the
            // description and the people rows.
            const content = [...fixture.nativeElement.querySelectorAll("[card-content] > *")];
            const at = (selector: string) => content.indexOf(fixture.nativeElement.querySelector(selector));
            expect(at(".aurelius-card-scores")).toBeGreaterThan(at(".aurelius-card-trail"));
            expect(at(".aurelius-card-scores")).toBeGreaterThan(at(".field.is-grouped"));
            expect(at(".aurelius-card-scores")).toBeLessThan(at(".aurelius-card-description"));
            expect(at(".aurelius-card-scores")).toBeLessThan(at("aurelius-atlas-ui-people-box"));
            // The join changes nothing else about the card (DET-65).
            expect(normalize(fixture.nativeElement.querySelector(".title.is-4 a")?.textContent)).toBe(
                "cost_centre_code",
            );
            expect(fixture.nativeElement.querySelector(".aurelius-card-description strong")?.textContent).toBe("code");
        });

        it("a rule card with no row prints no block and no placeholder (DET-65, DET-63's card half)", () => {
            for (const ruleScore of [
                undefined, // no row: the rule sits in a search result, another screen
                score("accuracy", -1), // DET-63: a score that never renders
                { rule: "r-1", name: "Not null", dimension: "accuracy", score: null as unknown as number },
            ]) {
                const { fixture } = mount(CARD, undefined, ruleScore);
                expect(fixture.nativeElement.querySelector(".aurelius-card-scores")).toBeNull();
                expect(fixture.nativeElement.querySelector(".aurelius-quality-not-available")).toBeNull();
            }
        });

        it("a row and DET-60's roll-up never both print: the row wins (DET-65)", () => {
            // ASQ-04 attaches totals to fields and above, so a rule entity's
            // own roll-up is empty — but the card's rule holds either way: the
            // joined row prints, the roll-up stays away.
            const { fixture } = mount({ ...CARD, quality: ROLL_UP }, undefined, score("Completeness", 1));
            const rows = [...fixture.nativeElement.querySelectorAll(".aurelius-card-scores .quality-dimension")];
            expect(rows).toHaveLength(1);
            expect(normalize(rows[0].textContent)).toBe("100% completeness");
            // Without the row the same card prints the roll-up (DET-60).
            const { fixture: rollUp } = mount({ ...CARD, quality: ROLL_UP });
            expect(
                [...rollUp.nativeElement.querySelectorAll(".aurelius-card-scores .quality-dimension")].map((row) =>
                    normalize(row.textContent),
                ),
            ).toEqual(["75% Accuracy (1)", "25% Completeness (2)"]);
        });

        it("a row whose dimension word is empty prints no row (DET-65)", () => {
            // Nothing names the line, so no line prints — DET-66's sort reads
            // the same row the same way.
            const { fixture } = mount(CARD, undefined, score("", 0.5));
            expect(fixture.nativeElement.querySelector(".aurelius-card-scores")).toBeNull();
        });

        it("an un-scored rule card elsewhere prints nothing extra (DET-65, DV-207)", () => {
            // A rule the scanner never scored keeps its card (DET-35's seed)
            // and draws no row, on either screen.
            const { fixture: results } = mount({ ...CARD, typeName: "m4i_data_quality" });
            expect(results.nativeElement.querySelector(".aurelius-card-scores")).toBeNull();
            const { fixture: section } = mount({ ...CARD, typeName: "m4i_data_quality" }, "field-1");
            expect(section.nativeElement.querySelector(".aurelius-card-scores")).toBeNull();
        });
    });
});
