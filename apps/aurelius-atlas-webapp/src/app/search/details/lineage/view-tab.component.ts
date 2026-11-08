import { ChangeDetectionStrategy, Component, computed, input } from "@angular/core";
import type { LineageModelMetadata } from "aurelius-atlas-data-access";

import type { LineageEntity } from "./lineage-entities";
import { mergeProperties } from "./lineage-entities";
import { LineagePropertyTable } from "./property-table.component";

/**
 * The View tab (LDG-24): the legacy `model-browser/view` component narrowed
 * to its three kept sections — Name, Description, and the Properties table
 * (the same LDG-21 merge over the view's metadata row). The legacy's other
 * parts stay out: the colour legend and palette (7.22b's deferral) and the
 * referenced/referencing-views tables — the lineage document places no views,
 * so those two lists are empty for every document this chain produces
 * (LDG-22's map keys nodes, relations, and their placements — never a view),
 * and a table that cannot ever render is not shipped.
 */
@Component({
    selector: "aurelius-atlas-webapp-lineage-view-tab",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [LineagePropertyTable],
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
        }
    `,
})
export class LineageViewTab {
    /** The selected view's entity record (the legacy's `selectedView$`). */
    readonly view = input<LineageEntity | null>(null);

    /** The answer's metadata rows (LDG-21's merge input). */
    readonly metadata = input<readonly LineageModelMetadata[]>([]);

    protected readonly propertyRows = computed(() => mergeProperties(this.view(), this.metadata()));
}
