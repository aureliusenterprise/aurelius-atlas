import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";

import { SortableTable, TableColumn, TableRow } from "aurelius-atlas-ui";

import type { LineageEntity } from "./lineage-entities";

/**
 * The Model tab and Selection tab entity table (LDG-23, LDG-22): the legacy
 * `model-browser-entities-table` component ported. The legacy table pairs a
 * narrow Type column (an archimate icon over the raw `type` sort key) with a
 * Name column; the lineage chain's relations and views have no archimate icon
 * (only `lineage_dataset`/`lineage_process` exist in the legacy definitions),
 * so the Type column shows the metamodel name (LDG-20) instead — the same
 * value the Selection tab shows. The legacy's relationship row (source →
 * target) is dropped: the spec simplifies both tables to the name/type shape.
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
                <td class="is-narrow">{{ row.humanReadableType }}</td>
                <td class="truncate" [title]="row.name">{{ row.name }}</td>
            </ng-template>
        </aurelius-atlas-ui-sortable-table>
    `,
    styles: `
        .truncate {
            max-width: 1px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
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
}
