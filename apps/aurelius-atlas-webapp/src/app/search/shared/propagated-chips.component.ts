//
// Aurelius Atlas - https://github.com/aurelius-atlas
// Licensed under the MIT License. See LICENSE file in the project root.
//
import { NgClass } from "@angular/common";
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
 * The row's name — icon and all — is one button, and the path is a real
 * trail with clickable crumbs, so every entity named in a row routes by
 * its own control (VDR-12). A button may not hold a link, which is why the
 * row itself is a container and not the button (DD-836). Each activation
 * is the mount's call — the header opens what was clicked, a card must not
 * also open itself — so this part emits the guid and stops the click from
 * bubbling any further.
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
    imports: [Breadcrumbs, ClassificationChip, FaIconComponent, NgClass],
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
                        <!-- The row is a container, not a button: the path's
                             crumbs are links the review asked to be clickable,
                             and a button may not hold a link (DD-836). The name
                             carries the icon and the whole source activation, so
                             the keyboard reaches the source through it (VDR-12).
                             Each control emits and stops: a crumb names its own
                             entity, and no click may also open the card. -->
                        <div class="dropdown-item aurelius-details-source" chip-sources>
                            <button
                                type="button"
                                class="aurelius-details-source-name"
                                [title]="nameOf(source)"
                                (click)="pick(source); $event.stopPropagation()"
                            >
                                @if (iconOf(source); as icon) {
                                    <span class="icon aurelius-details-source-icon">
                                        <fa-icon
                                            aria-hidden="true"
                                            [icon]="icon.icon"
                                            [ngClass]="icon.classIcon"
                                            [fixedWidth]="true"
                                        ></fa-icon>
                                    </span>
                                }
                                <span class="aurelius-details-source-name-text">{{ nameOf(source) }}</span>
                            </button>
                            @if (pathOf(source); as trail) {
                                <span class="aurelius-details-source-path">
                                    <aurelius-atlas-ui-breadcrumbs
                                        [items]="trail"
                                        (itemClicked)="crumbPicked($event)"
                                    />
                                </span>
                            }
                        </div>
                    }
                </aurelius-atlas-ui-classification-chip>
            </div>
        }
    `,
    styles: [
        `
            /* The chips are the mount's tag list, not a list of their own:
             * the mount seats them in a Bulma "field is-grouped" row beside
             * the entity's own chips, and only that row's children flex. With
             * a box of its own the host would be one flex item and each chip
             * would drop onto its own line, so the host takes no box and the
             * control wrappers become the row's items (VDR-12, DD-834). */
            :host {
                display: contents;
            }

            /* The menu is wider than Bulma's stock 12rem: a row carries a
             * name and a path, and the review asked for the box not to fold
             * them. The menu sizes from Bulma's own custom property, which
             * crosses the chip's style boundary by inheritance (the picker
             * box's menu had the same rule, DD-335). */
            .aurelius-propagated-chip {
                --bulma-dropdown-menu-min-width: 20rem;
            }

            /* A source row carries a name and a path on two lines: the name's
             * button takes the first line's full width (flex-basis 0, so even
             * the longest name clips instead of folding), and the path keeps
             * the second. The row's wide trailing gutter is for items with a
             * shortcut column, which these have not. */
            .aurelius-details-source {
                display: flex;
                flex-direction: column;
                align-items: stretch;
                gap: 0;
                padding-inline-end: 1rem;
                white-space: normal;
            }

            /* The name is the source's button (the keyboard path, VDR-12): the
             * icon rides inside it and the text clips to its line with the
             * full name in the tooltip, as the picker row's name does (EDT-33). */
            .aurelius-details-source-name {
                align-items: baseline;
                appearance: none;
                background: none;
                border: 0;
                color: inherit;
                cursor: pointer;
                display: flex;
                font: inherit;
                gap: 0 0.5rem;
                margin: 0;
                min-width: 0;
                padding: 0;
                text-align: start;
            }

            .aurelius-details-source-icon {
                flex-shrink: 0;
            }

            .aurelius-details-source-name-text {
                flex: 1 1 0;
                min-width: 0;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            /* The path rides its own line and clips instead of folding: the
             * trail's nowrap variable and the clip are the picker row's idiom
             * (DD-714), and the muted ink is what a card's trail never needed
             * but a menu row does. */
            .aurelius-details-source-path {
                --aurelius-breadcrumbs-wrap: nowrap;

                flex: 1 0 100%;
                font-size: 0.75rem;
                min-width: 0;
                opacity: 0.75;
                overflow: hidden;
            }

            /* The icon wears the legacy family ink (DET-26): the type map's
             * class arrives on it, as on a badge's or a crumb's — the
             * literals are the ones the badge's and crumb's styles keep. */
            .business {
                color: #ffa500;
            }

            .technical {
                color: #0000ff;
            }

            .technical-process {
                color: #00d1b2;
            }

            .meta {
                color: #b5b5b5;
            }

            /* The dark scheme (DD-156): the pure-blue technical ink is too
             * dark on the dark surface, the same lift the badge and the
             * crumb make. */
            :host-context([data-theme="dark"]) .technical {
                color: hsl(240, 100%, 75%);
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

    /** A clicked breadcrumb of a source's path: the mount routes it, as with a row. */
    protected crumbPicked(guid: string): void {
        this.sourceClicked.emit(guid);
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
