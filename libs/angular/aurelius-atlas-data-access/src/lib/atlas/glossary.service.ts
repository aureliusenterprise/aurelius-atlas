import { HttpClient, HttpParams } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { map, Observable } from "rxjs";
import { API_BASE_URL } from "../api-config";
import type { AtlasRelatedTermHeader } from "./atlas-entity";
import type {
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasGlossaryExtInfo,
    AtlasGlossaryTerm,
    AtlasRelatedCategoryHeader,
    GlossarySort,
} from "./atlas-glossary";
import type { AtlasExportAnswer, BulkImportResponse } from "./atlas-impexp";

/**
 * A glossary read's paging, as the routes read it (CLG-02, GLS-05). Every
 * field is optional and travels only when set: the server reads an absent
 * `limit` as -1 (every item), an absent `offset` as 0, and an absent `sort`
 * as `ASC` — so a default crosses as its absence, and a caller that passes
 * `limit: -1` explicitly is sent one. `offset` and `limit` of `0` are the
 * defaults too and stay absent, as in the twin's `_page_params`.
 */
export type GlossaryPage = {
    limit?: number;
    offset?: number;
    sort?: GlossarySort;
};

/**
 * The glossary endpoints of the Atlas server (`GlossaryREST`, AGL-01..07):
 * the first third of `routes/glossary.py` — the thirteen routes about
 * glossaries themselves. Terms (8.21) and categories (8.22) follow. Every
 * URL composes from the injected {@link API_BASE_URL} (APC-01). The Python
 * twin is `AtlasClient.glossary` (CLG-01..CLG-09); its resource-object
 * methods (`glossary.glossaries()`, …) compose into these flat names, as
 * 8.15/8.16 did for lineage and relationships.
 */
@Injectable({
    providedIn: "root",
})
export class GlossaryService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(API_BASE_URL);

    /**
     * Every glossary, paged and sorted (`getGlossaries`, GET `/v2/glossary`
     * — GLS-05, AGL-02). The paging follows {@link GlossaryPage}: an unset
     * field sends no parameter.
     * @param page the paging, or nothing for the server's defaults
     * @returns the glossaries of the page
     */
    getGlossaries(page: GlossaryPage = {}): Observable<AtlasGlossary[]> {
        return this.http.get<AtlasGlossary[]>(this.glossaryUrl(""), { params: this.pageParams(page) });
    }

    /**
     * Create a glossary (`createGlossary`, POST `/v2/glossary` — GLS-02,
     * AGL-03). The name and the qualified name are the server's check.
     * @param glossary the glossary to create
     * @returns the created glossary, with its guid
     */
    createGlossary(glossary: AtlasGlossary): Observable<AtlasGlossary> {
        return this.http.post<AtlasGlossary>(this.glossaryUrl(""), glossary);
    }

    /**
     * The glossary (`getGlossary`, GET `/v2/glossary/{guid}` — GLS-01,
     * GLS-06, AGL-01). The route reads no query parameter.
     * @param glossaryGuid the glossary GUID
     * @returns the glossary, bare
     */
    getGlossary(glossaryGuid: string): Observable<AtlasGlossary> {
        return this.http.get<AtlasGlossary>(this.glossaryUrl(`/${encodeURIComponent(glossaryGuid)}`));
    }

    /**
     * The glossary with its terms and categories by GUID (`getDetailedGlossary`,
     * GET `/v2/glossary/{guid}/detailed` — GLS-06, AGL-01).
     * @param glossaryGuid the glossary GUID
     * @returns the glossary plus `termInfo` and `categoryInfo`, keyed by GUID
     */
    getDetailedGlossary(glossaryGuid: string): Observable<AtlasGlossaryExtInfo> {
        return this.http.get<AtlasGlossaryExtInfo>(this.glossaryUrl(`/${encodeURIComponent(glossaryGuid)}/detailed`));
    }

    /**
     * The glossary's categories, paged (`getGlossaryCategories`, GET
     * `/v2/glossary/{guid}/categories` — GLS-05, AGL-02).
     * @param glossaryGuid the glossary GUID
     * @param page the paging, or nothing for the server's defaults
     * @returns the categories of the page
     */
    getGlossaryCategories(glossaryGuid: string, page: GlossaryPage = {}): Observable<AtlasGlossaryCategory[]> {
        return this.http.get<AtlasGlossaryCategory[]>(
            this.glossaryUrl(`/${encodeURIComponent(glossaryGuid)}/categories`),
            {
                params: this.pageParams(page),
            },
        );
    }

    /**
     * The glossary's category headers, paged (`getGlossaryCategoriesHeaders`,
     * GET `/v2/glossary/{guid}/categories/headers` — GLS-05, AGL-02).
     * @param glossaryGuid the glossary GUID
     * @param page the paging, or nothing for the server's defaults
     * @returns the category headers of the page
     */
    getGlossaryCategoriesHeaders(
        glossaryGuid: string,
        page: GlossaryPage = {},
    ): Observable<AtlasRelatedCategoryHeader[]> {
        return this.http.get<AtlasRelatedCategoryHeader[]>(
            this.glossaryUrl(`/${encodeURIComponent(glossaryGuid)}/categories/headers`),
            { params: this.pageParams(page) },
        );
    }

    /**
     * The glossary's terms, paged (`getGlossaryTerms`, GET
     * `/v2/glossary/{guid}/terms` — GTM-06, AGL-02).
     * @param glossaryGuid the glossary GUID
     * @param page the paging, or nothing for the server's defaults
     * @returns the terms of the page
     */
    getGlossaryTerms(glossaryGuid: string, page: GlossaryPage = {}): Observable<AtlasGlossaryTerm[]> {
        return this.http.get<AtlasGlossaryTerm[]>(this.glossaryUrl(`/${encodeURIComponent(glossaryGuid)}/terms`), {
            params: this.pageParams(page),
        });
    }

    /**
     * The glossary's term headers, paged (`getGlossaryTermHeaders`, GET
     * `/v2/glossary/{guid}/terms/headers` — GTM-06, AGL-02).
     * @param glossaryGuid the glossary GUID
     * @param page the paging, or nothing for the server's defaults
     * @returns the term headers of the page
     */
    getGlossaryTermsHeaders(glossaryGuid: string, page: GlossaryPage = {}): Observable<AtlasRelatedTermHeader[]> {
        return this.http.get<AtlasRelatedTermHeader[]>(
            this.glossaryUrl(`/${encodeURIComponent(glossaryGuid)}/terms/headers`),
            { params: this.pageParams(page) },
        );
    }

    /**
     * Update a glossary (`updateGlossary`, PUT `/v2/glossary/{guid}` —
     * GLS-03, AGL-03). The body guid is not rewritten here: the server
     * grafts the path GUID onto the body it stores, as in the twin (CLG-08).
     * @param glossaryGuid the glossary GUID of the path
     * @param glossary the glossary to store
     * @returns the updated glossary
     */
    updateGlossary(glossaryGuid: string, glossary: AtlasGlossary): Observable<AtlasGlossary> {
        return this.http.put<AtlasGlossary>(this.glossaryUrl(`/${encodeURIComponent(glossaryGuid)}`), glossary);
    }

    /**
     * Set the given attributes of a glossary (`partialUpdateGlossary`, PUT
     * `/v2/glossary/{guid}/partial` — GLS-03, AGL-04). The body is the plain
     * JSON object of attribute values (name, the two descriptions, language,
     * usage). A field the glossary does not have stays the server's answer
     * (`INVALID_PARTIAL_UPDATE_ATTR`).
     * @param glossaryGuid the glossary GUID
     * @param fields the attribute values to set
     * @returns the whole updated glossary
     * @throws ValueError-equivalent: a `Error` when `fields` is empty — the
     * server's answer for it is `BAD_REQUEST` (NO_PARTIAL_UPDATES), so the
     * client refuses the wasted round trip, as the twin's `_no_fields` does
     * (CLG-03). No request is made.
     */
    partialUpdateGlossary(glossaryGuid: string, fields: Record<string, unknown>): Observable<AtlasGlossary> {
        if (Object.keys(fields).length === 0) {
            throw new Error("no fields to set: the server answers BAD_REQUEST (NO_PARTIAL_UPDATES, GLS-03)");
        }
        return this.http.put<AtlasGlossary>(this.glossaryUrl(`/${encodeURIComponent(glossaryGuid)}/partial`), fields);
    }

    /**
     * Delete a glossary (`deleteGlossary`, DELETE `/v2/glossary/{guid}` —
     * GLS-04, CLG-09, AGL-05). Answers 204. The route has no `deleteType`.
     * @param glossaryGuid the glossary GUID
     */
    deleteGlossary(glossaryGuid: string): Observable<void> {
        return this.http.delete<void>(this.glossaryUrl(`/${encodeURIComponent(glossaryGuid)}`));
    }

    /**
     * The glossary import template, as a download (`produceTemplate`, GET
     * `/v2/glossary/import/template` — GIM-06, AGL-06). The `{ body,
     * contentType }` pair of DD-315's shape, the twin of the Python client's
     * `(bytes, content-type)` tuple (CLG-06, CL-64).
     */
    glossaryImportTemplate(): Observable<AtlasExportAnswer> {
        return this.http
            .get(`${this.baseUrl}/atlas/v2/glossary/import/template`, {
                responseType: "arraybuffer",
                observe: "response",
            })
            .pipe(
                map((response) => ({
                    body: response.body,
                    contentType: response.headers.get("content-type") ?? "",
                })),
            );
    }

    /**
     * Apply a glossary import file (`importGlossaryData`, POST
     * `/v2/glossary/import` — GIM-01..GIM-05, DV-104, AGL-06). The `file`
     * form part carries the bytes; the client never reads a path (CLG-06).
     * @param fileName the name the file part carries
     * @param content the CSV or Excel bytes
     * @returns the terms the import made and those it could not
     */
    importGlossaryData(fileName: string, content: Blob): Observable<BulkImportResponse> {
        const form = new FormData();
        form.append("file", content, fileName);
        return this.http.post<BulkImportResponse>(this.glossaryUrl("/import"), form);
    }

    private glossaryUrl(path: string): string {
        return `${this.baseUrl}/atlas/v2/glossary${path}`;
    }

    /**
     * The paging as the twin's `_page_params` builds it (CLG-02): a default
     * travels as absence — an unset field, or a `0` `limit`/`offset`, sends
     * nothing — and every value that is given always travels, `-1` included.
     */
    private pageParams(page: GlossaryPage): HttpParams {
        let params = new HttpParams();
        if (page.limit !== undefined && page.limit !== 0) {
            params = params.set("limit", String(page.limit));
        }
        if (page.offset !== undefined && page.offset !== 0) {
            params = params.set("offset", String(page.offset));
        }
        if (page.sort !== undefined) {
            params = params.set("sort", page.sort);
        }
        return params;
    }
}
