import { Injectable, inject, signal } from "@angular/core";
import { LineageModelService, type LineageModelMetadata } from "aurelius-atlas-data-access";

import { parseAr3Model, type Ar3Model } from "./parse-ar3";

/**
 * The Lineage Model fetch state (DD-400): the page-level signal that owns
 * the LDG-01 call, so the stats bar can read it beside the box (DET-23's
 * rule: the page owns one fetch state and the section config's stat reads
 * it — the legacy polls `lineageModelStatus$` onto the page display service
 * the same way). Provided by the details screen, injected by the box
 * (7.22b's box held this state privately; LDG-32's stat needs it without
 * mounting the box, so the state moves here in this slice's first step).
 *
 * The three values are the box's three states (LDG-10): pending, drawn (a
 * model), or at-rest (the 204, a failure, or an unparseable document all
 * rest empty — DD-392's single fallback). {@link load} follows the route's
 * guid; the newest load wins (the `DetailsState` stale-answer guard,
 * DET-08's idiom), so a superseded answer never paints.
 */
@Injectable()
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
     * Fetch the model for one guid (LDG-01 via the 7.22a client): the
     * newest load wins, a superseded answer paints nothing.
     * @param guid the route's entity address
     */
    load(guid: string): void {
        this.latestGuid = guid;
        this.loading.set(true);
        this.model.set(null);
        this.metadata.set([]);
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
