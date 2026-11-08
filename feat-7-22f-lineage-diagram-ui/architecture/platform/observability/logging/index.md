# Logging

The server writes its log records to two places: its process's output, which the container runtime keeps, and the collector, which passes them to Loki. The records come from its own logger, from the libraries it runs (`aurelius_atlas_core`, `aurelius_atlas_store_es`) and from uvicorn's errors. They go over the same per-service leg and credential as its traces and metrics. A server without an ingest credential sends nothing to the collector, and its output is the only record.

## Correlation

A record written while a request is answered carries that request's trace and span ids. Its 5xx answers carry the trace id as `requestId` (SRV-07), so one id leads from the caller's error to the trace in Tempo and to the records in Loki:

```
{service_name="aurelius-atlas-server"} | trace_id="<requestId>"
```

In Grafana, a span of the trace opens the records written under it (Tempo's link to Loki).

## What is logged

| Logger | Records |
| --- | --- |
| `aurelius-atlas-server` | start and stop; failures of the metrics, audit-aging and task schedulers; audit-write failures |
| `aurelius_atlas_core` | the core services' failures: the model loader's patches, the audit aging |
| `uvicorn.error` | the server's own failures, such as a socket or TLS error |

The level is `AURELIUS_ATLAS_SERVER_LOG_LEVEL`; `debug` also prints spans and records to the output. Loki deletes them after 30 days ([lifetimes](<https://aureliusenterprise.github.io/feat-7-22f-lineage-diagram-ui/architecture/data-lifecycle-management/data-archiving/index.md>)).
