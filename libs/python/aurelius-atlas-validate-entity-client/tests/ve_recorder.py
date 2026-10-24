"""The recording transport the client tests share: answer, record, no sockets (CL-02).

Its own module, not the conftest: the trace check collects ``tests/`` and
``e2e/`` in one run, and same-named ``conftest`` modules collide — helpers
import by a unique name (the 8.2 fake upstream sets the pattern).
"""

# ruff: noqa: INP001
from collections.abc import Callable
from typing import Any

import httpx2 as httpx


class Recorder:
    """A ``MockTransport`` that records every request and answers from a queue, a handler, or 500.

    Answers queue in order (:meth:`answer`); a handler (:attr:`handler`) answers
    what is left over. A request with neither is a test bug, answered 500 loudly.
    """

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        """Every request the client sent, in order."""
        self.handler: Callable[[httpx.Request], httpx.Response] | None = None
        """The fallback handler for requests the queue is done with."""
        self._answers: list[httpx.Response] = []

    def transport(self) -> httpx.MockTransport:
        """The transport to inject into a client (CL-02)."""
        return httpx.MockTransport(self._handle)

    def answer(self, status: int, payload: Any = None, text: str | None = None) -> None:  # noqa: ANN401 - the JSON body of the answer
        """Queue one answer: JSON ``payload``, plain ``text``, or the bare status (204)."""
        if text is not None:
            self._answers.append(httpx.Response(status, text=text))
        elif payload is None:
            self._answers.append(httpx.Response(status))
        else:
            self._answers.append(httpx.Response(status, json=payload))

    def _handle(self, request: httpx.Request) -> httpx.Response:
        """Record the request, pop the queued answer, fall back to the handler."""
        self.requests.append(request)
        if self._answers:
            return self._answers.pop(0)
        if self.handler is not None:
            return self.handler(request)
        return httpx.Response(500, text=f"no answer queued for {request.method} {request.url}")

    def sent(self, index: int = 0) -> httpx.Request:
        """The request at ``index`` — usually the only one."""
        return self.requests[index]
