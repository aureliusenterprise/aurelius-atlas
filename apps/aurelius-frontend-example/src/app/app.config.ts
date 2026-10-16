import { provideHttpClient, withInterceptors, withXhr } from "@angular/common/http";
import {
    ApplicationConfig,
    ErrorHandler,
    provideBrowserGlobalErrorListeners,
    provideZonelessChangeDetection,
} from "@angular/core";
import { provideRouter } from "@angular/router";
import { provideApiBaseUrl } from "aurelius-data-access";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { OTLPMetricExporter } from "@opentelemetry/exporter-metrics-otlp-http";
import {
    AureliusTraceErrorHandler,
    aureliusOpenTelemetryHttpInterceptor,
    createAureliusSessionResource,
    provideAureliusOpenTelemetry,
    provideAureliusOpenTelemetryMetrics,
} from "aurelius-observability";
import {
    INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG,
    includeBearerTokenInterceptor,
    provideKeycloak,
} from "keycloak-angular";
import { AppConfig, parseAppConfig } from "./config";
import { routes } from "./routes";

/**
 * Load and validate the runtime configuration served at `/config.json`.
 *
 * Fails loudly (rather than blank-screening) when the file is missing, not
 * reachable, or has the wrong shape.
 * @returns The typed {@link AppConfig}.
 */
async function loadConfig(): Promise<AppConfig> {
    const response = await fetch("/config.json");

    if (!response.ok) {
        throw new Error(`Failed to load app config (/config.json): ${response.status} ${response.statusText}`);
    }

    return parseAppConfig(await response.json());
}

/**
 * Metric signal URL: explicit config wins, else the traces endpoint with its
 * trailing signal swapped (`.../v1/traces` -> `.../v1/metrics`).
 * @param config The parsed app config.
 * @returns The OTLP metrics endpoint.
 */
export function metricsUrl(config: AppConfig): string {
    return config.otelMetricsExporterUrl ?? config.otelExporterUrl.replace(/traces$/, "metrics");
}

/**
 * Load the application configuration from the server and initialize the application.
 * @returns ApplicationConfig
 */
export async function initialize(): Promise<ApplicationConfig> {
    const config = await loadConfig();
    const sessionResource = createAureliusSessionResource();

    return {
        providers: [
            provideBrowserGlobalErrorListeners(),
            // Uncaught errors (window.onerror + unhandledrejection, handed to
            // the DI ErrorHandler by the listeners above) become exception
            // events on the active span, or a standalone error span.
            { provide: ErrorHandler, useClass: AureliusTraceErrorHandler },
            provideAureliusOpenTelemetry({
                exporter: new OTLPTraceExporter({
                    url: config.otelExporterUrl,
                }),
                name: "aurelius-frontend-example",
                resource: sessionResource,
            }),
            provideAureliusOpenTelemetryMetrics({
                exporter: new OTLPMetricExporter({
                    url: metricsUrl(config),
                }),
                name: "aurelius-frontend-example",
                resource: sessionResource,
            }),
            provideApiBaseUrl(config.apiBaseUrl),
            provideKeycloak({
                config: config.keycloak,
                initOptions: {
                    onLoad: "check-sso",
                    silentCheckSsoRedirectUri: globalThis.location.origin + "/silent-check-sso.html",
                },
            }),
            {
                provide: INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG,
                useValue: [{ urlPattern: /^.*\/api\/.*$/ }],
            },
            provideRouter(routes),
            provideHttpClient(
                withXhr(),
                withInterceptors([aureliusOpenTelemetryHttpInterceptor, includeBearerTokenInterceptor]),
            ),
            provideZonelessChangeDetection(),
        ],
    };
}
