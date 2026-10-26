import { HttpClient, HttpParams } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { API_BASE_URL } from "../api-config";
import {
    AtlasQuickSearchResult,
    AtlasSearchResult,
    AtlasSuggestionsResult,
    QuickSearchParameters,
    SearchParameters,
    SortOrder,
} from "./atlas-search";

/**
 * The `HttpParams` of a search: nil-dropped, the Java defaults (a false flag, a
 * zero page) left out as their absence — the server reads an absent boolean as
 * `false` and an absent number as `0`, exactly the defaults its routes pass on —
 * and the parameter names kept verbatim (`typeName`, `attrValuePrefix`, …).
 * @param params the endpoint's parameters, with the wire names
 * @returns the query parameters to send
 */
function searchParams(params: Record<string, unknown>): HttpParams {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params)) {
        if (value != null && value !== false && value !== 0) {
            httpParams = httpParams.set(key, `${value}`);
        }
    }
    return httpParams;
}

/** The GET `basic` parameters, as the server's `searchUsingBasic` reads them (SRC-11). */
export type BasicSearchQuery = {
    query?: string | null;
    typeName?: string | null;
    classification?: string | null;
    sortBy?: string | null;
    sortOrder?: SortOrder | null;
    excludeDeletedEntities?: boolean;
    limit?: number;
    offset?: number;
    marker?: string | null;
};

/** The GET `attribute` parameters, as the server's `searchUsingAttribute` reads them (SRC-11). */
export type AttributeSearchQuery = {
    typeName?: string | null;
    attrName?: string | null;
    attrValuePrefix?: string | null;
    limit?: number;
    offset?: number;
};

/** The GET `fulltext` parameters, as the server's `searchUsingFullText` reads them (FTX-05). */
export type FullTextSearchQuery = {
    query: string;
    excludeDeletedEntities?: boolean;
    limit?: number;
    offset?: number;
};

/** The GET `quick` parameters, as the server's `quickSearch` reads them (QSR-01). */
export type QuickSearchQuery = {
    query?: string | null;
    typeName?: string | null;
    excludeDeletedEntities?: boolean;
    limit?: number;
    offset?: number;
    sortBy?: string | null;
    sortOrder?: SortOrder | null;
};

/**
 * The search endpoints of the Atlas server (`DiscoveryREST`, APC-11): the basic,
 * attribute, full-text and quick searches and the term suggestions of
 * increments 4.1/4.2. The wire shapes are {@link SearchParameters} and friends
 * (APC-03 — see `atlas-search.ts`); a non-2xx answer carries the typed Atlas
 * error body (APC-04 — see `atlas-error.ts`). Every URL composes from the
 * injected {@link API_BASE_URL} with the `/atlas` prefix intact (APC-01).
 *
 * The POST searches send the parameters as the body the server validates
 * (SRC-02, QSR-01); the GET searches send them as query parameters, which the
 * server validates more leniently (SRC-11) — as the server's routes do.
 */
@Injectable({
    providedIn: "root",
})
export class SearchService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(API_BASE_URL);

    private searchUrl(path: string): string {
        return `${this.baseUrl}/atlas/v2/search${path}`;
    }

    /**
     * The entities the body's search finds, validated first (SRC-02) —
     * `searchWithParameters` of `DiscoveryREST`.
     * @param parameters what to search for, how to sort and page
     * @returns the entities the search found
     */
    searchWithParameters(parameters: SearchParameters): Observable<AtlasSearchResult> {
        return this.http.post<AtlasSearchResult>(this.searchUrl("/basic"), parameters);
    }

    /**
     * A search of the query parameters, not body-validated (SRC-11) —
     * `searchUsingBasic`.
     * @param query the search's parameters
     * @returns the entities the search found
     */
    searchUsingBasic(query: BasicSearchQuery = {}): Observable<AtlasSearchResult> {
        return this.http.get<AtlasSearchResult>(this.searchUrl("/basic"), { params: searchParams(query) });
    }

    /**
     * The entities whose attribute starts with the prefix (SRC-11) —
     * `searchUsingAttribute`.
     * @param query the attribute, its prefix, the type, and the page
     * @returns the entities the search found
     */
    searchUsingAttribute(query: AttributeSearchQuery): Observable<AtlasSearchResult> {
        return this.http.get<AtlasSearchResult>(this.searchUrl("/attribute"), { params: searchParams(query) });
    }

    /**
     * The entities matching the free-text query, best match first, with their
     * scores (FTX-05) — `searchUsingFullText`.
     * @param query the query text and the page
     * @returns the entities the search found, each with its score
     */
    searchUsingFullText(query: FullTextSearchQuery): Observable<AtlasSearchResult> {
        const { query: text, ...page } = query;
        return this.http.get<AtlasSearchResult>(this.searchUrl("/fulltext"), {
            params: searchParams({ ...page, query: text }),
        });
    }

    /**
     * The quick search of the body, with its facets, validated first (QSR-01) —
     * `quickSearch(QuickSearchParameters)`.
     * @param parameters what to search for
     * @returns the results and the facet counts
     */
    quickSearch(parameters: QuickSearchParameters): Observable<AtlasQuickSearchResult> {
        return this.http.post<AtlasQuickSearchResult>(this.searchUrl("/quick"), parameters);
    }

    /**
     * A quick search of the query parameters, only the query's length checked
     * (QSR-01, QSR-02) — the legacy header search-bar call.
     * @param query the search's parameters
     * @returns the results and the facet counts
     */
    quickSearchUsingQuery(query: QuickSearchQuery = {}): Observable<AtlasQuickSearchResult> {
        return this.http.get<AtlasQuickSearchResult>(this.searchUrl("/quick"), { params: searchParams(query) });
    }

    /**
     * The terms suggested for a prefix, of the heaviest fields or of the one
     * field named (SUG-01, SUG-02) — `getSuggestions`.
     * @param prefixString the prefix the terms begin with
     * @param fieldName the field to read the terms from, optional
     * @returns up to five terms, most frequent first
     */
    getSuggestions(prefixString: string, fieldName?: string): Observable<AtlasSuggestionsResult> {
        return this.http.get<AtlasSuggestionsResult>(this.searchUrl("/suggestions"), {
            params: searchParams({ prefixString, fieldName }),
        });
    }
}
