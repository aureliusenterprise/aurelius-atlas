/**
 * The client shape the seam reads: the same structural seams
 * keycloak-angular's bearer interceptor uses (`authenticated` /
 * `updateToken` / `token`). Declared structurally — not as `Keycloak` — so
 * the lib stays auth-provider-agnostic (the dev stack's Keycloak is named in
 * the doc comments, not in the types).
 */
export interface OtelIngestAuthClient {
    /** Whether the client's session is signed in. */
    authenticated: boolean;

    /** The current access token, once signed in. */
    token?: string;

    /**
     * Refresh the token when it expires within `minValidity` seconds.
     * @param minValidity seconds of remaining validity to require
     * @returns true when the token is (still) valid
     */
    updateToken: (minValidity: number) => Promise<boolean>;
}

/**
 * The OTLP ingest credential (7.17, DD-193, CIA-02): the signed-in user's
 * Keycloak access token, attached to every OTLP push so the collector's OIDC
 * receiver attributes the telemetry to that user and rejects token-less pushes.
 *
 * The OTLP exporters ride XHR/fetch outside Angular's HttpClient, so the
 * bearer interceptor never sees them — the token is attached through the
 * exporter `headers` factory (OTel calls it per export) instead:
 *
 * ```ts
 * new OTLPTraceExporter({ url, headers: ingestAuth.headers });
 * ```
 *
 * The exporters are constructed at bootstrap, before Angular DI and Keycloak
 * init exist, so the credential is read lazily: {@link AureliusOtelIngestAuth.attach}
 * hands the factory the live client once the app's `provideKeycloak`
 * initializer has resolved — register a `provideAppInitializer` right after
 * `provideKeycloak` (app initializers run in registration order, so the token
 * state is settled when this attaches). A signed-out tab yields no header —
 * the collector answers 401, the accepted pre-login telemetry loss (DD-193).
 */
export interface AureliusOtelIngestAuth {
    /**
     * The exporter `headers` factory: the current bearer header, refreshed
     * ahead of expiry; empty while signed out or before {@link attach}.
     */
    headers: () => Promise<Record<string, string>>;

    /**
     * Binds the seam to the live client (the app's Keycloak DI instance —
     * the same one the bearer interceptor reads).
     * @param client the initialized auth client
     */
    attach: (client: OtelIngestAuthClient) => void;
}

/**
 * Create the OTLP ingest-credential seam (see {@link AureliusOtelIngestAuth}).
 * @returns the exporter `headers` factory and its `attach` binding
 */
export function createAureliusOtelIngestAuth(): AureliusOtelIngestAuth {
    let client: OtelIngestAuthClient | undefined;

    return {
        headers: async () => {
            if (!client?.authenticated) {
                return {};
            }
            try {
                // The dev realm's access token lives 60s: refresh ahead of
                // expiry so a long session keeps exporting.
                await client.updateToken(30);
            } catch {
                // Refresh failed (session gone): send the current token; the
                // collector rejects it, visible as a 401 in devtools (DD-193).
            }

            const headers: Record<string, string> = {};
            if (client.token) {
                headers["Authorization"] = `Bearer ${client.token}`;
            }

            return headers;
        },
        attach: (next) => {
            client = next;
        },
    };
}
