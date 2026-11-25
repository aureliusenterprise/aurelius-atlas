import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";
import { Accordion, PropertiesItem } from "aurelius-atlas-ui";

import { type DetailProperty } from "./property-filter";

/**
 * The properties accordion (DET-11): the opened entity's attributes as the
 * legacy `sortable-table-shell` swap inside an expandable box — with rows, the
 * two-column table (a Key header, a Value header, one row per attribute, each
 * value the shared property-value renderer); with none, the "No data available"
 * line in place of the whole table, headers included. Zero rows is every
 * no-entity state (DET-02) and an entity whose attributes all ride the header,
 * the box, or the blacklist.
 *
 * A painter, not a store: the rows arrive from the screen (the view's merge,
 * filtered, sorted, and blacklisted there), and the accordion opens on its own
 * with the title it is handed. A property link re-emits its guid as `linkClicked`
 * for the screen to route (DD-154) — only the screen touches the router (DET-06).
 * The accordion keeps its legacy anchor id (`#properties-details`, the side
 * navigation's and the stats bar's scroll target) and starts expanded, as 7.20
 * left it. It injects no store, router, or client.
 */
@Component({
    imports: [Accordion, PropertiesItem],
    selector: "aurelius-atlas-webapp-details-properties",
    template: `
        <aurelius-atlas-ui-accordion id="properties-details" class="block" [expanded]="true">
            <ng-container header>
                <h2 class="title is-3 aurelius-details-properties-title">{{ title() }}</h2>
            </ng-container>
            <ng-container content>
                <!-- The legacy 'sortable-table-shell' swap (DET-11): with
                         rows, the table; with none, its noData line in place of
                         the whole table, headers included. Zero rows is every
                         no-entity state (DET-02) and an entity whose attributes
                         all ride the header, the box, or the blacklist. -->
                @if (rows().length > 0) {
                    <table class="table is-fullwidth aurelius-details-properties">
                        <thead>
                            <tr>
                                <th i18n="@@search.details.components.properties.key">Key</th>
                                <th i18n="@@search.details.components.properties.value">Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            @for (property of rows(); track property.key) {
                                <tr>
                                    <td>{{ property.key }}</td>
                                    <td>
                                        <aurelius-atlas-ui-properties-item
                                            [value]="property.value"
                                            (itemClicked)="linkClicked.emit($event)"
                                        />
                                    </td>
                                </tr>
                            }
                        </tbody>
                    </table>
                } @else {
                    <p class="content has-text-centered aurelius-details-properties-empty">
                        <span><i i18n="@@components.sortableTableShell.noData">No data available</i></span>
                    </p>
                }
            </ng-container>
        </aurelius-atlas-ui-accordion>
    `,
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DetailsProperties {
    /** The rendered property rows (DET-11), filtered and sorted by the screen. */
    readonly rows = input.required<DetailProperty[]>();

    /** The accordion's title (DET-11: the layout's own key, else the default). */
    readonly title = input.required<string>();

    /** The clicked property link's guid (DD-154) — the screen routes the screen. */
    readonly linkClicked = output<string>();
}
