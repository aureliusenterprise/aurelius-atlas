/// <reference types="@angular/localize" />
import { CommonModule } from "@angular/common";
import {
    ChangeDetectionStrategy,
    Component,
    computed,
    contentChildren,
    ElementRef,
    effect,
    inject,
    input,
    model,
    output,
    signal,
} from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faArrowsUpDown, faArrowDown, faArrowUp, faSpinner } from "@fortawesome/free-solid-svg-icons";

import { Pagination } from "../pagination/pagination.component";
import { SortDirection, TableColumn, TableRow } from "./table-column";

/** Instance counter for the row-select hint's id (TABLE-003): two tables on one page must not share it. */
let sortableTableInstances = 0;

/**
 * The Aurelius sortable table (`sortable-table-shell` + `sortable-table`),
 * ported without `@angular/material`, `ngx-pagination`, or the redux store
 * service (DD-135, UIC-05): sort, page, and selection are `model()` state,
 * paging reuses `Pagination`, and sorting is header clicks.
 *
 * Columns are `ng-template` blocks with the `aurelius-atlas-ui-table-column`
 * directive and rows render through the `aurelius-atlas-ui-table-row`
 * template, so a caller declares each column's content once and the table
 * clones it per row. Header text is caller content (DD-136).
 */
@Component({
    selector: "aurelius-atlas-ui-sortable-table",
    // TableColumn/TableRow are applied by the *caller's* template — the
    // column/row ng-templates are projected content, queried by token below —
    // so they are not imports here (NG8113 flags directives a component's own
    // template never applies; the webapp build surfaces this once the table
    // is first compiled by an app, in the 7.5 landing slice).
    imports: [CommonModule, FontAwesomeModule, Pagination],
    templateUrl: "./sortable-table.component.html",
    styleUrl: "./sortable-table.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SortableTable<T extends Record<string, unknown>> {
    /**
     * The rows. The Aurelius shell's `data` input, sorted and paged by the
     * table itself.
     */
    readonly rows = input<T[]>([]);

    /**
     * Property the rows are sorted by, `undefined` for the source order.
     * Two-way bindable, the Aurelius `sort.active` half.
     */
    readonly sortBy = model<string | undefined>(undefined);

    /**
     * Direction of the sort. Two-way bindable, the Aurelius `sort.direction`
     * half. Meaningless while `sortBy` is unset.
     */
    readonly sortDirection = model<SortDirection>("asc");

    /**
     * The 0-based page shown. Two-way bindable, the Aurelius `currentPage`.
     */
    readonly pageIndex = model(0);

    /**
     * The rows on one page, as the Aurelius `itemsPerPage` was.
     */
    readonly pageSize = input(10);

    /**
     * Whether a row click selects the row, as the Aurelius `rowsSelectable`
     * was. Selection toggles: clicking the selected row deselects it.
     */
    readonly rowsSelectable = input(true);

    /**
     * The selected row, `undefined` for none. Two-way bindable, the Aurelius
     * `selectedRow`.
     */
    readonly selectedRow = model<T | undefined>(undefined);

    /**
     * Total row count when the caller pages on the server, the Aurelius
     * `totalItems`. Unset means all `rows()` render on the client, paged
     * locally.
     */
    readonly totalItems = input<number>();

    /**
     * Show the table in the Bulma `table-container` wrapper, which scrolls
     * horizontally. The Aurelius `enableTableContainer`, defaulting to true.
     */
    readonly enableTableContainer = input(true);

    /**
     * Whether the table is loading. The Aurelius shell had no loading state
     * (callers showed a page spinner); a table-level one lets a slice show
     * it without dimming the chrome, and the empty markup carries the label.
     */
    readonly loading = input(false);

    /**
     * Accessible name of the empty-table message, the Aurelius `noData`
     * chrome string (DD-136). A caller passes a localised string.
     */
    readonly emptyLabel = input("No data available");

    /**
     * A short table caption for screen readers (TABLE-001), rendered as a
     * visually-hidden `<caption>`. Unset renders no caption element at all
     * — the header row is already the table's accessible structure. Like
     * the other chrome labels, a caller passes a localised string.
     */
    readonly caption = input<string>();

    /**
     * Emits the row when a row is clicked, the Aurelius `rowClicked`.
     */
    readonly rowClicked = output<T>();

    /**
     * Emits the row when it becomes selected, the Aurelius `rowSelected`.
     */
    readonly rowSelected = output<T>();

    /**
     * Emits when the selection is cleared, the Aurelius `rowDeselected`.
     */
    readonly rowDeselected = output<void>();

    /**
     * Emits the new 0-based page, the Aurelius `pageChanged`.
     */
    readonly pageChanged = output<number>();

    /** TABLE-003: per-instance id of the hidden hint the focusable rows point at. */
    protected readonly selectHintId = `aurelius-sortable-table-select-hint-${(sortableTableInstances += 1)}`;

    /**
     * TABLE-005: the text of the persistent live region (WCAG 4.1.3) — the
     * empty state, the loaded count, the sort change, and the selection.
     * Empty until something happens; the region itself never leaves the DOM.
     */
    protected readonly liveMessage = signal("");

    private readonly element = inject(ElementRef);

    protected readonly faArrowDown = faArrowDown;
    protected readonly faArrowUp = faArrowUp;
    protected readonly faArrowsUpDown = faArrowsUpDown;
    protected readonly faSpinner = faSpinner;

    constructor() {
        // TABLE-005: `loading` and `rows` flip under the caller's hand, so
        // those announcements come from an effect comparing the previous
        // run (the first run stays quiet); sort and selection announce
        // through the handlers below.
        let first = true;
        let wasLoading = false;
        let wasCount = 0;
        effect(() => {
            const loading = this.loading();
            const count = this.rows().length;
            if (!first && !loading) {
                if (count === 0 && (wasLoading || wasCount > 0)) {
                    this.liveMessage.set(this.emptyLabel());
                } else if (wasLoading && count > 0) {
                    this.liveMessage.set($localize`:@@components.sortableTable.rowsLoaded:${count}:count: rows loaded`);
                }
            }
            first = false;
            wasLoading = loading;
            wasCount = count;
        });
    }

    protected readonly headerColumns = contentChildren(TableColumn, { descendants: true, read: TableColumn });
    protected readonly rowTemplates = contentChildren(TableRow, { descendants: true, read: TableRow });
    protected readonly rowTemplate = computed(() => this.rowTemplates()[0]?.templateRef);

    /**
     * The rows in the current sort order: the Aurelius service's
     * `handleSort` — the same `<` compare over the sorted property, source
     * order while unsorted, ties kept in source order.
     */
    protected readonly sortedRows = computed(() => {
        const rows = this.rows();
        const key = this.sortBy();
        if (!key) {
            return rows;
        }
        const factor = this.sortDirection() === "asc" ? 1 : -1;
        return rows
            .map((row, index) => ({ row, index }))
            .sort((a, b) => {
                const left = a.row[key] as number | string;
                const right = b.row[key] as number | string;
                if (left === right) {
                    return a.index - b.index;
                }
                return (left < right ? -1 : 1) * factor;
            })
            .map((entry) => entry.row);
    });

    /**
     * The rows of the current page: client-side paging (the Aurelius
     * `paginate` pipe) over `sortedRows`; server-paged callers slice
     * themselves, so `rows()` are the page.
     */
    protected readonly pageRows = computed(() => {
        if (this.totalItems() !== undefined) {
            return this.sortedRows();
        }
        const start = this.pageIndex() * this.pageSize();
        return this.sortedRows().slice(start, start + this.pageSize());
    });

    /**
     * Rows counted for pagination: the server total when set, else the
     * client's sorted row count.
     */
    protected readonly paginatedTotal = computed(() => this.totalItems() ?? this.sortedRows().length);

    /**
     * Toggle the row selection as the Aurelius shell did: clicking the
     * selected row deselects it, and every click emits `rowClicked`.
     * @param row The clicked row.
     */
    protected onRowClicked(row: T): void {
        this.rowClicked.emit(row);
        if (!this.rowsSelectable()) {
            return;
        }
        if (this.selectedRow() === row) {
            this.selectedRow.set(undefined);
            this.rowDeselected.emit();
            // TABLE-003: the live region says what the class swap cannot.
            this.liveMessage.set($localize`:@@components.sortableTable.selectionCleared:Selection cleared`);
        } else {
            this.selectedRow.set(row);
            this.rowSelected.emit(row);
            this.liveMessage.set($localize`:@@components.sortableTable.rowSelected:Row selected`);
        }
    }

    /**
     * Cycle a column's sort: unset → ascending → descending → ascending, the
     * `matSort` cycle, over the Aurelius property compare.
     * @param key The property to sort by.
     */
    protected onHeaderClicked(key: string | undefined): void {
        if (!key) {
            return;
        }
        if (this.sortBy() !== key) {
            this.sortBy.set(key);
            this.sortDirection.set("asc");
        } else {
            this.sortDirection.update((direction) => (direction === "asc" ? "desc" : "asc"));
        }
        // TABLE-005: say what the header click did.
        this.liveMessage.set(this.sortAnnouncement(key));
    }

    /**
     * The live-region line for a sort change (TABLE-005). The column's own
     * header text is read back from the rendered `<th>` so the announcement
     * names what the user sees, with the property key as the fallback.
     * @param key The column just sorted.
     * @returns The localised announcement.
     */
    private sortAnnouncement(key: string): string {
        const index = this.headerColumns().findIndex((column) => column.sortBy() === key);
        const cell = (this.element.nativeElement as HTMLElement).querySelectorAll("thead th")[index];
        const header = cell?.textContent?.trim() || key;
        const direction =
            this.sortDirection() === "asc"
                ? $localize`:@@components.sortableTable.ascending:ascending`
                : $localize`:@@components.sortableTable.descending:descending`;
        return $localize`:@@components.sortableTable.sortedBy:Sorted by ${header}:header:, ${direction}:direction:`;
    }

    /**
     * The `aria-sort` value of a column's header cell, the ARIA form of the
     * `matSort` state. TABLE-006: only the active column carries it — a
     * `none` on every other header turns a screen-reader column sweep into
     * noise, and omitting the attribute is the ARIA-accurate "no sort".
     * @param key The column's `sortBy`.
     * @returns `ascending` or `descending` for the active column, `null` to omit.
     */
    protected ariaSort(key: string | undefined): "ascending" | "descending" | null {
        if (!key || this.sortBy() !== key) {
            return null;
        }
        return this.sortDirection() === "asc" ? "ascending" : "descending";
    }

    /**
     * The icon of a header: neutral when the column is unsorted, the
     * direction arrow when it is active — the caret `matSort` rendered.
     * @param key The column's `sortBy`.
     * @returns The icon definition to render.
     */
    protected sortIcon(key: string | undefined) {
        if (!key || this.sortBy() !== key) {
            return this.faArrowsUpDown;
        }
        return this.sortDirection() === "asc" ? this.faArrowUp : this.faArrowDown;
    }

    /**
     * Handle a page change from the `Pagination` control, as the Aurelius
     * shell's `(pageChange)` did.
     * @param index The new 0-based page.
     */
    protected onPageChanged(index: number): void {
        this.pageIndex.set(index);
        this.pageChanged.emit(index);
    }
}
