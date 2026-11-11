"""The upstream factories: the catalogue pool, the app's own mint, the circuit breaker (VEV-04, VEV-06; DD-499, DD-500).

The pool is built here and owned by the app's lifespan (DD-205's pattern, 8.2):
an injected client keeps its own pool and appears in no list. The bearer the
client carries is the app's OWN service identity (VEV-04, DD-499): minted once
by the auth-less ``ClientCredentialsTokenSource`` of the OTel library — the
client-credentials flow with a refresh-ahead cache, the job identity of DD-458
read from a service's side — never the caller's token, which stops at the gate.

The breaker is the app's resilience policy, not the client library's: pybreaker's
documented shapes, the callable ``exclude`` predicate and a logging listener
(DD-500, the same policy lineage-model keeps for its feeds).
"""

import ssl
from collections.abc import Callable

import httpx2 as httpx
from aurelius_atlas_otel import ClientCredentialsTokenSource
from aurelius_atlas_server_client.client import AtlasClient
from pybreaker import CircuitBreaker, CircuitBreakerListener, CircuitBreakerState

from aurelius_atlas_validate_entity.errors import UpstreamError
from aurelius_atlas_validate_entity.globals import (
    BAD_GATEWAY,
    BAD_REQUEST,
    LOGGER,
    SERVER_ERROR,
    UPSTREAM_TIMEOUT_SECONDS,
)
from aurelius_atlas_validate_entity.settings import ValidateEntitySettings

MINT_REFUSAL = "the issuer refused the app's credentials: no rules read runs without an identity"
"""The bearer source's answer when the mint fails: VEV-06's 502, never an anonymous read."""

MINT_UNCONFIGURED = "the catalogue leg has no service identity: SERVER_CLIENT_SECRET is unset"
"""The answer of a cluster without the realm join (VEV-06): verdicts are never invented."""


class _LoggingListener(CircuitBreakerListener):
    """Log the circuit's state changes — an open circuit must be visible (the AUX-02 pattern)."""

    def state_change(
        self,
        cb: CircuitBreaker,
        old_state: CircuitBreakerState | None,
        new_state: CircuitBreakerState | None,
    ) -> None:
        """Log one transition: the circuit's name, its old state and its new one."""
        LOGGER.debug("Circuit breaker %s state changed from %s to %s", cb.name, old_state, new_state)


def is_upstream_fact(error: BaseException) -> bool:
    """Whether the error is a catalogue 4xx — a fact about the request, not an outage (VEV-06).

    The server client raises ``AtlasClientError`` carrying the answer's status; a
    transport failure (``httpx.RequestError``) carries none and is an outage. The
    predicate is pybreaker's exclude form (DD-500, LM-13's sibling): a rejected
    search answers the caller and resets the failure counter, never opening the
    circuit.
    """
    status: int = getattr(error, "status_code", SERVER_ERROR)
    return BAD_REQUEST <= status < SERVER_ERROR


def _tokens(source: ClientCredentialsTokenSource) -> Callable[[], str]:
    """The bearer source the catalogue client carries: the app's own token, or the refusal (VEV-04).

    ``ClientCredentialsTokenSource.bearer`` answers ``None`` when the mint fails
    and no cached token is usable (DD-196: no silent fallback). For an exporter
    that means an anonymous OTLP call; for a rules read it must mean a refused
    request — an anonymous catalogue call would be a 401 misread as the catalogue's
    outage (the scanner's ``_tokens`` wrapper, DD-458's shape).
    """

    def bearer() -> str:
        token = source.bearer()
        if token is None:
            raise UpstreamError(BAD_GATEWAY, MINT_REFUSAL)
        return token

    return bearer


def _refused() -> str:
    """The bearer source of a leg with no mint configured (VEV-06): every read is refused."""
    raise UpstreamError(BAD_GATEWAY, MINT_UNCONFIGURED)


def upstream_http(settings: ValidateEntitySettings) -> httpx.AsyncClient:
    """The httpx pool for the catalogue server (DD-205's shape, 8.2).

    The issuer's CA is the TLS material — the dev cluster's one CA verifies the
    server, the issuer and the mint alike — and ``UPSTREAM_TIMEOUT_SECONDS`` the
    call bound (DD-200).
    """
    ca_file = settings.auth_ca_file
    verify: ssl.SSLContext = (
        ssl.create_default_context(cafile=str(ca_file)) if ca_file else ssl.create_default_context()
    )
    return httpx.AsyncClient(base_url=str(settings.server_base_url), verify=verify, timeout=UPSTREAM_TIMEOUT_SECONDS)


def server_breaker(settings: ValidateEntitySettings) -> CircuitBreaker:
    """The rule read's circuit breaker (VEV-06): outages open it, facts exclude (DD-500).

    Two exclusions ride pybreaker's list: a catalogue 4xx is the leg's fact
    (:func:`is_upstream_fact`), and the app's own refused mint is a
    configuration fact — it must answer its stable 502, never count toward an
    open circuit whose message would hide the cause.
    """
    return CircuitBreaker(
        name="validate_entity_server",
        fail_max=settings.breaker_fail_max,
        reset_timeout=settings.breaker_reset_timeout,
        exclude=[is_upstream_fact, UpstreamError],
        listeners=[_LoggingListener()],
    )


def build_upstreams(
    settings: ValidateEntitySettings,
    atlas: AtlasClient | None = None,
) -> tuple[AtlasClient, list[httpx.AsyncClient]]:
    """The catalogue client, and the pools the app itself built (DD-499, DD-205's pattern).

    An injected client brings its own pool and appears in no list — its builder
    closes it, not the app (the tests' seam, 8.2's). Built from the settings, the
    client carries the app's own service identity (VEV-04): the mint of
    ``SERVER_CLIENT_ID`` with its secret. Without the secret the leg is unconfigured
    and its bearer source refuses every read (VEV-06) — the app still serves,
    ``POST /`` answers 502.
    """
    pools: list[httpx.AsyncClient] = []
    if atlas is None:
        atlas_http = upstream_http(settings)
        pools.append(atlas_http)
        if settings.server_client_secret is None:
            atlas = AtlasClient(atlas_http, _refused)
        else:
            source = ClientCredentialsTokenSource(
                token_url=str(settings.token_url),
                client_id=settings.server_client_id,
                client_secret=settings.server_client_secret.get_secret_value(),
                ca_file=str(settings.auth_ca_file) if settings.auth_ca_file else None,
            )
            atlas = AtlasClient(atlas_http, _tokens(source))
    return atlas, pools
