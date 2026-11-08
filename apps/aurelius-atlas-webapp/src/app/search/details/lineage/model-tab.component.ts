import { ChangeDetectionStrategy, Component, computed, input, output, signal } from "@angular/core";
import { SearchField } from "aurelius-atlas-ui";

import type { LineageEntity } from "./lineage-entities";
import { LineageEntityTable } from "./entity-table.component";

/**
 * The Model tab (LDG-23): the legacy `model-browser/model` component ported,
 * with its `FuzzySearchInputComponent` replaced by the webapp's keyword filter
 * (DD-396, the DET-20 posture): a case-insensitive substring match on name
 * and human-readable type, narrowing both tables as the reader types (the
 * legacy tokenizer indexed those same two fields — plus id/description, which
 * carry nothing to match on the shipped chain).
 *
 * The two tables (Elements / Relationships — the legacy's headings and order)
 * list the model's elements and relations over the same selected-concept
 * signal as the Selection tab (LDG-25): a row click selects in the diagram.
 */
@Component({
    selector: "aurelius-atlas-webapp-lineage-model-tab",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [SearchField, LineageEntityTable],
    template: `
        <div class="field">
            <aurelius-atlas-ui-search-field
                class="is-fullwidth"
                [withSubmitButton]="false"
                [placeholder]="searchPlaceholder"
                [(query)]="query"
            ></aurelius-atlas-ui-search-field>
        </div>
        <div class="field">
            <p class="label" i18n="@@modelview2.modelBrowser.model.elements">Elements</p>
            <aurelius-atlas-webapp-lineage-entity-table
                [rows]="filteredElements()"
                [selectedEntity]="selectedEntity()"
                (chosen)="conceptChosen.emit($event)"
                (cleared)="cleared.emit()"
            />
        </div>
        <div class="field">
            <p class="label" i18n="@@modelview2.modelBrowser.model.relationships">Relationships</p>
            <aurelius-atlas-webapp-lineage-entity-table
                [rows]="filteredRelations()"
                [selectedEntity]="selectedEntity()"
                (chosen)="conceptChosen.emit($event)"
                (cleared)="cleared.emit()"
            />
        </div>
    `,
})
export class LineageModelTab {
    /** The model's element entities (the legacy's `Object.values(elements)`). */
    readonly elements = input<LineageEntity[]>([]);

    /** The model's relation entities. */
    readonly relations = input<LineageEntity[]>([]);

    /** The selected concept's record (LDG-25's one signal, projected); null for none. */
    readonly selectedEntity = input<LineageEntity | null>(null);

    /** The legacy fuzzy box's placeholder, carried by the vendored catalogue. */
    protected readonly searchPlaceholder = $localize`:@@components.fuzzySearchInput.searchPlaceholder:Search...`;

    /** A row click (LDG-25). */
    readonly conceptChosen = output<string>();

    /** The selected row clicked again — clear the selection. */
    readonly cleared = output<void>();

    /** The live keyword (DD-375's posture: the filter follows the typing). */
    protected readonly query = signal<string | null>(null);

    protected readonly filteredElements = computed(() => this.filter(this.elements()));

    protected readonly filteredRelations = computed(() => this.filter(this.relations()));

    /** The keyword filter (LDG-23): substring on name and type, case-insensitive. */
    private filter(rows: LineageEntity[]): LineageEntity[] {
        const keyword = (this.query() ?? "").trim().toLowerCase();
        if (keyword === "") {
            return rows;
        }
        return rows.filter(
            (row) => row.name.toLowerCase().includes(keyword) || row.humanReadableType.toLowerCase().includes(keyword),
        );
    }
}
