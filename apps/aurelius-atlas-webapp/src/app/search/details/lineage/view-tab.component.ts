import { ChangeDetectionStrategy, Component, computed, input, output } from "@angular/core";
import { deriveCategoryLegend, type CategoryMap } from "aurelius-atlas-ui";
import type { LineageModelMetadata } from "aurelius-atlas-data-access";

import { SortableTable, TableColumn, TableRow } from "aurelius-atlas-ui";

import type { LineageEntity } from "./lineage-entities";
import { mergeProperties } from "./lineage-entities";
import { LineagePropertyTable } from "./property-table.component";

/**
 * The View tab (LDG-24, widened by UIC-31): the legacy `model-browser/view`
 * component narrowed to its kept sections — Name, Description, the
 * Properties table (the same LDG-21 merge over the view's metadata row),
 * and the Colour legend (7.22g, the legacy's `legendTableConfig`): one row
 * per category with its colour, each colour a picker the reader can
 * customise (the legacy's `updateLegendColor` — the whole category repaints
 * through the canvas's legend join). The table renders only when a colour
 * view exists — the legacy gated it on the legend, and the details page has
 * no bucketing producer today (DD-420), so it stays hidden until one
 * supplies categories. The legacy's palette select stays out (the
 * deviation table). The referenced/referencing-views tables stay out — the
 * lineage document places no views, so those two lists are empty for every
 * document this chain produces (LDG-22's map keys nodes, relations, and
 * their placements — never a view), and a table that cannot ever render is
 * not shipped.
 */
@Component({
    selector: "aurelius-atlas-webapp-lineage-view-tab",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [LineagePropertyTable, SortableTable, TableColumn, TableRow],
    template: `
        @if (view(); as drawn) {
            @if (drawn.name) {
                <div class="field">
                    <p class="label" i18n="@@modelview2.modelBrowser.view.name">Name</p>
                    <p>{{ drawn.name }}</p>
                </div>
            }
            @if (drawn.description) {
                <div class="field">
                    <p class="label" i18n="@@modelview2.modelBrowser.view.description">Description</p>
                    <p>{{ drawn.description }}</p>
                </div>
            }
            @let rows = propertyRows();
            @if (rows.length > 0) {
                <div class="field">
                    <p class="label" i18n="@@modelview2.modelBrowser.view.properties">Properties</p>
                    <aurelius-atlas-webapp-lineage-property-table [rows]="rows" />
                </div>
            }
            <!-- UIC-31: the legacy's legend table, rendered only when a
                 colour view exists (the legacy's *ngIf over the legend). The
                 picker is a native colour input styled as the legacy's
                 square (DD-420's zero-dependency deviation). -->
            @let legend = legendRows();
            @if (legend.length > 0) {
                <div class="field">
                    <p class="label" i18n="@@modelview2.modelBrowser.view.colorLegend">Color legend</p>
                    <aurelius-atlas-ui-sortable-table [rows]="legend" [pageSize]="6" [rowsSelectable]="false">
                        <ng-template aurelius-atlas-ui-table-column [sortBy]="'category'" [title]="categoryHint">
                            {{ categoryTitle }}
                        </ng-template>
                        <ng-template aurelius-atlas-ui-table-column [sortBy]="'color'" [title]="colorHint">
                            {{ colorTitle }}
                        </ng-template>
                        <ng-template aurelius-atlas-ui-table-row let-row>
                            <th scope="row" class="truncate" [title]="row.category">{{ row.category }}</th>
                            <td class="legend-color">
                                <input
                                    type="color"
                                    class="legend-swatch"
                                    [value]="row.color"
                                    [attr.aria-label]="row.category"
                                    (input)="onPick(row.category, $event)"
                                />
                            </td>
                        </ng-template>
                    </aurelius-atlas-ui-sortable-table>
                </div>
            }
        }
    `,
    styles: `
        .truncate {
            max-width: 1px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .legend-color {
            /* The legacy's view.component.scss: the square centred in its
               narrow cell. */
            text-align: center;
            vertical-align: middle;
        }
        .legend-swatch {
            /* The legacy's color-square look (a flat square, no chrome), on
               the native input. */
            inline-size: 24px;
            block-size: 24px;
            padding: 0;
            border: 1px solid var(--bulma-grey-light, #dbdbdb);
            background: none;
            cursor: pointer;
        }
    `,
})
export class LineageViewTab {
    /** The selected view's entity record (the legacy's `selectedView$`). */
    readonly view = input<LineageEntity | null>(null);

    /** The answer's metadata rows (LDG-21's merge input). */
    readonly metadata = input<readonly LineageModelMetadata[]>([]);

    /** The colour view's categories (UIC-31): concept id → category, the
        same map the canvas draws with. Empty or null keeps the legend
        hidden (the legacy's null legend). */
    readonly categories = input<CategoryMap | null>(null);

    /** The picked overrides (UIC-31): category → hex, what the reader has
        changed from the palette. */
    readonly categoryColors = input<CategoryMap | null>(null);

    /** The reader picked a new colour for a category (the legacy's
        `updateLegendColor`): the caller writes it so the canvas repaints. */
    readonly colorPicked = output<{ category: string; color: string }>();

    protected readonly propertyRows = computed(() => mergeProperties(this.view(), this.metadata()));

    /** The legend table's rows (UIC-31): the same join the canvas's fills
        read, so a row's colour is the colour its category draws with. */
    protected readonly legendRows = computed(() => {
        const legend = deriveCategoryLegend(this.categories(), this.categoryColors());
        return Object.entries(legend).map(([category, color]) => ({ category, color }));
    });

    /** The legacy legendTableConfig's raw header strings (the pattern the
        properties table set: the legacy's `displayName`s were never
        translated). */
    protected readonly categoryTitle = "Category";
    protected readonly colorTitle = "Color";
    protected readonly categoryHint = "The name of the category";
    protected readonly colorHint = "Concepts in the view with this color belong to the corresponding category";

    /** A swatch changed (UIC-31): hand the picked hex to the caller. */
    protected onPick(category: string, event: Event): void {
        const value = (event.target as HTMLInputElement).value;
        this.colorPicked.emit({ category, color: value });
    }
}
