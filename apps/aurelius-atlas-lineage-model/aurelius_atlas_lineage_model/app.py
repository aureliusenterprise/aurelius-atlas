"""The FastAPI application: settings, auth, telemetry, the ``/`` lineage route (LM-01, LM-08, DD-108)."""

import logging
from importlib.metadata import version
from typing import Annotated

import httpx
import logfire
from aurelius_atlas_auth import AuthConfig, KeycloakAuth
from aurelius_atlas_otel import ClientCredentialsTokenSource, IngestPipeline, build_otlp_pipeline
from fastapi import FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from aurelius_atlas_lineage_model.lineage import (
    LINEAGE_RULES,
    Direction,
    LineageInfo,
    UpstreamError,
    flatten_relations,
)
from aurelius_atlas_lineage_model.settings import LineageModelSettings

NAME = "aurelius-atlas-lineage-model"
LOGGER = logging.getLogger(NAME)

OK = 200
"""The status of a successful upstream call (LM-01, LM-04)."""

BAD_REQUEST = 400
"""The status of a query the app will not process (LM-07, DV-20, DV-21)."""

NOT_FOUND = 404
"""The upstream's answer for a guid it has no lineage for (LM-05)."""

BAD_GATEWAY = 502
"""The status of a failing upstream (LM-07, DV-22)."""

DEFAULT_DEPTH = 3
"""The lineage depth the legacy defaults to when the query omits it (LM-01)."""

UPSTREAM_TIMEOUT_SECONDS = 10.0
"""How long an upstream call may take before the app gives up on it."""

ATLAS_ERROR_CODE = "ATLAS-400-00-029"
"""Atlas's code for a request it will not process; the 8.x apps reuse it (DTM-11 family)."""


def create_app(
    settings: LineageModelSettings,
    auth: KeycloakAuth | None = None,
    http: httpx.Client | None = None,
) -> FastAPI:
    """Build the application.

    Args:
        settings: The app's settings.
        auth: The token verifier; by default one built from the settings. Injectable for
            tests, which point it at a fake issuer.
        http: The client for the upstream calls (LM-04); by default one built from the
            settings. Injectable for tests, which point it at a mock transport (DD-111).

    The app is a stateless proxy: no store, no cache (the legacy's dev ``@cached`` is
    not ported), no start-up work beyond the telemetry (DD-108).
    """
    verifier = auth if auth is not None else _auth(settings)
    client = http if http is not None else _http(settings)

    app = FastAPI(title=NAME, version=version(NAME), docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.auth = verifier
    app.state.http = client

    atlas_root = str(settings.atlas_base_url).rstrip("/")
    extract_url = f"{str(settings.data2model_url).rstrip('/')}/extract"

    @app.get("/liveness", status_code=204)
    def liveness() -> None:
        """The container healthcheck: 204 while the process serves (no auth)."""

    @app.get("/", dependencies=[verifier.require_auth])
    def lineage_model(
        guid: str,
        depth: Annotated[int, Query(ge=1)] = DEFAULT_DEPTH,
        direction: Direction = "BOTH",
        token: Annotated[str, verifier.require_bearer] = "",
    ) -> Response:
        """Flatten the entity's lineage and extract its model (LM-01).

        The token is verified for this app's audience (LM-08, DV-23) and the caller's
        raw token is forwarded to both upstreams (LM-04) — the legacy's design: the
        upstream services accept the browser's own token.
        """
        headers = {"authorization": f"Bearer {token}"}
        answer = client.get(
            f"{atlas_root}/v2/lineage/{guid}",
            params={"depth": depth, "direction": direction},
            headers=headers,
        )
        if answer.status_code == NOT_FOUND:
            LOGGER.info("No lineage for guid %s", guid)
            return Response(status_code=204)
        _check_lineage_answer(answer)

        info = LineageInfo.model_validate_json(answer.content)
        if not info.relations:
            LOGGER.info("Lineage for guid %s has no relations", guid)
            return Response(status_code=204)

        rows = flatten_relations(info)
        extracted = client.post(extract_url, json={"data": rows, "rules": LINEAGE_RULES}, headers=headers)
        if extracted.status_code != OK:
            raise UpstreamError(BAD_GATEWAY, "the model extraction failed")
        return Response(content=extracted.content, status_code=OK, media_type="application/json")

    @app.exception_handler(UpstreamError)
    def upstream_error(_request: Request, error: UpstreamError) -> JSONResponse:
        """The upstream's status, mapped: 400 stays 400, anything else is a 502 (LM-05, LM-07)."""
        LOGGER.warning("Upstream failure, answered %s: %s", error.status_code, error)
        return _atlas_error(error.status_code, str(error))

    @app.exception_handler(httpx.RequestError)
    def upstream_unreachable(_request: Request, error: httpx.RequestError) -> JSONResponse:
        """An upstream that cannot be reached is a gateway failure (LM-07, DV-22)."""
        LOGGER.warning("Upstream %s unreachable: %s", error.request.url, error)
        return _atlas_error(BAD_GATEWAY, "the lineage service is unreachable")

    @app.exception_handler(RequestValidationError)
    def validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
        """A query the app will not process is a 400 with an Atlas-shaped error body (LM-07, DV-20, DV-21).

        The legacy let ``int()``, ``Enum()`` and a literal-``None`` guid crash
        Flask — a 500; the port states 400.
        """
        first = error.errors()[0] if error.errors() else {}
        message = f"invalid lineage request: {first.get('msg', 'malformed query')}"
        LOGGER.info("Rejected lineage request: %s", message)
        return _atlas_error(BAD_REQUEST, message)

    # Telemetry (DD-107, DD-108): the app owns its OTLP export through the shared
    # pipeline — a client-credentials JWT as otel-lineage-model, refreshed per export;
    # unset settings mean console-only (AUX-03).
    ingest = _ingest_pipeline(settings)
    logfire.configure(
        send_to_logfire=False,
        service_name=NAME,
        service_version=app.version,
        min_level=settings.log_level,
        console=logfire.ConsoleOptions(min_log_level=settings.log_level),
        **(
            {
                "additional_span_processors": [ingest[0]],
                "metrics": logfire.MetricsOptions(additional_readers=[ingest[1]]),
            }
            if ingest is not None
            else {}
        ),
    )
    logfire.instrument_fastapi(app)
    LOGGER.setLevel(settings.log_level.upper())
    return app


def _check_lineage_answer(answer: httpx.Response) -> None:
    """Map a lineage-fetch answer that is not a success to its status (LM-05, LM-07)."""
    if answer.status_code == BAD_REQUEST:
        raise UpstreamError(BAD_REQUEST, "the lineage service rejected the request")
    if answer.status_code != OK:
        raise UpstreamError(BAD_GATEWAY, "the lineage service failed")


def _atlas_error(status_code: int, message: str) -> JSONResponse:
    """The Atlas-shaped error body on the given status (LM-07)."""
    return JSONResponse(status_code=status_code, content={"errorCode": ATLAS_ERROR_CODE, "errorMessage": message})


def _auth(settings: LineageModelSettings) -> KeycloakAuth:
    """The app's token verifier, mapped from the settings (LM-08)."""
    return KeycloakAuth(
        AuthConfig(
            server_url=str(settings.auth_server_url),
            realm=settings.auth_realm,
            audience=settings.auth_audience,
            ca_file=str(settings.auth_ca_file) if settings.auth_ca_file else None,
        )
    )


def _http(settings: LineageModelSettings) -> httpx.Client:
    """The client for the upstream calls: a bounded timeout, the issuer's CA for TLS (DD-111)."""
    ca_file = str(settings.auth_ca_file) if settings.auth_ca_file else True
    return httpx.Client(timeout=UPSTREAM_TIMEOUT_SECONDS, verify=ca_file)


def _ingest_pipeline(settings: LineageModelSettings) -> IngestPipeline | None:
    """The app-owned OTLP export for the per-service ingest leg (DD-107, DD-108).

    None when the ingest credential is not configured (console-only telemetry).
    """
    if settings.otel_token_url is None or settings.otel_client_secret is None:
        return None
    source = ClientCredentialsTokenSource(
        token_url=str(settings.otel_token_url),
        client_id=settings.otel_client_id,
        client_secret=settings.otel_client_secret.get_secret_value(),
        ca_file=str(settings.otel_ca_file) if settings.otel_ca_file else None,
    )
    ca_file = str(settings.otel_ca_file) if settings.otel_ca_file else None
    return build_otlp_pipeline(settings.otel_endpoint, ca_file, source)
