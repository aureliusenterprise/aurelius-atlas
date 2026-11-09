import { computed, inject, Injectable, signal } from "@angular/core";
import type { CategoryMap } from "aurelius-atlas-ui";
import { LineageModelService, type LineageModelMetadata } from "aurelius-atlas-data-access";

import { parseAr3Model, type Ar3Model, type Ar3View } from "./parse-ar3";

/**
 * The Lineage Model state (DD-400, widened by DD-415): the app-scoped
 * signal set that owns the LDG-01 call and the diagram's shared surface
 * state, so the stats bar, the box, the viewer, and the routed quickview
 * drawer read one instance (DET-23's rule: one owner, many readers — the
 * legacy polls `lineageModelStatus$` onto the page display service the
 * same way). App-scoped since DD-415 (provided by the details screen
 * before it): the drawer lives in the root `drawer` aux outlet and a
 * route there cannot see a page-level provider, so the shared selection
 * rides the app singleton; the guid-keyed stale-answer guard below makes
 * one instance correct across detail pages.
 *
 * The three fetch values are the box's three states (LDG-10): pending,
 * drawn (a model), or at-rest (the 204, a failure, or an unparseable
 * document all rest empty — DD-392's single fallback). {@link load}
 * follows the route's guid; the newest load wins (the `DetailsState`
 * stale-answer guard, DET-08's idiom), so a superseded answer never
 * paints.
 */
@Injectable({ providedIn: "root" })
export class LineageModelState {
    private readonly lineageModel = inject(LineageModelService);

    /** The guid of the newest load — the stale-answer guard's key. */
    private latestGuid = "";

    /** Whether the newest load is in flight (LDG-10's pending state). */
    readonly loading = signal(true);

    /** The parsed model, or null for the empty/failed states (LDG-10). */
    readonly model = signal<Ar3Model | null>(null);

    /**
     * The answer's metadata rows (LDG-02's list): 7.22c's quickview merges
     * them into the Selection tab's Properties table (LDG-21), so they ride
     * beside the parsed model.
     */
    readonly metadata = signal<readonly LineageModelMetadata[]>([]);

    /**
     * The selected concept (LDG-25's one signal, DD-415): the viewer
     * paints it, the routed drawer reads and writes it. A concept id, or
     * null for none — the same value the URL's `drawer:lineage:...`
     * segment carries while the Selection tab is open.
     */
    readonly selected = signal<string | null>(null);

    /**
     * The view the reader chose (LDG-23, DD-415): null for the document's
     * first (LDG-12's default, {@link activeView}).
     */
    readonly drawnViewId = signal<string | null>(null);

    /**
     * The colour view's categories (UIC-30, DD-420, the legacy's
     * `bucketMapping`): concept id → category name. The legacy fed it only
     * from a host with a bucketing producer (model-compare, a violation
     * report) and the details page never had one; the same is true here —
     * null until a producer (a heatmap, a metric) writes it. The canvas
     * fills its elements from it and the View tab's legend table lists it.
     */
    readonly categories = signal<CategoryMap | null>(null);

    /**
     * The picked category colours (UIC-31, the legacy's legend edits):
     * category name → hex, written by the View tab's colour picker.
     * Session-only, as the legacy's were — a picked colour lives until the
     * categories change or the page reloads (DD-420).
     */
    readonly categoryColors = signal<CategoryMap | null>(null);

    /**
     * One category's picked colour (UIC-31): the legacy's
     * `updateLegendColor` — write the pick, every element in the category
     * repaints through the canvas's legend join.
     * @param category the legend row's category
     * @param color the picked hex
     */
    setCategoryColor(category: string, color: string): void {
        this.categoryColors.update((current) => ({ ...current, [category]: color }));
    }

    /**
     * The view actually drawn (LDG-12's default resolved once, DD-415):
     * the chosen one, else the document's first, else none. The viewer
     * draws it; the drawer marks it selected and reads its concept (the
     * View tab's condition) — one resolution, both surfaces.
     */
    readonly activeView = computed<Ar3View | null>(() => {
        const model = this.model();
        if (model === null) {
            return null;
        }
        const id = this.drawnViewId();
        if (id === null) {
            return model.views[0] ?? null;
        }
        return model.views.find((view) => view.id === id) ?? null;
    });

    /**
     * Fetch the model for one guid (LDG-01 via the 7.22a client): the
     * newest load wins, a superseded answer paints nothing. The old
     * document's selection and drawn view clear with it (DD-415) — both
     * are ids into the model being replaced, and the routed drawer must
     * not outlive them.
     * @param guid the route's entity address
     */
    load(guid: string): void {
        this.latestGuid = guid;
        this.loading.set(true);
        this.model.set(null);
        this.metadata.set([]);
        this.selected.set(null);
        this.drawnViewId.set(null);
        // UIC-30: the categories are keyed by the replaced document's ids
        // too, so they clear with it. The picks (UIC-31) are keyed by
        // category name and stay — an override for a category the next
        // document has no row for simply colours nothing, as in the legacy,
        // whose regenerated legend dropped a pick only when the palette
        // re-ran.
        this.categories.set(null);
        if (guid === "") {
            return;
        }
        this.lineageModel.getLineageModel(guid).subscribe({
            next: (response) => {
                if (this.latestGuid !== guid) {
                    return;
                }
                this.loading.set(false);
                // A 204 answers null (LDG-03); a malformed document throws
                // in the reader (LDG-11). Both rest at the empty state
                // (LDG-10, DD-392).
                if (response === null) {
                    return;
                }
                try {
                    this.model.set(parseAr3Model(response.model));
                    this.metadata.set(response.metadata);
                } catch {
                    this.model.set(null);
                    this.metadata.set([]);
                }
            },
            // DD-392: the legacy's silent catch, kept — the drawer is this
            // app's error channel (the widened 7.19 chain).
            error: () => {
                if (this.latestGuid !== guid) {
                    return;
                }
                this.loading.set(false);
                this.model.set(null);
                this.metadata.set([]);
            },
        });
    }
}
