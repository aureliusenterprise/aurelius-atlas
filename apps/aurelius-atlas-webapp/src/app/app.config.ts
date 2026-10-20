import { provideHttpClient, withInterceptors, withXhr } from "@angular/common/http";
import {
    ApplicationConfig,
    ErrorHandler,
    provideBrowserGlobalErrorListeners,
    provideZonelessChangeDetection,
} from "@angular/core";
import { provideRouter, withComponentInputBinding, withInMemoryScrolling } from "@angular/router";
import { OTLPMetricExporter } from "@opentelemetry/exporter-metrics-otlp-http";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import {
    AureliusTraceErrorHandler,
    aureliusOpenTelemetryHttpInterceptor,
    createAureliusSessionResource,
    provideAureliusOpenTelemetry,
    provideAureliusOpenTelemetryMetrics,
} from "aurelius-atlas-observability";

import { AppConfig, parseAppConfig } from "./config";
import { routes } from "./routes";
import { APP_CONFIG } from "./tokens";

/**
 * Load and validate the runtime configuration served at `/config.json`.
 *
 * Fails loudly (rather than blank-screening) when the file is missing, not
 * reachable, or has the wrong shape (SHL-02).
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
 * Load the application configuration and assemble the providers.
 *
 * Increment 7.1 wires the shell (config + router) and the operational
 * telemetry (SHL-14): traces, metrics with Core Web Vitals, uncaught errors as
 * span events, and `traceparent` propagation on HTTP calls — all through
 * `aurelius-atlas-observability`, replacing the Aurelius Google Analytics and
 * clickstream paths (DD-040). The Keycloak and bearer-token providers arrive
 * with 7.3, which owns the auth wiring.
 * @returns The {@link ApplicationConfig} to bootstrap with.
 */
export async function initialize(): Promise<ApplicationConfig> {
    const config = await loadConfig();
    const sessionResource = createAureliusSessionResource();

    return {
        providers: [
            provideBrowserGlobalErrorListeners(),
            // Uncaught errors (window.onerror + unhandledrejection) become
            // exception events on the active span, or a standalone error span.
            { provide: ErrorHandler, useClass: AureliusTraceErrorHandler },
            provideAureliusOpenTelemetry({
                exporter: new OTLPTraceExporter({
                    url: config.otelExporterUrl,
                }),
                name: "aurelius-atlas-webapp",
                resource: sessionResource,
            }),
            provideAureliusOpenTelemetryMetrics({
                exporter: new OTLPMetricExporter({
                    url: metricsUrl(config),
                }),
                name: "aurelius-atlas-webapp",
                resource: sessionResource,
            }),
            provideZonelessChangeDetection(),
            provideRouter(
                routes,
                withComponentInputBinding(),
                // Aurelius routes with `scrollPositionRestoration: 'enabled'` (SHL-06).
                withInMemoryScrolling({ anchorScrolling: "enabled", scrollPositionRestoration: "enabled" }),
            ),
            // The OTLP interceptor adds W3C traceparent to every API call so
            // browser and server spans join one trace (ADR 016).
            provideHttpClient(withXhr(), withInterceptors([aureliusOpenTelemetryHttpInterceptor])),
            // The validated config is provided so feature slices read it from DI
            // instead of fetching it themselves (SHL-10: one settings channel).
            { provide: APP_CONFIG, useValue: config },
        ],
    };
}
