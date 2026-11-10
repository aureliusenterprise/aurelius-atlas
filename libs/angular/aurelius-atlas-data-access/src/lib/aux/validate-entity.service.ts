import { HttpClient } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { VALIDATE_ENTITY_BASE_URL } from "./aux-config";

/**
 * A `{"raw": …}` wrapper — every leaf of the governance document is one
 * (VE-02). `raw` is a string, or a list of strings for `usedattributes`.
 */
export type GovQualityValue = {
    raw: string | string[];
};

/**
 * The `_meta` of an item: the engine that produced it, its score and its
 * document id (VE-02).
 */
export type GovQualityMeta = {
    /** The engine, e.g. `atlas-dev-gov-quality`. */
    engine: string;
    /** The item's score. */
    score: number;
    /** The document id, e.g. a `doc-…` id. */
    id: string;
};

/**
 * One governance check: a verdict item of a card (VE-02). Every leaf keeps the
 * `{"raw": …}` wrapper of the wire contract, and `compliant.raw` is the string
 * `"0"`/`"1"` — as the legacy emits it, not a boolean.
 * `dataqualityruledimension` is in the legacy's `GovQualitySearchObject` but
 * the deployed 8.3 mock answers without it, so it is optional here.
 */
export type GovQualityItem = {
    /** The human-readable verdict. */
    result: GovQualityValue;
    /** The kind of check; `attribute` checks carry the legacy's name. */
    dataqualitytype: GovQualityValue;
    /** The entity attributes the check reads. */
    usedattributes: GovQualityValue;
    /** The check's name, e.g. `Attribute - <key>`. */
    name: GovQualityValue;
    /** The verdict flag, the string `"0"`/`"1"`. */
    compliant: GovQualityValue;
    /** The rule's dimension, when the answer carries it (see above). */
    dataqualityruledimension?: GovQualityValue;
    /** The producing engine's record. */
    _meta: GovQualityMeta;
    /** The item's document id, wrapped like every leaf. */
    id: GovQualityValue;
};

/**
 * One governance card: the items of one aspect, with the card's verdict
 * (VE-02). `isNonCompliant` is whether any item fails.
 */
export type ValidationCard = {
    items: GovQualityItem[];
    isNonCompliant: boolean;
};

/**
 * The answer of `POST {baseUrl}/` (EDT-21, VE-01/VE-02): one card per aspect
 * key. The deployed 8.3 mock answers the keys `dataEntity`, `definition`,
 * `domainLead` and `name`; the keys are open because the editor renders by
 * them (EDT-24) and a future engine may answer more. The twin is
 * `aurelius_atlas_validate_entity_client.ValidationResponse` (CL-40, DD-203).
 */
export type EntityValidationResponse = {
    [cardKey: string]: ValidationCard;
};

/**
 * The validate-entity auxiliary API (ADR 055, 8.3): the browser's call that
 * checks a draft entity against the governance rules. The API is a mock today
 * (DV-67) — it accepts the entity, never reads it, and answers the fixed
 * four-card document — but the contract is the real one, so the editor renders
 * its answer as verdict lines (EDT-24). This client is the Angular twin of
 * `aurelius_atlas_validate_entity_client.ValidateEntityClient` (CL-40) and of
 * the legacy `gov-quality-api-client.service.ts`, whose swallowed errors are
 * the editor's job, not this one's (the legacy catch-all is not ported, the
 * DD-386 rule). Every URL composes from the injected
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
     * Validate the draft entity (EDT-21, VE-01/VE-02) — the legacy
     * `validateEntity(entityDetails)`. The aux API's route is its root, so the
     * URL is `{baseUrl}/` with the entity as the JSON body and no query
     * string. A `200` answers the typed cards; a `4xx`, `5xx`, or unreachable
     * API stays on the error channel with its body — this client interprets
     * nothing; the editor swallows quietly (EDT-23, DD-436).
     * @param entity the draft entity, as the editor form holds it
     * @returns the governance cards, one per aspect key
     */
    validateEntity(entity: unknown): Observable<EntityValidationResponse> {
        return this.http.post<EntityValidationResponse>(`${this.baseUrl}/`, entity);
    }
}
