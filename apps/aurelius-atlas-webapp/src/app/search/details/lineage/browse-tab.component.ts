import { ChangeDetectionStrategy, Component, computed, input, model, output } from "@angular/core";
import { Select } from "aurelius-atlas-ui";

import type { LineageEntity } from "./lineage-entities";

/** A dropdown row: a view of the model, keyed by id (the ui Select's row). */
type ViewRow = { id: string; name: string; [key: string]: unknown };

/**
 * The Browse tab (LDG-23): the legacy `model-browser/browse` component
 * ported down to its view dropdown — the organization folder tree stays out
 * (DD-395: the lineage document's folders are fixed and one dropdown reaches
 * the one view). The ui Select in its plain-dropdown shape (the settings
 * panel's precedent, searchVisible off): the legacy's search-modal opener
 * served a repository with many views; here the option list IS the whole
 * choice.
 *
 * The dropdown lists every view of the model by name; the drawn view reads
 * back as the control's value (the legacy's `viewId` → control sync), and
 * choosing a row emits it — the viewer re-draws and the panel closes
 * (LDG-25).
 */
@Component({
    selector: "aurelius-atlas-webapp-lineage-browse-tab",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [Select],
    template: `
        <div class="field aurelius-browse-view-select">
            <aurelius-atlas-ui-select
                [options]="viewRows()"
                displayField="name"
                [value]="selectedRow()"
                [label]="label"
                [nullInputMessage]="nullMessage"
                [noDataMessage]="noDataMessage"
                [searchVisible]="false"
                (valueChange)="onPicked($event)"
            ></aurelius-atlas-ui-select>
        </div>
    `,
})
export class LineageBrowseTab {
    /** The model's view entities, in document order. */
    readonly views = input<LineageEntity[]>([]);

    /** The drawn view id (the legacy's `viewId`, one-way into the control). */
    readonly drawnViewId = input<string | null>(null);

    /** A row was chosen: the viewer draws it (LDG-23/LDG-25). */
    readonly viewChosen = output<string>();

    protected readonly label = $localize`:@@modelview2.modelBrowser.browse.viewSelect.label:View`;
    protected readonly nullMessage = $localize`:@@modelview2.modelBrowser.browse.viewSelect.nullInputMessage:No view selected`;
    protected readonly noDataMessage = $localize`:@@modelview2.modelBrowser.browse.viewSelect.noDataMessage:No views available`;

    /** The dropdown rows (the legacy's displayField 'name'). */
    protected readonly viewRows = computed<ViewRow[]>(() =>
        this.views().map((view) => ({ id: view.id, name: view.name })),
    );

    /**
     * The control's row: the drawn view's row, or null for the placeholder.
     * The object identity must be stable across change detection or the
     * select's strict-equality compare loses the value (DD-155) — so the row
     * comes from `viewRows()`, computed once per model, not rebuilt here.
     */
    protected readonly selectedRow = computed(() => {
        const drawn = this.drawnViewId();
        return drawn === null ? null : (this.viewRows().find((row) => row.id === drawn) ?? null);
    });

    protected onPicked(row: ViewRow | null): void {
        if (row !== null) {
            this.viewChosen.emit(row.id);
        }
    }
}
