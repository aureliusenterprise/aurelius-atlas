"""Unit tests for the telemetry factories: the ingest leg, the logfire wiring (DD-107, DD-108, AUX-03)."""

from typing import Any

import pytest
from aurelius_atlas_validate_entity.globals import LOGGER, NAME
from aurelius_atlas_validate_entity.providers.telemetry import configure_telemetry, ingest_pipeline
from aurelius_atlas_validate_entity.settings import ValidateEntitySettings
from fastapi import FastAPI
from pydantic import HttpUrl, SecretStr


def _otel_settings(**overrides: Any) -> ValidateEntitySettings:  # noqa: ANN401  # the settings fields under test
    """The conftest's settings plus the ingest credential, as the dev deployment sets them."""
    values: dict[str, Any] = {
        "otel_token_url": HttpUrl("http://issuer.test/realms/master/protocol/openid-connect/token"),
        "otel_client_secret": SecretStr("s3cr3t"),
    }
    values.update(overrides)
    return ValidateEntitySettings(auth_server_url=HttpUrl("http://issuer.test"), **values)


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.telemetry.ingest_pipeline", rules=["AUX-03"])
def test__no_ingest_credential_means_console_only(settings: ValidateEntitySettings) -> None:
    """Without the ingest secret there is no OTLP leg: the app exports to the console (AUX-03)."""
    assert ingest_pipeline(settings) is None


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.telemetry.ingest_pipeline", rules=["AUX-03"])
def test__one_half_of_the_credential_is_no_credential() -> None:
    """A token URL without the secret builds no leg — the pair is the setting (DD-107)."""
    assert ingest_pipeline(_otel_settings(otel_client_secret=None)) is None


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.telemetry.ingest_pipeline", rules=["AUX-01"])
def test__the_credential_builds_the_export_leg() -> None:
    """With the pair set, the pipeline is the (span processor, metric reader) pair for logfire (DD-107)."""
    pipeline = ingest_pipeline(_otel_settings())

    assert pipeline is not None
    span_processor, metric_reader = pipeline
    assert type(span_processor).__name__ == "BatchSpanProcessor"
    assert type(metric_reader).__name__ == "PeriodicExportingMetricReader"
    span_processor.shutdown()
    metric_reader.shutdown()


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.telemetry.configure_telemetry", rules=["AUX-01"])
def test__the_leg_rides_the_logfire_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The configured leg travels to logfire as the extra processor and reader (DD-108)."""
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "aurelius_atlas_validate_entity.providers.telemetry.logfire.configure",
        lambda **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(
        "aurelius_atlas_validate_entity.providers.telemetry.logfire.instrument_fastapi", lambda _a: None
    )

    configure_telemetry(FastAPI(title=NAME, version="0"), _otel_settings())

    assert len(calls) == 1
    assert calls[0]["service_name"] == NAME
    assert "additional_span_processors" in calls[0]
    assert "metrics" in calls[0]


@pytest.mark.covers("aurelius_atlas_validate_entity.providers.telemetry.configure_telemetry", rules=["AUX-03"])
def test__console_only_configures_no_leg(monkeypatch: pytest.MonkeyPatch, settings: ValidateEntitySettings) -> None:
    """Without the leg, logfire is configured plainly — and the app's log level is applied (AUX-03)."""
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "aurelius_atlas_validate_entity.providers.telemetry.logfire.configure",
        lambda **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(
        "aurelius_atlas_validate_entity.providers.telemetry.logfire.instrument_fastapi", lambda _a: None
    )
    level = LOGGER.level
    try:
        configure_telemetry(FastAPI(title=NAME, version="0"), settings.model_copy(update={"log_level": "warning"}))

        assert "additional_span_processors" not in calls[0]
        assert LOGGER.level == 30  # logging.WARNING: the settings' level reaches the app's logger
    finally:
        LOGGER.setLevel(level)
