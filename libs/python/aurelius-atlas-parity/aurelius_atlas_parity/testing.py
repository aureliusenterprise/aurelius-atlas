"""A sample ASGI application for this library's own tests.

Note:
    Test infrastructure: like every ``testing`` module, it is outside the traceability check (DD-010).
"""

import json
import uuid
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

import httpx2 as httpx

type Scope = MutableMapping[str, Any]
type Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
type Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]


class SampleApp:
    """A small ASGI application with Atlas-like answers, so the harness has something to talk to.

    - ``GET /api/version``: a fixed JSON object
    - ``POST /api/entities``: stores ``{"name": ...}`` under a new GUID and returns it with a create time
    - ``GET /api/entities/<guid>``: the stored entity, or a 404 with an Atlas-like error
    - ``DELETE /api/entities/<guid>``: 204 with no body
    - ``GET /api/echo``: the query parameters and the ``x-test`` header as JSON
    - ``GET /api/ping``: ``pong`` as text
    """

    def __init__(self) -> None:
        self.entities: dict[str, dict[str, Any]] = {}
        self.requests = 0

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Answer one HTTP request."""
        self.requests += 1
        body = b""
        while True:
            message = await receive()
            body += message.get("body", b"")
            if not message.get("more_body"):
                break
        status, content_type, payload = self._answer(scope, body)
        headers = [(b"content-type", content_type.encode())] if payload else []
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": payload})

    def _answer(self, scope: Scope, body: bytes) -> tuple[int, str, bytes]:  # noqa: PLR0911 - one return per route
        method, path = scope["method"], scope["path"]
        if (method, path) == ("GET", "/api/version"):
            return self._json(200, {"Version": "2.4.0", "Name": "apache-atlas", "Description": "Metadata"})
        if (method, path) == ("GET", "/api/ping"):
            return 200, "text/plain", b"pong"
        if (method, path) == ("GET", "/api/echo"):
            headers = dict(scope["headers"])
            query = httpx.QueryParams(scope["query_string"].decode())
            return self._json(200, {"params": dict(query.multi_items()), "test": headers[b"x-test"].decode()})
        if (method, path) == ("POST", "/api/entities"):
            guid = str(uuid.uuid4())
            self.entities[guid] = {"guid": guid, "name": json.loads(body)["name"], "createTime": 1700000000000}
            return self._json(200, self.entities[guid])
        if path.startswith("/api/entities/"):
            guid = path.removeprefix("/api/entities/")
            if guid not in self.entities:
                return self._json(404, {"errorCode": "ATLAS-404-00-005", "errorMessage": f"{guid} not found"})
            if method == "DELETE":
                del self.entities[guid]
                return 204, "", b""
            return self._json(200, self.entities[guid])
        return 404, "text/plain", b"no route"

    @staticmethod
    def _json(status: int, document: object) -> tuple[int, str, bytes]:
        return status, "application/json", json.dumps(document).encode()
