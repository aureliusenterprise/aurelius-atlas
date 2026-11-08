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
