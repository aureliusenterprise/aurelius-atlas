# aurelius-atlas-observability

Browser OpenTelemetry providers and interceptors for Angular apps. This file
covers wiring specific to this lib; workspace-wide rules live in the root
`AGENTS.md` and the Angular lib recipe in `libs/angular/AGENTS.md`.

## Layout

- `src/lib/` — `provideAureliusOpenTelemetry()`, the tracer injection tokens, and
  `aureliusOpenTelemetryHttpInterceptor`; `src/index.ts` is the public API
- `src/lib/opentelemetry-metrics.provider.ts` — `provideAureliusOpenTelemetryMetrics()`
  with Core Web Vitals histograms (`instrumentAureliusWebVitals`); web-vitals runs
  with `reportAllChanges` and the provider records `metric.value`, because the
  library only forces its callback at pagehide — after any teardown flush.
  `flushMetricsOnPageHide` (attached _after_ instrumentation, listener order!) is
  a belt-and-braces flush; `service.instance.id` is generated so the collector
  emits `target_info` and resource attributes become Prometheus labels.
- `src/lib/opentelemetry-session.ts` — tab-scoped `session.id` resource shared by
  the tracer and meter providers (`createAureliusSessionResource`)
- `src/lib/opentelemetry-error.handler.ts` — `AureliusTraceErrorHandler`, bound as
  the app's `ErrorHandler`; records into the active span or a standalone
  `uncaught exception` span, and never rethrows (re-entry via `window.onerror`)
- `.spec.ts` files colocated with source

## Wiring Checklist

- `tsconfig.base.json` — `aurelius-atlas-observability` path alias used by the frontend.
- Consumed in `apps/aurelius-atlas-frontend-example` `app.config.ts`; the exporter is
  chosen by the **app**, not here (the lib defaults to `ConsoleSpanExporter`).
- Dev trace export goes through the frontend's `/otel` proxy
  (`proxy.conf.json` → collector `:4318`) — no collector host config in the lib.
- `package.json` — peer deps pin the OpenTelemetry SDK majors; bump them together
  with the app's direct `@opentelemetry/*` dependencies.

## Commands

```bash
nx test aurelius-atlas-observability -c ci   # Vitest unit tests
nx build aurelius-atlas-observability        # ng-packagr-lite package build
```

## Conventions

- The lib must stay exporter-agnostic: accept an exporter/options, never import a
  concrete exporter into the public API.
- The interceptor must propagate W3C `traceparent` and set span status from the
  HTTP response — keep both behaviours covered by tests.
- Service name defaults (`aurelius-frontend`) are overridable via options; don't
  hard-code app identity deeper in the lib.
- Metrics are DELTA-free: histograms use the SDK default (cumulative) temporality,
  which the collector's prometheus exporter serves as classic buckets (the JS SDK
  sets explicit boundaries) — dashboard panels query `<metric>_bucket`.

## Removal

Part of the spine. Removing it means removing the `aurelius-atlas-observability` alias,
the `provideAureliusOpenTelemetry()` call and interceptor registration in the
frontend, its `/otel` proxy entry, and its `mkdocs.yaml` entries.
