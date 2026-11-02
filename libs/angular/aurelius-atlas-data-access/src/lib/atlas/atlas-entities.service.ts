import { HttpClient, HttpParams } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { map, Observable } from "rxjs";
import { API_BASE_URL } from "../api-config";
import type { EntityAuditEventV2 } from "./atlas-audit";
import type {
    AtlasClassification,
    AtlasClassifications,
    AtlasEntitiesWithExtInfo,
    AtlasEntityWithExtInfo,
    ClassificationAssociateRequest,
} from "./atlas-entity";
import type { AtlasExportAnswer, BulkImportResponse } from "./atlas-impexp";
import type { DeleteType, EntityMutationResponse } from "./atlas-mutation";
import type { AtlasEntityHeader, AtlasEntityHeaders } from "./atlas-search";

/**
 * The audit-read query of {@link AtlasEntitiesService.getAuditEvents}
 * (AEN-05). Every field travels only when given — unlike the lib's flag
 * habit, a given `count` of 0 or `offset` of -1 travels too: those are
 * choices, not defaults (CLE-10, the twin's own deviation from `_present`).
 */
export type EntityAuditQuery = {
    auditAction?: EntityAuditEventV2["action"];
    startKey?: string;
    count?: number;
    offset?: number;
    sortBy?: string;
    sortOrder?: string;
};

/**
 * The entity endpoints of the Atlas server (`EntityREST`, DET-03): the reads
 * of a guid, a unique attribute, a set of guids, and the entity audits
 * (8.17, AEN-01..AEN-07), the writes and deletes (8.18, AEW-01..AEW-06), and
 * the classifications, business metadata, and labels (8.19, ACL-01..ACL-09) —
 * all thirty-seven routes of `routes/entity.py`, the Angular twin of
 * `AtlasClient.entity` (CLE-01..CLE-12). The wire
 * format is typed from the Apache Atlas 2.4.0 source (see
 * `atlas-entity.ts`); the endpoints are server 2.3's surface — against
 * today's server (admin and types only) the calls answer 404, and the specs
 * assert the request, not a 200 (DD-140's honesty rule, DD-187).
 *
 * Every URL composes from the injected {@link API_BASE_URL} with the
 * `/atlas` prefix intact (APC-01, DD-139) — the server API is the webapp's
 * one data plane (ADR 054, DD-188). No screen calls this service until the
 * 2.3+7.6 wiring increment (DET-02, DD-186).
 */
@Injectable({
    providedIn: "root",
})
export class AtlasEntitiesService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(API_BASE_URL);

    private entityUrl(path: string): string {
        return `${this.baseUrl}/atlas/v2/entity${path}`;
    }

    /**
     * The `minExtInfo` / `ignoreRelationships` pair, each sent only when
     * true (AEN-01, APC-11 — the Java-default-absence rule the Python twin
     * applies through `_present`, CLE-02).
     */
    private extInfoParams(minExtInfo: boolean, ignoreRelationships: boolean, base = new HttpParams()): HttpParams {
        let params = base;
        if (minExtInfo) {
            params = params.set("minExtInfo", "true");
        }
        if (ignoreRelationships) {
            params = params.set("ignoreRelationships", "true");
        }
        return params;
    }

    /**
     * The unique-attribute values as `attr:<name>` parameters, as the route's
     * `getAttributes` reads them (AEN-03, ERD-08, CLE-03).
     */
    private attrParams(attributes: Record<string, unknown>): HttpParams {
        let params = new HttpParams();
        for (const [name, value] of Object.entries(attributes)) {
            params = params.set(`attr:${name}`, String(value));
        }
        return params;
    }

    /**
     * The entity with that GUID, as `AtlasEntityWithExtInfo`
     * (`EntityREST.getEntityByGuid`, GET `/v2/entity/guid/{guid}` — the
     * surface of increment 2.3, extended by 8.17). The guid is URL-encoded,
     * as every lookup in the typedefs client encodes its key (APC-03's
     * idiom). Each flag travels as its query parameter only when true, so
     * the default call sends none (AEN-01, DET-03).
     * @param guid the entity GUID
     * @param minExtInfo ask for the minimal ext-info body (ERD-02)
     * @param ignoreRelationships leave the relationship attributes out
     * @returns the entity read, its type definitions in the same body
     */
    getEntityByGuid(guid: string, minExtInfo = false, ignoreRelationships = false): Observable<AtlasEntityWithExtInfo> {
        return this.http.get<AtlasEntityWithExtInfo>(this.entityUrl(`/guid/${encodeURIComponent(guid)}`), {
            params: this.extInfoParams(minExtInfo, ignoreRelationships),
        });
    }

    /**
     * The header of the entity with that GUID — its identity, status,
     * classifications and labels, without its attributes
     * (`EntityREST.getEntityHeaderByGuid`, GET `/v2/entity/guid/{guid}/header`,
     * ERD-07, AEN-02). The route reads no flags, so the call sends none.
     * @param guid the entity GUID
     */
    getEntityHeaderByGuid(guid: string): Observable<AtlasEntityHeader> {
        return this.http.get<AtlasEntityHeader>(this.entityUrl(`/guid/${encodeURIComponent(guid)}/header`));
    }

    /**
     * The entity that holds the given unique-attribute values, as
     * `AtlasEntityWithExtInfo` (`EntityREST.getEntityByUniqueAttributes`,
     * GET `/v2/entity/uniqueAttribute/type/{typeName}` — ERD-08, AEN-03).
     * Each entry travels as an `attr:<name>` query parameter; the flags
     * follow {@link getEntityByGuid}.
     * @param typeName the entity type to look in
     * @param attributes the unique attribute values, e.g. `{ qualifiedName: "s1.table.orders" }`
     * @param minExtInfo ask for the minimal ext-info body
     * @param ignoreRelationships leave the relationship attributes out
     */
    getEntityByUniqueAttributes(
        typeName: string,
        attributes: Record<string, unknown>,
        minExtInfo = false,
        ignoreRelationships = false,
    ): Observable<AtlasEntityWithExtInfo> {
        const params = this.extInfoParams(minExtInfo, ignoreRelationships, this.attrParams(attributes));
        return this.http.get<AtlasEntityWithExtInfo>(
            this.entityUrl(`/uniqueAttribute/type/${encodeURIComponent(typeName)}`),
            { params },
        );
    }

    /**
     * The header of the entity that holds the given unique-attribute values
     * (`EntityREST.getEntityHeaderByUniqueAttributes`, GET
     * `/v2/entity/uniqueAttribute/type/{typeName}/header` — ERD-07, AEN-02).
     * @param typeName the entity type to look in
     * @param attributes the unique attribute values
     */
    getEntityHeaderByUniqueAttributes(
        typeName: string,
        attributes: Record<string, unknown>,
    ): Observable<AtlasEntityHeader> {
        return this.http.get<AtlasEntityHeader>(
            this.entityUrl(`/uniqueAttribute/type/${encodeURIComponent(typeName)}/header`),
            { params: this.attrParams(attributes) },
        );
    }

    /**
     * The entities of every GUID, in order, as `AtlasEntitiesWithExtInfo`
     * (`EntityREST.getEntitiesByGuids`, GET `/v2/entity/bulk` — ERD-01,
     * AEN-04). Every GUID travels as a repeated `guid` query parameter; an
     * empty list is the server's `INSTANCE_GUID_NOT_FOUND` (ERD-01) — the
     * client sends it as asked.
     * @param guids the entity GUIDs
     * @param minExtInfo ask for the minimal ext-info body
     * @param ignoreRelationships leave the relationship attributes out
     */
    getEntitiesByGuids(
        guids: string[],
        minExtInfo = false,
        ignoreRelationships = false,
    ): Observable<AtlasEntitiesWithExtInfo> {
        let params = this.extInfoParams(minExtInfo, ignoreRelationships);
        for (const guid of guids) {
            params = params.append("guid", guid);
        }
        return this.http.get<AtlasEntitiesWithExtInfo>(this.entityUrl("/bulk"), { params });
    }

    /**
     * The entity each unique-attribute set finds, as `AtlasEntitiesWithExtInfo`
     * (`EntityREST.getEntitiesByUniqueAttributes`, GET
     * `/v2/entity/bulk/uniqueAttribute/type/{typeName}` — ERD-08, AEN-04).
     * Set number `n` (1-based, in the given order — DV-19) renders its values
     * as `attr_<n>:<name>` parameters, distinct from the single read's
     * `attr:<name>` (AEN-03).
     * @param typeName the entity type to look in
     * @param attributeSets one unique-attribute map per entity wanted
     * @param minExtInfo ask for the minimal ext-info body
     * @param ignoreRelationships leave the relationship attributes out
     */
    getEntitiesByUniqueAttributes(
        typeName: string,
        attributeSets: Record<string, unknown>[],
        minExtInfo = false,
        ignoreRelationships = false,
    ): Observable<AtlasEntitiesWithExtInfo> {
        let params = new HttpParams();
        attributeSets.forEach((attributes, index) => {
            for (const [name, value] of Object.entries(attributes)) {
                params = params.set(`attr_${index + 1}:${name}`, String(value));
            }
        });
        params = this.extInfoParams(minExtInfo, ignoreRelationships, params);
        return this.http.get<AtlasEntitiesWithExtInfo>(
            this.entityUrl(`/bulk/uniqueAttribute/type/${encodeURIComponent(typeName)}`),
            { params },
        );
    }

    /**
     * The audit events of the entity with that GUID, newest first or sorted
     * (`EntityREST.getAuditEvents`, GET `/v2/entity/{guid}/audit` —
     * AUD-06..AUD-09, AEN-05). Each field of {@link EntityAuditQuery} travels
     * only when given; a given `count` of 0 or `offset` of -1 travels too
     * (CLE-10). An absent `count` the server reads as 100, an absent
     * `offset` as -1.
     * @param guid the entity GUID
     * @param query the audit paging, sorting, and action filter
     */
    getAuditEvents(guid: string, query: EntityAuditQuery = {}): Observable<EntityAuditEventV2[]> {
        const given: Record<string, unknown> = {
            auditAction: query.auditAction,
            startKey: query.startKey,
            count: query.count,
            offset: query.offset,
            sortBy: query.sortBy,
            sortOrder: query.sortOrder,
        };
        let params = new HttpParams();
        for (const [name, value] of Object.entries(given)) {
            if (value !== undefined) {
                params = params.set(name, String(value));
            }
        }
        return this.http.get<EntityAuditEventV2[]>(this.entityUrl(`/${encodeURIComponent(guid)}/audit`), { params });
    }

    /**
     * The entities whose classifications changed since the given time
     * (`EntityREST.getChangedClassifications`, GET `/v2/entity/bulk/headers`
     * with `tagUpdateStartTime` — CAU-07, AEN-06). The client sends no end
     * time; the server uses its own clock.
     * @param since epoch milliseconds to search from
     */
    getChangedClassifications(since: number): Observable<AtlasEntityHeaders> {
        const params = new HttpParams().set("tagUpdateStartTime", String(since));
        return this.http.get<AtlasEntityHeaders>(this.entityUrl("/bulk/headers"), { params });
    }

    /**
     * `deleteType` travels only when given — absent, the server applies its
     * own setting (EDL-04, AEW-05, CLE-04).
     */
    private deleteTypeParams(deleteType?: DeleteType): HttpParams {
        return deleteType === undefined ? new HttpParams() : new HttpParams().set("deleteType", deleteType);
    }

    /**
     * Create the entity — and the entities it names — or update them
     * (`EntityREST.createOrUpdate`, POST `/v2/entity` — EWR-02, AEW-01). The
     * body is the bare `AtlasEntityWithExtInfo`; the client validates nothing
     * the server validates (CLE-12).
     * @param entity the entity and the entities it refers to
     * @returns the mutated headers and guid assignments (ENT-17)
     */
    createOrUpdateEntity(entity: AtlasEntityWithExtInfo): Observable<EntityMutationResponse> {
        return this.http.post<EntityMutationResponse>(this.entityUrl(""), entity);
    }

    /**
     * Create or update every entity of the bulk body (`EntityREST`'s
     * `createOrUpdate` of `AtlasEntitiesWithExtInfo`, POST
     * `/v2/entity/bulk` — EWR-02, AEW-02).
     * @param entities the entities to write, and the entities they refer to
     */
    createOrUpdateEntities(entities: AtlasEntitiesWithExtInfo): Observable<EntityMutationResponse> {
        return this.http.post<EntityMutationResponse>(this.entityUrl("/bulk"), entities);
    }

    /**
     * Set one attribute of the entity with that GUID (`EntityREST`'s
     * `partialUpdateEntityAttrByGuid`, PUT `/v2/entity/guid/{guid}` — EWR-15,
     * AEW-03). The body is the bare JSON value — a string, a number, an
     * array — the server reads whatever it is as the attribute's new value.
     * The optional `name` names the attribute and travels only when given.
     * @param guid the entity GUID
     * @param value the attribute's new value, as JSON
     * @param name the attribute name, when the body alone does not name it
     */
    partialUpdateAttribute(guid: string, value: unknown, name?: string): Observable<EntityMutationResponse> {
        const params = name === undefined ? new HttpParams() : new HttpParams().set("name", name);
        return this.http.put<EntityMutationResponse>(this.entityUrl(`/guid/${encodeURIComponent(guid)}`), value, {
            params,
        });
    }

    /**
     * Partially update the entity that holds the given unique-attribute
     * values (`EntityREST.partialUpdateEntityByUniqueAttributes`, PUT
     * `/v2/entity/uniqueAttribute/type/{typeName}` — EWR-14, AEW-04). The
     * attributes travel as `attr:<name>` parameters (AEN-03) and the body is
     * the bare `AtlasEntityWithExtInfo` of the fields to change.
     * @param typeName the entity type to look in
     * @param attributes the unique attribute values that find the entity
     * @param entity the fields to change, as a sparse entity body
     */
    partialUpdateByUniqueAttributes(
        typeName: string,
        attributes: Record<string, unknown>,
        entity: AtlasEntityWithExtInfo,
    ): Observable<EntityMutationResponse> {
        return this.http.put<EntityMutationResponse>(
            this.entityUrl(`/uniqueAttribute/type/${encodeURIComponent(typeName)}`),
            entity,
            { params: this.attrParams(attributes) },
        );
    }

    /**
     * Delete the entity with that GUID, and what it owns (`EntityREST.deleteByGuid`,
     * DELETE `/v2/entity/guid/{guid}` — EDL-01, AEW-05).
     * @param guid the entity GUID
     * @param deleteType `SOFT`/`HARD` to override the server's strategy (EDL-04)
     */
    deleteEntityByGuid(guid: string, deleteType?: DeleteType): Observable<EntityMutationResponse> {
        return this.http.delete<EntityMutationResponse>(this.entityUrl(`/guid/${encodeURIComponent(guid)}`), {
            params: this.deleteTypeParams(deleteType),
        });
    }

    /**
     * Delete the entities of every GUID, and what they own
     * (`EntityREST.deleteByGuids`, DELETE `/v2/entity/bulk` — EDL-01/EDL-02,
     * AEW-05). Every GUID travels as a repeated `guid` parameter (AEN-04's
     * shape).
     * @param guids the entity GUIDs
     * @param deleteType `SOFT`/`HARD` to override the server's strategy
     */
    deleteEntitiesByGuids(guids: string[], deleteType?: DeleteType): Observable<EntityMutationResponse> {
        let params = this.deleteTypeParams(deleteType);
        for (const guid of guids) {
            params = params.append("guid", guid);
        }
        return this.http.delete<EntityMutationResponse>(this.entityUrl("/bulk"), { params });
    }

    /**
     * Delete the entity that holds the given unique-attribute values
     * (`EntityREST.deleteByUniqueAttribute`, DELETE
     * `/v2/entity/uniqueAttribute/type/{typeName}` — EDL-02, AEW-05).
     * @param typeName the entity type to look in
     * @param attributes the unique attribute values that find the entity
     * @param deleteType `SOFT`/`HARD` to override the server's strategy
     */
    deleteEntityByUniqueAttributes(
        typeName: string,
        attributes: Record<string, unknown>,
        deleteType?: DeleteType,
    ): Observable<EntityMutationResponse> {
        let params = this.attrParams(attributes);
        if (deleteType !== undefined) {
            params = params.set("deleteType", deleteType);
        }
        return this.http.delete<EntityMutationResponse>(
            this.entityUrl(`/uniqueAttribute/type/${encodeURIComponent(typeName)}`),
            { params },
        );
    }

    /**
     * A classification of the entity with that GUID, by its type name
     * (`EntityREST.getClassification`, GET `/v2/entity/guid/{guid}/classification/{name}`
     * — CLS-03, ACL-01).
     * @param guid the entity GUID
     * @param classificationName the classification type name
     */
    getClassification(guid: string, classificationName: string): Observable<AtlasClassification> {
        return this.http.get<AtlasClassification>(
            this.entityUrl(
                `/guid/${encodeURIComponent(guid)}/classification/${encodeURIComponent(classificationName)}`,
            ),
        );
    }

    /**
     * The entity's classifications, as an `AtlasClassifications` `PList`
     * (`EntityREST.getClassifications`, GET `/v2/entity/guid/{guid}/classifications`
     * — CLS-03, ACL-01). The route reads no paging parameters: the `PList`
     * carries the whole-list answer.
     * @param guid the entity GUID
     */
    getClassifications(guid: string): Observable<AtlasClassifications> {
        return this.http.get<AtlasClassifications>(this.entityUrl(`/guid/${encodeURIComponent(guid)}/classifications`));
    }

    /**
     * Attach the classifications to the entity (`EntityREST.addClassifications`,
     * POST `/v2/entity/guid/{guid}/classifications` — CLS-04/CLS-05, ACL-02).
     * The body is the bare JSON array. Answers 204.
     * @param guid the entity GUID
     * @param classifications the classifications to attach
     */
    addClassifications(guid: string, classifications: AtlasClassification[]): Observable<void> {
        return this.http.post<void>(
            this.entityUrl(`/guid/${encodeURIComponent(guid)}/classifications`),
            classifications,
        );
    }

    /**
     * Attach the classifications to the entity holding the unique-attribute
     * values (`add…ByUniqueAttribute`, POST
     * `/v2/entity/uniqueAttribute/type/{typeName}/classifications` — CLS-06,
     * ACL-02). Answers 204.
     * @param typeName the entity type to look in
     * @param attributes the unique attribute values that find the entity
     * @param classifications the classifications to attach
     */
    addClassificationsByUniqueAttributes(
        typeName: string,
        attributes: Record<string, unknown>,
        classifications: AtlasClassification[],
    ): Observable<void> {
        return this.http.post<void>(
            this.entityUrl(`/uniqueAttribute/type/${encodeURIComponent(typeName)}/classifications`),
            classifications,
            { params: this.attrParams(attributes) },
        );
    }

    /**
     * Change the entity's classifications (`EntityREST.updateClassifications`,
     * PUT `/v2/entity/guid/{guid}/classifications` — CLS-08, ACL-02). Answers 204.
     * @param guid the entity GUID
     * @param classifications the classifications as changed
     */
    updateClassifications(guid: string, classifications: AtlasClassification[]): Observable<void> {
        return this.http.put<void>(
            this.entityUrl(`/guid/${encodeURIComponent(guid)}/classifications`),
            classifications,
        );
    }

    /**
     * Change the classifications of the entity holding the unique-attribute
     * values (PUT `/v2/entity/uniqueAttribute/type/{typeName}/classifications`
     * — CLS-06, ACL-02). Answers 204.
     * @param typeName the entity type to look in
     * @param attributes the unique attribute values that find the entity
     * @param classifications the classifications as changed
     */
    updateClassificationsByUniqueAttributes(
        typeName: string,
        attributes: Record<string, unknown>,
        classifications: AtlasClassification[],
    ): Observable<void> {
        return this.http.put<void>(
            this.entityUrl(`/uniqueAttribute/type/${encodeURIComponent(typeName)}/classifications`),
            classifications,
            { params: this.attrParams(attributes) },
        );
    }

    /**
     * Remove the entity's classification of that type name
     * (`EntityREST.deleteClassification`, DELETE
     * `/v2/entity/guid/{guid}/classification/{name}` — CLS-09, ACL-03). The
     * optional `associatedEntityGuid` travels only when given. Answers 204.
     * @param guid the entity GUID
     * @param classificationName the classification type name
     * @param associatedEntityGuid the propagation's source entity, when given
     */
    deleteClassification(guid: string, classificationName: string, associatedEntityGuid?: string): Observable<void> {
        const params =
            associatedEntityGuid === undefined
                ? new HttpParams()
                : new HttpParams().set("associatedEntityGuid", associatedEntityGuid);
        return this.http.delete<void>(
            this.entityUrl(
                `/guid/${encodeURIComponent(guid)}/classification/${encodeURIComponent(classificationName)}`,
            ),
            { params },
        );
    }

    /**
     * Remove the classification of the entity holding the unique-attribute
     * values (DELETE `/v2/entity/uniqueAttribute/type/{typeName}/classification/{name}`
     * — CLS-06, ACL-03). Answers 204.
     * @param typeName the entity type to look in
     * @param attributes the unique attribute values that find the entity
     * @param classificationName the classification type name
     */
    deleteClassificationByUniqueAttributes(
        typeName: string,
        attributes: Record<string, unknown>,
        classificationName: string,
    ): Observable<void> {
        return this.http.delete<void>(
            this.entityUrl(
                `/uniqueAttribute/type/${encodeURIComponent(typeName)}/classification/${encodeURIComponent(classificationName)}`,
            ),
            { params: this.attrParams(attributes) },
        );
    }

    /**
     * Attach one classification to many entities, by GUID or by unique
     * attributes (`EntityREST.addClassification`, POST
     * `/v2/entity/bulk/classification` — CLS-07, ACL-04). Answers 204. The
     * client checks nothing — the server answers `INVALID_PARAMETERS`
     * (CLE-12).
     * @param request the classification and its targets
     */
    associateClassification(request: ClassificationAssociateRequest): Observable<void> {
        return this.http.post<void>(this.entityUrl("/bulk/classification"), request);
    }

    /**
     * Give each header's entity its classifications (`EntityREST.setClassifications`,
     * POST `/v2/entity/bulk/setClassifications` — CLA-04, ACL-05). The answer
     * is a JSON array of per-guid summaries, not a model (DV-36): `unknown[]`,
     * never reordered.
     * @param headers the entities and their classifications, by guid
     */
    setClassifications(headers: AtlasEntityHeaders): Observable<unknown[]> {
        return this.http.post<unknown[]>(this.entityUrl("/bulk/setClassifications"), headers);
    }

    /**
     * Set the entity's business-attribute values, or replace them all with
     * `isOverwrite` (`EntityREST.addOrUpdateBusinessAttributes`, POST
     * `/v2/entity/guid/{guid}/businessmetadata` — BMD-01, ACL-06). The body
     * maps each business-metadata name to its attribute values, or null. The
     * `isOverwrite` flag travels only when true. Answers 204.
     * @param guid the entity GUID
     * @param attributes the values by business-metadata name
     * @param isOverwrite replace all values instead of setting the given ones
     */
    addOrUpdateBusinessMetadata(
        guid: string,
        attributes: Record<string, Record<string, unknown> | null>,
        isOverwrite = false,
    ): Observable<void> {
        const params = isOverwrite ? new HttpParams().set("isOverwrite", "true") : new HttpParams();
        return this.http.post<void>(this.entityUrl(`/guid/${encodeURIComponent(guid)}/businessmetadata`), attributes, {
            params,
        });
    }

    /**
     * Remove the entity's given business attributes (`removeBusinessAttributes`,
     * DELETE `/v2/entity/guid/{guid}/businessmetadata` — BMD-05, ACL-06). A
     * DELETE with a body rides `HttpClient.request` — the typed
     * `HttpClient.delete` takes none (ACL-06's platform note). Answers 204.
     * @param guid the entity GUID
     * @param attributes the attributes to remove, by business-metadata name
     */
    removeBusinessMetadata(guid: string, attributes: Record<string, Record<string, unknown> | null>): Observable<void> {
        return this.http.request<void>("DELETE", this.entityUrl(`/guid/${encodeURIComponent(guid)}/businessmetadata`), {
            body: attributes,
        });
    }

    /**
     * Set one business metadata's values on the entity (POST
     * `/v2/entity/guid/{guid}/businessmetadata/{bmName}` — BMD-03, ACL-06).
     * The body is the bare attribute map — the server files it under the name
     * in the path. Answers 204.
     * @param guid the entity GUID
     * @param bmName the business-metadata name
     * @param attributes the attribute values
     */
    addOrUpdateBusinessMetadataOf(guid: string, bmName: string, attributes: Record<string, unknown>): Observable<void> {
        return this.http.post<void>(
            this.entityUrl(`/guid/${encodeURIComponent(guid)}/businessmetadata/${encodeURIComponent(bmName)}`),
            attributes,
        );
    }

    /**
     * Remove one business metadata's attributes — or all of them, with an
     * empty map (DELETE `/v2/entity/guid/{guid}/businessmetadata/{bmName}` —
     * BMD-05, ACL-06). Answers 204.
     * @param guid the entity GUID
     * @param bmName the business-metadata name
     * @param attributes the attribute names to remove
     */
    removeBusinessMetadataOf(guid: string, bmName: string, attributes: Record<string, unknown>): Observable<void> {
        return this.http.request<void>(
            "DELETE",
            this.entityUrl(`/guid/${encodeURIComponent(guid)}/businessmetadata/${encodeURIComponent(bmName)}`),
            { body: attributes },
        );
    }

    /**
     * The business-metadata import template, as a download (`produceTemplate`,
     * GET `/v2/entity/businessmetadata/import/template` — BMI-01, ACL-07).
     * The `{ body, contentType }` pair of DD-315's shape, the twin of the
     * Python client's `(bytes, content-type)` tuple (CLE-09, CL-64).
     */
    businessMetadataTemplate(): Observable<AtlasExportAnswer> {
        return this.http
            .get(`${this.baseUrl}/atlas/v2/entity/businessmetadata/import/template`, {
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
     * Apply a business-metadata import file (`importBMAttributes`, POST
     * `/v2/entity/businessmetadata/import` — BMI-02..BMI-05, ACL-07). The
     * `file` form part carries the bytes; the client never reads a path
     * (CLE-09).
     * @param fileName the name the file part carries
     * @param content the CSV or Excel bytes
     * @returns the rows the import made and those it could not
     */
    importBusinessMetadata(fileName: string, content: Blob): Observable<BulkImportResponse> {
        const form = new FormData();
        form.append("file", content, fileName);
        return this.http.post<BulkImportResponse>(this.entityUrl("/businessmetadata/import"), form);
    }

    /**
     * The entity's labels become exactly these (`EntityREST.setLabels`, POST
     * `/v2/entity/guid/{guid}/labels` — LBL-01/LBL-02, ACL-08). The body is a
     * bare JSON array of names. Answers 204.
     * @param guid the entity GUID
     * @param labels the labels to set
     */
    setLabels(guid: string, labels: string[]): Observable<void> {
        return this.http.post<void>(this.entityUrl(`/guid/${encodeURIComponent(guid)}/labels`), labels);
    }

    /**
     * Add the labels to the entity's (`EntityREST.addLabels`, PUT
     * `/v2/entity/guid/{guid}/labels` — LBL-01/LBL-03, ACL-08). Answers 204.
     * @param guid the entity GUID
     * @param labels the labels to add
     */
    addLabels(guid: string, labels: string[]): Observable<void> {
        return this.http.put<void>(this.entityUrl(`/guid/${encodeURIComponent(guid)}/labels`), labels);
    }

    /**
     * Take the labels from the entity's (`EntityREST.removeLabels`, DELETE
     * `/v2/entity/guid/{guid}/labels` — LBL-01/LBL-04, ACL-08). The body
     * rides `HttpClient.request` (ACL-06's platform note). Answers 204.
     * @param guid the entity GUID
     * @param labels the labels to remove
     */
    removeLabels(guid: string, labels: string[]): Observable<void> {
        return this.http.request<void>("DELETE", this.entityUrl(`/guid/${encodeURIComponent(guid)}/labels`), {
            body: labels,
        });
    }

    /**
     * The labels of the entity holding the unique-attribute values become
     * exactly these (POST `/v2/entity/uniqueAttribute/type/{typeName}/labels`
     * — LBL-02, ACL-08). Answers 204.
     * @param typeName the entity type to look in
     * @param attributes the unique attribute values that find the entity
     * @param labels the labels to set
     */
    setLabelsByUniqueAttributes(
        typeName: string,
        attributes: Record<string, unknown>,
        labels: string[],
    ): Observable<void> {
        return this.http.post<void>(
            this.entityUrl(`/uniqueAttribute/type/${encodeURIComponent(typeName)}/labels`),
            labels,
            { params: this.attrParams(attributes) },
        );
    }

    /**
     * Add the labels to the entity holding the unique-attribute values (PUT
     * `/v2/entity/uniqueAttribute/type/{typeName}/labels` — LBL-03, ACL-08).
     * Answers 204.
     * @param typeName the entity type to look in
     * @param attributes the unique attribute values that find the entity
     * @param labels the labels to add
     */
    addLabelsByUniqueAttributes(
        typeName: string,
        attributes: Record<string, unknown>,
        labels: string[],
    ): Observable<void> {
        return this.http.put<void>(
            this.entityUrl(`/uniqueAttribute/type/${encodeURIComponent(typeName)}/labels`),
            labels,
            { params: this.attrParams(attributes) },
        );
    }

    /**
     * Take the labels from the entity holding the unique-attribute values
     * (DELETE `/v2/entity/uniqueAttribute/type/{typeName}/labels` — LBL-04,
     * ACL-08). Answers 204.
     * @param typeName the entity type to look in
     * @param attributes the unique attribute values that find the entity
     * @param labels the labels to remove
     */
    removeLabelsByUniqueAttributes(
        typeName: string,
        attributes: Record<string, unknown>,
        labels: string[],
    ): Observable<void> {
        return this.http.request<void>(
            "DELETE",
            this.entityUrl(`/uniqueAttribute/type/${encodeURIComponent(typeName)}/labels`),
            { body: labels, params: this.attrParams(attributes) },
        );
    }
}
