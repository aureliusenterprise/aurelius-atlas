import { HttpClient, HttpParams } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { API_BASE_URL } from "../api-config";
import type { EntityAuditEventV2 } from "./atlas-audit";
import type { AtlasEntitiesWithExtInfo, AtlasEntityWithExtInfo } from "./atlas-entity";
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
 * (8.17, AEN-01..AEN-07) and the writes and deletes (8.18, AEW-01..AEW-06) —
 * the Angular twin of `AtlasClient.entity`'s reads, writes and deletes
 * (CLE-01..CLE-04, CLE-11, CLE-12). The classification, business-metadata,
 * and label routes come in 8.19. The wire
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
}
