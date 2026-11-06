import { Injectable, signal } from "@angular/core";
import type { Breadcrumb } from "aurelius-atlas-ui";

/**
 * The details screen's breadcrumb trail store (DET-12, DD-317): app-side
 * state the screen renders, with no data source yet.
 *
 * The legacy trail read the `breadcrumbguid`/`breadcrumbname`/
 * `breadcrumbtype` arrays off the App Search document, built at index time
 * by a Flink job that concatenated the parent document's trail. Aurelius
 * Atlas has no such index and no endpoint that computes a parent chain, so
 * this store answers empty: the screen shows the trail under the
 * breadcrumbs' empty guard, and DET-06's crumb routing stays wired.
 *
 * The store is the seam the API join fills later (DD-317): a future
 * increment calls {@link setTrail} from an endpoint's answer, and the
 * screen's binding does not change. Nothing derives crumbs from the entity
 * read, and nothing here fetches.
 */
@Injectable()
export class DetailsBreadcrumbState {
    /** The trail, oldest first — empty until an endpoint fills it (DET-12). */
    readonly trail = signal<Breadcrumb[]>([]);

    /**
     * Replace the trail (the future API join's call, DET-12). Nothing calls
     * this yet — the seam's contract is its signature.
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
