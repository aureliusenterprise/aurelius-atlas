import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";
import { Markdown, PeopleBox, type PeopleRow } from "aurelius-atlas-ui";

/**
 * The layout's first row (DET-15, DET-16): the description box, and beside it
 * the People box on the layouts that carry one (DET-23). The description text
 * renders as markdown and an empty description shows the italic centred
 * placeholder (DET-10, DD-321); the People box paints the three labelled rows
 * it is handed and emits the clicked person's guid (UIC-28).
 *
 * A painter, not a store: the titles and the placeholder come from the type's
 * layout row, the description and the rows from the opened entity (the screen
 * reads them all and hands them in). The guard that skips the whole row on the
 * person page (`descriptionBox`, DET-39, DD-518) lives with the screen, not
 * here — this part paints the row it is asked to paint. It injects no store,
 * router, or client; the screen routes the person click.
 */
@Component({
    imports: [Markdown, PeopleBox],
    selector: "aurelius-atlas-webapp-details-first-row",
    styleUrl: "./first-row.component.scss",
    template: `
        <div class="columns">
            <div class="column">
                <div id="description-details" class="box">
                    <!-- HEADING-002: the section titles sit one level under
                         the entity h1 (was h3, a skipped level); the Bulma
                         classes keep the pixels. -->
                    <h2 class="title is-3">{{ descriptionTitle() }}</h2>
                    <!-- The legacy description component (DET-10, DD-321):
                             the text renders as markdown, and an empty
                             description shows its italic centered placeholder
                             line instead of a blank box. -->
                    @if (description()) {
                        <aurelius-atlas-ui-markdown class="aurelius-details-description" [markdown]="description()" />
                    } @else {
                        <p class="is-italic has-text-centered aurelius-details-description-empty">
                            <span i18n="@@search.components.description.notAvailable">No description available.</span>
                        </p>
                    }
                </div>
            </div>
            @if (peopleBox()) {
                <div class="column">
                    <div id="people-details" class="box aurelius-details-people">
                        <h2 class="title is-3">{{ peopleTitle() }}</h2>
                        <!-- The People box (DET-23, UIC-28): the three labelled
                             rows of the opened entity, deduped and filtered
                             app-side; a person link routes the screen. -->
                        <aurelius-atlas-ui-people-box
                            [rows]="people()"
                            [emptyLabel]="peopleEmpty()"
                            (personClicked)="personClicked.emit($event)"
                        />
                    </div>
                </div>
            }
        </div>
    `,
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DetailsFirstRow {
    /** The description box's title (DET-15: the layout's own key). */
    readonly descriptionTitle = input.required<string>();

    /** The opened entity's description text, empty when it has none (DET-10). */
    readonly description = input.required<string>();

    /** Whether this layout carries the People box (DET-23). */
    readonly peopleBox = input.required<boolean>();

    /** The People box's title (DET-23: the layout's own key). */
    readonly peopleTitle = input.required<string>();

    /** The People box's rows, deduped and filtered by the screen (UIC-28). */
    readonly people = input.required<PeopleRow[]>();

    /** The People box's empty-state label (UIC-28's placeholder). */
    readonly peopleEmpty = input.required<string>();

    /** The clicked person's guid (UIC-28) — the screen routes the screen. */
    readonly personClicked = output<string>();
}
