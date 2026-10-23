"""The async client for the data2model API (CL-01..CL-05, CL-21; DD-114, DD-115, DD-116).

The shared client conventions of increment 8.4: constructed from an externally
built ``httpx.AsyncClient`` and a token source, reading no environment variables
(CL-01) — the app builds the httpx client from its own settings and passes it in.
The request path is relative, appended to that client's base URL, so a URL with a
trailing slash — the ``str()`` of a pydantic ``HttpUrl`` — works as given (CL-01);
the builder closes the pool, the API client never touches its lifecycle. Tests
hand over one built on a ``MockTransport`` and no socket opens (CL-02);
the bearer token goes on every call (CL-03); :class:`Data2ModelClientError` rises
on a non-2xx answer, with the Atlas-shaped body when it parses (CL-04); an
unreachable upstream propagates as ``httpx``'s own error (CL-05).

``extract`` posts an :class:`~aurelius_atlas_data2model_client.models.ExtractionRequest`
— the same model class the server validates — and returns an
:class:`~aurelius_atlas_data2model_client.models.ExtractionResponse`, so the 8.2
chain's payload and the 8.1 answer are one contract on both sides (CL-21).
"""

from collections.abc import Callable

import httpx

from aurelius_atlas_data2model_client.models import ExtractionRequest, ExtractionResponse

type TokenSource = str | Callable[[], str]
"""Where the bearer token comes from: a fixed token, or a callable that yields one (CL-03)."""

DEFAULT_TIMEOUT_SECONDS = 10.0
"""The suggested request timeout, seconds — for the httpx client an app builds (DD-111's bound)."""

EXTRACT_PATH = "extract"
"""The extraction endpoint of the data2model app (DTM-01), relative to the base URL (CL-01)."""

CLIENT_ERROR = 400
"""The status where an answer becomes an error: the client-error boundary (CL-04)."""


class Data2ModelClientError(RuntimeError):
    """A non-2xx answer from the data2model API, with the status and the error body (CL-04)."""

    def __init__(self, status_code: int, error_code: str | None, error_message: str | None) -> None:
        self.status_code = status_code
        """The HTTP status the API answered with."""
        self.error_code = error_code
        """The ``errorCode`` of the Atlas-shaped body, when it parsed (DTM-11)."""
        self.error_message = error_message
        """The ``errorMessage`` of the Atlas-shaped body, when it parsed."""
        detail = f"{error_code}: {error_message}" if error_code else f"HTTP {status_code}"
        super().__init__(f"the data2model API answered {status_code}: {detail}")


def _bearer(token: TokenSource) -> dict[str, str]:
    """The authorization header for the token source's current token (CL-03).

    An empty token is the unauthenticated call: no header at all — an empty
    bearer is not a legal header value, and a token source the caller leaves
    empty (a route that needs no auth, a service whose leg carries no token)
    must reach the wire unauthenticated, not malformed.
    """
    value = token() if callable(token) else token
    return {} if not value else {"authorization": f"Bearer {value}"}


class Data2ModelClient:
    """The client for one data2model service (CL-21, DD-114, DD-116).

    Args:
        http: The ``httpx.AsyncClient`` to speak through, built by the caller —
            its builder owns its lifecycle, this client only speaks through it.
            Its base URL carries the service root; the path above is relative to it.
        token: The bearer token source (CL-03) — 8.2 forwards the caller's own.
    """

    def __init__(self, http: httpx.AsyncClient, token: TokenSource) -> None:
        self._http = http
        self._token = token

    def with_token(self, token: TokenSource) -> Data2ModelClient:
        """The same client speaking with ``token`` — sharing the connection pool (CL-03, LM-04)."""
        return Data2ModelClient(self._http, token)

    async def extract(self, request: ExtractionRequest) -> ExtractionResponse:
        """``POST /extract``: the rows and rules in, the ar3 model and metadata out (DTM-01, CL-21).

        Raises:
            Data2ModelClientError: The API answered 4xx/5xx (a 400 is the DTM-11
                validation answer, with the Atlas-shaped body).
        """
        response = await self._http.post(
            EXTRACT_PATH, json=request.model_dump(mode="json", by_alias=True), headers=_bearer(self._token)
        )
        if response.status_code >= CLIENT_ERROR:
            raise Data2ModelClientError(response.status_code, *_error_fields(response))
        return ExtractionResponse.model_validate_json(response.content)


def _error_fields(response: httpx.Response) -> tuple[str | None, str | None]:
    """The ``errorCode``/``errorMessage`` of the answer, when it is the DTM-11 body (CL-04)."""
    try:
        body = response.json()
    except ValueError:
        return None, None
    if not isinstance(body, dict):
        return None, None
    return body.get("errorCode"), body.get("errorMessage")
