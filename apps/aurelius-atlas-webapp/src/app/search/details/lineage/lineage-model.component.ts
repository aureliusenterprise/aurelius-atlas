import { ChangeDetectionStrategy, Component, computed, effect, inject, input, viewChild } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faSearch } from "@fortawesome/free-solid-svg-icons";

import { LineageModelState } from "./lineage-state";
import { LineageViewer } from "./lineage-viewer.component";

/**
 * The Lineage Model box (LDG-09/LDG-10, DD-392): the legacy
 * `search/details/components/lineage-model` component, ported. The dataset
 * and the process layouts embed it between two card boxes; the box owns the
 * LDG-01 call for the page's entity and shows one of three states — the
 * loading message while the model is retrieved, the empty message when the
 * entity has no lineage, and the diagram (the viewer, LDG-12..18) when it
 * has one.
 *
 * A failed call renders the empty message too (LDG-10, DD-392): the legacy's
 * single fallback, kept deliberately — the failure itself reaches the 7.19
 * alert drawer through the widened shared error chain, not the box. A model
 * that fails to parse (LDG-11's throw) is a producer contract break and reads
 * the same way.
 *
 * The header is the drawn view's name (LDG-09) — the model's own data, the
 * server's rule names the view "Lineage" — not a catalogue string. The two
 * messages are catalogue keys carried in both locales (DD-128). The header
 * and message markup follows the details page's box pattern (the card
 * sections' `h3.title.is-3`), the legacy box's `h5.title.is-5` messages.
 *
 * The fetch state lives in the page's {@link LineageModelState} (DD-400):
 * the box keeps the trigger (its effect follows the guid, so only a page
 * that renders the box ever calls), while the LDG-32 stat reads the same
 * signals without mounting this component.
 */
@Component({
    selector: "aurelius-atlas-webapp-lineage-model",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [FontAwesomeModule, LineageViewer],
    template: `
        @if (this.loading()) {
            <!-- LDG-10's pending state: the legacy's loader + message. -->
            <div class="has-text-centered aurelius-lineage-loading">
                <span class="icon loader" aria-hidden="true"></span>
                <h5 class="title is-5" i18n="@@search.details.components.lineageModel.loading">
                    Loading the lineage model...
                </h5>
            </div>
        } @else if (this.drawn(); as model) {
            <!-- LDG-09: the header is the drawn view's name — the model's
                 data (the server names the view "Lineage"), never a key.
                 LDG-27: the header's right side carries the Browse button
                 (the legacy's level-right, label plus search icon). -->
            <div class="level aurelius-lineage-header">
                <div class="level-left">
                    <h3 class="title is-3 aurelius-lineage-title">{{ viewName() }}</h3>
                </div>
                <div class="level-right">
                    <button
                        type="button"
                        class="button is-info level-item aurelius-lineage-browse"
                        [attr.aria-label]="browseTooltip"
                        (click)="viewerRef().openBrowser()"
                    >
                        <span class="icon" aria-hidden="true"><fa-icon [icon]="faSearch"></fa-icon></span>
                        <span>{{ browseTooltip }}</span>
                    </button>
                </div>
            </div>
            <aurelius-atlas-webapp-lineage-viewer #viewer [highlightedGuid]="guid()" />
        } @else {
            <!-- LDG-10 / DD-392: no model and a failed call read alike. -->
            <div class="has-text-centered aurelius-lineage-empty">
                <h5 class="title is-5" i18n="@@search.details.components.lineageModel.noLineageModelAvailable">
                    No lineage model available
                </h5>
            </div>
        }
    `,
})
export class LineageModel {
    /** The page's fetch state (DD-400): the stats bar reads the same signals. */
    private readonly state = inject(LineageModelState);

    /** The page's entity guid (LDG-09): the box draws its lineage, highlighted. */
    readonly guid = input.required<string>();

    /** Whether the model call is in flight (LDG-10's pending state). */
    protected readonly loading = computed(() => this.state.loading());

    /** The parsed model, or null for the empty/failed states (LDG-10). */
    protected readonly drawn = computed(() => this.state.model());

    /** The drawn view's name — the box header (LDG-09), the model's data. */
    protected readonly viewName = computed(() => this.drawn()?.views[0]?.name ?? "");

    /** The header's Browse icon and its label (LDG-27 — `modelview2.browse`). */
    protected readonly faSearch = faSearch;
    protected readonly browseTooltip = $localize`:@@modelview2.browse:Browse the model`;

    /** The viewer — the header's Browse opens the quickview through it.
        (Named apart from the `#viewer` template ref, which shadows a
        member of the same name inside the template.) */
    protected readonly viewerRef = viewChild.required<LineageViewer>("viewer");

    constructor() {
        // The call follows the guid (LDG-01 via the 7.22a client): every
        // arrival and every guid change re-fetches through the page state
        // (DD-400) — the state's own newest-load guard drops a superseded
        // answer (the DET-08 idiom), so the trigger can stay this cheap.
        effect(() => {
            this.state.load(this.guid());
        });
    }
}
