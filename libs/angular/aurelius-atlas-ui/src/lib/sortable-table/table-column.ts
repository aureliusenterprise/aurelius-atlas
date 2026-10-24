import { Directive, inject, input, TemplateRef } from "@angular/core";

/**
 * Sort directions the table cycles through, as `matSort` did.
 */
export type SortDirection = "asc" | "desc";

/**
 * Declares one header cell of `aurelius-atlas-ui-sortable-table`, projected
 * as an `ng-template` whose content becomes the `<th>` text — the ported
 * form of the Aurelius config object's `displayName` (DD-135): column names
 * are caller-localised content, not a component string.
 *
 * A column is sortable when `sortBy` names the row property to sort, and
 * static when it is unset — the Aurelius `isStatic` flag.
 */
@Directive({
    selector: "[aurelius-atlas-ui-table-column]",
    standalone: true,
})
export class TableColumn {
    /**
     * The header content, rendered by the table in this column's `<th>`.
     * A caller writes the column as `<ng-template aureliusAtlasUiTableColumn
     * sortBy="name">Name</ng-template>`, and the table injects the template.
     */
    readonly headerTemplate = inject(TemplateRef<unknown>);

    /**
     * The row property this column sorts by, as the Aurelius config key was.
     * Unset makes the header static (not sortable).
     */
    readonly sortBy = input<string>();

    /**
     * Hint shown when hovering the column name — the Aurelius config's
     * `description`. Caller-localised.
     */
    readonly title = input<string>();

    /**
     * Whether the column shrinks to fit its content, the Aurelius
     * `isNarrow` flag.
     */
    readonly isNarrow = input(false);
}

/**
 * Marker for the `ng-template` that renders one table row: its context is
 * the row, so `<ng-template aurelius-atlas-ui-table-row let-row>` projects
 * the `<td>` cells — the Aurelius shell's row `TemplateRef` (DD-135).
 */
@Directive({
    selector: "[aurelius-atlas-ui-table-row]",
    standalone: true,
})
export class TableRow<T> {
    /**
     * The row template, read by the table for its `ngTemplateOutlet`.
     */
    readonly templateRef = inject(TemplateRef<{ $implicit: T; index: number }>);

    /**
     * Type the `let-row` context for consumers.
     */
    static ngTemplateContextGuard<T>(_dir: TableRow<T>, _ctx: unknown): _ctx is { $implicit: T; index: number } {
        return true;
    }
}
