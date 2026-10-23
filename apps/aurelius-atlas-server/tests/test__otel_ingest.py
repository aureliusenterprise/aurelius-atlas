"""Unit tests for the OTLP ingest credential shim (7.18, DD-107, CIA-07)."""

from __future__ import annotations

import base64
import io
import json
import time
from typing import TYPE_CHECKING, Any, Self, cast
from urllib.error import URLError
from urllib.parse import parse_qs

import pytest
import requests
import requests.adapters
from _pytest.monkeypatch import MonkeyPatch
from aurelius_atlas_server.otel_ingest import (
    REFRESH_AHEAD_SECONDS,
    ClientCredentialsTokenSource,
    _IngestSession,
    build_otlp_pipeline,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace.export import BatchSpanProcessor

if TYPE_CHECKING:
    from urllib.request import Request

TOKEN_URL = "http://keycloak.localhost:8080/realms/master/protocol/openid-connect/token"  # noqa: S105  # a URL constant, not a secret (S105 fires on the _URL name)


def _source(**overrides: object) -> ClientCredentialsTokenSource:
    args: dict[str, object] = {"token_url": TOKEN_URL, "client_id": "otel-atlas-server", "client_secret": "s3cret"}
    args.update(overrides)
    return ClientCredentialsTokenSource(**args)  # type: ignore[arg-type]


class _FakeResponse:
    """Minimal context-managed urlopen response carrying a JSON payload."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:  # pragma: no cover  # json.load uses the iterated form
        return json.dumps(self._payload).encode()


def _install_mint(monkeypatch: MonkeyPatch, payload: dict) -> list[Request]:
    """Replace urlopen with a mint server; return the list capturing requests."""
    requests_made: list[Request] = []

    def fake_urlopen(request: Request, *_args: object, **_kwargs: object) -> _FakeResponse:
        requests_made.append(request)
        return _FakeResponse(payload)

    monkeypatch.setattr("aurelius_atlas_server.otel_ingest.urlopen", fake_urlopen)
    return requests_made


@pytest.mark.covers("aurelius_atlas_server.otel_ingest.ClientCredentialsTokenSource.bearer", rules=["CIA-07"])
def test__bearer_mints_client_secret_basic_and_caches(monkeypatch: MonkeyPatch) -> None:
    """The first call mints with the basic credential; later calls reuse the cache."""
    source = _source()
    minted = _install_mint(monkeypatch, {"access_token": "tok-1", "expires_in": 60})

    assert source.bearer() == "tok-1"
    assert source.bearer() == "tok-1"  # cached: exactly one mint
    assert len(minted) == 1

    (request,) = minted
    basic = request.get_header("Authorization")
    assert basic == "Basic " + base64.b64encode(b"otel-atlas-server:s3cret").decode()
    assert isinstance(request.data, bytes)  # the shim encodes a urlencoded body
    assert parse_qs(request.data.decode()) == {"grant_type": ["client_credentials"]}


@pytest.mark.covers("aurelius_atlas_server.otel_ingest.ClientCredentialsTokenSource.bearer", rules=["CIA-07"])
def test__bearer_refreshes_inside_the_refresh_ahead_window(monkeypatch: MonkeyPatch) -> None:
    """A token expiring within REFRESH_AHEAD_SECONDS is replaced, not served."""
    source = _source()
    mints: list[int] = []

    def minting_urlopen(_request: Request, *_args: object, **_kwargs: object) -> _FakeResponse:
        mints.append(len(mints) + 1)
        return _FakeResponse({"access_token": f"tok-{len(mints)}", "expires_in": 60})

    monkeypatch.setattr("aurelius_atlas_server.otel_ingest.urlopen", minting_urlopen)
    assert source.bearer() == "tok-1"

    # Simulate the clock reaching the refresh-ahead window.
    source._expires_at = time.time() + REFRESH_AHEAD_SECONDS - 1  # noqa: SLF001  # the cache seam under test

    assert source.bearer() == "tok-2"
    assert len(mints) == 2  # a second mint happened


@pytest.mark.covers("aurelius_atlas_server.otel_ingest.ClientCredentialsTokenSource.bearer", rules=["CIA-07"])
def test__bearer_failure_without_a_cache_is_none(monkeypatch: MonkeyPatch) -> None:
    """A failed mint with nothing cached yields None — the export goes header-less."""

    def failing_urlopen(_request: Request, *_args: object, **_kwargs: object) -> _FakeResponse:
        msg = "connection refused"
        raise URLError(msg)

    monkeypatch.setattr("aurelius_atlas_server.otel_ingest.urlopen", failing_urlopen)

    assert _source().bearer() is None


@pytest.mark.covers("aurelius_atlas_server.otel_ingest.ClientCredentialsTokenSource.bearer", rules=["CIA-07"])
def test__bearer_failure_serves_the_still_valid_cache(monkeypatch: MonkeyPatch) -> None:
    """After a good mint, a failed refresh keeps serving the cached token."""
    source = _source()
    _install_mint(monkeypatch, {"access_token": "tok-1", "expires_in": 60})
    assert source.bearer() == "tok-1"

    def failing_urlopen(_request: Request, *_args: object, **_kwargs: object) -> _FakeResponse:
        msg = "connection refused"
        raise URLError(msg)

    # Inside the refresh-ahead window (so a refresh is attempted) but before
    # real expiry (so the cache is still serveable).
    source._expires_at = time.time() + REFRESH_AHEAD_SECONDS - 1  # noqa: SLF001  # the cache seam under test
    monkeypatch.setattr("aurelius_atlas_server.otel_ingest.urlopen", failing_urlopen)

    assert source.bearer() == "tok-1"


@pytest.mark.covers("aurelius_atlas_server.otel_ingest._IngestSession.request", rules=["CIA-07"])
def test__ingest_session_stamps_a_fresh_bearer_per_request(monkeypatch: MonkeyPatch) -> None:
    """Every request carries the current bearer; a None token ships header-less."""
    _install_mint(monkeypatch, {"access_token": "tok-1", "expires_in": 60})
    source = _source()
    session = _IngestSession(source)

    sent: list[requests.PreparedRequest] = []

    class _Capture(requests.adapters.BaseAdapter):
        def send(self, request: requests.PreparedRequest, **_kwargs: Any) -> requests.Response:  # noqa: ANN401  # pyright: ignore[reportIncompatibleMethodOverride]  # the capture adapter ignores send's kwargs
            sent.append(request)
            response = requests.Response()
            response.status_code = 200
            response.url = request.url or ""
            response.request = request
            response.raw = io.BytesIO(b"")
            response.headers["Content-Type"] = "application/x-protobuf"
            return response

        def close(self) -> None:
            return None

    session.mount("http://", _Capture())
    session.mount("https://", _Capture())

    session.get("https://otel-collector:4319/v1/traces")
    assert sent[0].headers["Authorization"] == "Bearer tok-1"

    # Token expires; the mint endpoint is down → bearer() is None → the
    # export proceeds with no Authorization header (the collector's 401 path).
    source._token = None  # noqa: SLF001  # the cache seam under test
    source._expires_at = 0.0  # noqa: SLF001

    def down_urlopen(_request: Request, *_args: object, **_kwargs: object) -> _FakeResponse:
        msg = "down"
        raise URLError(msg)

    monkeypatch.setattr("aurelius_atlas_server.otel_ingest.urlopen", down_urlopen)
    session.get("https://otel-collector:4319/v1/traces")
    assert "Authorization" not in sent[1].headers


@pytest.mark.covers("aurelius_atlas_server.otel_ingest.build_otlp_pipeline", rules=["CIA-07"])
def test__build_otlp_pipeline_wires_the_ingest_session_into_both_exporters(monkeypatch: MonkeyPatch) -> None:
    """The pipeline's exporters ride one ingest session to the traces/metrics endpoints."""
    _install_mint(monkeypatch, {"access_token": "tok-1", "expires_in": 60})
    processor, reader = build_otlp_pipeline("https://otel-collector:4319", None, _source())

    assert isinstance(processor, BatchSpanProcessor)
    assert isinstance(reader, PeriodicExportingMetricReader)

    span_exporter = cast("OTLPSpanExporter", processor.span_exporter)
    metric_exporter = cast("OTLPMetricExporter", reader._exporter)  # noqa: SLF001  # the wiring seam under test
    assert span_exporter._endpoint == "https://otel-collector:4319/v1/traces"  # noqa: SLF001  # the wiring seam under test
    assert metric_exporter._endpoint == "https://otel-collector:4319/v1/metrics"  # noqa: SLF001
    assert isinstance(span_exporter._session, _IngestSession)  # noqa: SLF001
    assert metric_exporter._session is span_exporter._session  # noqa: SLF001  # one session, one token source
