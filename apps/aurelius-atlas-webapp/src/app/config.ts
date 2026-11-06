/**
 * Shape of the runtime configuration served at `/config.json`.
 *
 * This file is fetched at bootstrap and is **not** bundled into the production
 * build (see `build.configurations.development.assets` in `project.json`). Each
 * deployment serves its own `config.json`, so the same image can target any
 * environment. The Aurelius `environments/environment.ts` is not ported — this
 * is the settings channel (ADR 018, DD-130, SHL-10).
 */
/**
 * The default {@link AppConfig.atlasClientId}: the Keycloak client the
 * server's settings call `auth_client_id` (DD-300, DD-324).
 */
export const DEFAULT_ATLAS_CLIENT_ID = "aurelius-atlas-server";

export interface AppConfig {
    /**
     * Keycloak connection settings for the `keycloak-angular` client.
     */
    readonly keycloak: AppConfigKeycloak;

    /**
     * Base URL that the API is reachable under, same-origin (e.g. `/api`).
     * Provided to `aurelius-atlas-data-access` via the `API_BASE_URL` token
     * once the API client arrives (increment 7.3).
     */
    readonly apiBaseUrl: string;

    /**
     * OTLP trace exporter endpoint, same-origin (e.g. `/otel/v1/traces`).
     */
    readonly otelExporterUrl: string;

    /**
     * OTLP metric exporter endpoint, same-origin (e.g. `/otel/v1/metrics`).
     * When omitted, consumers derive it from {@link otelExporterUrl} by
     * swapping the trailing `traces` signal for `metrics`.
     */
    readonly otelMetricsExporterUrl?: string;

    /**
     * Application name: the shell header's brand and the footer's centre line
     * (SHC-02, SHC-06). The Aurelius `environments/environment.ts`'s
     * `shell.appName` — the runtime config is the settings channel (SHL-10).
     */
    readonly appName: string;

    /**
     * Copyright year shown in the footer, the Aurelius `shell.appCopyright`.
     */
    readonly appCopyright: number;

    /**
     * Application version shown in the footer, the Aurelius
     * `VersionService.appVersion` (package version + git hash). The image
     * label carries the same value; the deployment serves it here.
     */
    readonly appVersion: string;

    /**
     * The Keycloak client that owns the Atlas privileges (DD-300): the write
     * affordances render only for a token holding `atlas-write` in this
     * client's roles (EDT-09, DD-324). It pairs with the server's
     * `auth_client_id` and defaults to its value, `aurelius-atlas-server`.
     */
    readonly atlasClientId?: string;
}

/**
 * Keycloak client settings within {@link AppConfig}.
 */
export interface AppConfigKeycloak {
    /**
     * The Keycloak client id (public client — safe to expose in the browser).
     */
    readonly clientId: string;

    /**
     * The Keycloak realm name.
     */
    readonly realm: string;

    /**
     * The base URL of the Keycloak server.
     */
    readonly url: string;
}

/**
 * Validate and narrow an unknown value (e.g. parsed JSON) into a typed
 * {@link AppConfig}. Throws a descriptive error when the shape is wrong so a
 * misconfigured deployment fails loudly at bootstrap instead of blank-screening
 * (SHL-02).
 *
 * @param value The parsed `/config.json` payload.
 * @returns The validated {@link AppConfig}.
 * @throws If the payload does not match the expected shape.
 */
export function parseAppConfig(value: unknown): AppConfig {
    if (typeof value !== "object" || value === null) {
        throw new Error("Invalid app config: expected a JSON object.");
    }

    const {
        keycloak,
        apiBaseUrl,
        otelExporterUrl,
        otelMetricsExporterUrl,
        appName,
        appCopyright,
        appVersion,
        atlasClientId,
    } = value as Partial<AppConfig>;

    if (typeof keycloak !== "object" || keycloak === null) {
        throw new Error('Invalid app config: missing "keycloak" object.');
    }

    const { clientId, realm, url } = keycloak as Partial<AppConfigKeycloak>;

    const requireString = (name: string, field: unknown): string => {
        if (typeof field !== "string" || field.length === 0) {
            throw new Error(`Invalid app config: "${name}" must be a non-empty string.`);
        }
        return field;
    };

    if (otelMetricsExporterUrl !== undefined) {
        requireString("otelMetricsExporterUrl", otelMetricsExporterUrl);
    }

    if (atlasClientId !== undefined) {
        requireString("atlasClientId", atlasClientId);
    }

    const requireYear = (name: string, field: unknown): number => {
        if (typeof field !== "number" || !Number.isInteger(field)) {
            throw new TypeError(`Invalid app config: "${name}" must be an integer year.`);
        }
        return field;
    };

    return {
        keycloak: {
            clientId: requireString("keycloak.clientId", clientId),
            realm: requireString("keycloak.realm", realm),
            url: requireString("keycloak.url", url),
        },
        apiBaseUrl: requireString("apiBaseUrl", apiBaseUrl),
        otelExporterUrl: requireString("otelExporterUrl", otelExporterUrl),
        appName: requireString("appName", appName),
        appCopyright: requireYear("appCopyright", appCopyright),
        appVersion: requireString("appVersion", appVersion),
        ...(otelMetricsExporterUrl ? { otelMetricsExporterUrl } : {}),
        atlasClientId: atlasClientId ?? DEFAULT_ATLAS_CLIENT_ID,
    };
}
