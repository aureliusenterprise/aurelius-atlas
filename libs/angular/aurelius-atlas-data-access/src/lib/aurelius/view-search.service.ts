import { HttpClient } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { API_BASE_URL } from "../api-config";
import { ViewSearchAnswer, ViewSearchRequest } from "../atlas/atlas-view";

/**
 * The client of the view family's search door (VSR-03, ADR 064): the server's
 * own endpoint under `/aurelius/v1`, beside Atlas's, behind the same
 * {@link API_BASE_URL} and authentication. One body in, one answer out — the
 * door's `mode` key chooses words, meaning or both (ASV-01), so the caller
 * needs no second endpoint for a search by meaning.
 */
@Injectable({
    providedIn: "root",
})
export class ViewSearchService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(API_BASE_URL);

    /**
     * The cards, facets and count of a search of the door's population: every
     * active entity, narrowed by the request's filters (AVR-11).
     * @param request the query, the mode, the filters, the facets and the page
     * @returns the page of cards, each facet's counts, and the total
     */
    search(request: ViewSearchRequest): Observable<ViewSearchAnswer> {
        return this.http.post<ViewSearchAnswer>(`${this.baseUrl}/aurelius/v1/search`, request);
    }
}
