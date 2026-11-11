"""The fake Atlas catalogue the app's rules door reads.

Its own module, not the conftest: the trace check collects ``tests/`` and
``e2e/`` in one run, and same-named ``conftest`` modules collide — helpers
import by a unique name (the 8.2 fake upstream sets the pattern).
"""

# ruff: noqa: INP001
from collections.abc import Callable
from typing import Any

import httpx2 as httpx

SEARCH_PATH = "/api/atlas/v2/search/basic"
"""The basic-search endpoint the rules door walks (VEV-03)."""


class FakeCatalogue:
    """The Atlas server's rule search, recorded and answered.

    A test sets :attr:`handler` to answer requests; every request is appended
    to :attr:`requests` so a test can assert on the bearer the app minted, the
    search parameters, and the paging walk (VEV-03/04).
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

    def searches(self) -> list[httpx.Request]:
        """The recorded rule-search requests, in order."""
        return [request for request in self.requests if request.url.path == SEARCH_PATH]

    @staticmethod
    def json(status_code: int, payload: Any) -> httpx.Response:  # noqa: ANN401 - any JSON value
        """A JSON response for the handler to return."""
        return httpx.Response(status_code, json=payload)


def rule_entity(
    guid: str,
    name: str,
    attributes: dict[str, Any],
    *,
    type_name: str = "m4i_gov_data_quality",
) -> dict[str, Any]:
    """One search header for a stored governance rule, as the server answers it."""
    return {"typeName": type_name, "guid": guid, "status": "ACTIVE", "displayText": name, "attributes": attributes}


def search_result(entities: list[dict[str, Any]], next_marker: str | None = None) -> dict[str, Any]:
    """One page of the rule search (SRC-09): the headers and the next marker."""
    return {"entities": entities, "numberOfMatches": len(entities), "nextMarker": next_marker}
