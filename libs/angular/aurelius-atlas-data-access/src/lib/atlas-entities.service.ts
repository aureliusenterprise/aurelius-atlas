import { HttpClient } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { API_BASE_URL } from "./api-config";
import type { AtlasEntityWithExtInfo } from "./atlas-entity";

/**
 * The entity endpoints of the Atlas server (`EntityREST`, DET-03): the
 * by-guid read, the DTOs of {@link AtlasEntityWithExtInfo}. The wire format
 * is typed from the Apache Atlas 2.4.0 source (see `atlas-entity.ts`); the
 * endpoint itself is increment 2.3's surface — against today's server (admin
 * and types only) the call answers 404, and the specs assert the request,
 * not a 200 (DD-140's honesty rule, DD-097).
 *
 * Every URL composes from the injected {@link API_BASE_URL} with the
 * `/atlas` prefix intact (APC-01, DD-139) — the server API is the webapp's
 * one data plane (ADR 054, DD-098). No screen calls this service until the
 * 2.3+7.6 wiring increment (DET-02, DD-096).
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
     * The entity with that GUID, as `AtlasEntityWithExtInfo`
     * (`EntityREST.getEntityByGuid`, GET `/v2/entity/guid/{guid}` — the
     * surface of increment 2.3). The guid is URL-encoded, as every lookup
     * in the typedefs client encodes its key (APC-03's idiom).
     * @param guid the entity GUID
     * @returns the entity read, its type definitions in the same body
     */
    getEntityByGuid(guid: string): Observable<AtlasEntityWithExtInfo> {
        return this.http.get<AtlasEntityWithExtInfo>(this.entityUrl(`/guid/${encodeURIComponent(guid)}`));
    }
}
