import { AppConfig, parseAppConfig } from "./config";
import { metricsUrl } from "./app.config";

const valid = {
    keycloak: { clientId: "aurelius", realm: "master", url: "http://keycloak.localhost:8080" },
    apiBaseUrl: "/api",
    otelExporterUrl: "/otel/v1/traces",
    appName: "Aurelius Atlas Data Governance",
    atlasClientId: "aurelius-atlas-server",
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
    ])("throws when %s is missing or empty", (name, payload) => {
        expect(() => parseAppConfig(payload)).toThrow(new RegExp(`"${name}" must be a non-empty string`));
    });

    it("keeps the shell name in the parsed config (SHC-06)", () => {
        expect(parseAppConfig(valid).appName).toBe("Aurelius Atlas Data Governance");
    });

    it("ignores a version and a copyright year in the payload (VER-01, VER-04, DD-725/DD-726)", () => {
        // An old config.json still carrying the keys must not fail bootstrap,
        // and must not put them back on the parsed shape.
        const config = parseAppConfig({ ...valid, appVersion: "1.2.3", appCopyright: 2022 });
        expect("appVersion" in config).toBe(false);
        expect("appCopyright" in config).toBe(false);
    });

    it("keeps the metrics endpoint optional", () => {
        expect("otelMetricsExporterUrl" in parseAppConfig(valid)).toBe(false);
        const withMetrics = { ...valid, otelMetricsExporterUrl: "/otel/v1/metrics" };
        expect(parseAppConfig(withMetrics).otelMetricsExporterUrl).toBe("/otel/v1/metrics");
    });

    it("throws when otelMetricsExporterUrl is present but empty", () => {
        expect(() => parseAppConfig({ ...valid, otelMetricsExporterUrl: "" })).toThrow(/"otelMetricsExporterUrl"/);
    });

    it("defaults atlasClientId to the server's client (EDT-09, DD-324)", () => {
        const { atlasClientId, ...without } = valid;

        expect(parseAppConfig(without).atlasClientId).toBe("aurelius-atlas-server");
    });

    it("keeps an explicit atlasClientId (DD-324)", () => {
        expect(parseAppConfig({ ...valid, atlasClientId: "other-client" }).atlasClientId).toBe("other-client");
    });

    it("throws when atlasClientId is present but empty (DD-324)", () => {
        expect(() => parseAppConfig({ ...valid, atlasClientId: "" })).toThrow(/"atlasClientId"/);
    });

    it("keeps lineageModelBaseUrl absent when the config omits it (LDG-07)", () => {
        // The client's own /lineage-model default is what the app runs on, so
        // the parsed config must not invent a key (DD-387's override-only rule).
        expect("lineageModelBaseUrl" in parseAppConfig(valid)).toBe(false);
    });

    it("keeps an explicit lineageModelBaseUrl (LDG-07)", () => {
        expect(parseAppConfig({ ...valid, lineageModelBaseUrl: "/aux/lineage" }).lineageModelBaseUrl).toBe(
            "/aux/lineage",
        );
    });

    it("throws when lineageModelBaseUrl is present but empty (LDG-07)", () => {
        expect(() => parseAppConfig({ ...valid, lineageModelBaseUrl: "" })).toThrow(/"lineageModelBaseUrl"/);
    });

    it("keeps validateEntityBaseUrl absent when the config omits it (EDT-22)", () => {
        // The client's own /validate-entity default is what the app runs on,
        // so the parsed config must not invent a key (DD-387's rule, DD-445).
        expect("validateEntityBaseUrl" in parseAppConfig(valid)).toBe(false);
    });

    it("keeps an explicit validateEntityBaseUrl (EDT-22)", () => {
        expect(parseAppConfig({ ...valid, validateEntityBaseUrl: "/aux/validate" }).validateEntityBaseUrl).toBe(
            "/aux/validate",
        );
    });

    it("throws when validateEntityBaseUrl is present but empty (EDT-22)", () => {
        expect(() => parseAppConfig({ ...valid, validateEntityBaseUrl: "" })).toThrow(/"validateEntityBaseUrl"/);
    });

    it("keeps docsRef absent when the config omits it (SHC-03, DD-886)", () => {
        // The header's own `main` default is what the app runs on, so the
        // parsed config must not invent a key (DD-387's override-only rule).
        expect("docsRef" in parseAppConfig(valid)).toBe(false);
    });

    it("keeps an explicit docsRef (SHC-03, DD-886)", () => {
        expect(parseAppConfig({ ...valid, docsRef: "v0.1.0-rc.11" }).docsRef).toBe("v0.1.0-rc.11");
    });

    it("throws when docsRef is present but empty (SHC-03, DD-886)", () => {
        expect(() => parseAppConfig({ ...valid, docsRef: "" })).toThrow(/"docsRef"/);
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
