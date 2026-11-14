import { HttpClient } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable, of } from "rxjs";
import { tap } from "rxjs/operators";
import { API_BASE_URL } from "../api-config";
import { ViewForTypeAnswer } from "../atlas/atlas-view";

/**
 * The client of the view family's form-slice door (VDE-02, AVW-11): one read
 * answers the whole type chain an editor needs to build a form for one type —
 * the named entity type and each of its supertypes, every typedef whole —
 * behind the same {@link API_BASE_URL} and authentication as the entity doors.
 *
 * Each chain is kept in memory by type name (DD-611): a second editor for the
 * same type, and the create flow that learns the type before the entity exists,
 * ask once. The last answers are what a session edits, and a loaded registry
 * entry cannot change under a name mid-session (a type edit through the door is
 * refused, AVW-04's type rule), so the cache needs no invalidation.
 */
@Injectable({
    providedIn: "root",
})
export class ViewTypeService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(API_BASE_URL);
    private readonly chains = new Map<string, ViewForTypeAnswer>();

    /**
     * The type chain of one entity type: from memory when the session asked,
     * from the door otherwise (VDE-02).
     * @param name the entity type to build a form for
     * @returns the named type and its supertype chain, each typedef whole
     */
    forType(name: string): Observable<ViewForTypeAnswer> {
        const remembered = this.chains.get(name);
        if (remembered !== undefined) return of(remembered);
        return this.http
            .get<ViewForTypeAnswer>(`${this.baseUrl}/aurelius/v1/types/for-type/${encodeURIComponent(name)}`)
            .pipe(tap((answer) => this.chains.set(name, answer)));
    }
}
