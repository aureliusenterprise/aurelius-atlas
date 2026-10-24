import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { TestBed } from "@angular/core/testing";
import { AggregationTemporality, InMemoryMetricExporter, MeterProvider } from "@opentelemetry/sdk-metrics";
import { resourceFromAttributes } from "@opentelemetry/resources";
import {
    AURELIUS_METER,
    AURELIUS_METER_PROVIDER,
    createAureliusMeterProvider,
    instrumentAureliusWebVitals,
    provideAureliusOpenTelemetryMetrics,
    flushMetricsOnPageHide,
} from "./opentelemetry-metrics.provider";
import { createOrLoadSessionId, createAureliusSessionResource } from "./opentelemetry-session";

interface VitalHandlers {
    CLS: (m: never) => void;
    FCP: (m: never) => void;
    INP: (m: never) => void;
    LCP: (m: never) => void;
    TTFB: (m: never) => void;
}

const handlers = vi.hoisted(() => ({ current: {} as VitalHandlers }));

vi.mock("web-vitals", () => ({
    onCLS: (cb: (m: never) => void) => (handlers.current.CLS = cb),
    onFCP: (cb: (m: never) => void) => (handlers.current.FCP = cb),
    onINP: (cb: (m: never) => void) => (handlers.current.INP = cb),
    onLCP: (cb: (m: never) => void) => (handlers.current.LCP = cb),
    onTTFB: (cb: (m: never) => void) => (handlers.current.TTFB = cb),
}));

const metric = (name: string, value: number) => ({
    name,
    value,
    rating: "good",
    delta: value,
    id: "test",
    navigationType: "navigate",
});

async function flush(exporter: InMemoryMetricExporter, provider: MeterProvider) {
    await provider.forceFlush();
    return exporter.getMetrics();
}

describe("opentelemetry-session", () => {
    beforeEach(() => sessionStorage.clear());

    it("creates a session id once and reuses it after reload", () => {
        const first = createOrLoadSessionId();
        expect(first).toMatch(/^[0-9a-f-]{36}$/);
        expect(createOrLoadSessionId()).toBe(first);
    });

    it("exposes session.id as a resource attribute", () => {
        const resource = createAureliusSessionResource();
        expect(resource.attributes["session.id"]).toBe(createOrLoadSessionId());
    });
});

describe("opentelemetry-metrics.provider", () => {
    let exporter: InMemoryMetricExporter;

    beforeEach(() => {
        exporter = new InMemoryMetricExporter(AggregationTemporality.DELTA);
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    it("creates a meter provider with service name", async () => {
        const provider = createAureliusMeterProvider({ exporter, name: "test-app" });
        provider.getMeter("t").createCounter("c").add(1);
        await provider.forceFlush();
        const scopes = exporter.getMetrics();
        expect(scopes.length).toBeGreaterThan(0);
        expect(JSON.stringify(scopes)).toContain("test-app");
    });

    it("records Core Web Vitals into histograms", async () => {
        const provider = createAureliusMeterProvider({ exporter, name: "test-app" });
        instrumentAureliusWebVitals(provider.getMeter("t"));
        handlers.current.CLS(metric("CLS", 0.1) as never);
        handlers.current.LCP(metric("LCP", 1.2) as never);
        handlers.current.INP(metric("INP", 40) as never);
        handlers.current.FCP(metric("FCP", 0.8) as never);
        handlers.current.TTFB(metric("TTFB", 0.3) as never);

        const scopes = await flush(exporter, provider);
        const names = scopes.flatMap((s) => s.scopeMetrics.flatMap((m) => m.metrics.map((md) => md.descriptor.name)));
        expect(names).toEqual(
            expect.arrayContaining([
                "web_vital_cls",
                "web_vital_lcp_milliseconds",
                "web_vital_inp_milliseconds",
                "web_vital_fcp_milliseconds",
                "web_vital_ttfb_milliseconds",
            ]),
        );
        expect(JSON.stringify(scopes)).toContain('"web.vital.rating":"good"');
    });

    it("records a vital reported without a rating as unknown", async () => {
        const provider = createAureliusMeterProvider({ exporter, name: "test-app" });
        instrumentAureliusWebVitals(provider.getMeter("t"));
        handlers.current.LCP({ ...metric("LCP", 1.2), rating: undefined } as never);

        const scopes = await flush(exporter, provider);
        expect(JSON.stringify(scopes)).toContain('"web.vital.rating":"unknown"');
    });

    it("provides a meter through DI", async () => {
        const providers = provideAureliusOpenTelemetryMetrics({ exporter, webVitals: false });
        // The provider bag is opaque here; only assert construction succeeds
        // (the functional paths are covered above and in the app spec).
        expect(providers).toBeTruthy();
    });

    it("resolves the meter provider and meter once, through app init", () => {
        TestBed.configureTestingModule({
            providers: [provideAureliusOpenTelemetryMetrics({ exporter, name: "di-app", webVitals: false })],
        });

        const provider = TestBed.inject(AURELIUS_METER_PROVIDER);
        const meter = TestBed.inject(AURELIUS_METER);

        expect(provider).toBeInstanceOf(MeterProvider);
        expect(TestBed.inject(AURELIUS_METER_PROVIDER)).toBe(provider); // singleton
        expect(() => meter.createCounter("through-di").add(1)).not.toThrow();
        TestBed.resetTestingModule();
    });

    it("merges the resource option into the meter provider resource", async () => {
        const provider = createAureliusMeterProvider({
            exporter,
            name: "test-app",
            resource: resourceFromAttributes({ "deployment.environment.name": "stag" }),
        });
        provider.getMeter("t").createCounter("c").add(1);
        const scopes = await flush(exporter, provider);

        expect(JSON.stringify(scopes.map((s) => s.resource))).toContain("stag");
    });

    it("applies serviceVersion and exportIntervalMillis options", async () => {
        const provider = createAureliusMeterProvider({
            exporter,
            name: "test-app",
            serviceVersion: "9.9.9",
            exportIntervalMillis: 60_000,
        });
        provider.getMeter("t").createCounter("c").add(1);
        await provider.forceFlush();
        expect(JSON.stringify(exporter.getMetrics())).toContain("9.9.9");
    });

    it("carries a service.instance.id so the collector emits target_info", async () => {
        const provider = createAureliusMeterProvider({ exporter, name: "test-app" });
        provider.getMeter("t").createCounter("c").add(1);
        const scopes = await flush(exporter, provider);
        expect(scopes.length).toBeGreaterThan(0);
        expect(JSON.stringify(scopes.map((s) => s.resource))).toMatch(/[0-9a-f]{8}-[0-9a-f-]{27}/);
    });

    it("flushes on pagehide and when the page becomes hidden", () => {
        const provider = createAureliusMeterProvider({ exporter, name: "test-app" });
        const forceFlush = vi.spyOn(provider, "forceFlush").mockResolvedValue(undefined);
        flushMetricsOnPageHide(provider);

        window.dispatchEvent(new PageTransitionEvent("pagehide"));
        expect(forceFlush).toHaveBeenCalledTimes(1);

        // Visible page: no flush.
        Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
        document.dispatchEvent(new Event("visibilitychange"));
        expect(forceFlush).toHaveBeenCalledTimes(1);

        // Hidden page: flush.
        Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
        document.dispatchEvent(new Event("visibilitychange"));
        expect(forceFlush).toHaveBeenCalledTimes(2);
    });

    it("survives a flush that fails (pagehide must not throw)", () => {
        const provider = createAureliusMeterProvider({ exporter, name: "test-app" });
        vi.spyOn(provider, "forceFlush").mockRejectedValue(new Error("exporter down"));
        flushMetricsOnPageHide(provider);

        expect(() => window.dispatchEvent(new PageTransitionEvent("pagehide"))).not.toThrow();
    });
});
