"""The process's OpenTelemetry providers, installed natively (DD-210).

The apps reach telemetry through this module: ``setup_telemetry`` installs
the global tracer, meter and (optionally) logger providers; the app-built
export leg (``build_otlp_pipeline``) rides it as an extra processor/reader,
``bridge_logging`` routes stdlib log records into the log pipeline.

Two export legs, by design (DD-196, DD-197, DD-210):

- the **app-owned leg**: the collector's per-service port, whose bearer JWT
  must refresh per export — the app builds it (``build_otlp_pipeline``) and
  hands its processor/reader to ``setup_telemetry``;
- the **env leg**: when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set in the
  process environment, standard OTLP/HTTP exporters ride it with the
  standard env configuration (endpoint, certificate, static headers). This
  is the legacy shared-token leg (CIA-10): a static bearer is exactly what
  the OTel SDK reads from the environment, and that producer's token is
  static — its per-service graduation is deferred (DD-196).

logfire 5.2 (the shell DD-196 configured with ``send_to_logfire=False``) is
gone: every use of it was a thin wrapper over these native packages, and the
OTLP wire to the collector is plain OTLP/HTTP either way (DD-210).
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from opentelemetry import metrics, trace
from opentelemetry._logs import LoggerProvider as LoggerProviderABC
from opentelemetry._logs import get_logger_provider, set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor, _build_default_config
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogRecordExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SynchronousMultiSpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

if TYPE_CHECKING:
    from opentelemetry.sdk.metrics.export import MetricReader
    from opentelemetry.sdk.trace import SpanProcessor

    from aurelius_atlas_otel.ingest import IngestPipeline

OTEL_EXPORTER_OTLP_ENDPOINT = "OTEL_EXPORTER_OTLP_ENDPOINT"
"""The standard env var whose presence switches on the env leg (DD-210): the
OTLP exporters themselves read endpoint, certificate and headers from the
``OTEL_EXPORTER_OTLP_*`` family."""

_installed = False
"""Whether this process has installed its providers (first call wins, per the
OTel global-provider lifecycle)."""


def _process_metrics_config() -> dict[str, list[str] | None]:
    """The system-metrics instruments an app registers (DD-210).

    The package's own default set (the per-process ``process.*`` and CPython
    ``cpython.gc.*`` groups, with their package-owned label lists), minus the
    host-wide ``system.*`` group: the dev/e2e apps share one host, so five
    containers would report the same host series five times — the infra's
    host metrics ride the metrics pullers, not the apps.
    """
    return {name: labels for name, labels in _build_default_config().items() if not name.startswith("system.")}


Providers = tuple[TracerProvider, MeterProvider, LoggerProvider | None]
"""The (tracer, meter, logger) providers ``build_providers`` returns — the
logger provider is None when logs are not exported."""


def _env_leg_on() -> bool:
    """Whether the env leg is configured in this process's environment."""
    return bool(os.environ.get(OTEL_EXPORTER_OTLP_ENDPOINT, "").strip())


def build_providers(
    service_name: str,
    service_version: str,
    *,
    pipeline: IngestPipeline | None = None,
    logs: bool = False,
    console: bool = False,
) -> Providers:
    """Build the SDK providers for one service, without installing them.

    :param service_name: the ``service.name`` resource attribute
    :param service_version: the ``service.version`` resource attribute
    :param pipeline: the app-built ingest leg (DD-196) — its span processor
        and metric reader, riding the collector's per-service port
    :param logs: also build a logger provider, exporting log records over
        OTLP on the env leg (DD-210)
    :param console: also print spans and log records to stdout (the dev
        console for debug-level runs — the cheap replacement for logfire's,
        DD-210)
    """
    resource = Resource.create({"service.name": service_name, "service.version": service_version})
    env_leg = _env_leg_on()

    processors: list[SpanProcessor] = []
    if pipeline is not None:
        processors.append(pipeline[0])
    if env_leg:
        processors.append(BatchSpanProcessor(OTLPSpanExporter()))
    if console:
        processors.append(BatchSpanProcessor(ConsoleSpanExporter()))
    active = SynchronousMultiSpanProcessor()
    for processor in processors:
        active.add_span_processor(processor)
    tracer_provider = TracerProvider(resource=resource, active_span_processor=active)

    readers: list[MetricReader] = []
    if pipeline is not None:
        readers.append(pipeline[1])
    if env_leg:
        readers.append(PeriodicExportingMetricReader(OTLPMetricExporter()))
    meter_provider = MeterProvider(resource=resource, metric_readers=readers)
    SystemMetricsInstrumentor(config=_process_metrics_config()).instrument(meter_provider=meter_provider)

    logger_provider: LoggerProvider | None = None
    if logs:
        logger_provider = LoggerProvider(resource=resource)
        if env_leg:
            logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
        if console:
            logger_provider.add_log_record_processor(BatchLogRecordProcessor(ConsoleLogRecordExporter()))

    return tracer_provider, meter_provider, logger_provider


def setup_telemetry(
    service_name: str,
    service_version: str,
    *,
    pipeline: IngestPipeline | None = None,
    logs: bool = False,
    console: bool = False,
) -> None:
    """Install the process's global OTel providers (DD-210, supersedes the logfire shell).

    The providers are process-global and installed once: the first call in a
    process configures them, later calls are no-ops — the OTel globals are
    set-once, and the FastAPI test harnesses create one app per test. The
    meter provider carries the per-process/CPython system instruments (DD-210).

    :param service_name: the ``service.name`` resource attribute
    :param service_version: the ``service.version`` resource attribute
    :param pipeline: the app-built ingest leg (DD-196)
    :param logs: install a logger provider too, exporting log records over
        OTLP on the env leg (DD-210)
    :param console: also print spans to stdout (the dev console, debug runs)
    """
    global _installed  # noqa: PLW0603  # the set-once provider guard
    if _installed:
        return

    tracer_provider, meter_provider, logger_provider = build_providers(
        service_name,
        service_version,
        pipeline=pipeline,
        logs=logs,
        console=console,
    )
    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(meter_provider)
    if logger_provider is not None:
        set_logger_provider(logger_provider)

    _installed = True


def bridge_logging(*logger_names: str) -> None:
    """Route the named loggers' stdlib records into the OTel log pipeline (DD-210).

    Each logger carries exactly one ``LoggingHandler`` on the installed
    logger provider, with propagation off — the fastapi-example's log tail,
    replacing the handler wiring the logfire shell needed.

    :param logger_names: the loggers to bridge (the app's and uvicorn's)
    """
    provider: LoggerProviderABC = get_logger_provider()
    for name in logger_names:
        logger = logging.getLogger(name)
        logger.handlers = [handler for handler in logger.handlers if not isinstance(handler, LoggingHandler)]
        logger.addHandler(LoggingHandler(level=logging.NOTSET, logger_provider=provider))
        logger.propagate = False
