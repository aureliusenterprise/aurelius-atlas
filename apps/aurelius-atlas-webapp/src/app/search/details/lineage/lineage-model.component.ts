import { ChangeDetectionStrategy, Component, computed, effect, inject, input, signal } from "@angular/core";
import { LineageModelService } from "aurelius-atlas-data-access";

import { parseAr3Model, type Ar3Model } from "./parse-ar3";

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
 */
@Component({
    selector: "aurelius-atlas-webapp-lineage-model",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [LineageViewer],
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
                 data (the server names the view "Lineage"), never a key. -->
            <h3 class="title is-3 aurelius-lineage-title">{{ viewName() }}</h3>
            <aurelius-atlas-webapp-lineage-viewer [model]="model" [highlightedGuid]="guid()" />
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
    private readonly lineageModel = inject(LineageModelService);

    /** The page's entity guid (LDG-09): the box draws its lineage, highlighted. */
    readonly guid = input.required<string>();

    /** Whether the model call is in flight (LDG-10's pending state). */
    protected readonly loading = signal(true);

    /** The parsed model, or null for the empty/failed states (LDG-10). */
    protected readonly drawn = signal<Ar3Model | null>(null);

    /** The drawn view's name — the box header (LDG-09), the model's data. */
    protected readonly viewName = computed(() => this.drawn()?.views[0]?.name ?? "");

    constructor() {
        // The call follows the guid (LDG-01 via the 7.22a client): every
        // arrival and every guid change re-fetches, and the cleanup drops
        // the superseded call so a stale answer never paints (the DET-08
        // screen's own guard, same rule here).
        effect((onCleanup) => {
            const guid = this.guid();
            this.loading.set(true);
            this.drawn.set(null);
            if (guid === "") {
                return;
            }
            const subscription = this.lineageModel.getLineageModel(guid).subscribe({
                next: (response) => {
                    this.loading.set(false);
                    // A 204 answers null (LDG-03); a malformed document
                    // throws in the reader (LDG-11). Both rest at the
                    // empty message (LDG-10, DD-392).
                    if (response === null) {
                        this.drawn.set(null);
                        return;
                    }
                    try {
                        this.drawn.set(parseAr3Model(response.model));
                    } catch {
                        this.drawn.set(null);
                    }
                },
                // DD-392: the legacy's silent catch, kept — the drawer is
                // this app's error channel (the widened 7.19 chain).
                error: () => {
                    this.loading.set(false);
                    this.drawn.set(null);
                },
            });
            onCleanup(() => subscription.unsubscribe());
        });
    }
}
