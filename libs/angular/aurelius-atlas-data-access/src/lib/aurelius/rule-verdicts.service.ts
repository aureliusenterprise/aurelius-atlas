import { HttpClient } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { API_BASE_URL } from "../api-config";
import { RuleVerdictsAnswer } from "../atlas/atlas-view";

/**
 * The client of the view family's verdicts door (VDR-15, ADR 071): the server's
 * own endpoint under `/aurelius/v1`, beside Atlas's, behind the same
 * {@link API_BASE_URL} and authentication. One rule GUID in, the rule's stored
 * verdict rows out (AVS-12) — the read the rule page's two card lists and its
 * chart ride (7.25b). It is the only caller of the route: the App Search wire
 * gains no new consumer (ADR 071 R5).
 */
@Injectable({
    providedIn: "root",
})
export class RuleVerdictsService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(API_BASE_URL);

    /**
     * The stored verdicts of one rule, in the store's document id order
     * (ASG-09). The door never reads the rule (VDR-14): any GUID without
     * verdicts — an inactive rule, an entity, no entity — answers none.
     * @param rule the rule entity's GUID
     * @returns the rule's verdict rows
     */
    verdicts(rule: string): Observable<RuleVerdictsAnswer> {
        return this.http.post<RuleVerdictsAnswer>(`${this.baseUrl}/aurelius/v1/rule/verdicts`, { rule });
    }
}
