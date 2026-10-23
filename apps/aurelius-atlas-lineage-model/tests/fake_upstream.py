"""The fake Atlas lineage feed / data2model ``/extract`` the app's upstream client hits.

Its own module, not the conftest: the trace check collects ``tests/`` and
``e2e/`` in one run, and same-named ``conftest`` modules collide — helpers
import by a unique name (the auth library's tests set the pattern).
"""

# ruff: noqa: INP001
from collections.abc import Callable
from typing import Any

import httpx


class FakeUpstream:
    """The Atlas lineage feed and data2model ``/extract``, recorded and answered.

    A test sets :attr:`handler` to answer requests; every request is appended
    to :attr:`requests` so a test can assert on the forwarded token, the fetch
    path/params, and the extraction body (LM-04).
    """

    def __init__(self) -> None:
        self.handler: Callable[[httpx.Request], httpx.Response] = lambda _request: httpx.Response(500)
        self.requests: list[httpx.Request] = []

    def transport(self) -> httpx.MockTransport:
        """A transport that records requests and delegates to :attr:`handler`."""

        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return self.handler(request)

        return httpx.MockTransport(handler)

    def of(self, path: str) -> list[httpx.Request]:
        """The recorded requests whose URL path matches ``path``."""
        return [request for request in self.requests if request.url.path == path]

    @staticmethod
    def json(status_code: int, payload: Any) -> httpx.Response:  # noqa: ANN401  # any JSON value
        """A JSON response for the handler to return."""
        return httpx.Response(status_code, json=payload)
