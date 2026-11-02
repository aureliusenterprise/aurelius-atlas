import { HttpClient, HttpParams } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { API_BASE_URL } from "../api-config";
import type { AtlasLineageInfo, LineageDirection, LineageOnDemandConstraints } from "./atlas-lineage";

/**
 * The lineage endpoints of the Atlas server (`LineageREST`, LIN-01..06,
 * ALN-01..04): the lineage graph of an entity, its on-demand form, and the
 * graph of the entity a unique attribute names. Every URL composes from the
 * injected {@link API_BASE_URL} (APC-01). The Python twin is
 * `AtlasClient.lineage` (CL-61..CL-63); its resource-object methods
 * (`lineage.get`, …) compose the resource name into the flat method names
 * here, as 8.13 did for the saved searches.
 */
@Injectable({
    providedIn: "root",
})
export class LineageService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(API_BASE_URL);

    /**
     * The lineage graph of the entity (LIN-01..LIN-05, CL-61, ALN-01). `depth`
     * and `direction` are always sent — the twin's shape, not the absent-is-the-
     * default rule: the route reads them as JAX-RS converts them with exactly
     * these defaults (DV-39). A guid with no lineage answers its 404 through the
     * error channel (LM-05, APC-04).
     * @param guid the entity's guid
     * @param depth how many hops to walk
     * @param direction which way to walk
     * @returns the lineage graph
     */
    getLineage(guid: string, depth = 3, direction: LineageDirection = "BOTH"): Observable<AtlasLineageInfo> {
        return this.http.get<AtlasLineageInfo>(`${this.baseUrl}/atlas/v2/lineage/${encodeURIComponent(guid)}`, {
            params: new HttpParams().set("depth", depth).set("direction", direction),
        });
    }

    /**
     * The lineage graph of the entity on demand, within the constraints per guid
     * (LIN-06, CL-62, ALN-02). A missing or empty map sends no body — the twin's
     * `body or None`. A server with the feature off answers
     * `LINEAGE_ON_DEMAND_NOT_ENABLED` through the error channel; this client
     * does not pre-check the setting.
     * @param guid the entity's guid
     * @param constraints the per-guid limits, when given
     * @returns the lineage graph
     */
    getLineageOnDemand(
        guid: string,
        constraints?: Record<string, LineageOnDemandConstraints>,
    ): Observable<AtlasLineageInfo> {
        const body = constraints && Object.keys(constraints).length > 0 ? constraints : null;
        return this.http.post<AtlasLineageInfo>(`${this.baseUrl}/atlas/v2/lineage/${encodeURIComponent(guid)}`, body);
    }

    /**
     * The lineage graph of the entity that holds the unique attribute values
     * (LIN-01, CL-63, ALN-03). Each attribute travels as an `attr:<name>` query
     * parameter, as the route reads them; `depth` and `direction` are always
     * sent, per ALN-01.
     * @param typeName the entity's type name
     * @param attributes the unique attribute values
     * @param depth how many hops to walk
     * @param direction which way to walk
     * @returns the lineage graph
     */
    getLineageByUniqueAttributes(
        typeName: string,
        attributes: Record<string, unknown>,
        depth = 3,
        direction: LineageDirection = "BOTH",
    ): Observable<AtlasLineageInfo> {
        let params = new HttpParams().set("depth", depth).set("direction", direction);
        for (const [name, value] of Object.entries(attributes)) {
            params = params.set(`attr:${name}`, `${value}`);
        }
        return this.http.get<AtlasLineageInfo>(
            `${this.baseUrl}/atlas/v2/lineage/uniqueAttribute/type/${encodeURIComponent(typeName)}`,
            { params },
        );
    }
}
