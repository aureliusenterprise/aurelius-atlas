import { HttpClient, HttpParams } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { API_BASE_URL } from "../api-config";
import type { DeleteType } from "./atlas-mutation";
import type { AtlasRelationship, AtlasRelationshipWithExtInfo } from "./atlas-relationship";

/**
 * The relationship endpoints of the Atlas server (`RelationshipREST`,
 * REL-03..REL-08, AREL-01..04): create, update, the wrapped read, and the
 * soft/hard delete of a relationship between two entities. Every URL composes
 * from the injected {@link API_BASE_URL} (APC-01). The Python twin is
 * `AtlasClient.relationship` (CLR-01..CLR-04); its resource-object methods
 * (`relationship.create`, …) compose the resource name into the flat method
 * names here, as 8.15 did for lineage.
 */
@Injectable({
    providedIn: "root",
})
export class RelationshipService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(API_BASE_URL);

    /**
     * A new relationship between two entities (REL-04, REL-05, CLR-03,
     * AREL-01). The ends and the type are not checked here — the server
     * answers.
     * @param relationship the relationship to create
     * @returns the created relationship, bare
     */
    createRelationship(relationship: AtlasRelationship): Observable<AtlasRelationship> {
        return this.http.post<AtlasRelationship>(`${this.baseUrl}/atlas/v2/relationship`, relationship);
    }

    /**
     * The relationship's tag propagation and attributes (REL-07, CLR-03,
     * AREL-01).
     * @param relationship the relationship to update, with its guid
     * @returns the updated relationship, bare
     */
    updateRelationship(relationship: AtlasRelationship): Observable<AtlasRelationship> {
        return this.http.put<AtlasRelationship>(`${this.baseUrl}/atlas/v2/relationship`, relationship);
    }

    /**
     * The relationship (REL-03, REL-06, CLR-02, AREL-02). The answer is always
     * the `AtlasRelationshipWithExtInfo` wrapper — the server wraps even the
     * plain answer; `referredEntities` (the ends' headers) appears only when
     * `extendedInfo` is true. The parameter goes only when set (an absent flag
     * is Java's `false`).
     * @param guid the relationship's guid
     * @param extendedInfo whether the answer carries the ends' headers
     * @returns the wrapped relationship
     */
    getRelationship(guid: string, extendedInfo = false): Observable<AtlasRelationshipWithExtInfo> {
        let params = new HttpParams();
        if (extendedInfo) {
            params = params.set("extendedInfo", "true");
        }
        return this.http.get<AtlasRelationshipWithExtInfo>(
            `${this.baseUrl}/atlas/v2/relationship/guid/${encodeURIComponent(guid)}`,
            { params },
        );
    }

    /**
     * Remove the relationship, soft or hard (REL-08, EDL-04, CLR-04, AREL-03).
     * An absent `deleteType` sends no parameter: the server applies its own
     * configured strategy. Answers 204.
     * @param guid the relationship's guid
     * @param deleteType the delete strategy, when chosen
     */
    deleteRelationship(guid: string, deleteType?: DeleteType): Observable<void> {
        let params = new HttpParams();
        if (deleteType !== undefined) {
            params = params.set("deleteType", deleteType);
        }
        return this.http.delete<void>(`${this.baseUrl}/atlas/v2/relationship/guid/${encodeURIComponent(guid)}`, {
            params,
        });
    }
}
