"""The async client for the validate-entity API (CL-01..CL-05, CL-40; DD-203, DD-204, DD-205).

The shared client conventions of increment 8.4: constructed from an externally
built ``httpx.AsyncClient`` and a token source, reading no environment variables
(CL-01). The request path is relative, appended to that client's base URL, so a
URL with a trailing slash — the ``str()`` of a pydantic ``HttpUrl`` — works as
given (CL-01); the builder closes the pool, the API client never touches its
lifecycle. Tests pass one built on a
``MockTransport`` and no socket opens (CL-02); the bearer goes on every call
(CL-03); ``ValidateEntityClientError`` rises on a non-2xx answer (CL-04);
``httpx``'s own error propagates on an unreachable upstream (CL-05).

``validate`` posts any mapping — the endpoint never reads the body (VE-01, DD-201),
so the request is not a model — and parses the fixed governance document into a
:class:`~aurelius_atlas_validate_entity_client.models.ValidationResponse` (CL-40).
"""

from collections.abc import Callable, Mapping
from typing import Any

import httpx2 as httpx

from aurelius_atlas_validate_entity_client.models import ValidationResponse

type TokenSource = str | Callable[[], str]
"""Where the bearer token comes from: a fixed token, or a callable that yields one (CL-03)."""

DEFAULT_TIMEOUT_SECONDS = 10.0
"""The suggested request timeout, seconds — for the httpx client an app builds for this one (CL-01)."""

VALIDATE_PATH = ""
"""The validation endpoint of the 8.3 app (VE-01): the service root, relative to the base URL (CL-01)."""

CLIENT_ERROR = 400
"""The status where an answer becomes an error: the client-error boundary (CL-04)."""


class ValidateEntityClientError(RuntimeError):
    """A non-2xx answer from the validate-entity API, with the status (CL-04)."""

    def __init__(self, status_code: int, error_code: str | None, error_message: str | None) -> None:
        self.status_code = status_code
        """The HTTP status the API answered with."""
        self.error_code = error_code
        """The ``errorCode`` of the Atlas-shaped body, when it parsed (VE-03's 401)."""
        self.error_message = error_message
        """The ``errorMessage`` of the Atlas-shaped body, when it parsed."""
        detail = f"{error_code}: {error_message}" if error_code else f"HTTP {status_code}"
        super().__init__(f"the validate-entity API answered {status_code}: {detail}")


def _bearer(token: TokenSource) -> dict[str, str]:
    """The authorization header for the token source's current token (CL-03).

    An empty token is the unauthenticated call: no header at all — an empty
    bearer is not a legal header value, and a token source the caller leaves
    empty (a route that needs no auth, a service whose leg carries no token)
    must reach the wire unauthenticated, not malformed.
    """
    value = token() if callable(token) else token
    return {} if not value else {"authorization": f"Bearer {value}"}


class ValidateEntityClient:
    """The client for one validate-entity service (CL-40, DD-203, DD-205).

    Args:
        http: The ``httpx.AsyncClient`` to speak through, built by the caller —
            its builder owns its lifecycle, this client only speaks through it.
            Its base URL carries the service root; the path above is relative to it.
        token: The bearer token source (CL-03).
    """

    def __init__(self, http: httpx.AsyncClient, token: TokenSource) -> None:
        self._http = http
        self._token = token

    def with_token(self, token: TokenSource) -> ValidateEntityClient:
        """The same client speaking with ``token`` — sharing the connection pool (CL-03)."""
        return ValidateEntityClient(self._http, token)

    async def validate(self, entity: Mapping[str, Any]) -> ValidationResponse:
        """``POST /``: the entity in, the governance-quality document out (VE-01, CL-40).

        :param entity: the entity being edited; the mock never reads it (VE-01).

        Raises:
            ValidateEntityClientError: The API answered 4xx/5xx (a 401 is VE-03).
        """
        response = await self._http.post(VALIDATE_PATH, json=dict(entity), headers=_bearer(self._token))
        if response.status_code >= CLIENT_ERROR:
            raise ValidateEntityClientError(response.status_code, *_error_fields(response))
        return ValidationResponse.model_validate_json(response.content)


def _error_fields(response: httpx.Response) -> tuple[str | None, str | None]:
    """The ``errorCode``/``errorMessage`` of the answer, when it is the Atlas body (CL-04)."""
    try:
        body = response.json()
    except ValueError:
        return None, None
    if not isinstance(body, dict):
        return None, None
    return body.get("errorCode"), body.get("errorMessage")
