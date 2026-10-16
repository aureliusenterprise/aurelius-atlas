import { InjectionToken, makeEnvironmentProviders, provideAppInitializer } from "@angular/core";
import { Meter } from "@opentelemetry/api";
import { defaultResource, Resource, resourceFromAttributes } from "@opentelemetry/resources";
import {
    ConsoleMetricExporter,
    MeterProvider,
    PeriodicExportingMetricReader,
    type PushMetricExporter,
} from "@opentelemetry/sdk-metrics";
import { onCLS, onFCP, onINP, onLCP, onTTFB, type Metric } from "web-vitals";

export const AURELIUS_METER_PROVIDER = new InjectionToken<MeterProvider>("AURELIUS_METER_PROVIDER");
export const AURELIUS_METER = new InjectionToken<Meter>("AURELIUS_METER");

export interface AureliusOpenTelemetryMetricsOptions {
    /**
     * Metric exporter; defaults to {@link ConsoleMetricExporter}.
     */
    exporter?: PushMetricExporter;

    /**
     * Service name for the resource; defaults to `aurelius-frontend`.
     */
    name?: string;

    /**
     * Optional `service.version` resource attribute.
     */
    serviceVersion?: string;

    /**
     * Extra resource merged last (e.g. {@link createAureliusSessionResource}).
     */
    resource?: Resource;

    /**
     * Push cadence in milliseconds; defaults to 10s.
     */
    exportIntervalMillis?: number;

    /**
     * Instrument Core Web Vitals automatically; defaults to true.
     */
    webVitals?: boolean;
}

/**
 * Histograms per Core Web Vital, in the units the web-vitals library emits
 * (CLS unitless; INP/LCP/FCP/TTFB milliseconds). The JS SDK records with
 * explicit bucket boundaries, which the collector's Prometheus exporter
 * keeps as classic histograms — panels query `*_bucket` with `by (le)`.
 *
 * Reports are recorded with `reportAllChanges` enabled: web-vitals only
 * *forces* its callback at page-hide (after any teardown-time metric
 * collection has run), while with `reportAllChanges` every update is
 * delivered during page life and the periodic reader ships it. The library's
 * reporter dedupes unchanged values, so recording `metric.value` adds one
 * observation per page (plus rare updates such as a growing CLS).
 */
export function instrumentAureliusWebVitals(meter: Meter): void {
    const histograms: Record<string, ReturnType<Meter["createHistogram"]>> = {
        CLS: meter.createHistogram("web_vital_cls", { description: "Cumulative Layout Shift (unitless)" }),
        INP: meter.createHistogram("web_vital_inp_milliseconds", {
            unit: "ms",
            description: "Interaction to Next Paint",
        }),
        LCP: meter.createHistogram("web_vital_lcp_milliseconds", {
            unit: "ms",
            description: "Largest Contentful Paint",
        }),
        FCP: meter.createHistogram("web_vital_fcp_milliseconds", { unit: "ms", description: "First Contentful Paint" }),
        TTFB: meter.createHistogram("web_vital_ttfb_milliseconds", { unit: "ms", description: "Time To First Byte" }),
    };
    const record = (histogram: ReturnType<Meter["createHistogram"]>, metric: Metric) => {
        histogram.record(metric.value, {
            "web.vital.rating": metric.rating ?? "unknown",
            "web.vital.navigation_type": metric.navigationType,
        });
    };
    const opts = { reportAllChanges: true };
    onCLS((m) => record(histograms["CLS"], m), opts);
    onFCP((m) => record(histograms["FCP"], m), opts);
    onINP((m) => record(histograms["INP"], m), opts);
    onLCP((m) => record(histograms["LCP"], m), opts);
    onTTFB((m) => record(histograms["TTFB"], m), opts);
}

/**
 * Create a {@link MeterProvider} with a periodic OTel metric reader.
 * @param options Exporter/identity options.
 * @returns The meter provider (already configured, not yet globally registered).
 */
export function createAureliusMeterProvider(options?: AureliusOpenTelemetryMetricsOptions): MeterProvider {
    const reader = new PeriodicExportingMetricReader({
        exportIntervalMillis: options?.exportIntervalMillis ?? 10_000,
        exporter: options?.exporter ?? new ConsoleMetricExporter(),
    });
    let resource = defaultResource().merge(
        resourceFromAttributes({
            "service.name": options?.name ?? "aurelius-frontend",
            ...(options?.serviceVersion ? { "service.version": options.serviceVersion } : {}),
        }),
    );
    if (options?.resource) {
        resource = resource.merge(options.resource);
    }
    // The web SDK's default resource has no `service.instance.id`, and the
    // collector's Prometheus exporter only emits `target_info` (which is how
    // resource attributes such as `session.id` become Prom labels) when the
    // resource carries one.
    return new MeterProvider({
        resource: resource.merge(resourceFromAttributes({ "service.instance.id": crypto.randomUUID() })),
        readers: [reader],
    });
}

/**
 * Flush pending metric records when the page is hidden or unloaded. The
 * web-vitals library reports CLS, INP and the final LCP at pagehide, and the
 * periodic reader has no unload hook — without this, those records die with
 * the tab. Attach this *after* instrumenting web-vitals: listeners run in
 * registration order, and the flush must happen after the final records.
 * @param provider The meter provider to flush.
 */
export function flushMetricsOnPageHide(provider: MeterProvider): void {
    const flush = () => {
        provider.forceFlush().catch(() => undefined);
    };
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") {
            flush();
        }
    });
    window.addEventListener("pagehide", flush);
}

/**
 * Provides an OTel {@link Meter} and, by default, records Core Web Vitals
 * into histograms exported through the given metric exporter.
 * @param options Exporter/identity options.
 * @returns Environment providers.
 */
export function provideAureliusOpenTelemetryMetrics(options?: AureliusOpenTelemetryMetricsOptions) {
    let provider: MeterProvider | undefined;

    const resolve = (): MeterProvider => {
        if (!provider) {
            provider = createAureliusMeterProvider(options);
            if (options?.webVitals ?? true) {
                instrumentAureliusWebVitals(provider.getMeter("aurelius-observability"));
            }
            flushMetricsOnPageHide(provider);
        }
        return provider;
    };

    return makeEnvironmentProviders([
        provideAppInitializer(() => {
            resolve();
        }),
        {
            provide: AURELIUS_METER_PROVIDER,
            useFactory: resolve,
        },
        {
            provide: AURELIUS_METER,
            useFactory: () => resolve().getMeter("aurelius-observability"),
        },
    ]);
}
