import { HttpClient, HttpParams } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { API_BASE_URL } from "../api-config";
import { AtlasQuickSearchResult, QuickSearchParameters } from "../atlas/atlas-search";

/**
 * How a search by meaning ranks (SBM-01): by meaning alone, or by meaning and
 * the query's words together.
 */
export type SearchByMeaningMode = "semantic" | "hybrid";

/** A search by meaning: quick search's parameters and the mode (SBW-01, SBM-01). */
export type SearchByMeaningParameters = QuickSearchParameters & {
    mode?: SearchByMeaningMode;
};

/** What the nearest to one entity are looked for among (SBW-01, SBM-05). */
export type SimilarEntitiesQuery = {
    typeName?: string | null;
    excludeDeletedEntities?: boolean;
    offset?: number;
    limit?: number;
};

/**
 * The client of Aurelius's searches by meaning (SBW-01, DD-447): the server's
 * own endpoints under `/aurelius/v1`, beside Atlas's, behind the same
 * {@link API_BASE_URL} and authentication. Both answer as quick search
 * does, so a caller shows them as it shows quick search (DD-440).
 */
@Injectable({
    providedIn: "root",
})
export class SearchByMeaningService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(API_BASE_URL);

    /**
     * The entities nearest in meaning to the query, or by meaning and words
     * with `mode: "hybrid"` (SBM-02, SBM-03).
     * @param parameters the query, the type, the filters, the page and the mode
     * @returns the page of entities and the facets of the search
     */
    search(parameters: SearchByMeaningParameters): Observable<AtlasQuickSearchResult> {
        return this.http.post<AtlasQuickSearchResult>(`${this.baseUrl}/aurelius/v1/search/semantic`, parameters);
    }

    /**
     * The entities nearest in meaning to one entity, itself left out (SBM-05).
     * @param guid the entity's GUID
     * @param query the type, the deleted entities' exclusion and the page
     * @returns the page of entities and their facets
     */
    similar(guid: string, query: SimilarEntitiesQuery = {}): Observable<AtlasQuickSearchResult> {
        let params = new HttpParams();
        for (const [key, value] of Object.entries(query)) {
            if (value != null && value !== false) {
                params = params.set(key, `${value}`);
            }
        }
        const path = `${this.baseUrl}/aurelius/v1/entity/guid/${encodeURIComponent(guid)}/similar`;
        return this.http.get<AtlasQuickSearchResult>(path, { params });
    }
}
