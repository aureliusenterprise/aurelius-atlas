"""Unit tests for the telemetry factories: the ingest leg, the native provider wiring (DD-107, DD-108, DD-121)."""

from typing import Any
from unittest.mock import Mock

import pytest
from aurelius_atlas_lineage_model.globals import LOGGER, NAME
from aurelius_atlas_lineage_model.providers.telemetry import configure_telemetry, ingest_pipeline
from aurelius_atlas_lineage_model.settings import LineageModelSettings
from fastapi import FastAPI
from pydantic import HttpUrl, SecretStr


def _otel_settings(**overrides: Any) -> LineageModelSettings:  # noqa: ANN401  # the settings fields under test
    """The conftest's settings plus the ingest credential, as the dev deployment sets them."""
    values: dict[str, Any] = {
        "otel_token_url": HttpUrl("http://issuer.test/realms/master/protocol/openid-connect/token"),
        "otel_client_secret": SecretStr("s3cr3t"),
    }
    values.update(overrides)
    return LineageModelSettings(
        auth_server_url=HttpUrl("http://issuer.test"),
        atlas_base_url=HttpUrl("http://atlas.test"),
        data2model_url=HttpUrl("http://data2model.test"),
        **values,
    )


@pytest.mark.covers("aurelius_atlas_lineage_model.providers.telemetry.ingest_pipeline", rules=["LM-10"])
def test__no_ingest_credential_means_console_only(settings: LineageModelSettings) -> None:
    """Without the ingest secret there is no OTLP leg: the app exports no OTLP (AUX-03, DD-121)."""
    assert ingest_pipeline(settings) is None


@pytest.mark.covers("aurelius_atlas_lineage_model.providers.telemetry.ingest_pipeline", rules=["LM-10"])
def test__one_half_of_the_credential_is_no_credential() -> None:
    """A token URL without the secret builds no leg — the pair is the setting (DD-107)."""
    assert ingest_pipeline(_otel_settings(otel_client_secret=None)) is None


@pytest.mark.covers("aurelius_atlas_lineage_model.providers.telemetry.ingest_pipeline", rules=["LM-10"])
def test__the_credential_builds_the_export_leg() -> None:
    """With the pair set, the pipeline is the (span processor, metric reader) pair for the providers (DD-107)."""
    pipeline = ingest_pipeline(_otel_settings())

    assert pipeline is not None
    span_processor, metric_reader = pipeline
    assert type(span_processor).__name__ == "BatchSpanProcessor"
    assert type(metric_reader).__name__ == "PeriodicExportingMetricReader"
    span_processor.shutdown()
    metric_reader.shutdown()


@pytest.mark.covers("aurelius_atlas_lineage_model.providers.telemetry.configure_telemetry", rules=["LM-10"])
def test__the_leg_rides_the_provider_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The configured leg travels to the providers as the span processor and metric reader (DD-108, DD-121)."""
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    monkeypatch.setattr(
        "aurelius_atlas_lineage_model.providers.telemetry.setup_telemetry",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    monkeypatch.setattr("aurelius_atlas_lineage_model.providers.telemetry.FastAPIInstrumentor", Mock())
    monkeypatch.setattr("aurelius_atlas_lineage_model.providers.telemetry.HTTPX2ClientInstrumentor", Mock())

    configure_telemetry(FastAPI(title=NAME, version="0"), _otel_settings())

    assert len(calls) == 1
    (service_name, _version), kwargs = calls[0]
    assert service_name == NAME
    assert kwargs["pipeline"] is not None


@pytest.mark.covers("aurelius_atlas_lineage_model.providers.telemetry.configure_telemetry", rules=["LM-10"])
def test__the_chain_upstreams_are_instrumented(monkeypatch: pytest.MonkeyPatch) -> None:
    """The httpx instrumentor is wired, so the caller's traceparent rides the chain (DD-121)."""
    httpx_instrumentor = Mock()
    monkeypatch.setattr("aurelius_atlas_lineage_model.providers.telemetry.setup_telemetry", Mock())
    monkeypatch.setattr("aurelius_atlas_lineage_model.providers.telemetry.FastAPIInstrumentor", Mock())
    monkeypatch.setattr(
        "aurelius_atlas_lineage_model.providers.telemetry.HTTPX2ClientInstrumentor",
        httpx_instrumentor,
    )

    configure_telemetry(FastAPI(title=NAME, version="0"), _otel_settings())

    httpx_instrumentor.return_value.instrument.assert_called_once()


@pytest.mark.covers("aurelius_atlas_lineage_model.providers.telemetry.configure_telemetry", rules=["LM-10"])
def test__console_only_configures_no_leg(monkeypatch: pytest.MonkeyPatch, settings: LineageModelSettings) -> None:
    """Without the leg, the providers get no exporters — and the app's log level is applied (AUX-03)."""
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    monkeypatch.setattr(
        "aurelius_atlas_lineage_model.providers.telemetry.setup_telemetry",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    monkeypatch.setattr("aurelius_atlas_lineage_model.providers.telemetry.FastAPIInstrumentor", Mock())
    monkeypatch.setattr("aurelius_atlas_lineage_model.providers.telemetry.HTTPX2ClientInstrumentor", Mock())
    level = LOGGER.level
    try:
        configure_telemetry(FastAPI(title=NAME, version="0"), settings.model_copy(update={"log_level": "warning"}))

        assert calls[0][1]["pipeline"] is None
        assert LOGGER.level == 30  # logging.WARNING: the settings' level reaches the app's logger
    finally:
        LOGGER.setLevel(level)
