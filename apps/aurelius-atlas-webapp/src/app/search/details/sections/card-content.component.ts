import { ChangeDetectionStrategy, Component, computed, input, output } from "@angular/core";
import type { AtlasEntity } from "aurelius-atlas-data-access";
import { ClassificationChip, Markdown, PeopleBox } from "aurelius-atlas-ui";

import { cardDescription } from "../shared/card";
import { peopleRows } from "../shared/people";

/**
 * The uniform card body (DET-19, DD-367) — the block projected into the
 * 7.13 `entity-card`'s `[card-content]` slot: the classification chips
 * (one per entry of the entity's `classifications`, the 7.16 chip), the
 * description text (`definition` then `description`, the DET-10/DD-320
 * order) rendered by the ui `Markdown` and omitted when neither is a
 * string, and the people rows of the card entity's own
 * `relationshipAttributes` (the DET-23 grouping; the silent shape — no
 * placeholder line, the legacy card's `showPlaceholder` off).
 *
 * The legacy's per-type bodies led with a DQ column and a breadcrumb
 * trail, both without a source (DD-367, DD-369); what remains is the
 * same for every type, so one component draws all of them.
 */
@Component({
    selector: "aurelius-atlas-webapp-card-content",
    imports: [ClassificationChip, Markdown, PeopleBox],
    template: `
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
        @if (hasPeople()) {
            <aurelius-atlas-ui-people-box
                [rows]="people()"
                [showEmpty]="false"
                (personClicked)="personClicked.emit($event)"
            />
        }
    `,
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CardContent {
    /** The resolved card entity. */
    readonly entity = input.required<AtlasEntity>();

    /** Emits a clicked person's guid — the screen routes (DET-19). */
    readonly personClicked = output<string>();

    /** The chip labels (DET-19): the card entity's classifications. */
    protected readonly classifications = computed(() =>
        (this.entity().classifications ?? [])
            .filter((classification) => typeof classification?.typeName === "string" && classification.typeName !== "")
            .map((classification) => classification.typeName as string),
    );

    /** The description text (DET-19), or empty. */
    protected readonly description = computed(() => cardDescription(this.entity()));

    /** The card entity's own people rows (DET-19, the DET-23 grouping). */
    protected readonly people = computed(() => peopleRows(this.entity()));

    /** Whether any people row has a person — the block omits itself at none. */
    protected readonly hasPeople = computed(() => this.people().some((row) => row.people.length > 0));
}
