import { HttpClient, HttpParams } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { API_BASE_URL } from "./api-config";
import { AtlasTypeDef, AtlasTypeDefHeader, AtlasTypesDef, TypeDefsFilter } from "./atlas-typedef";

/**
 * The `HttpParams` of a typedef search: nil-dropped, booleans kept, the server's parameter
 * names kept verbatim (`SearchFilter`, TYR-06/07) — the Aurelius `createHttpParams`
 * idiom without lodash (the `filterParams` this lib already uses, lifted to `HttpParams`).
 * @param filter the search parameters
 * @returns the query parameters to send
 */
function searchParams(filter: TypeDefsFilter): HttpParams {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(filter)) {
        if (value != null && value !== "") {
            params = params.set(key, `${value}`);
        }
    }
    return params;
}

/** The path of each kind's by-name/by-guid lookups (`TypesREST.KIND_PATHS`, TYR-03). */
const KIND_PATHS = {
    enum: "enumdef",
    struct: "structdef",
    classification: "classificationdef",
    entity: "entitydef",
    relationship: "relationshipdef",
    businessMetadata: "businessmetadatadef",
} as const;

/** The kinds of the per-kind lookups. */
export type TypeDefKind = keyof typeof KIND_PATHS;

/**
 * The type-definition endpoints of the Atlas server (`TypesREST`, TYR-01..10, APC-02):
 * the lookups, searches, and create/update/delete of `TypesREST`. The wire shapes are
 * {@link AtlasTypesDef} and friends (APC-03); a non-2xx answer carries the typed Atlas
 * error body (APC-04 — see `atlas-error.ts`). Every URL composes from the injected
 * {@link API_BASE_URL} with the `/atlas` prefix intact (APC-01, DD-139).
 */
@Injectable({
    providedIn: "root",
})
export class TypeDefsService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(API_BASE_URL);

    private typesUrl(path: string): string {
        return `${this.baseUrl}/atlas/v2/types${path}`;
    }

    /**
     * The definitions a search keeps (TYR-05..07, APC-02) — `getAllTypeDefs`.
     * @param filter the search parameters
     * @returns the definitions of every kind the filter keeps
     */
    getTypedefs(filter: TypeDefsFilter = {}): Observable<AtlasTypesDef> {
        return this.http.get<AtlasTypesDef>(this.typesUrl("/typedefs"), { params: searchParams(filter) });
    }

    /**
     * The identity headers of the definitions a search keeps (TYR-08) — the cheap list
     * behind a type browser.
     * @param filter the search parameters
     * @returns one header per kept definition
     */
    getTypedefHeaders(filter: TypeDefsFilter = {}): Observable<AtlasTypeDefHeader[]> {
        return this.http.get<AtlasTypeDefHeader[]>(this.typesUrl("/typedefs/headers"), {
            params: searchParams(filter),
        });
    }

    /**
     * The definition of any kind with that name (TYR-01) — the legacy
     * `getTypeDefByName`/`getTypeByName` pair, one method (DD-140).
     * @param name the type name
     * @returns the definition, its kind in `category`
     */
    getTypeDefByName(name: string): Observable<AtlasTypeDef> {
        return this.http.get<AtlasTypeDef>(this.typesUrl(`/typedef/name/${encodeURIComponent(name)}`));
    }

    /**
     * The definition of any kind with that GUID (TYR-02).
     * @param guid the type GUID
     * @returns the definition, its kind in `category`
     */
    getTypeDefByGuid(guid: string): Observable<AtlasTypeDef> {
        return this.http.get<AtlasTypeDef>(this.typesUrl(`/typedef/guid/${encodeURIComponent(guid)}`));
    }

    /**
     * The definition of one kind with that name (TYR-03) — the per-kind
     * `/{kind}def/name/{name}` lookups, one method.
     * @param kind the definition kind
     * @param name the type name
     * @returns the definition
     */
    getTypedefByName(kind: TypeDefKind, name: string): Observable<AtlasTypeDef> {
        return this.http.get<AtlasTypeDef>(this.typesUrl(`/${KIND_PATHS[kind]}/name/${encodeURIComponent(name)}`));
    }

    /**
     * The definition of one kind with that GUID (TYR-03) — the per-kind
     * `/{kind}def/guid/{guid}` lookups, one method.
     * @param kind the definition kind
     * @param guid the type GUID
     * @returns the definition
     */
    getTypedefByGuid(kind: TypeDefKind, guid: string): Observable<AtlasTypeDef> {
        return this.http.get<AtlasTypeDef>(this.typesUrl(`/${KIND_PATHS[kind]}/guid/${encodeURIComponent(guid)}`));
    }

    /**
     * Create the definitions, all or none (TYR-09) — `createAtlasTypeDefs`.
     * @param typesDef the definitions to create
     * @returns the created definitions, as stored
     */
    createTypedefs(typesDef: AtlasTypesDef): Observable<AtlasTypesDef> {
        return this.http.post<AtlasTypesDef>(this.typesUrl("/typedefs"), typesDef);
    }

    /**
     * Update the definitions, all or none (TYR-09) — `updateAtlasTypeDefs`.
     * @param typesDef the definitions to update
     * @returns the updated definitions, as stored
     */
    updateTypedefs(typesDef: AtlasTypesDef): Observable<AtlasTypesDef> {
        return this.http.put<AtlasTypesDef>(this.typesUrl("/typedefs"), typesDef);
    }

    /**
     * Delete the definitions, all or none (TYR-10) — `deleteAtlasTypeDefs`; 204 answers.
     * @param typesDef the definitions to delete
     * @returns completes when the server has deleted them
     */
    deleteTypedefs(typesDef: AtlasTypesDef): Observable<void> {
        return this.http.delete<void>(this.typesUrl("/typedefs"), { body: typesDef });
    }

    /**
     * Delete the named definition (TYR-10) — `deleteAtlasTypeByName`; 204 answers.
     * @param name the type name
     * @returns completes when the server has deleted it
     */
    deleteTypedefByName(name: string): Observable<void> {
        return this.http.delete<void>(this.typesUrl(`/typedef/name/${encodeURIComponent(name)}`));
    }
}
