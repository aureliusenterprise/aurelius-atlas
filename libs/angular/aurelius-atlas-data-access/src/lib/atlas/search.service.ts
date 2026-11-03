import { HttpClient, HttpParams } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { API_BASE_URL } from "../api-config";
import type { AtlasUserSavedSearch } from "./atlas-profile";
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

/** The GET `dsl` parameters, as the server's `searchUsingDSL` reads them (DSE-01). */
export type DslSearchQuery = {
    query?: string | null;
    typeName?: string | null;
    classification?: string | null;
    limit?: number;
    offset?: number;
};

/**
 * The search endpoints of the Atlas server (`DiscoveryREST`, APC-11, ACS-01..06):
 * the basic, attribute, full-text and quick searches, the term suggestions, the
 * DSL search and the saved searches of the acting user, of increments 4.1–4.5.
 * The wire shapes are {@link SearchParameters} and friends
 * (APC-03 — see `atlas-search.ts` and `atlas-profile.ts`); a non-2xx answer
 * carries the typed Atlas error body (APC-04 — see `atlas-error.ts`). Every URL
 * composes from the injected {@link API_BASE_URL} with the `/atlas` prefix
 * intact (APC-01).
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

    /**
     * The entities a DSL query finds, of the type and classification given
     * (DSE-01, DSE-02, ACS-01) — `searchUsingDSL`. The client checks no query
     * length; the server answers `INVALID_QUERY_LENGTH` as the typed error
     * (APC-04), as `AtlasClient.search_using_dsl` (CSD-01) sends it too.
     * @param query the DSL query, its type and classification, and the page
     * @returns the entities the search found
     */
    searchUsingDsl(query: DslSearchQuery = {}): Observable<AtlasSearchResult> {
        return this.http.get<AtlasSearchResult>(this.searchUrl("/dsl"), { params: searchParams(query) });
    }

    /**
     * The body's search, saved for the acting user (SVS-02, ACS-02) —
     * `addSavedSearch`, `POST /search/saved`.
     * @param savedSearch the search to save, under its name
     * @returns the saved search as the server stored it
     */
    addSavedSearch(savedSearch: AtlasUserSavedSearch): Observable<AtlasUserSavedSearch> {
        return this.http.post<AtlasUserSavedSearch>(this.searchUrl("/saved"), savedSearch);
    }

    /**
     * The acting user's saved search of the body's GUID, replaced (SVS-03,
     * ACS-02) — `updateSavedSearch`, `PUT /search/saved`.
     * @param savedSearch the saved search with its GUID and new body
     * @returns the saved search as the server stored it
     */
    updateSavedSearch(savedSearch: AtlasUserSavedSearch): Observable<AtlasUserSavedSearch> {
        return this.http.put<AtlasUserSavedSearch>(this.searchUrl("/saved"), savedSearch);
    }

    /**
     * The saved searches of the acting user, or of the named one (SVS-04,
     * ACS-03) — `getSavedSearches`. The server answers 204, read here as a
     * `null` body, when the user has no profile: `null` and `[]` are kept
     * apart on purpose (DD-314, the pair of CSD-03's `None`).
     * @param user the profile to read, optional — the acting user by default
     * @returns the saved searches, or `null` without a profile
     */
    getSavedSearches(user?: string): Observable<AtlasUserSavedSearch[] | null> {
        return this.http.get<AtlasUserSavedSearch[] | null>(this.searchUrl("/saved"), {
            params: searchParams({ user }),
        });
    }

    /**
     * The saved search of that name, of the acting user or the named one
     * (SVS-04, ACS-04) — `getSavedSearch`. The name rides the path encoded,
     * and a missing search answers 404 as the typed error (APC-04).
     * @param name the saved search's name
     * @param user the profile to read, optional — the acting user by default
     * @returns the saved search
     */
    getSavedSearch(name: string, user?: string): Observable<AtlasUserSavedSearch> {
        return this.http.get<AtlasUserSavedSearch>(this.searchUrl(`/saved/${encodeURIComponent(name)}`), {
            params: searchParams({ user }),
        });
    }

    /**
     * The saved search of that GUID, removed (SVS-05, ACS-04) —
     * `deleteSavedSearch`. Read by name, delete by GUID: the server's verbs
     * are asymmetric on purpose. The answer is 204.
     * @param guid the saved search's GUID
     */
    deleteSavedSearch(guid: string): Observable<void> {
        return this.http.delete<void>(this.searchUrl(`/saved/${encodeURIComponent(guid)}`));
    }

    /**
     * The saved search of that name, run (SVS-06, ACS-05) —
     * `executeSavedSearchByName`: the answer is the search's result, not the
     * saved search itself.
     * @param name the saved search's name
     * @param user the profile to read, optional — the acting user by default
     * @returns the entities the saved search found
     */
    executeSavedSearchByName(name: string, user?: string): Observable<AtlasSearchResult> {
        return this.http.get<AtlasSearchResult>(this.searchUrl(`/saved/execute/${encodeURIComponent(name)}`), {
            params: searchParams({ user }),
        });
    }

    /**
     * The saved search of that GUID, run (SVS-06, ACS-05) —
     * `executeSavedSearchByGuid`. The route takes no `user`: the GUID names
     * the search directly.
     * @param guid the saved search's GUID
     * @returns the entities the saved search found
     */
    executeSavedSearchByGuid(guid: string): Observable<AtlasSearchResult> {
        return this.http.get<AtlasSearchResult>(this.searchUrl(`/saved/execute/guid/${encodeURIComponent(guid)}`));
    }
}
