"""The fake Atlas catalogue and verdicts API the tools relay to.

Its own module, not the conftest: the trace check collects ``tests/`` and
``e2e/`` in one run, and same-named ``conftest`` modules collide — helpers
import by a unique name (validate-entity's fake_catalogue sets the pattern).
"""

# ruff: noqa: INP001
from typing import Any

import httpx2 as httpx
from fastmcp.exceptions import ToolError
from mcp import ClientSession


class FakeUpstream:
    """The Atlas server and the verdicts API: recorded, and answered per path.

    A test sets :attr:`answers` — path suffix to (status, payload) — or replaces
    :meth:`handle` outright; everything not answered is a 404 with an Atlas-shaped body,
    which the relay surfaces (MCP-14).
    """

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.answers: dict[str, tuple[int, Any]] = {}
        self.fail: Exception | None = None
        """When set, the transport raises it instead of answering: the unreachable-upstream probe."""

    def transport(self) -> httpx.MockTransport:
        """A transport that records every request and answers through :meth:`handle`."""

        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            if self.fail is not None:
                raise self.fail
            return self.handle(request)

        return httpx.MockTransport(handler)

    def handle(self, request: httpx.Request) -> httpx.Response:
        """Answer the first registered suffix match; an Atlas-shaped 404 otherwise."""
        path = request.url.path.rstrip("/")
        for suffix, (status, payload) in self.answers.items():
            if path.endswith(suffix):
                if payload is None:
                    return httpx.Response(status)
                return httpx.Response(status, json=payload)
        return httpx.Response(404, json={"errorCode": "ATLAS404", "errorMessage": f"the fake upstream has no {path}"})

    def bearer_of(self, request: httpx.Request) -> str | None:
        """The bearer credential a recorded request carried."""
        header = request.headers.get("authorization", "")
        return header.removeprefix("Bearer ") or None

    def for_path(self, suffix: str) -> httpx.Request | None:
        """The first recorded request whose path ends with ``suffix``."""
        return next((r for r in self.requests if r.url.path.rstrip("/").endswith(suffix)), None)


async def call_tool(session: ClientSession, name: str, arguments: dict[str, Any] | None = None) -> Any:  # noqa: ANN401 - the tool's structured answer
    """Call a tool and answer its structured content, raising what MCP-14 promises as a failure.

    :raises ToolError: when the tool answered an error — so tests read the tool's
        answer, or the failure, exactly as an MCP client does.
    """
    result = await session.call_tool(name, arguments or {})
    if result.is_error:
        texts = [text for content in result.content if isinstance(text := getattr(content, "text", None), str)]
        raise ToolError(texts[0] if texts else str(result))
    if result.structured_content is None:
        msg = f"the tool {name} answered no structured content"
        raise AssertionError(msg)
    return result.structured_content
