import { AppConfig, parseAppConfig } from "./config";
import { metricsUrl } from "./app.config";

const valid = {
    keycloak: { clientId: "aurelius", realm: "master", url: "http://keycloak.localhost:8080" },
    apiBaseUrl: "/api",
    otelExporterUrl: "/otel/v1/traces",
    appName: "Aurelius Atlas Data Governance",
    appCopyright: 2022,
    appVersion: "0.0.0",
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
        ["appName", { ...valid, appName: "" }],
        ["appVersion", { ...valid, appVersion: "" }],
    ])("throws when %s is missing or empty", (name, payload) => {
        expect(() => parseAppConfig(payload)).toThrow(new RegExp(`"${name}" must be a non-empty string`));
    });

    it("throws when appCopyright is not an integer year (SHC-06, SHL-02)", () => {
        expect(() => parseAppConfig({ ...valid, appCopyright: "2022" })).toThrow(/"appCopyright" must be an integer/);
        expect(() => parseAppConfig({ ...valid, appCopyright: 2022.5 })).toThrow(/"appCopyright" must be an integer/);
        expect(() => parseAppConfig({ ...valid, appCopyright: undefined })).toThrow(
            /"appCopyright" must be an integer/,
        );
    });

    it("keeps the shell fields in the parsed config (SHC-06)", () => {
        const config = parseAppConfig(valid);
        expect(config.appName).toBe("Aurelius Atlas Data Governance");
        expect(config.appCopyright).toBe(2022);
        expect(config.appVersion).toBe("0.0.0");
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
