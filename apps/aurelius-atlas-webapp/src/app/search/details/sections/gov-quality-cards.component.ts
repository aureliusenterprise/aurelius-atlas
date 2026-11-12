import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faCheckCircle, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { EntityCard } from "aurelius-atlas-ui";

import { nameDisplay } from "../../meta/type-display";
import { typeIcon } from "../../meta/type-icons";
import type { GovQualityRow } from "./gov-quality.state";

/**
 * The rows of the Governance Quality Rules box (DET-42, DD-521): the dumb
 * half of the person page's `#gov-quality` box. One card per rule — the
 * 7.13 card with the rule's name as its link title and the badge of its
 * type — and the legacy card's body projected into its `card-content`
 * slot: the rule's description line, then the verdict line (the success or
 * warning icon of the rule's verdict for the opened record, then the rule's
 * dimension titlecased; no icon at no verdict, the unread rule of VEV-03).
 *
 * The state lives with the screen's store (`gov-quality.state.ts`); this
 * part knows nothing but the rows it is handed (the DD-136 split). A title
 * click emits `ruleClicked(guid)` — the screen routes, the part never does
 * (DET-06).
 */
@Component({
    imports: [EntityCard, FontAwesomeModule],
    selector: "aurelius-atlas-webapp-gov-quality-cards",
    template: `
        <div class="columns is-multiline">
            @for (row of rows(); track row.guid) {
                <!-- The grid's column sizing rides the DET-22 helpers:
                     three across on a desktop at most. -->
                <div class="column is-half-tablet is-one-third-desktop">
                    <aurelius-atlas-ui-entity-card
                        [guid]="row.guid"
                        [name]="row.name"
                        [typeName]="ruleTypeName"
                        [typeIcon]="ruleIcon?.icon"
                        [typeIconClass]="ruleIcon?.classIcon"
                        [showQuality]="false"
                        (entityClicked)="ruleClicked.emit($event)"
                    >
                        <div card-content class="aurelius-gov-quality-body">
                            @if (row.description !== "") {
                                <p class="aurelius-gov-quality-description">{{ row.description }}</p>
                            }
                            <p class="is-size-7 aurelius-gov-quality-verdict">
                                <span class="icon-text">
                                    @if (row.compliant !== null) {
                                        <span
                                            class="icon"
                                            [class.has-text-success]="row.compliant"
                                            [class.has-text-warning]="!row.compliant"
                                        >
                                            @if (row.compliant) {
                                                <fa-icon aria-hidden="true" [icon]="faCheckCircle"></fa-icon>
                                            } @else {
                                                <fa-icon aria-hidden="true" [icon]="faExclamationTriangle"></fa-icon>
                                            }
                                        </span>
                                    }
                                    @if (row.dimension !== "") {
                                        <span class="aurelius-gov-quality-dimension">{{
                                            titlecase(row.dimension)
                                        }}</span>
                                    }
                                </span>
                            </p>
                        </div>
                    </aurelius-atlas-ui-entity-card>
                </div>
            }
        </div>
    `,
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GovQualityCards {
    /** The box's rows, name-ordered by the store (DET-42). */
    readonly rows = input.required<readonly GovQualityRow[]>();

    /** Emits the clicked rule's guid — the screen routes (DET-06). */
    readonly ruleClicked = output<string>();

    protected readonly faCheckCircle = faCheckCircle;
    protected readonly faExclamationTriangle = faExclamationTriangle;

    /** The badge's type name: the rule type's dictionary name (DET-26's rule). */
    protected readonly ruleTypeName = nameDisplay("m4i_gov_data_quality");

    /** The badge's icon: the same type-to-icon map the cards ride. */
    protected readonly ruleIcon = typeIcon("m4i_gov_data_quality");

    /**
     * The dimension word, titlecased — the legacy card's `| titlecase`.
     * @param dimension the stored dimension, e.g. `COMPLETENESS`
     * @returns the word with its first letter upper, the rest lower
     */
    protected titlecase(dimension: string): string {
        return dimension.charAt(0).toUpperCase() + dimension.slice(1).toLowerCase();
    }
}
