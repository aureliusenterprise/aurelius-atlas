"""Unit tests for the native provider setup (DD-121): the legs, the install guard, the log bridge."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

import pytest
from aurelius_atlas_otel.ingest import ClientCredentialsTokenSource, build_otlp_pipeline
from aurelius_atlas_otel.telemetry import bridge_logging, build_providers, setup_telemetry
from opentelemetry import metrics, trace
from opentelemetry._logs import _internal as logs_internal
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.metrics import _internal as metrics_internal
from opentelemetry.sdk._logs._internal import SynchronousMultiLogRecordProcessor
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace import SynchronousMultiSpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor

if TYPE_CHECKING:
    from aurelius_atlas_otel.telemetry import Providers


@pytest.fixture(autouse=True)
def _clean_globals(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Reset the OTel global-provider state so each test installs fresh providers.

    The OTel globals are set-once; the tests restore the state on teardown so
    no provider leaks between tests.
    """
    saved = (
        trace._TRACER_PROVIDER_SET_ONCE._done,  # noqa: SLF001  # the set-once seam under test
        trace._TRACER_PROVIDER,  # noqa: SLF001
        metrics_internal._METER_PROVIDER_SET_ONCE._done,  # noqa: SLF001
        metrics_internal._METER_PROVIDER,  # noqa: SLF001
        logs_internal._LOGGER_PROVIDER_SET_ONCE._done,  # noqa: SLF001
        logs_internal._LOGGER_PROVIDER,  # noqa: SLF001
    )
    monkeypatch.setattr("aurelius_atlas_otel.telemetry._installed", False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    yield
    (
        trace._TRACER_PROVIDER_SET_ONCE._done,  # noqa: SLF001
        trace._TRACER_PROVIDER,  # noqa: SLF001
        metrics_internal._METER_PROVIDER_SET_ONCE._done,  # noqa: SLF001
        metrics_internal._METER_PROVIDER,  # noqa: SLF001
        logs_internal._LOGGER_PROVIDER_SET_ONCE._done,  # noqa: SLF001
        logs_internal._LOGGER_PROVIDER,  # noqa: SLF001
    ) = saved


def _processors(providers: Providers) -> list[str]:
    tracer_provider, _meter, _logger = providers
    multi = tracer_provider._active_span_processor  # noqa: SLF001  # the wiring seam under test
    assert isinstance(multi, SynchronousMultiSpanProcessor)
    return [type(cast("BatchSpanProcessor", p).span_exporter).__name__ for p in multi._span_processors]  # noqa: SLF001  # the wiring seam under test


def _log_processors(providers: Providers) -> list[str]:
    _tracer, _meter, logger_provider = providers
    assert logger_provider is not None
    multi = logger_provider._multi_log_record_processor  # noqa: SLF001  # the wiring seam under test
    assert isinstance(multi, SynchronousMultiLogRecordProcessor)
    exporters = [cast("BatchLogRecordProcessor", p)._batch_processor._exporter for p in multi._log_record_processors]  # noqa: SLF001  # the wiring seam under test
    return [type(e).__name__ for e in exporters]


@pytest.mark.covers("aurelius_atlas_otel.telemetry.build_providers", rules=["CIA-07"])
def test__without_the_env_leg_only_the_apps_processors_ride(monkeypatch: pytest.MonkeyPatch) -> None:
    """No endpoint in the environment: the providers carry exactly what the app passes."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    source = ClientCredentialsTokenSource("http://issuer.test/token", "otel-svc", "s3cret")
    pipeline = build_otlp_pipeline("https://otel-collector:4319", None, source)

    providers = build_providers("svc", "1.2", pipeline=pipeline)
    tracer_provider, meter_provider, logger_provider = providers

    assert logger_provider is None
    assert _processors(providers) == ["OTLPSpanExporter"]
    readers = cast("list[PeriodicExportingMetricReader]", meter_provider._metric_readers)  # noqa: SLF001  # the wiring seam under test
    assert [type(r).__name__ for r in readers] == ["PeriodicExportingMetricReader"]
    resource = tracer_provider.resource.attributes
    assert resource["service.name"] == "svc"
    assert resource["service.version"] == "1.2"
    tracer_provider.shutdown()
    meter_provider.shutdown()


@pytest.mark.covers("aurelius_atlas_otel.telemetry.build_providers", rules=["CIA-10"])
def test__the_env_leg_adds_standard_otlp_exporters(monkeypatch: pytest.MonkeyPatch) -> None:
    """With OTEL_EXPORTER_OTLP_ENDPOINT set, standard exporters ride the env config."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://otel-collector:4321")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_HEADERS", "Authorization=Bearer shared-token")

    providers = build_providers("svc", "1.0", logs=True)
    tracer_provider, meter_provider, logger_provider = providers

    assert _processors(providers) == ["OTLPSpanExporter"]
    assert _log_processors(providers) == ["OTLPLogExporter"]
    assert logger_provider is not None
    readers = cast("list[PeriodicExportingMetricReader]", meter_provider._metric_readers)  # noqa: SLF001  # the wiring seam under test
    exporters = [cast("OTLPMetricExporter", r._exporter) for r in readers]  # noqa: SLF001  # the wiring seam under test
    assert [type(e).__name__ for e in exporters] == ["OTLPMetricExporter"]
    # The SDK reads the standard env: the legacy leg's static shared bearer rides as a header.
    assert exporters[0]._headers.get("authorization") == "Bearer shared-token"  # noqa: SLF001
    tracer_provider.shutdown()
    meter_provider.shutdown()


@pytest.mark.covers("aurelius_atlas_otel.telemetry.build_providers", rules=["CIA-07"])
def test__the_process_metrics_ride_the_meter_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """The per-process/CPython instruments register on the built meter provider (DD-121)."""
    instrumentor = Mock()
    monkeypatch.setattr("aurelius_atlas_otel.telemetry.SystemMetricsInstrumentor", instrumentor)

    providers = build_providers("svc", "1.0")
    _tracer, meter_provider, _logger = providers

    _args, ctor_kwargs = instrumentor.call_args
    names = set(ctor_kwargs["config"])
    assert "process.cpu.time" in names
    assert "cpython.gc.collections" in names
    assert not [n for n in names if n.startswith("system.")], "the host-wide set stays off (DD-121)"
    wire = instrumentor.return_value.instrument.call_args.kwargs
    assert wire["meter_provider"] is meter_provider
    meter_provider.shutdown()


@pytest.mark.covers("aurelius_atlas_otel.telemetry.build_providers", rules=["CIA-07"])
def test__console_adds_stdout_exporters(monkeypatch: pytest.MonkeyPatch) -> None:
    """The dev console prints spans, and log records when logs are on."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    providers = build_providers("svc", "1.0", logs=True, console=True)
    tracer_provider, meter_provider, logger_provider = providers

    assert _processors(providers) == ["ConsoleSpanExporter"]
    assert _log_processors(providers) == ["ConsoleLogRecordExporter"]
    assert logger_provider is not None
    tracer_provider.shutdown()
    meter_provider.shutdown()
    logger_provider.shutdown()


@pytest.mark.covers("aurelius_atlas_otel.telemetry.setup_telemetry", rules=["CIA-07"])
def test__setup_installs_the_globals_once() -> None:
    """The first call installs the tracer/meter/logger globals; a second is a no-op."""
    setup_telemetry("svc", "1.0", logs=True)

    tracer_provider = trace.get_tracer_provider()
    meter_provider = metrics.get_meter_provider()
    logger_provider = logs_internal.get_logger_provider()
    assert type(tracer_provider).__name__ == "TracerProvider"
    assert type(meter_provider).__name__ == "MeterProvider"
    assert type(logger_provider).__name__ == "LoggerProvider"

    # A second call (a second create_app in the same process) changes nothing.
    setup_telemetry("other", "9.9")
    assert trace.get_tracer_provider() is tracer_provider
    assert metrics.get_meter_provider() is meter_provider


@pytest.mark.covers("aurelius_atlas_otel.telemetry.bridge_logging", rules=["CIA-10"])
def test__bridge_logging_attaches_exactly_one_handler_each() -> None:
    """Each named logger ends up with one OTel handler, propagation off, idempotently."""
    setup_telemetry("svc", "1.0", logs=True)

    names = ("bridge-test-a", "bridge-test-b")
    saved = {name: (logging.getLogger(name).handlers, logging.getLogger(name).propagate) for name in names}
    try:
        bridge_logging(*names)
        bridge_logging("bridge-test-a")  # a repeat replaces, never stacks

        for name in names:
            logger = logging.getLogger(name)
            handlers = [h for h in logger.handlers if isinstance(h, LoggingHandler)]
            assert len(handlers) == 1
            assert logger.propagate is False
    finally:
        for name, (handlers, propagate) in saved.items():
            logger = logging.getLogger(name)
            logger.handlers = handlers
            logger.propagate = propagate
