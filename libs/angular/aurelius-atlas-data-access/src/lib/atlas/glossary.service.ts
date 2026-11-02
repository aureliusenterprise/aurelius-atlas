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
    AtlasRelatedObjectId,
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
 * The glossary endpoints of the Atlas server (`GlossaryREST`, AGL-01..07,
 * AGT-01..06, AGC-01..04): all thirty-two routes of `routes/glossary.py` —
 * the thirteen about glossaries themselves (8.20), the eleven about terms
 * (8.21), and the eight about categories (8.22). Every URL composes from the
 * injected {@link API_BASE_URL} (APC-01). The Python twin is
 * `AtlasClient.glossary` (CLG-01..CLG-09); its resource-object methods
 * (`glossary.glossaries()`, …) compose into these flat names, as 8.15/8.16
 * did for lineage and relationships.
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

    /**
     * The term (`getTerm`, GET `/v2/glossary/term/{guid}` — GTM-01, AGT-01).
     * @param termGuid the term GUID
     * @returns the term, bare
     */
    getTerm(termGuid: string): Observable<AtlasGlossaryTerm> {
        return this.http.get<AtlasGlossaryTerm>(this.glossaryUrl(`/term/${encodeURIComponent(termGuid)}`));
    }

    /**
     * Create a term (`createTerm`, POST `/v2/glossary/term` — GTM-02,
     * AGT-01). The anchor is not checked here: a term without one is the
     * server's `MISSING_MANDATORY_ANCHOR` answer, as in the twin (CLG-05).
     * @param term the term to create
     * @returns the created term, with its guid
     */
    createTerm(term: AtlasGlossaryTerm): Observable<AtlasGlossaryTerm> {
        return this.http.post<AtlasGlossaryTerm>(this.glossaryUrl("/term"), term);
    }

    /**
     * Create every term (`createTerms`, POST `/v2/glossary/terms` — GTM-02,
     * AGT-01). Every anchor is the server's check (CLG-05).
     * @param terms the terms to create
     * @returns the created terms, in the request's order
     */
    createTerms(terms: AtlasGlossaryTerm[]): Observable<AtlasGlossaryTerm[]> {
        return this.http.post<AtlasGlossaryTerm[]>(this.glossaryUrl("/terms"), terms);
    }

    /**
     * Update a term (`updateTerm`, PUT `/v2/glossary/term/{guid}` — GTM-04,
     * AGT-02). The body guid is not rewritten here: the server grafts the
     * path GUID onto the body it stores (CLG-08).
     * @param termGuid the term GUID of the path
     * @param term the term to store
     * @returns the updated term
     */
    updateTerm(termGuid: string, term: AtlasGlossaryTerm): Observable<AtlasGlossaryTerm> {
        return this.http.put<AtlasGlossaryTerm>(this.glossaryUrl(`/term/${encodeURIComponent(termGuid)}`), term);
    }

    /**
     * Set the given attributes of a term (`partialUpdateTerm`, PUT
     * `/v2/glossary/term/{guid}/partial` — GTM-04, AGT-02). The body is the
     * plain JSON object of attribute values (name, the two descriptions,
     * abbreviation, usage). A field the term does not have stays the
     * server's answer (`INVALID_PARTIAL_UPDATE_ATTR`).
     * @param termGuid the term GUID
     * @param fields the attribute values to set
     * @returns the whole updated term
     * @throws a `Error` when `fields` is empty — the server's answer for it
     * is `BAD_REQUEST` (NO_PARTIAL_UPDATES, GTM-04), so the client refuses
     * the wasted round trip, as the twin's `_no_fields` does (CLG-03). No
     * request is made.
     */
    partialUpdateTerm(termGuid: string, fields: Record<string, unknown>): Observable<AtlasGlossaryTerm> {
        if (Object.keys(fields).length === 0) {
            throw new Error("no fields to set: the server answers BAD_REQUEST (NO_PARTIAL_UPDATES, GTM-04)");
        }
        return this.http.put<AtlasGlossaryTerm>(
            this.glossaryUrl(`/term/${encodeURIComponent(termGuid)}/partial`),
            fields,
        );
    }

    /**
     * Delete a term (`deleteTerm`, DELETE `/v2/glossary/term/{guid}` —
     * GTM-05, CLG-09, AGT-03). Answers 204.
     * @param termGuid the term GUID
     */
    deleteTerm(termGuid: string): Observable<void> {
        return this.http.delete<void>(this.glossaryUrl(`/term/${encodeURIComponent(termGuid)}`));
    }

    /**
     * The term's related terms by relation (`getRelatedTerms`, GET
     * `/v2/glossary/terms/{guid}/related` — GTM-06, CLG-07, AGT-04). The key
     * is the relation's JSON name (`seeAlso`, `synonyms`, …). The page
     * parameters the server reads and ignores, the client does not send.
     * @param termGuid the term GUID
     * @returns the headers of each relation, keyed by relation name
     */
    getRelatedTerms(termGuid: string): Observable<Record<string, AtlasRelatedTermHeader[]>> {
        return this.http.get<Record<string, AtlasRelatedTermHeader[]>>(
            this.glossaryUrl(`/terms/${encodeURIComponent(termGuid)}/related`),
        );
    }

    /**
     * The entities assigned to the term (`getAssignedEntities`, GET
     * `/v2/glossary/terms/{guid}/assignedEntities` — GTA-01, AGT-05). The
     * paging follows {@link GlossaryPage}.
     * @param termGuid the term GUID
     * @param page the paging, or nothing for the server's defaults
     * @returns the assigned entities of the page
     */
    getAssignedEntities(termGuid: string, page: GlossaryPage = {}): Observable<AtlasRelatedObjectId[]> {
        return this.http.get<AtlasRelatedObjectId[]>(
            this.glossaryUrl(`/terms/${encodeURIComponent(termGuid)}/assignedEntities`),
            { params: this.pageParams(page) },
        );
    }

    /**
     * Assign the term to the entities (`assignTerm`, POST
     * `/v2/glossary/terms/{guid}/assignedEntities` — GTA-02, CLG-04,
     * AGT-06). The body is the bare array of related object ids; nothing is
     * checked here. Answers 204.
     * @param termGuid the term GUID
     * @param objectIds the entities to assign, as related object ids
     */
    assignTerm(termGuid: string, objectIds: AtlasRelatedObjectId[]): Observable<void> {
        return this.http.post<void>(
            this.glossaryUrl(`/terms/${encodeURIComponent(termGuid)}/assignedEntities`),
            objectIds,
        );
    }

    /**
     * Remove the term's assignments from the entities (`removeTermAssignment`,
     * DELETE `/v2/glossary/terms/{guid}/assignedEntities` — GTA-03, CLG-04,
     * AGT-06). The body rides `HttpClient.request` — the typed
     * `HttpClient.delete` takes none. Answers 204.
     * @param termGuid the term GUID
     * @param objectIds the assignments to remove, as related object ids
     */
    removeTermAssignment(termGuid: string, objectIds: AtlasRelatedObjectId[]): Observable<void> {
        return this.http.request<void>(
            "DELETE",
            this.glossaryUrl(`/terms/${encodeURIComponent(termGuid)}/assignedEntities`),
            { body: objectIds },
        );
    }

    /**
     * As {@link removeTermAssignment} (PUT
     * `/v2/glossary/terms/{guid}/assignedEntities` — GTA-03, CLG-04,
     * AGT-06). Kept so a caller states its intent. Answers 204.
     * @param termGuid the term GUID
     * @param objectIds the assignments to disassociate, as related object ids
     */
    disassociateTermAssignment(termGuid: string, objectIds: AtlasRelatedObjectId[]): Observable<void> {
        return this.http.put<void>(
            this.glossaryUrl(`/terms/${encodeURIComponent(termGuid)}/assignedEntities`),
            objectIds,
        );
    }

    /**
     * The category's terms, paged (`categoryTerms`, GET
     * `/v2/glossary/category/{guid}/terms` — GTM-06, AGC-01). The paging
     * follows {@link GlossaryPage}.
     * @param categoryGuid the category GUID
     * @param page the paging, or nothing for the server's defaults
     * @returns the term headers of the page
     */
    getCategoryTerms(categoryGuid: string, page: GlossaryPage = {}): Observable<AtlasRelatedTermHeader[]> {
        return this.http.get<AtlasRelatedTermHeader[]>(
            this.glossaryUrl(`/category/${encodeURIComponent(categoryGuid)}/terms`),
            { params: this.pageParams(page) },
        );
    }

    /**
     * The category (`category`, GET `/v2/glossary/category/{guid}` — GCT-01,
     * AGC-01).
     * @param categoryGuid the category GUID
     * @returns the category, bare
     */
    getCategory(categoryGuid: string): Observable<AtlasGlossaryCategory> {
        return this.http.get<AtlasGlossaryCategory>(this.glossaryUrl(`/category/${encodeURIComponent(categoryGuid)}`));
    }

    /**
     * The category's parent and children (`relatedCategories`, GET
     * `/v2/glossary/category/{guid}/related` — GCT-07, CLG-07, AGC-01). The
     * keys are `parent` and `children`; a missing relation is absent.
     * @param categoryGuid the category GUID
     * @returns the headers of each relation, keyed by relation name
     */
    getRelatedCategories(categoryGuid: string): Observable<Record<string, AtlasRelatedCategoryHeader[]>> {
        return this.http.get<Record<string, AtlasRelatedCategoryHeader[]>>(
            this.glossaryUrl(`/category/${encodeURIComponent(categoryGuid)}/related`),
        );
    }

    /**
     * Create a category (`createCategory`, POST `/v2/glossary/category` —
     * GCT-02, AGC-02). The anchor is not checked here: a category without
     * one is the server's `MISSING_MANDATORY_ANCHOR` answer, as in the twin
     * (CLG-05).
     * @param category the category to create
     * @returns the created category, with its guid
     */
    createCategory(category: AtlasGlossaryCategory): Observable<AtlasGlossaryCategory> {
        return this.http.post<AtlasGlossaryCategory>(this.glossaryUrl("/category"), category);
    }

    /**
     * Create every category (`createCategories`, POST
     * `/v2/glossary/categories` — GCT-02, AGC-02). Every anchor is the
     * server's check (CLG-05).
     * @param categories the categories to create
     * @returns the created categories, in the request's order
     */
    createCategories(categories: AtlasGlossaryCategory[]): Observable<AtlasGlossaryCategory[]> {
        return this.http.post<AtlasGlossaryCategory[]>(this.glossaryUrl("/categories"), categories);
    }

    /**
     * Update a category (`updateCategory`, PUT `/v2/glossary/category/{guid}`
     * — GCT-04, AGC-03). The body guid is not rewritten here: the server
     * grafts the path GUID onto the body it stores (CLG-08).
     * @param categoryGuid the category GUID of the path
     * @param category the category to store
     * @returns the updated category
     */
    updateCategory(categoryGuid: string, category: AtlasGlossaryCategory): Observable<AtlasGlossaryCategory> {
        return this.http.put<AtlasGlossaryCategory>(
            this.glossaryUrl(`/category/${encodeURIComponent(categoryGuid)}`),
            category,
        );
    }

    /**
     * Set the given attributes of a category (`partialUpdateCategory`, PUT
     * `/v2/glossary/category/{guid}/partial` — GCT-05, AGC-03). The body is
     * the plain JSON object of attribute values (name, the two
     * descriptions). A field the category does not have stays the server's
     * answer (`INVALID_PARTIAL_UPDATE_ATTR`).
     * @param categoryGuid the category GUID
     * @param fields the attribute values to set
     * @returns the whole updated category
     * @throws a `Error` when `fields` is empty — the server's answer for it
     * is `BAD_REQUEST` (NO_PARTIAL_UPDATES, GCT-05), so the client refuses
     * the wasted round trip, as the twin's `_no_fields` does (CLG-03). No
     * request is made.
     */
    partialUpdateCategory(categoryGuid: string, fields: Record<string, unknown>): Observable<AtlasGlossaryCategory> {
        if (Object.keys(fields).length === 0) {
            throw new Error("no fields to set: the server answers BAD_REQUEST (NO_PARTIAL_UPDATES, GCT-05)");
        }
        return this.http.put<AtlasGlossaryCategory>(
            this.glossaryUrl(`/category/${encodeURIComponent(categoryGuid)}/partial`),
            fields,
        );
    }

    /**
     * Delete a category (`deleteCategory`, DELETE
     * `/v2/glossary/category/{guid}` — GCT-06, CLG-09, AGC-04). Answers 204.
     * @param categoryGuid the category GUID
     */
    deleteCategory(categoryGuid: string): Observable<void> {
        return this.http.delete<void>(this.glossaryUrl(`/category/${encodeURIComponent(categoryGuid)}`));
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
