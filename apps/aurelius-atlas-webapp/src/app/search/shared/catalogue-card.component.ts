import { ChangeDetectionStrategy, Component, computed, input, output } from "@angular/core";
import type { EntityCard as ViewCard } from "aurelius-atlas-data-access";
import { Breadcrumbs, ClassificationChip, EntityCard, Markdown, PeopleBox, type PeopleRow } from "aurelius-atlas-ui";

import { nameDisplay } from "../meta/type-display";
import { typeIcon } from "../meta/type-icons";
import { PEOPLE_ENDS } from "../details/shared/people";
import { trailOf } from "./trail";

/** The relationship attribute the document's derived people arrive under (LAS-05). */
const PERSON_ATTRIBUTE = "m4i_person";

/**
 * The one rich card of both screens (VCF-01, DD-616): the 7.13 card shell
 * with the view-family card's body — the breadcrumb trail (the stored
 * `breadcrumb` plus the card's own crumb, `trailOf`'s rule shared with
 * the details header; the crumb of the entity being viewed is the
 * active one, DD-625), the classification chips (`classificationNames`,
 * DD-379's names), the description text (the card's `definition`, DD-614's
 * fallback included) as markdown, and the people rows: one labelled row
 * per role — Domain Lead(s), Data Owner(s), Data Steward(s) — from the
 * door's role relations (VCF-15, AVS-10, ASD-06), the flat "People" row
 * of 16.5d kept as the fallback for a document still awaiting its
 * re-derive round (VCF-16, DD-628).
 *
 * The results row and the details section card mount this one component
 * (VCF-05): the same entity cannot render differently on the two screens
 * twice. The badge carries no alias (the card shape has no `typeAlias`,
 * DV-167); the loading row is not this component's — DET-18's loading row
 * stays the plain shell's, owned by the sections store's caller.
 *
 * The part is dumb (DD-154's split): every title, crumb, and person click
 * emits the guid on `cardClicked` and the screen routes.
 */
@Component({
    selector: "aurelius-atlas-webapp-catalogue-card",
    imports: [Breadcrumbs, ClassificationChip, EntityCard, Markdown, PeopleBox],
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
            [typeIcon]="badgeIcon()?.icon"
            [typeIconClass]="badgeIcon()?.classIcon"
            [showQuality]="false"
            (entityClicked)="cardClicked.emit($event)"
        >
            <div card-content>
                <aurelius-atlas-ui-breadcrumbs
                    class="aurelius-card-trail"
                    [items]="trail()"
                    [activeGuid]="pageGuid() ?? card().guid"
                    (itemClicked)="cardClicked.emit($event)"
                />
                @if (classifications().length > 0) {
                    <div class="field is-grouped is-grouped-multiline">
                        @for (name of classifications(); track name) {
                            <div class="control">
                                <aurelius-atlas-ui-classification-chip [label]="name" />
                            </div>
                        }
                    </div>
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

    /** Emits the clicked card's, crumb's, or person's guid — the screen routes (DD-154). */
    readonly cardClicked = output<string>();

    /** The flat row's label — the dictionary's own derived-people name, "People" / "Personen". */
    private static readonly peopleLabel = $localize`:@@derivedperson:People`;

    /** The badge's type name (DET-26, DD-379): the dictionary display name, raw outside the dictionary. */
    protected readonly badgeName = computed(() => nameDisplay(this.card().typeName));

    /** The badge's icon (DET-26, DD-378): the app's type map; an unmapped type renders none. */
    protected readonly badgeIcon = computed(() => typeIcon(this.card().typeName));

    /** The card's trail (VCF-01): the stored breadcrumb plus its own active crumb (VDR-06's rule). */
    protected readonly trail = computed(() => trailOf(this.card(), (typeName) => typeIcon(typeName)));

    /** The chip labels (DD-379): the card's classification names, each by its dictionary display name. */
    protected readonly classifications = computed(() =>
        (this.card().classificationNames ?? [])
            .filter((name) => typeof name === "string" && name !== "")
            .map((name) => nameDisplay(name)),
    );

    /** The description text (VCF-03): the card's `definition`, DD-614's fallback already applied. */
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
