import { EnvironmentProviders, InjectionToken, makeEnvironmentProviders } from "@angular/core";

/**
 * Base URL that the lineage-model auxiliary API is reachable under, same-origin
 * (e.g. `/lineage-model`) — 7.22a, LDG-07.
 *
 * The aux APIs are separate deployments from the Atlas server (ADR 055), so
 * this client composes its URLs from its own token and never from
 * {@link API_BASE_URL} (DD-387). Consuming apps provide this from their runtime
 * configuration (see {@link provideLineageModelBaseUrl}); it defaults to the
 * webapp's nginx location of the same name when not provided.
 */
export const LINEAGE_MODEL_BASE_URL = new InjectionToken<string>("LINEAGE_MODEL_BASE_URL", {
    providedIn: "root",
    factory: () => "/lineage-model",
});

/**
 * Provide the lineage-model base URL for {@link LineageModelService} from an
 * app's runtime configuration.
 * @param baseUrl The base URL the aux API is reachable under (e.g. `/lineage-model`).
 * @returns Environment providers for `appConfig.providers`.
 */
export function provideLineageModelBaseUrl(baseUrl: string): EnvironmentProviders {
    return makeEnvironmentProviders([{ provide: LINEAGE_MODEL_BASE_URL, useValue: baseUrl }]);
}

/**
 * Base URL that the validate-entity auxiliary API is reachable under,
 * same-origin (e.g. `/validate-entity`) — 7.24, EDT-22.
 *
 * Like {@link LINEAGE_MODEL_BASE_URL}, this client composes its URLs from its
 * own token and never from `API_BASE_URL` (DD-387's rule, every aux API).
 * Consuming apps provide this from their runtime configuration (see
 * {@link provideValidateEntityBaseUrl}); it defaults to the webapp's nginx
 * location of the same name when not provided (DD-445 — the DV-142 sibling:
 * the legacy's `validate_entity` deployment-proxy path is not ported).
 */
export const VALIDATE_ENTITY_BASE_URL = new InjectionToken<string>("VALIDATE_ENTITY_BASE_URL", {
    providedIn: "root",
    factory: () => "/validate-entity",
});

/**
 * Provide the validate-entity base URL for {@link ValidateEntityService} from
 * an app's runtime configuration.
 * @param baseUrl The base URL the aux API is reachable under (e.g. `/validate-entity`).
 * @returns Environment providers for `appConfig.providers`.
 */
export function provideValidateEntityBaseUrl(baseUrl: string): EnvironmentProviders {
    return makeEnvironmentProviders([{ provide: VALIDATE_ENTITY_BASE_URL, useValue: baseUrl }]);
}
