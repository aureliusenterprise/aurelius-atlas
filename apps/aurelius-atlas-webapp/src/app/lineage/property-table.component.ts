import { ChangeDetectionStrategy, Component, input } from "@angular/core";

import { SortableTable, TableColumn, TableRow } from "aurelius-atlas-ui";

/**
 * The name/value properties table the Selection and View tabs share
 * (LDG-21, LDG-24): the legacy's `propertiesTableConfig` — Name / Value,
 * 5 per page, not selectable. The headers are the legacy config's raw
 * 'Name'/'Value' strings, which its translate pipe never resolved (the
 * entities table carries the same note).
 */
@Component({
    selector: "aurelius-atlas-webapp-lineage-property-table",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [SortableTable, TableColumn, TableRow],
    template: `
        <aurelius-atlas-ui-sortable-table [rows]="rows()" [pageSize]="5" [rowsSelectable]="false">
            <ng-template aurelius-atlas-ui-table-column [sortBy]="'name'" [title]="nameHint">
                {{ nameTitle }}
            </ng-template>
            <ng-template aurelius-atlas-ui-table-column [sortBy]="'value'" [title]="valueHint">
                {{ valueTitle }}
            </ng-template>
            <ng-template aurelius-atlas-ui-table-row let-row>
                <th scope="row" class="truncate" [title]="row.name">{{ row.name }}</th>
                <td class="truncate" [title]="row.value">{{ row.value }}</td>
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
export class LineagePropertyTable {
    /** The merged rows (LDG-21's output, key-sorted). */
    readonly rows = input<{ name: string; value: string }[]>([]);

    /** The legacy config's raw header strings. */
    protected readonly nameTitle = "Name";
    protected readonly valueTitle = "Value";
    protected readonly nameHint = "The name of the property";
    protected readonly valueHint = "The value of the property";
}
