import { ApplicationConfig, provideBrowserGlobalErrorListeners, provideZonelessChangeDetection } from "@angular/core";
import { provideRouter, withComponentInputBinding, withInMemoryScrolling } from "@angular/router";

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
 * Load the application configuration and assemble the providers.
 *
 * Increment 7.1 wires only what the shell needs: the validated runtime config
 * (kept for later slices to read) and the router. The Keycloak, OpenTelemetry,
 * and bearer-token providers arrive with 7.3, which owns the auth wiring.
 * @returns The {@link ApplicationConfig} to bootstrap with.
 */
export async function initialize(): Promise<ApplicationConfig> {
    const config = await loadConfig();

    return {
        providers: [
            provideBrowserGlobalErrorListeners(),
            provideZonelessChangeDetection(),
            provideRouter(
                routes,
                withComponentInputBinding(),
                // Aurelius routes with `scrollPositionRestoration: 'enabled'` (SHL-06).
                withInMemoryScrolling({ anchorScrolling: "enabled", scrollPositionRestoration: "enabled" }),
            ),
            // The validated config is provided so feature slices read it from DI
            // instead of fetching it themselves (SHL-10: one settings channel).
            { provide: APP_CONFIG, useValue: config },
        ],
    };
}
