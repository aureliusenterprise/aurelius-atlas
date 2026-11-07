import { ChangeDetectionStrategy, Component, computed, inject, input, output } from "@angular/core";
import { Router } from "@angular/router";
import type { LineageModelMetadata } from "aurelius-atlas-data-access";
import { EntityCard, SortableTable, TableColumn, TableRow } from "aurelius-atlas-ui";

import { LINEAGE_ICON_PATHS, lineageClass } from "./lineage-shapes";
import type { LineageEntity } from "./lineage-entities";
import { mergeProperties } from "./lineage-entities";
import type { LineageIndexes } from "./lineage-indexes";
import { LineageEntityTable } from "./entity-table.component";
import { LineagePropertyTable } from "./property-table.component";

/**
 * The Selection tab (LDG-20/LDG-21/LDG-22): the legacy
 * `model-browser/selection` component ported, minus its two deferred parts —
 * the `MODEL_BROWSER_SELECTION_ADDONS` outlet (the Data governance addon,
 * 7.8's deferral) and the colour legend (7.22b's). Over the legacy's shape:
 *
 * - the Name / Type / Description fields, each hidden when empty (the
 *   legacy's `*ngIf` conditions); the Type row shows the icon of the two
 *   lineage types that have one (the legacy's archimate-icon, whose icon set
 *   names only `lineage_dataset`/`lineage_process`) plus the metamodel's
 *   human-readable name;
 * - the "Open this view" button (the legacy's `parserType === 'view'` row,
 *   kept: a view entity can be selected through the tables) — choosing it
 *   draws that view (LDG-23's rule, emitted);
 * - the Properties table: {@link mergeProperties} — the concept's own
 *   `ar3_properties` widened by the metadata row with the same id (the
 *   legacy's `{ ...properties, ...data }` over `dataByConceptId`); hidden
 *   when the merge is empty;
 * - the three reference tables over the LDG-22 indexes (Referenced concepts
 *   — the ends of a selected relation; Referencing concepts — the relations
 *   touching the selection), each hidden when empty;
 * - the Referencing views table (DD-412): the legacy's own shape — a Name /
 *   Description table (name in a `th scope="row"`), not the entities table,
 *   selectable, the drawn view the selected row, a row click drawing it (the
 *   legacy's `selectView`). The legacy's row-deselect clears the selected
 *   view; the shipped chain always draws one (LDG-12's first-view default),
 *   so a re-click of the selected row keeps the view — there is no "no view"
 *   state to return to;
 * - the grey ID line below the sections.
 *
 * A table row click selects that concept here too (the legacy's
 * `selectEntity`), closing nothing — the drawer stays on the Selection tab
 * with the new concept (LDG-25).
 *
 * A selected element gains the search card above the fields (DD-405): the
 * ui card the results screen rows, title-click routes to the entity's
 * details page — the convenient hop from a diagram box to the entity itself
 * the reader asked for (the shipped chain's element ids are the guids). The
 * LDG-20 fields stay; the card is the navigation, not a replacement.
 */
@Component({
    selector: "aurelius-atlas-webapp-lineage-selection",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [EntityCard, LineageEntityTable, LineagePropertyTable, SortableTable, TableColumn, TableRow],
    template: `
        @if (entity(); as selected) {
            @if (selected.kind === "element") {
                <!-- DD-405: the legacy results card, reused — its title click
                     opens the entity's details screen. -->
                <aurelius-atlas-ui-entity-card
                    class="aurelius-selection-card"
                    [guid]="selected.id"
                    [name]="selected.name"
                    [typeName]="selected.humanReadableType || selected.type"
                    [showIcon]="false"
                    (entityClicked)="openDetails($event)"
                />
            }
            @if (selected.name) {
                <div class="field">
                    <p class="label" i18n="@@modelview2.modelBrowser.selection.name">Name</p>
                    <p>{{ selected.name }}</p>
                </div>
            }
            @if (selected.humanReadableType || selected.type) {
                <div class="field">
                    <p class="label" i18n="@@modelview2.modelBrowser.selection.type">Type</p>
                    <p class="aurelius-selection-type">
                        @if (icon()) {
                            <span class="icon is-small" aria-hidden="true">
                                <svg width="16px" height="16px" viewBox="0 0 16 16">
                                    <path [attr.d]="icon()!" [class]="iconClass()"></path>
                                </svg>
                            </span>
                        }
                        <span>{{ selected.humanReadableType || selected.type }}</span>
                    </p>
                </div>
            }
            @if (selected.description) {
                <div class="field">
                    <p class="label" i18n="@@modelview2.modelBrowser.selection.description">Description</p>
                    <p>{{ selected.description }}</p>
                </div>
            }
            @if (selected.kind === "view") {
                <div class="field">
                    <button
                        type="button"
                        class="button is-link is-small aurelius-selection-open-view"
                        [class.is-static]="selected.id === drawnViewId()"
                        (click)="viewChosen.emit(selected.id)"
                    >
                        <span i18n="@@modelview2.modelBrowser.selection.openView">Open this view</span>
                    </button>
                </div>
            }
            @let rows = propertyRows();
            @if (rows.length > 0) {
                <div class="field">
                    <p class="label" i18n="@@modelview2.modelBrowser.selection.properties">Properties</p>
                    <aurelius-atlas-webapp-lineage-property-table [rows]="rows" />
                </div>
            }
            @let referenced = referencedConcepts();
            @if (referenced.length > 0) {
                <div class="field">
                    <p class="label" i18n="@@modelview2.modelBrowser.selection.referencedConcepts">
                        Referenced concepts
                    </p>
                    <aurelius-atlas-webapp-lineage-entity-table
                        [rows]="referenced"
                        [selectedEntity]="selected"
                        (chosen)="conceptChosen.emit($event)"
                    />
                </div>
            }
            @let referencing = referencingConcepts();
            @if (referencing.length > 0) {
                <div class="field">
                    <p class="label" i18n="@@modelview2.modelBrowser.selection.referencingConcepts">
                        Referencing concepts
                    </p>
                    <aurelius-atlas-webapp-lineage-entity-table
                        [rows]="referencing"
                        [selectedEntity]="selected"
                        (chosen)="conceptChosen.emit($event)"
                    />
                </div>
            }
            @let viewsHere = referencingViews();
            @if (viewsHere.length > 0) {
                <div class="field">
                    <p class="label" i18n="@@modelview2.modelBrowser.selection.referencingViews">Referencing views</p>
                    <!-- DD-412: the legacy's own Name | Description table
                         (viewsTableConfig) — the name in a row header, the
                         documentation beside it; the drawn view is the
                         selected row and a row click draws that view. The
                         headers are the legacy config's raw strings, which
                         its translate pipe never resolved. -->
                    <aurelius-atlas-ui-sortable-table
                        [rows]="viewsHere"
                        [pageSize]="5"
                        [rowsSelectable]="true"
                        [selectedRow]="selectedViewRow()"
                        (rowSelected)="viewChosen.emit($event.id)"
                    >
                        <ng-template aurelius-atlas-ui-table-column [sortBy]="'name'" [title]="viewNameHint">
                            Name
                        </ng-template>
                        <ng-template
                            aurelius-atlas-ui-table-column
                            [sortBy]="'description'"
                            [title]="viewDescriptionHint"
                        >
                            Description
                        </ng-template>
                        <ng-template aurelius-atlas-ui-table-row let-row>
                            <th class="truncate" scope="row" [title]="row.name">{{ row.name }}</th>
                            <td class="truncate" [title]="row.description">{{ row.description }}</td>
                        </ng-template>
                    </aurelius-atlas-ui-sortable-table>
                </div>
            }
            <!-- The legacy's ID line: the small light-grey line under the
                 sections (is-size-7 has-text-grey-light). -->
            <div class="field">
                <p class="is-size-7 has-text-grey-light has-text-weight-light aurelius-selection-id">
                    <!-- The literal legacy line: "ID:&nbsp;<guid>". -->
                    ID:&nbsp;{{ selected.id }}
                </p>
            </div>
        }
    `,
    styles: `
        .aurelius-selection-card {
            display: block;
            margin-bottom: 1rem;
        }
        .aurelius-selection-type {
            display: flex;
            align-items: center;
            gap: 0.4em;
        }
        .truncate {
            max-width: 1px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .aurelius-selection-type .icon .dataset {
            fill: blue;
            stroke: none;
        }
        .aurelius-selection-type .icon .process {
            fill: #00d1b2;
            stroke: none;
        }
    `,
})
export class LineageSelectionPanel {
    private readonly router = inject(Router);

    /** The selected concept's entity record (the legacy's `selectedEntity$`). */
    readonly entity = input<LineageEntity | null>(null);

    /** The answer's metadata rows (the legacy's `dataByConceptId` source). */
    readonly metadata = input<readonly LineageModelMetadata[]>([]);

    /** The three LDG-22 maps. */
    readonly indexes = input.required<LineageIndexes>();

    /** Every entity record, for the reference tables' id lookups. */
    readonly entities = input.required<ReadonlyMap<string, LineageEntity>>();

    /** The drawn view — the Open-this-view button's static state. */
    readonly drawnViewId = input<string | null>(null);

    /** A reference-table row click: select this concept (LDG-25). */
    readonly conceptChosen = output<string>();

    /** A view was chosen (the Open button, or a referencing-view row): draw it. */
    readonly viewChosen = output<string>();

    protected readonly propertyRows = computed(() => mergeProperties(this.entity(), this.metadata()));

    /** Referenced concepts (LDG-22): the ends of a selected relation. */
    protected readonly referencedConcepts = computed(() => this.resolve(this.indexes().conceptsByRelationId));

    /** Referencing concepts (LDG-22): the relations touching the selection. */
    protected readonly referencingConcepts = computed(() => this.resolve(this.indexes().relationsByConceptId));

    /** Referencing views (LDG-22): the views containing the selection. */
    protected readonly referencingViews = computed(() => this.resolve(this.indexes().viewsByEntityId));

    /** The drawn view's row in the Referencing views table (DD-412, the
        legacy's `selectedView$` over the same list); undefined for none. */
    protected readonly selectedViewRow = computed(() => {
        const id = this.drawnViewId();
        return id === null ? undefined : this.referencingViews().find((view) => view.id === id);
    });

    /** The legacy viewsTableConfig's raw hint strings. */
    protected readonly viewNameHint = "The name of the view";
    protected readonly viewDescriptionHint = "The view documentation";

    /** The Type row's icon (LDG-20): the two lineage types have one. */
    protected readonly icon = computed(() => {
        const entity = this.entity();
        if (entity === null) {
            return null;
        }
        const cssClass = lineageClass(entity.type);
        return cssClass === null ? null : LINEAGE_ICON_PATHS[cssClass];
    });

    protected readonly iconClass = computed(() => {
        const entity = this.entity();
        return entity === null ? "" : (lineageClass(entity.type) ?? "");
    });

    /**
     * The card's title click (DD-405): open the entity's details page — the
     * results screen's rule, `search/details/<guid>`; the shipped chain's
     * element ids are the Atlas guids.
     * @param guid the selected element's id
     */
    protected openDetails(guid: string): void {
        void this.router.navigate(["/search/details", guid]);
    }

    /** The map's ids under the selection, resolved to entities (the legacy's selectEntitiesById). */
    private resolve(map: ReadonlyMap<string, readonly string[]>): LineageEntity[] {
        const selected = this.entity();
        if (selected === null) {
            return [];
        }
        const ids = map.get(selected.id) ?? [];
        const entities = this.entities();
        return ids.map((id) => entities.get(id)).filter((entity): entity is LineageEntity => entity !== undefined);
    }
}
