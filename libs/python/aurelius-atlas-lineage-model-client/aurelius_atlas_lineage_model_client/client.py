"""The async client for the lineage-model API (CL-01..CL-05, CL-30; DD-114, DD-115, DD-116).

The shared client conventions of increment 8.4: constructed from an externally
built ``httpx.AsyncClient`` and a token source, reading no environment variables
(CL-01). The request path is relative, appended to that client's base URL, so a
URL with a trailing slash — the ``str()`` of a pydantic ``HttpUrl`` — works as
given (CL-01); the builder closes the pool, the API client never touches its
lifecycle. Tests hand over one built on a
``MockTransport`` and no socket opens (CL-02); the bearer goes on every call
(CL-03); ``LineageModelClientError`` rises on a non-2xx answer with the
Atlas-shaped body when it parses (CL-04); an unreachable upstream propagates as
``httpx``'s own error (CL-05).

The 204 of LM-05/LM-06 — the empty answer, no model — is *not* an error: it maps to
``None``, the caller's success path (CL-04).
"""

from collections.abc import Callable
from uuid import UUID

import httpx2 as httpx
from aurelius_atlas_server_client.lineage import Direction

from aurelius_atlas_lineage_model_client.models import DEFAULT_DEPTH, LineageModelResponse

type TokenSource = str | Callable[[], str]
"""Where the bearer token comes from: a fixed token, or a callable that yields one (CL-03)."""

DEFAULT_TIMEOUT_SECONDS = 10.0
"""The suggested request timeout, seconds — for the httpx client an app builds (the browser's bound)."""

NO_CONTENT = 204
"""The empty answer of a guid with no lineage: the caller's success, not an error (CL-04, LM-05/LM-06)."""

CLIENT_ERROR = 400
"""The status where an answer becomes an error: the client-error boundary (CL-04)."""


class LineageModelClientError(RuntimeError):
    """A non-2xx answer from the lineage-model API, with the status and the error body (CL-04)."""

    def __init__(self, status_code: int, error_code: str | None, error_message: str | None) -> None:
        self.status_code = status_code
        """The HTTP status the API answered with."""
        self.error_code = error_code
        """The ``errorCode`` of the Atlas-shaped body, when it parsed (DV-55/DV-56/DV-22)."""
        self.error_message = error_message
        """The ``errorMessage`` of the Atlas-shaped body, when it parsed."""
        detail = f"{error_code}: {error_message}" if error_code else f"HTTP {status_code}"
        super().__init__(f"the lineage-model API answered {status_code}: {detail}")


def _bearer(token: TokenSource) -> dict[str, str]:
    """The authorization header for the token source's current token (CL-03).

    An empty token is the unauthenticated call: no header at all — an empty
    bearer is not a legal header value, and a token source the caller leaves
    empty (a route that needs no auth, a service whose leg carries no token)
    must reach the wire unauthenticated, not malformed.
    """
    value = token() if callable(token) else token
    return {} if not value else {"authorization": f"Bearer {value}"}


class LineageModelClient:
    """The client for one lineage-model service (CL-30, DD-114, DD-116).

    Args:
        http: The ``httpx.AsyncClient`` to speak through, built by the caller —
            its builder owns its lifecycle, this client only speaks through it.
            Its base URL carries the service root; the route path is relative to it.
        token: The bearer token source (CL-03).
    """

    def __init__(self, http: httpx.AsyncClient, token: TokenSource) -> None:
        self._http = http
        self._token = token

    def with_token(self, token: TokenSource) -> LineageModelClient:
        """The same client speaking with ``token`` — sharing the connection pool (CL-03)."""
        return LineageModelClient(self._http, token)

    async def get(
        self, guid: UUID, depth: int = DEFAULT_DEPTH, direction: Direction = "BOTH"
    ) -> LineageModelResponse | None:
        """``GET /?guid=&depth=&direction=``: the flattened lineage's model (LM-01, CL-30).

        :returns: the model document, or ``None`` for the empty answer of LM-05/LM-06 (204).

        Raises:
            LineageModelClientError: The API answered 4xx/5xx (400 is DV-55/DV-56,
                502 is DV-22 — both with the Atlas-shaped body).
        """
        response = await self._http.get(
            "",
            params={"guid": str(guid), "depth": depth, "direction": direction},
            headers=_bearer(self._token),
        )
        if response.status_code == NO_CONTENT:
            return None
        if response.status_code >= CLIENT_ERROR:
            raise LineageModelClientError(response.status_code, *_error_fields(response))
        return LineageModelResponse.model_validate_json(response.content)


def _error_fields(response: httpx.Response) -> tuple[str | None, str | None]:
    """The ``errorCode``/``errorMessage`` of the answer, when it is the Atlas body (CL-04)."""
    try:
        body = response.json()
    except ValueError:
        return None, None
    if not isinstance(body, dict):
        return None, None
    return body.get("errorCode"), body.get("errorMessage")
