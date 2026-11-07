import { HttpClient, HttpParams } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { LINEAGE_MODEL_BASE_URL } from "./aux-config";

/**
 * Which way the lineage-model API walks the lineage. The same vocabulary as
 * the Atlas server's `LineageDirection` (atlas-lineage.ts) and the Python
 * twin's `Direction` — the aux API forwards the value to `LineageREST`
 * unchanged (LM-01, DV-69).
 */
export type LineageModelDirection = "INPUT" | "OUTPUT" | "BOTH";

/**
 * One metadata row of the answer: the provenance of one element, edge, or view
 * of the model and its mapped attributes (LM-04). The rows are open key/value
 * maps by the data2model contract, so `data` is not narrowed further.
 */
export type LineageModelMetadata = {
    /** The id the model document refers to this row by. */
    id: string;
    /** The row's attributes, as the data2model rules mapped them. */
    data: Record<string, unknown>;
};

/**
 * The answer of `GET {baseUrl}/` (LDG-02, LM-04): the flattened lineage as an
 * ar3 model and its metadata rows. The twin is
 * `aurelius_atlas_lineage_model_client.LineageModelResponse` (CL-30, DD-203);
 * `model` stays a JSON *string*, not a parsed object — DV-68's passthrough
 * contract, kept by both clients.
 */
export type LineageModelResponse = {
    /** The ar3 model, JSON-encoded as a string; the browser draws it. */
    model: string;
    /** One row per element, edge, and view — empty when the model has none. */
    metadata: LineageModelMetadata[];
};

/**
 * The lineage-model auxiliary API (ADR 055, 8.2): the browser's single call
 * that turns one entity into an archimate3 diagram model. The API flattens the
 * Atlas lineage (`LineageREST`), feeds it to data2model, and forwards the
 * answer (LM-01..LM-08) — this client is the Angular twin of
 * `aurelius_atlas_lineage_model_client.LineageModelClient` (CL-30) and of the
 * legacy `get-lineage-model` service, whose swallowed errors are not ported
 * (DD-386). Every URL composes from the injected {@link LINEAGE_MODEL_BASE_URL}
 * and never from `API_BASE_URL` (DD-387); the aux API is a separate deployment.
 */
@Injectable({
    providedIn: "root",
})
export class LineageModelService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(LINEAGE_MODEL_BASE_URL);

    /**
     * The lineage model of the entity (LDG-01..04, LM-01/LM-04/LM-05/LM-06,
     * CL-30) — the legacy `getLineageModel(guid, 3, 'BOTH')`. The aux API's
     * route is its root, so the URL is `{baseUrl}/?guid=&depth=&direction=`;
     * every parameter travels on every call, the ALN-01 convention — the route
     * reads the absent parameter as exactly these defaults (LM-01). A `204` is
     * the empty lineage and answers `null`, not an error (LDG-03, DD-386 —
     * the caller decides what absence looks like); a `400`, `401`, or `502`
     * stays on the error channel with its Atlas-shaped body (LDG-04, LM-07) —
     * this client interprets nothing, unlike the legacy catch-all.
     * @param guid the entity's guid
     * @param depth how many hops of lineage to walk (the route's default, 3)
     * @param direction which way to walk (the route's default, `BOTH`)
     * @returns the model and its rows, or `null` for the empty lineage
     */
    getLineageModel(
        guid: string,
        depth = 3,
        direction: LineageModelDirection = "BOTH",
    ): Observable<LineageModelResponse | null> {
        return this.http.get<LineageModelResponse | null>(`${this.baseUrl}/`, {
            params: new HttpParams().set("guid", guid).set("depth", depth).set("direction", direction),
        });
    }
}
