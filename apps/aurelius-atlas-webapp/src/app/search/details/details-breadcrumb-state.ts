import { Injectable, signal } from "@angular/core";
import type { Breadcrumb } from "aurelius-atlas-ui";

/**
 * The details screen's breadcrumb trail store (DET-12, DD-317, VDR-06):
 * app-side state the screen renders, fed by the read door's view.
 *
 * The legacy trail read the `breadcrumbguid`/`breadcrumbname`/
 * `breadcrumbtype` arrays off the App Search document, built at index time
 * by a Flink job that concatenated the parent document's trail. Aurelius
 * Atlas answers the same arrays on the entity's App Search document
 * (14.2's derived breadcrumb), and since 16.5b the read door carries them
 * on the view (AVS-02): the screen's trail effect calls {@link setTrail}
 * with the view's stored breadcrumb and its own crumb (DD-317's seam,
 * filled), and DET-06's crumb routing is unchanged.
 *
 * Nothing here fetches: the store holds what the screen hands it, so the
 * screen's binding and this store stayed as 7.20 shipped them.
 */
@Injectable()
export class DetailsBreadcrumbState {
    /** The trail the screen renders, oldest first — empty with no entity (DET-12). */
    readonly trail = signal<Breadcrumb[]>([]);

    /**
     * Replace the trail (the trail effect's call, DET-12, VDR-06).
     * @param items the trail, oldest first
     */
    setTrail(items: Breadcrumb[]): void {
        this.trail.set(items);
    }

    /** Empty the trail (the entity changes until the API join fills it). */
    clear(): void {
        this.trail.set([]);
    }
}
