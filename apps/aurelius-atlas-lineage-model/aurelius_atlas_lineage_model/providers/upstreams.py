"""The upstream factories: the httpx pools, the circuit breakers, the clients (DD-205, DD-206).

The pools are built here and owned by the app's lifespan (DD-205): an injected
client keeps its own pool and appears in no list. The breakers are the app's
resilience policy, not the client libraries' (DD-205 keeps the libs
transport-only), with pybreaker's documented shapes: the callable ``exclude``
predicate and a logging listener.
"""

import ssl

import httpx2 as httpx
from aurelius_atlas_data2model_client.client import Data2ModelClient
from aurelius_atlas_server_client.client import AtlasClient
from pybreaker import CircuitBreaker, CircuitBreakerListener, CircuitBreakerState
from pydantic import HttpUrl

from aurelius_atlas_lineage_model.globals import BAD_REQUEST, LOGGER, SERVER_ERROR, UPSTREAM_TIMEOUT_SECONDS
from aurelius_atlas_lineage_model.settings import LineageModelSettings


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
    """Whether the error is an upstream 4xx — a fact about the request, not an outage (LM-13).

    The client libraries raise their ``*ClientError`` carrying the answer's status
    (CL-04); a transport failure (``httpx.RequestError``, CL-05) carries none and is
    an outage. The predicate is pybreaker's exclude form, as the auth library uses it
    for the issuer (AUX-02): the 404 of LM-05 (answered 204) and the 400 of LM-07
    answer the caller and reset the failure counter, never opening the circuit.
    """
    status: int = getattr(error, "status_code", SERVER_ERROR)
    return BAD_REQUEST <= status < SERVER_ERROR


def upstream_http(settings: LineageModelSettings, base_url: HttpUrl) -> httpx.AsyncClient:
    """The httpx pool for one upstream, for the standalone container (DD-203, DD-205).

    The issuer's CA is the TLS material, ``UPSTREAM_TIMEOUT_SECONDS`` the call bound
    (DD-200); the bearer token is a placeholder the route rebinds per request, and the
    client normalises the base URL, so it passes through as the settings state it.
    """
    ca_file = settings.auth_ca_file
    verify: ssl.SSLContext = (
        ssl.create_default_context(cafile=str(ca_file)) if ca_file else ssl.create_default_context()
    )
    return httpx.AsyncClient(base_url=str(base_url), verify=verify, timeout=UPSTREAM_TIMEOUT_SECONDS)


def atlas_breaker(settings: LineageModelSettings) -> CircuitBreaker:
    """The Atlas feed's circuit breaker (LM-11, LM-15): outages open it, facts exclude (LM-13)."""
    return _breaker(settings, "atlas")


def d2m_breaker(settings: LineageModelSettings) -> CircuitBreaker:
    """The data2model extract's circuit breaker (LM-11, LM-15): the same shape, counted apart."""
    return _breaker(settings, "data2model")


def _breaker(settings: LineageModelSettings, name: str) -> CircuitBreaker:
    """One upstream's breaker: pybreaker's documented callable ``exclude`` and listener (DD-206)."""
    return CircuitBreaker(
        name=f"lineage_model_{name}",
        fail_max=settings.breaker_fail_max,
        reset_timeout=settings.breaker_reset_timeout,
        exclude=[is_upstream_fact],
        listeners=[_LoggingListener()],
    )


def build_upstreams(
    settings: LineageModelSettings,
    atlas: AtlasClient | None = None,
    d2m: Data2ModelClient | None = None,
) -> tuple[AtlasClient, Data2ModelClient, list[httpx.AsyncClient]]:
    """The upstream clients, and the pools the app itself built (DD-205).

    An injected client brings its own pool and appears in no list — its builder
    closes it, not the app. The token is a placeholder the route rebinds per
    request with the caller's own.
    """
    pools: list[httpx.AsyncClient] = []
    if atlas is None:
        atlas_http = upstream_http(settings, settings.atlas_base_url)
        pools.append(atlas_http)
        atlas = AtlasClient(atlas_http, "")
    if d2m is None:
        d2m_http = upstream_http(settings, settings.data2model_url)
        pools.append(d2m_http)
        d2m = Data2ModelClient(d2m_http, "")
    return atlas, d2m, pools
