import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";

import { SortableTable, TableColumn, TableRow } from "aurelius-atlas-ui";

import { LINEAGE_ICON_PATHS, lineageClass } from "./lineage-shapes";
import { relationVerb } from "./lineage-metamodel";
import type { LineageEntity } from "./lineage-entities";

/**
 * The Model tab and Selection tab entity table (LDG-23, LDG-22, DD-411): the
 * legacy `model-browser-entities-table` component ported row for row. The
 * legacy table pairs a narrow Type column holding the element's archimate
 * icon with a Name column; only `lineage_dataset`/`lineage_process` have an
 * icon in the legacy's set, so any other type's cell draws nothing — as the
 * legacy's icon component did for an unknown type. A relationship row is one
 * cell across both columns (`colspan`, the legacy's) with three lines: the
 * source end (icon + bold name), the middle `<em>` line (the relation's
 * name, or the verb its type carries — the legacy relationship row's
 * `name || displayName` — with the human-readable type in parentheses), and
 * the target end. The Type column still sorts on `humanReadableType`: the
 * legacy's `type` sort key was the raw `@xsi_type`, which the shipped chain's
 * rows carry too — the metamodel name keeps the header honest about what the
 * comparison means (an unportable detail: the legacy sorted the raw type).
 *
 * A row click selects the concept (LDG-25); clicking the selected row again
 * clears it (the legacy's `rowDeselected` → `deleteConceptSelection`). The
 * headers are the legacy's raw config strings ('Type', 'Name'), which its
 * translate pipe never resolved — they read as English in the legacy's Dutch
 * UI too, so they carry no catalogue key here either.
 */
@Component({
    selector: "aurelius-atlas-webapp-lineage-entity-table",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [SortableTable, TableColumn, TableRow],
    template: `
        <aurelius-atlas-ui-sortable-table
            [rows]="rows()"
            [pageSize]="5"
            [rowsSelectable]="true"
            [selectedRow]="selectedEntity() ?? undefined"
            (rowSelected)="onSelected($event)"
            (rowDeselected)="cleared.emit()"
        >
            <ng-template
                aurelius-atlas-ui-table-column
                [isNarrow]="true"
                [sortBy]="'humanReadableType'"
                [title]="typeHint"
            >
                {{ typeTitle }}
            </ng-template>
            <ng-template aurelius-atlas-ui-table-column [sortBy]="'name'" [title]="nameHint">
                {{ nameTitle }}
            </ng-template>
            <ng-template aurelius-atlas-ui-table-row let-row>
                @if (row.kind === "relation") {
                    <!-- DD-411: the legacy's relationship row — one cell across
                         both columns, the two ends each with their icon, and
                         the em line between them. A missing end (an edge into
                         a model that does not hold it) keeps the legacy's
                         shape: its div stays, with only the name cell's text
                         gone — the shipped chain always holds both ends. -->
                    <td colspan="2">
                        <!-- The legacy relationship-row component's host: the
                             three lines stack in a centered column. -->
                        <div class="aurelius-relation-row">
                            @if (row.sourceName !== "") {
                                <div
                                    class="level is-mobile is-marginless aurelius-relation-end"
                                    [title]="row.sourceName"
                                >
                                    <span class="icon is-small">
                                        @if (endIcon(row.sourceType); as path) {
                                            <svg width="16px" height="16px" viewBox="0 0 16 16" aria-hidden="true">
                                                <path [attr.d]="path" [class]="endClass(row.sourceType)"></path>
                                            </svg>
                                        }
                                    </span>
                                    <strong class="truncate">{{ row.sourceName }}</strong>
                                </div>
                            }
                            <p>
                                <em>
                                    @if (relationLabel(row); as label) {
                                        <span class="truncate" [title]="label">{{ label }}</span>
                                    }
                                    <!-- The nbsp stands for the space between the
                                         legacy template's two spans ("Flows into
                                         (Data Lineage)") — Angular's whitespace
                                         handling would eat a plain one. -->
                                    <span>&nbsp;({{ row.humanReadableType || row.type }})</span>
                                </em>
                            </p>
                            @if (row.targetName !== "") {
                                <div
                                    class="level is-mobile is-marginless aurelius-relation-end"
                                    [title]="row.targetName"
                                >
                                    <span class="icon is-small">
                                        @if (endIcon(row.targetType); as path) {
                                            <svg width="16px" height="16px" viewBox="0 0 16 16" aria-hidden="true">
                                                <path [attr.d]="path" [class]="endClass(row.targetType)"></path>
                                            </svg>
                                        }
                                    </span>
                                    <strong class="truncate">{{ row.targetName }}</strong>
                                </div>
                            }
                        </div>
                    </td>
                } @else {
                    <!-- The legacy's element row: the narrow icon cell — the
                         archimate icon for the two lineage types, nothing for
                         a type the legacy set has none for — and the name. -->
                    <td class="is-narrow">
                        <span class="icon is-small">
                            @if (endIcon(row.type); as path) {
                                <svg width="16px" height="16px" viewBox="0 0 16 16" aria-hidden="true">
                                    <path [attr.d]="path" [class]="endClass(row.type)"></path>
                                </svg>
                            }
                        </span>
                    </td>
                    <td class="truncate" [title]="row.name">{{ row.name }}</td>
                }
            </ng-template>
        </aurelius-atlas-ui-sortable-table>
    `,
    styles: `
        .truncate {
            /* The legacy's own cap (its shell/row styles) — not the
               max-width: 1px table trick, which collapses a flex child to a
               sliver: the ends live inside Bulma's flex .level and vanished. */
            max-width: 12rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .aurelius-relation-row {
            /* The legacy relationship-row component's host: a centered
               column — the three lines stack, centered in the cell. */
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .aurelius-relation-end .icon {
            margin-right: 0.4em;
        }
        .icon .dataset {
            fill: blue;
            stroke: none;
        }
        .icon .process {
            fill: #00d1b2;
            stroke: none;
        }
    `,
})
export class LineageEntityTable {
    /** The rows — the entities to list. */
    readonly rows = input<LineageEntity[]>([]);

    /** The entity holding the selection (the legacy's `selectedEntity$`); null for none. */
    readonly selectedEntity = input<LineageEntity | null>(null);

    /** A row click (LDG-25): the clicked entity's concept id. */
    readonly chosen = output<string>();

    /** The selected row clicked again (the legacy's deselect affordance). */
    readonly cleared = output<void>();

    /** The legacy config's raw header strings (never translated — see above). */
    protected readonly typeTitle = "Type";
    protected readonly nameTitle = "Name";
    protected readonly typeHint = "The type of the entity";
    protected readonly nameHint = "The name of the entity";

    protected onSelected(row: LineageEntity): void {
        this.chosen.emit(row.id);
    }

    /**
     * The archimate-icon path of a type (DD-411): the two lineage types have
     * one (LDG-13's shapes); an unknown type draws nothing, as the legacy's
     * icon component did when its definitions had no entry.
     * @param type an entity or relation-end type
     */
    protected endIcon(type: string): string | null {
        const cssClass = lineageClass(type);
        return cssClass === null ? null : LINEAGE_ICON_PATHS[cssClass];
    }

    /**
     * The icon's fill class (LDG-13: blue dataset, `#00d1b2` process).
     * @param type an entity or relation-end type
     */
    protected endClass(type: string): string {
        return lineageClass(type) ?? "";
    }

    /**
     * The middle line's leading word (DD-411): the relation's own name, or
     * the verb its type carries (the legacy relationship row's
     * `name || displayName`). Empty hides the span, as the legacy's `*ngIf`
     * hid it — only the parenthesised type is left.
     * @param row the relation row
     */
    protected relationLabel(row: LineageEntity): string {
        return row.name !== "" ? row.name : relationVerb(row.type);
    }
}
