import { ChangeDetectionStrategy, Component, computed, input, output } from "@angular/core";
import type { EntityCard as ViewCard, RuleScore } from "aurelius-atlas-data-access";
import {
    Breadcrumbs,
    ClassificationChip,
    EntityCard,
    GovQualityList,
    Markdown,
    PeopleBox,
    QualityDimensionList,
    type PeopleRow,
    type QualityDimensionRow,
} from "aurelius-atlas-ui";

import { nameDisplay } from "../meta/type-display";
import { typeIcon } from "../meta/type-icons";
import { hasScoreSource, printableRuleScore, qualityRows } from "./quality-mapping";
import { PEOPLE_ENDS } from "../details/shared/people";
import { PropagatedChips, type PropagatedChipEntry } from "./propagated-chips.component";
import { trailOf } from "./trail";

/** The relationship attribute the document's derived people arrive under (LAS-05). */
const PERSON_ATTRIBUTE = "m4i_person";

/**
 * The one rich card of both screens (VCF-01, DD-616): the 7.13 card shell
 * with the view-family card's body — the breadcrumb trail (the stored
 * `breadcrumb` plus the card's own crumb, `trailOf`'s rule shared with
 * the details header; the crumb of the entity being viewed is the
 * active one, DD-625), the classification chips (`classificationNames`,
 * DD-379's names), the description text (the card's `definition`, which the
 * server derives from the entity's `description` since 18.8) as markdown, and
 * the people rows: one labelled row
 * per role — Domain Lead(s), Data Owner(s), Data Steward(s) — from the
 * door's role relations (VCF-15, AVS-10, ASD-06), the flat "People" row
 * of 16.5d kept as the fallback for a document still awaiting its
 * re-derive round (VCF-16, DD-628).
 *
 * The card's governance mark (VCF-19, 16.5h) rides the shell's quality column,
 * which only an entity the governance worker has judged opens (VCF-20): the
 * mark is UIC-38's, fed straight from `card.verdicts` (AVS-11, VDR-13) — no
 * fetch, no loading state, the mark paints with the card. An unjudged card
 * draws no mark at all, not even the legacy's blanket green check (DV-198).
 *
 * The results row and the details section card mount this one component
 * (VCF-05): the same entity cannot render differently on the two screens
 * twice. The badge carries the card's alias alone, no base-type suffix —
 * the legacy card's shape (7-21a), on the field the card shape gained in
 * 18.1 (MMS-09, DD-721); the loading row is not this component's — DET-18's
 * loading row stays the plain shell's, owned by the sections store's caller.
 *
 * The part is dumb (DD-154's split): every title, crumb, and person click
 * emits the guid on `cardClicked` and the screen routes.
 */
@Component({
    selector: "aurelius-atlas-webapp-catalogue-card",
    imports: [
        Breadcrumbs,
        ClassificationChip,
        EntityCard,
        GovQualityList,
        Markdown,
        PeopleBox,
        QualityDimensionList,
        PropagatedChips,
    ],
    // The demo's card body is a stack of blocks with a 16px gap; here the
    // body is the slotted content of the shell, so the rhythm lives on
    // [card-content]: a flex column with a fixed gap, and the chips field
    // with Bulma's -12px pull removed so the gap measures clean. (VCF-03)
    styles: [
        `
            [card-content] {
                display: flex;
                flex-direction: column;
                gap: 16px;
            }
            [card-content] .field.is-grouped {
                margin-bottom: 0;
            }
        `,
    ],
    template: `
        <aurelius-atlas-ui-entity-card
            [guid]="card().guid"
            [name]="card().displayText"
            [typeName]="badgeName()"
            [typeAlias]="badgeAlias()"
            [typeIcon]="badgeIcon()?.icon"
            [typeIconClass]="badgeIcon()?.classIcon"
            [showQuality]="showGovQuality()"
            (entityClicked)="cardClicked.emit($event)"
        >
            @if (showGovQuality()) {
                <!-- The governance mark, in the shell's quality column and
                     nothing else (VCF-19, VCF-20): the rows are the door's
                     joined refusals (AVS-11), each one its message and
                     nothing under it. The card still knows the rule name
                     (DD-839), and shows it in the details box. -->
                <aurelius-atlas-ui-gov-quality-list card-quality [nonCompliant]="govQuality()" />
            }
            <div card-content>
                <aurelius-atlas-ui-breadcrumbs
                    class="aurelius-card-trail"
                    [items]="trail()"
                    [activeGuid]="pageGuid() ?? card().guid"
                    (itemClicked)="cardClicked.emit($event)"
                />
                @if (classifications().length > 0 || propagated().length > 0) {
                    <div class="field is-grouped is-grouped-multiline">
                        @for (name of classifications(); track name) {
                            <div class="control">
                                <aurelius-atlas-ui-classification-chip [label]="name" />
                            </div>
                        }
                        <!-- The propagated tags ride the same row (VDR-12 as
                             amended by DD-836): a result line marks its own
                             tags just as the opened entity does, by the shared
                             part — same chip, same source rows. -->
                        <aurelius-atlas-webapp-propagated-chips
                            [entries]="propagated()"
                            (sourceClicked)="cardClicked.emit($event)"
                        />
                    </div>
                }
                @if (scoreRows().length > 0) {
                    <!-- The score rows (DET-60 as amended by 7.25d): the
                             legacy card's showDataQuality block — the same
                             scored-dimension list the details box draws,
                             above the description. A card with no rows
                             prints no block and no placeholder (DET-63's
                             card half, DET-64's count gate). Both screens
                             print it (DET-61 as amended, DD-860): the data
                             decides, the screen does not. DET-65 (7.25e,
                             DD-866): a card the field scored prints that one
                             row in DET-60's place instead — one list, one
                             shape, and the count hidden (the legacy rule
                             card printed pie, percent, dimension word). -->
                    <aurelius-atlas-ui-quality-dimension-list
                        class="aurelius-card-scores"
                        [dimensions]="scoreRows()"
                        [showCount]="showScoreCount()"
                    />
                }
                @if (description()) {
                    <div class="aurelius-card-description">
                        <aurelius-atlas-ui-markdown [markdown]="description()" />
                    </div>
                }
                @if (peopleRows().length > 0) {
                    <aurelius-atlas-ui-people-box
                        [rows]="peopleRows()"
                        [showEmpty]="false"
                        (personClicked)="cardClicked.emit($event)"
                    />
                }
            </div>
        </aurelius-atlas-ui-entity-card>
    `,
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CatalogueCard {
    /** The view-family card to render — either door's answer. */
    readonly card = input.required<ViewCard>();

    /**
     * The entity being viewed, whose crumb is the trail's plain-text one
     * (DD-625): the details sections pass the page's guid, as the legacy
     * card's `parentId$` did, so the entity you are already at is the
     * non-clickable crumb and the card's own stays a link. Unset — a
     * results row, where no entity is open — leaves the card's own crumb
     * active (VCF-02).
     */
    readonly pageGuid = input<string | undefined>(undefined);

    /**
     * The opened field's score row for this card's rule (DET-65, AVS-13,
     * DD-865): the sections store joined it by GUID, so the card prints it in
     * DET-60's place (DD-866). Absent — a search result, another screen, a
     * rule the scanner never scored (DV-207) — leaves the card exactly as
     * DET-60 states, so the join never adds a block anywhere else.
     */
    readonly ruleScore = input<RuleScore | undefined>(undefined);

    /** Emits the clicked card's, crumb's, or person's guid — the screen routes (DD-154). */
    readonly cardClicked = output<string>();

    /** The flat row's label — the dictionary's own derived-people name, "People" / "Personen". */
    private static readonly peopleLabel = $localize`:@@derivedperson:People`;

    /** The badge's type name (DET-26, DD-379): the dictionary display name, raw outside the dictionary. */
    protected readonly badgeName = computed(() => nameDisplay(this.card().typeName));

    /** The badge's icon (DET-26, DD-378): the app's type map; an unmapped type renders none. */
    protected readonly badgeIcon = computed(() => typeIcon(this.card().typeName));

    /**
     * The badge's alias (MMS-09, DD-721): the card's `typeAlias` as a
     * non-empty string, else nothing. The server already leaves an empty
     * attribute out (AVS-01 as amended); the guard covers a door that still
     * answers one. The alias is author text and shows as stored, never
     * through `nameDisplay` (DET-26's rule).
     */
    protected readonly badgeAlias = computed(() => {
        const alias = this.card().typeAlias;
        return typeof alias === "string" && alias !== "" ? alias : undefined;
    });

    /** The card's trail (VCF-01): the stored breadcrumb plus its own active crumb (VDR-06's rule). */
    protected readonly trail = computed(() => trailOf(this.card(), (typeName) => typeIcon(typeName)));

    /** The chip labels (DD-379): the card's classification names, each by its dictionary display name. */
    protected readonly classifications = computed(() =>
        (this.card().classificationNames ?? [])
            .filter((name) => typeof name === "string" && name !== "")
            .map((name) => nameDisplay(name)),
    );

    /**
     * The propagated chips (VDR-12 as amended by DD-836): one per tag the
     * door brought in, each by its dictionary display name, with the entities
     * it came from. The search door fills the card's field now, so a result
     * line marks what it carries by propagation exactly as the header of the
     * same entity does — the card draws no row of its own.
     */
    protected readonly propagated = computed<PropagatedChipEntry[]>(() =>
        (this.card().propagatedClassifications ?? [])
            .filter((entry) => typeof entry.typeName === "string" && entry.typeName !== "")
            .map((entry) => ({
                label: nameDisplay(entry.typeName),
                sources: (entry.entities ?? []).filter(
                    (source) => typeof source.guid === "string" && source.guid !== "",
                ),
            })),
    );

    /**
     * Whether the card opens the quality column (VCF-20, DD-840): only an
     * entity the governance worker has judged (`governed` true, AVS-01) draws
     * a mark. `false` or absent is unjudged — not compliant — so the column
     * stays closed and no check or warning shows.
     */
    protected readonly showGovQuality = computed(() => this.card().governed === true);

    /**
     * The mark's dropdown rows (VCF-19): the card's joined refusals straight
     * through (AVS-11, VDR-13), each verdict its one message (DD-839 keeps
     * the rule name on the wire for the details box). No fetch — the door
     * already joined them, in rule-name order.
     */
    protected readonly govQuality = computed(() =>
        (this.card().verdicts ?? []).map((verdict) => ({ message: verdict.message })),
    );

    /**
     * The field's joined row as UIC-37 draws it (DET-65, DD-866): the pie,
     * the percent at `percent: '1.0-1'` (the pipe's, on the raw score), and
     * the dimension word lowercased — the legacy rule card's shape. DET-63's
     * posture holds: a score the screen cannot use — absent, negative, not a
     * number — yields no row, and an empty dimension word never prints a
     * wordless row either. The card's own `quality` is never the source here.
     */
    protected readonly ruleScoreRow = computed<QualityDimensionRow | undefined>(() => {
        const row = printableRuleScore(this.ruleScore());
        if (row === undefined) {
            return undefined;
        }
        // The count never renders for this row (DET-65), so it carries 0.
        return { dimension: row.dimension.toLowerCase(), score: row.score, count: 0 };
    });

    /**
     * The score block's rows (DET-60 as amended by DET-65): the field's
     * joined rule row when there is one — and then never DET-60's roll-up
     * too — else the card's own score rows (AVS-01) in DET-56's dimension
     * order, a partial set printing its scored dimensions only. The legacy's
     * source gate reads the same here as on the box (DET-63): a sourceless
     * card yields the empty list no block renders for, and never a
     * placeholder (DET-60's card half).
     */
    protected readonly scoreRows = computed<QualityDimensionRow[]>(() => {
        const row = this.ruleScoreRow();
        if (row !== undefined) {
            return [row];
        }
        return hasScoreSource(this.card().quality) ? qualityRows(this.card().quality) : [];
    });

    /** Whether the printed rows carry their counts (DD-866): the roll-up
     * prints them (DET-60), the rule's own row does not (DET-65). */
    protected readonly showScoreCount = computed(() => this.ruleScoreRow() === undefined);

    /** The description text (VCF-03 as amended by SPA-05): the card's
     * `definition`, which the server derives from the entity's `description`. */
    protected readonly description = computed(() => {
        const definition = this.card().definition;
        return typeof definition === "string" ? definition : "";
    });

    /** The flat people of the card's derived person relations (DD-617), deduped by guid. */
    private readonly persons = computed(() => {
        const seen = new Map<string, { guid: string; displayText: string }>();
        for (const relation of this.card().relations ?? []) {
            if (relation.attribute !== PERSON_ATTRIBUTE) continue;
            for (const entity of relation.entities ?? []) {
                if (typeof entity.guid !== "string" || entity.guid === "" || seen.has(entity.guid)) continue;
                const name = typeof entity.name === "string" && entity.name !== "" ? entity.name : entity.guid;
                seen.set(entity.guid, { guid: entity.guid, displayText: name });
            }
        }
        return [...seen.values()];
    });

    /**
     * The card's people rows (VCF-15): one labelled row per role — Domain
     * Lead(s), Data Owner(s), Data Steward(s), the legacy order — read from
     * the door's role relations (AVS-10), each deduped by guid first-wins,
     * a role with no people drawing no row. A card whose document has
     * person names but no role ends — derived before 16.5f, awaiting its
     * round (VCF-16, ASD-07) — keeps the flat "People" row instead, never
     * both.
     */
    protected readonly peopleRows = computed<PeopleRow[]>(() => {
        const relations = this.card().relations ?? [];
        const rows: PeopleRow[] = [];
        for (const { key, label } of PEOPLE_ENDS) {
            const seen = new Map<string, { guid: string; displayText: string }>();
            for (const relation of relations) {
                if (relation.attribute !== key) continue;
                for (const entity of relation.entities ?? []) {
                    if (typeof entity.guid !== "string" || entity.guid === "" || seen.has(entity.guid)) continue;
                    const name = typeof entity.name === "string" && entity.name !== "" ? entity.name : entity.guid;
                    seen.set(entity.guid, { guid: entity.guid, displayText: name });
                }
            }
            if (seen.size > 0) rows.push({ label, people: [...seen.values()] });
        }
        if (rows.length > 0) return rows;
        const people = this.persons();
        return people.length > 0 ? [{ label: CatalogueCard.peopleLabel, people }] : [];
    });
}
