import { provideHttpClient, withInterceptors, withXhr } from "@angular/common/http";
import { DATE_PIPE_DEFAULT_TIMEZONE } from "@angular/common";
import {
    ApplicationConfig,
    ErrorHandler,
    inject,
    provideAppInitializer,
    provideBrowserGlobalErrorListeners,
    provideZonelessChangeDetection,
} from "@angular/core";
import { provideRouter, withComponentInputBinding, withInMemoryScrolling } from "@angular/router";
import { provideApiBaseUrl } from "aurelius-atlas-data-access";
import { OTLPMetricExporter } from "@opentelemetry/exporter-metrics-otlp-http";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import {
    aureliusOpenTelemetryHttpInterceptor,
    createAureliusOtelIngestAuth,
    createAureliusSessionResource,
    provideAureliusOpenTelemetry,
    provideAureliusOpenTelemetryMetrics,
} from "aurelius-atlas-observability";
import {
    INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG,
    includeBearerTokenInterceptor,
    provideKeycloak,
} from "keycloak-angular";
import Keycloak, { type KeycloakInitOptions } from "keycloak-js";

import { AppConfig, parseAppConfig } from "./config";
import { alertsErrorHandlerFactory } from "./alerts/alerts-error-handler";
import { alertsHttpInterceptor } from "./alerts/alerts-http.interceptor";
import { routes } from "./routes";
import { TelemetryService } from "./settings/telemetry.service";
import { TimezoneService } from "./settings/timezone.service";
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
 * The Keycloak init options: `check-sso` (an existing SSO session signs in without a
 * click; the root guard in `routes.ts` redirects everyone else) with a silent-SSO
 * redirect at the origin root, where the `silent-check-sso.html` asset is served
 * (APC-05).
 * @returns the init options for {@link provideKeycloak}
 */
export function keycloakInitOptions(): KeycloakInitOptions {
    return {
        onLoad: "check-sso",
        silentCheckSsoRedirectUri: globalThis.location.origin + "/silent-check-sso.html",
    };
}

/**
 * The bearer-token interceptor config (APC-06, DD-004): the token rides every
 * same-origin `/api` call — the Atlas API — and nothing else. The server ignores it
 * until 6.1; sending it from day one is the stated pre-6.1 condition (DD-141).
 */
export const bearerTokenConfig = [{ urlPattern: /^.*\/api\/.*$/ }];

/**
 * Load the application configuration and assemble the providers.
 *
 * Increment 7.1 wires the shell (config + router) and the operational
 * telemetry (SHL-14): traces, metrics with Core Web Vitals, uncaught errors as
 * span events, and `traceparent` propagation on HTTP calls — all through
 * `aurelius-atlas-observability`, replacing the Aurelius Google Analytics and
 * clickstream paths (DD-129). Increment 7.3 adds the auth wiring (DD-133):
 * Keycloak with check-sso + silent-SSO (APC-05) and the bearer-token
 * interceptor on `/api` (APC-06, DD-004's in-memory token store), replacing the
 * Aurelius `libs/authentication` wholesale (DD-141) — the same provider set the
 * example app proves.
 * @returns The {@link ApplicationConfig} to bootstrap with.
 */
export async function initialize(): Promise<ApplicationConfig> {
    const config = await loadConfig();
    const sessionResource = createAureliusSessionResource();
    // The OTLP credential seam (DD-193, aurelius-atlas-observability): the
    // exporters read the user's token through its headers factory, lazily —
    // per export, from the live Keycloak client the gate's initializer
    // attaches below. No ordering is read into that attach: the factory
    // resolves the token at export time, when check-sso has long settled.
    const ingestAuth = createAureliusOtelIngestAuth();

    return {
        providers: [
            provideBrowserGlobalErrorListeners(),
            // Uncaught errors (window.onerror + unhandledrejection) become
            // exception events on the active span, or a standalone error
            // span — and, above it (ALR-04, DD-172), an alert in the drawer.
            // The chain records first, then delegates: SHL-14 is untouched.
            { provide: ErrorHandler, useFactory: alertsErrorHandlerFactory },
            // The telemetry gate (SPL-11, DD-158): the stored switch decides
            // at bootstrap. Off = no providers at all — the interceptor falls
            // back to the no-op global tracer; TelemetryService's optional
            // token injections return null exactly then. On = the SDK is
            // assembled as before (SHL-14).
            ...(TelemetryService.storedEnabled()
                ? [
                      provideAureliusOpenTelemetry({
                          exporter: new OTLPTraceExporter({
                              url: config.otelExporterUrl,
                              // The user token rides every push (DD-193):
                              // the OTLP leg is outside HttpClient, so the
                              // bearer interceptor above cannot cover it.
                              headers: ingestAuth.headers,
                          }),
                          name: "aurelius-atlas-webapp",
                          resource: sessionResource,
                      }),
                      provideAureliusOpenTelemetryMetrics({
                          exporter: new OTLPMetricExporter({
                              url: metricsUrl(config),
                              headers: ingestAuth.headers,
                          }),
                          name: "aurelius-atlas-webapp",
                          resource: sessionResource,
                      }),
                      // The seam's other end (DD-193, CIA-02): the live
                      // Keycloak client — the same DI instance the bearer
                      // interceptor reads — into the headers factory. Inside
                      // the gate: with telemetry off there is no exporter to
                      // feed, and no credential to stage.
                      provideAppInitializer(() => ingestAuth.attach(inject(Keycloak))),
                  ]
                : []),
            // The display time zone (SPL-07): the stored choice, null = the
            // system default. DatePipe formats against it (the token replaces
            // the legacy DATE_TIME_ZONE, removed in Angular 22); changing it
            // takes effect on reload, which the settings panel states.
            { provide: DATE_PIPE_DEFAULT_TIMEZONE, useFactory: () => TimezoneService.storedTimezone() },
            // The REST client composes every URL from this base — the Aurelius
            // deployment-proxy coupling is not ported (APC-01, DD-139).
            provideApiBaseUrl(config.apiBaseUrl),
            // check-sso + silent-SSO: an existing SSO session signs in without a
            // click; the root guard (routes.ts) redirects everyone else (APC-05).
            provideKeycloak({
                config: config.keycloak,
                initOptions: keycloakInitOptions(),
            }),
            // Bearer token on every /api call (APC-06, DD-004). The server
            // ignores it until 6.1; sending it from day one is the stated
            // pre-6.1 condition (DD-141), and refresh is keycloak-angular's —
            // the legacy updateToken loop is not ported (APC-07).
            {
                provide: INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG,
                useValue: bearerTokenConfig,
            },
            provideZonelessChangeDetection(),
            provideRouter(
                routes,
                withComponentInputBinding(),
                // Aurelius routes with `scrollPositionRestoration: 'enabled'` (SHL-06).
                withInMemoryScrolling({ anchorScrolling: "enabled", scrollPositionRestoration: "enabled" }),
            ),
            // The OTLP interceptor adds W3C traceparent to every API call so
            // browser and server spans join one trace (ADR 016); the bearer
            // interceptor adds the Keycloak token to /api (APC-06); the alerts
            // reporter watches /api responses and records 5xx/network failures
            // as alerts, re-throwing untouched (ALR-05, DD-173).
            provideHttpClient(
                withXhr(),
                withInterceptors([
                    aureliusOpenTelemetryHttpInterceptor,
                    includeBearerTokenInterceptor,
                    alertsHttpInterceptor,
                ]),
            ),
            // The validated config is provided so feature slices read it from DI
            // instead of fetching it themselves (SHL-10: one settings channel).
            { provide: APP_CONFIG, useValue: config },
        ],
    };
}
