//
// Aurelius Atlas - https://github.com/aurelius-atlas
// Licensed under the MIT License. See LICENSE file in the project root.
//
import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";
import { FaIconComponent } from "@fortawesome/angular-fontawesome";
import type { RelationEntity } from "aurelius-atlas-data-access";
import { Breadcrumbs, ClassificationChip } from "aurelius-atlas-ui";

import { typeIcon } from "../meta/type-icons";
import { trailOf } from "./trail";

/**
 * The propagated-classification chips of the view family (VDR-12, DD-836): one
 * marked chip per propagated tag, whose dropdown lists the entities the tag
 * came from. The details header (VDR-12) and the shared rich card (VCF-01 as
 * amended by DD-836) draw the same thing, so the whole control lives here once
 * — a card that invented its own row would read differently from the header it
 * came from.
 *
 * Each source row shows what a card line shows: the type icon, the name,
 * and the path it sits on in place of its type name (the review asked for
 * the breadcrumb where the type stood). A source with no stored parent
 * keeps the plain name, as the trail rule draws no crumb for one (DD-630).
 * The rows are buttons, not links: clicking one is the mount's call — the
 * header opens the source, a card must not also open itself — so this part
 * emits the pick and stops the row click from bubbling any further.
 */

/** One propagated chip: the classification's label plus the entities it came from. */
export interface PropagatedChipEntry {
    /** The tag label, the classification's dictionary display name. */
    readonly label: string;
    /** The entities the tag was propagated from, door order; empty when the store lost them. */
    readonly sources: RelationEntity[];
}

@Component({
    selector: "aurelius-atlas-webapp-propagated-chips",
    imports: [Breadcrumbs, ClassificationChip, FaIconComponent],
    template: `
        @for (entry of entries(); track entry.label) {
            <div class="control aurelius-propagated-chip">
                <aurelius-atlas-ui-classification-chip
                    [label]="entry.label"
                    [propagated]="true"
                    [propagatedLabel]="propagatedLabel"
                    [originLabel]="originLabel"
                >
                    @for (source of entry.sources; track source.guid) {
                        <button
                            type="button"
                            class="dropdown-item aurelius-details-source"
                            chip-sources
                            (click)="pick(source); $event.stopPropagation()"
                        >
                            @if (iconOf(source); as icon) {
                                <span class="icon aurelius-details-source-icon">
                                    <fa-icon aria-hidden="true" [icon]="icon.icon" [fixedWidth]="true"></fa-icon>
                                </span>
                            }
                            <span class="aurelius-details-source-name">{{ nameOf(source) }}</span>
                            @if (pathOf(source); as trail) {
                                <span class="aurelius-details-source-path">
                                    <aurelius-atlas-ui-breadcrumbs [items]="trail" [links]="false" />
                                </span>
                            }
                        </button>
                    }
                </aurelius-atlas-ui-classification-chip>
            </div>
        }
    `,
    styles: [
        `
            /* A source row carries an icon, a name and a path, so it wraps
             * across lines instead of squeezing them — a card's menu is as
             * narrow as its card. Only the menu's defaults that fit a one-word
             * entry are eased here, as the header's rows had them: the names
             * are long and wrap, and the menu's wide trailing gutter is for
             * items with a shortcut column, which these have not. */
            .aurelius-details-source {
                display: flex;
                flex-wrap: wrap;
                align-items: baseline;
                gap: 0 0.5rem;
                padding-inline-end: 1rem;
                white-space: normal;
            }

            .aurelius-details-source-name {
                flex: 1 1 auto;
                min-width: 0;
                overflow-wrap: anywhere;
            }

            /* The path sits under the name, as the type line did: the row is
             * two lines, and the path takes the weak ink. */
            .aurelius-details-source-path {
                flex: 1 0 100%;
                opacity: 0.75;
            }
        `,
    ],
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PropagatedChips {
    /** The propagated chips to draw, in tag order. */
    readonly entries = input.required<PropagatedChipEntry[]>();

    /** The source whose row was clicked — the mount routes it, the part does not. */
    readonly sourceClicked = output<string>();

    /** The chip trigger's title and dropdown lead line (UIC-20's bridge key). */
    protected readonly propagatedLabel = $localize`:@@search.components.classification.isPropagated:Is propagated`;

    /** The dropdown's origin line (UIC-20's bridge key, `originates`). */
    protected readonly originLabel = $localize`:@@search.components.classification.originates:originates from the following sources:`;

    protected pick(source: RelationEntity): void {
        this.sourceClicked.emit(source.guid);
    }

    /** The source type's icon from the app map, or nothing for an unmapped type (DET-26). */
    protected iconOf(source: RelationEntity): ReturnType<typeof typeIcon> {
        return typeIcon(source.typeName ?? "");
    }

    /** The source's name, falling back to its type then its guid as a card line does (LAS-04). */
    protected nameOf(source: RelationEntity): string {
        return source.name || source.typeName || source.guid;
    }

    /**
     * The path the source sits on — the stored parents, top down — or nothing
     * when it has no stored parent, the trail rule of the cards and the
     * header (VDR-06, DD-630). The source's own crumb is left off: the row
     * already shows its name, and the legacy row put the type where the path
     * now stands, never the entity twice (DD-836).
     */
    protected pathOf(source: RelationEntity) {
        const trail = trailOf(
            {
                guid: source.guid,
                name: source.name ?? undefined,
                typeName: source.typeName ?? "",
                breadcrumb: source.breadcrumb ?? undefined,
            },
            typeIcon,
        );
        return trail.length > 1 ? trail.slice(0, -1) : null;
    }
}
