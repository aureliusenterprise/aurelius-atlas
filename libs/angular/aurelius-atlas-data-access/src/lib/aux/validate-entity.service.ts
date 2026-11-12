import { HttpClient } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { VALIDATE_ENTITY_BASE_URL } from "./aux-config";

/**
 * One ACTIVE governance rule's answer about the draft (VEV-02, 12.7).
 * `compliant` is a JSON boolean — 12.6's verdict, not the mock's string
 * `"0"`/`"1"` — and `message` is the verdict line the engine carries: the
 * rule's own sentence for its verdict, the kind's reason when the rule stores
 * none (GQ-06). The twin is
 * `aurelius_atlas_validate_entity_client.GovernanceVerdict` (CL-40 as amended
 * by 12.7, DD-498).
 */
export type GovernanceVerdict = {
    /** The catalogue guid of the rule that answered. */
    ruleGuid: string;
    /** The rule's name, as the catalogue holds it. */
    ruleName: string;
    /** The entity attribute the rule measures: the banner groups by it. */
    attribute: string;
    /** The rule's quality dimension, e.g. `COMPLETENESS`. */
    dimension: string;
    /** The verdict: whether the draft passes the rule. */
    compliant: boolean;
    /** The line to show: the rule's own sentence, or the kind's reason. */
    message: string;
};

/**
 * A rule the vocabulary cannot read — recorded, never executed (VEV-03,
 * DV-146). 12.7's banner shows no line for it; it rides the answer for the
 * caller that asks (the 7.28 rule box).
 */
export type UnreadRule = {
    /** The catalogue guid of the unread rule. */
    ruleGuid: string;
    /** The rule's name, as the catalogue holds it. */
    ruleName: string;
    /** Why the vocabulary cannot read it, e.g. a stored expression rule. */
    error: string;
};

/**
 * The answer of `POST {baseUrl}/` (EDT-21 as amended by 12.7, VEV-02/VEV-03):
 * the verdicts of the ACTIVE rules and the rules that could not be read.
 * The flat array replaces the mock's keyed cards (DD-498): the banner groups
 * `verdicts` by `attribute` (EDT-24 amended). The twin is
 * `aurelius_atlas_validate_entity_client.ValidationResponse` (CL-40).
 */
export type EntityValidationResponse = {
    verdicts: GovernanceVerdict[];
    unreadRules: UnreadRule[];
};

/**
 * The validate-entity auxiliary API (ADR 061, 8.3 grown by 12.7): the
 * browser's call that checks a draft entity against the governance rules.
 * Since 12.7 the app runs the catalogue's ACTIVE rules over the draft and
 * answers real verdicts (VEV-02) — the 8.3 mock and its card document retired
 * with DV-67 (DV-153, the clean cut of DD-501). This client is the Angular
 * twin of `aurelius_atlas_validate_entity_client.ValidateEntityClient` (CL-40)
 * and of the legacy `gov-quality-api-client.service.ts`, whose swallowed
 * errors are the editor's job, not this one's (the legacy catch-all is not
 * ported, the DD-386 rule). Every URL composes from the injected
 * {@link VALIDATE_ENTITY_BASE_URL} and never from `API_BASE_URL` (DD-387); the
 * aux API is a separate deployment.
 */
@Injectable({
    providedIn: "root",
})
export class ValidateEntityService {
    private readonly http = inject(HttpClient);
    private readonly baseUrl = inject(VALIDATE_ENTITY_BASE_URL);

    /**
     * Validate the draft entity (EDT-21, VEV-01/VEV-02) — the legacy
     * `validateEntity(entityDetails)`. The aux API's route is its root, so the
     * URL is `{baseUrl}/` with the entity as the JSON body and no query
     * string. A `200` answers the typed verdicts; a `4xx`, `5xx`, or
     * unreachable API stays on the error channel with its body — this client
     * interprets nothing; the editor swallows quietly (EDT-23, DD-446).
     * @param entity the draft entity, as the editor form holds it
     * @returns the verdicts of the ACTIVE rules, and the unread ones
     */
    validateEntity(entity: unknown): Observable<EntityValidationResponse> {
        return this.http.post<EntityValidationResponse>(`${this.baseUrl}/`, entity);
    }
}
