import { HttpClient } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable, of } from "rxjs";
import { tap } from "rxjs/operators";
import { API_BASE_URL } from "../api-config";
import { EntityView } from "../atlas/atlas-view";

/** How many views the service remembers, the cap ADR 064's cache clause sets (DD-605, VDR-07). */
const CACHE_SIZE = 50;

/**
 * The client of the view family's read door (VDR-01, ADR 064): one GUID in, that
 * entity's live view out, behind the same {@link API_BASE_URL} and
 * authentication as the search door. The last {@link CACHE_SIZE} views are kept
 * in memory, so a crumb or a property link opened again in the session paints
 * without a request (DD-605); the editor's save tick evicts the saved guid and
 * the read goes out again (VDR-07). A page reload clears the memory, and a
 * second tab's view of the same entity can be answered from a stale cache —
 * accepted, the last 50 are what a screen walks, not what an audit reads.
 */
@Injectable({
    providedIn: "root",
})
export class ViewEntityService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(API_BASE_URL);
    private readonly views = new Map<string, EntityView>();

    /**
     * The live view of one entity: from memory when the session read it, from
     * the door otherwise (VDR-01, VDR-07).
     * @param guid the entity to read
     * @returns the entity's view, answered by the door or by the cache
     */
    view(guid: string): Observable<EntityView> {
        const remembered = this.views.get(guid);
        if (remembered !== undefined) return of(remembered);
        return this.http
            .get<EntityView>(`${this.baseUrl}/aurelius/v1/entity/guid/${guid}`)
            .pipe(tap((view) => this.remember(view)));
    }

    /**
     * Drop one entity's remembered view, so the next read asks the door (VDR-07:
     * the editor's save tick calls this before re-reading).
     * @param guid the entity whose view is no longer current
     */
    evict(guid: string): void {
        this.views.delete(guid);
    }

    /** Keep ``view`` as the freshest, dropping the oldest past the cap (DD-605). */
    private remember(view: EntityView): void {
        this.views.delete(view.guid); // a re-read keeps one entry, at the front
        this.views.set(view.guid, view);
        if (this.views.size > CACHE_SIZE) {
            const oldest = this.views.keys().next();
            if (!oldest.done) this.views.delete(oldest.value);
        }
    }
}
