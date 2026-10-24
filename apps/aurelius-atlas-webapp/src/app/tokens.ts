import { InjectionToken } from "@angular/core";

import { AppConfig } from "./config";

/**
 * The validated runtime configuration, provided at bootstrap.
 *
 * Components and services inject this instead of fetching `/config.json`
 * themselves, so there is one settings channel (SHL-10, ADR 018).
 */
export const APP_CONFIG = new InjectionToken<AppConfig>("APP_CONFIG");
