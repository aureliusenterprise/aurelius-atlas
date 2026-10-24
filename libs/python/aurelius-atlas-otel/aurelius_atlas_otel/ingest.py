"""The OTLP ingest credential for the collector's per-service leg (7.18, DD-107, CIA-07).

The collector's per-service leg (4317 gRPC / 4319 HTTP) accepts only Keycloak
client-credentials JWTs minted for the service's realm client
``otel-<service>`` (audience ``otel-collector``, the ``otel-ingest``
scope). The OTel Python SDK reads ``OTEL_EXPORTER_OTLP_HEADERS`` statically,
and the dev realm's access token lives 60s — a bearer JWT in a static header
expires a minute in. So the app owns the OTLP export: a refresh-ahead token
source feeds a ``requests.Session`` that injects a fresh bearer header on
every OTLP request, handed to app-built exporters whose processor/reader
``setup_telemetry`` installs on the process's providers (DD-121).

Extracted from the Atlas server's ``otel_ingest`` module so every service on
the leg shares one credential (8.0, DD-108); the server keeps the settings
mapping, this library owns the mechanism.

No new dependency: the session rides the ``requests`` the OTLP exporter
already uses, and the mint is stdlib urllib. The dev realm's 60s token is
why the header is read per request, not once.
"""

from __future__ import annotations

import base64
import json
import ssl
import threading
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import requests
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace.export import BatchSpanProcessor

REFRESH_AHEAD_SECONDS = 20
"""Refresh when the token expires within this window (the dev realm's token
lives 60s, so a 20s margin keeps every export inside validity)."""

IngestPipeline = tuple[BatchSpanProcessor, PeriodicExportingMetricReader]
"""The (span processor, metric reader) pair ``build_otlp_pipeline`` returns,
for ``setup_telemetry``'s ``span_processors`` / ``metric_readers``."""


class ClientCredentialsTokenSource:
    """Mints and caches a client-credentials JWT, refreshed ahead of expiry.

    :param token_url: the issuer's ``.../protocol/openid-connect/token`` endpoint
    :param client_id: the ingest client (``otel-atlas-server``)
    :param client_secret: the client's secret
    :param ca_file: PEM CA verifying the token endpoint's TLS (None: system
        trust — the dev plaintext :8080 issuer)
    """

    def __init__(self, token_url: str, client_id: str, client_secret: str, ca_file: str | None = None) -> None:
        self._token_url = token_url
        self._auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        self._ssl = ssl.create_default_context(cafile=ca_file) if ca_file else None
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_at = 0.0

    def bearer(self) -> str | None:
        """A valid bearer token, minting/refreshing as needed.

        On mint failure with no usable token, ``None`` — the request then goes
        out header-less and the collector's 401 is the visible failure
        (DD-107: no silent fallback).
        """
        with self._lock:
            if self._token is not None and time.time() < self._expires_at - REFRESH_AHEAD_SECONDS:
                return self._token
            try:
                self._mint()
            except HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError:
                # Mint failed: serve the cached token while it is (still)
                # valid — the collector rejects it once expired, 401-visible.
                if self._token is not None and time.time() < self._expires_at:
                    return self._token
                return None
            return self._token

    def _mint(self) -> None:
        body = urlencode({"grant_type": "client_credentials"}).encode()
        request = Request(  # noqa: S310  # the settings-owned issuer URL (HttpUrl-validated, http/https only)
            self._token_url,
            data=body,
            method="POST",
            headers={"Authorization": f"Basic {self._auth}", "Content-Type": "application/x-www-form-urlencoded"},
        )
        with urlopen(request, timeout=5, context=self._ssl) as response:  # noqa: S310  # the settings-owned issuer URL (HttpUrl-validated)
            payload = json.load(response)
        self._token = payload["access_token"]
        self._expires_at = time.time() + float(payload.get("expires_in", 30))


class _IngestSession(requests.Session):
    """A ``requests`` session that stamps a fresh ingest bearer on every request.

    The OTLP exporters ride it; the token is read per export, so a 60s dev
    token never ships expired.
    """

    def __init__(self, source: ClientCredentialsTokenSource) -> None:
        super().__init__()
        self._source = source

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:  # type: ignore[override]  # noqa: ANN401  # forwards to Session.request kwargs
        token = self._source.bearer()
        if token is not None:
            headers = dict(kwargs.get("headers") or {})
            headers["Authorization"] = f"Bearer {token}"
            kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


def build_otlp_pipeline(
    endpoint: str,
    ca_file: str | None,
    token_source: ClientCredentialsTokenSource,
) -> IngestPipeline:
    """The app-owned OTLP export (DD-107): a trace processor + metric reader.

    The exporters inject the bearer header per export through the ingest
    session.

    :param endpoint: the collector's service-leg base (``https://host:4319``)
    :param ca_file: PEM CA verifying the collector's TLS
    :param token_source: the ingest credential source
    :returns: a span processor and a metric reader for ``setup_telemetry``
    """
    session = _IngestSession(token_source)
    span_exporter = OTLPSpanExporter(
        endpoint=f"{endpoint}/v1/traces",
        certificate_file=ca_file,
        session=session,
    )
    metric_exporter = OTLPMetricExporter(
        endpoint=f"{endpoint}/v1/metrics",
        certificate_file=ca_file,
        session=session,
    )
    return BatchSpanProcessor(span_exporter), PeriodicExportingMetricReader(metric_exporter)
