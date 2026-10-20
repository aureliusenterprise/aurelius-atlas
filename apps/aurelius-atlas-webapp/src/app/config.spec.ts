import { AppConfig, parseAppConfig } from "./config";
import { metricsUrl } from "./app.config";

const valid = {
    keycloak: { clientId: "aurelius", realm: "master", url: "http://keycloak.localhost:8080" },
    apiBaseUrl: "/api",
    otelExporterUrl: "/otel/v1/traces",
};

describe("parseAppConfig", () => {
    it("returns a typed config for a valid payload", () => {
        expect(parseAppConfig(valid)).toEqual(valid as AppConfig);
    });

    it("throws when the payload is not an object", () => {
        expect(() => parseAppConfig(null)).toThrow(/expected a JSON object/);
        expect(() => parseAppConfig("nope")).toThrow(/expected a JSON object/);
    });

    it("throws when keycloak is missing", () => {
        expect(() => parseAppConfig({ ...valid, keycloak: undefined })).toThrow(/missing "keycloak"/);
    });

    it.each([
        ["keycloak.clientId", { keycloak: { realm: "master", url: "u" }, apiBaseUrl: "/api", otelExporterUrl: "/o" }],
        ["keycloak.realm", { keycloak: { clientId: "c", url: "u" }, apiBaseUrl: "/api", otelExporterUrl: "/o" }],
        ["keycloak.url", { keycloak: { clientId: "c", realm: "r" }, apiBaseUrl: "/api", otelExporterUrl: "/o" }],
        ["apiBaseUrl", { keycloak: valid.keycloak, otelExporterUrl: "/o" }],
        ["otelExporterUrl", { keycloak: valid.keycloak, apiBaseUrl: "/api" }],
    ])("throws when %s is missing or empty", (name, payload) => {
        expect(() => parseAppConfig(payload)).toThrow(new RegExp(`"${name}" must be a non-empty string`));
    });

    it("keeps the metrics endpoint optional", () => {
        expect("otelMetricsExporterUrl" in parseAppConfig(valid)).toBe(false);
        const withMetrics = { ...valid, otelMetricsExporterUrl: "/otel/v1/metrics" };
        expect(parseAppConfig(withMetrics).otelMetricsExporterUrl).toBe("/otel/v1/metrics");
    });

    it("throws when otelMetricsExporterUrl is present but empty", () => {
        expect(() => parseAppConfig({ ...valid, otelMetricsExporterUrl: "" })).toThrow(/"otelMetricsExporterUrl"/);
    });
});

describe("metricsUrl", () => {
    it("prefers the explicit metrics endpoint", () => {
        const config = { ...valid, otelMetricsExporterUrl: "/collect/metrics" } as AppConfig;
        expect(metricsUrl(config)).toBe("/collect/metrics");
    });

    it("derives it from the traces endpoint when unset", () => {
        expect(metricsUrl(valid as AppConfig)).toBe("/otel/v1/metrics");
    });
});
