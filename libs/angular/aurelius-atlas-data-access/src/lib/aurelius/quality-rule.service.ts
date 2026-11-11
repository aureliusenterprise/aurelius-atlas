import { HttpClient } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { catchError, Observable, shareReplay, throwError } from "rxjs";
import { API_BASE_URL } from "../api-config";

/**
 * One check kind of the closed vocabulary (QRE-01): the dimension it measures, the
 * parameters it needs, and the reason line it reports a failure with. The parameter
 * names are the engine's camelCase ones (DQ-01), which the editor maps onto the
 * stored `dq` attributes (EDT-26).
 */
export type QualityKind = {
    name: string;
    dimension: string;
    required: string[];
    optional: string[];
    reason: string;
};

/** The kinds resource of 12.5 (QRE-01): every kind, the castable types, the threshold bounds. */
export type QualityKinds = {
    kinds: QualityKind[];
    castableTypes: string[];
    thresholdMin: number;
    thresholdMax: number;
};

/**
 * The validate answer of 12.5 (QRE-02): a rule the vocabulary reads comes back with its
 * kind and dimension; one it cannot read comes back with the engine's reason.
 */
export type QualityRuleValidation = {
    valid: boolean;
    kind?: string;
    dimension?: string;
    reason?: string;
};

/**
 * The client of Aurelius's rule vocabulary (EDT-30, QRE-01/02, DD-473): the two 12.5
 * routes under `/aurelius/v1/quality`, behind the same {@link API_BASE_URL} and
 * authentication as every other call (APC). The drawer's quality mode never fetches
 * them itself; this service is the only caller, and it caches the kinds answer after
 * its first success — the vocabulary is static per server build (EDT-25's "once").
 */
@Injectable({
    providedIn: "root",
})
export class QualityRuleService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(API_BASE_URL);

    private kindsCache?: Observable<QualityKinds>;

    /**
     * The closed rule vocabulary of the deployed server (EDT-25, QRE-01), cached after
     * the first success. A failed load is not cached, so a later open retries it.
     * @returns the kinds, the castable types, and the threshold bounds
     */
    kinds(): Observable<QualityKinds> {
        this.kindsCache ??= this.http.get<QualityKinds>(`${this.baseUrl}/aurelius/v1/quality/kinds`).pipe(
            catchError((error: unknown) => {
                this.kindsCache = undefined;
                return throwError(() => error);
            }),
            shareReplay({ bufferSize: 1, refCount: false }),
        );
        return this.kindsCache;
    }

    /**
     * A draft rule's stored attributes through the server's parser (EDT-28, QRE-02,
     * DD-474). Both answers arrive as 200: `{valid: true}` names the kind and dimension
     * the engine read, `{valid: false}` carries its reason.
     * @param attributes the rule as the store keeps it (the `dq` names, DQ-01)
     * @returns the validate answer
     */
    validateRule(attributes: Record<string, unknown>): Observable<QualityRuleValidation> {
        return this.http.post<QualityRuleValidation>(`${this.baseUrl}/aurelius/v1/quality/rules/validate`, attributes);
    }
}
