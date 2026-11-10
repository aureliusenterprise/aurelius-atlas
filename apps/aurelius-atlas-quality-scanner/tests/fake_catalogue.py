"""The fake catalogue the scanner's tests speak to: rules, bindings and the one write, no sockets.

Its own module, not the conftest: the trace check collects ``tests/`` and ``e2e/`` in one run and
same-named ``conftest`` modules collide on ``sys.path`` (the 8.2 fake upstream and the client's
recorder set the pattern). It answers the three calls the scan makes — the basic search of the
rules, the bulk read of the fields' bindings, and the bulk write of the scores — with the wire
shapes the server writes, so a test exercises the real client and the real read/write models.
"""

# ruff: noqa: INP001
import base64
import json
from typing import Any

import httpx2 as httpx

SEARCH_BASIC = "/api/atlas/v2/search/basic"
ENTITY_BULK = "/api/atlas/v2/entity/bulk"


def marker_for(offset: int) -> str:
    """The page marker of ``offset``: the fake's own encoding, opaque to the scan."""
    return base64.b64encode(f"m:{offset}".encode()).decode()


def decode_marker(marker: str | None) -> int:
    """The offset a marker names; no marker, ``*``, or ``-1`` is the start."""
    if not marker or marker in {"*", "-1"}:
        return 0
    return int(base64.b64decode(marker.encode()).decode().split(":", 1)[1])


def rule_header(guid: str, attributes: dict[str, Any]) -> dict[str, Any]:
    """One ``m4i_data_quality`` header as the basic search answers it, attributes under the wire map."""
    return {"typeName": "m4i_data_quality", "guid": guid, "status": "ACTIVE", "attributes": attributes}


def entity_with_fields(guid: str, field_refs: list[dict[str, Any]]) -> dict[str, Any]:
    """One rule entity as the bulk read answers it, its ``fields`` end under relationshipAttributes."""
    return {
        "typeName": "m4i_data_quality",
        "guid": guid,
        "status": "ACTIVE",
        "relationshipAttributes": {"fields": field_refs},
    }


def field_with_datasets(guid: str, dataset_refs: list[dict[str, Any]]) -> dict[str, Any]:
    """One field entity as the bulk read answers it, its ``datasets`` end under relationshipAttributes."""
    return {
        "typeName": "m4i_field",
        "guid": guid,
        "status": "ACTIVE",
        "relationshipAttributes": {"datasets": dataset_refs},
    }


def related(guid: str, qualified_name: str) -> dict[str, Any]:
    """A related-object id the relationship ends carry: a guid and a qualifiedName."""
    return {"guid": guid, "typeName": "m4i_dataset", "status": "ACTIVE", "qualifiedName": qualified_name}


class FakeCatalogue:
    """The rules, their bindings and the scores back, recorded and answered over the wire.

    A test loads the pages of rule headers (:attr:`rule_pages`), the rule entities the bulk read
    answers (:attr:`rules`), and the field entities (:attr:`fields`), keyed by guid. The bulk write
    is recorded per entity on :attr:`written`, in order, and answered with the empty mutation the
    route returns.
    """

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        """Every request the scan sent, in order."""
        self.written: list[dict[str, Any]] = []
        """Every entity the scan wrote, in order (DQS-06)."""
        self.write_requests = 0
        """The bulk writes the scan made: the run answers with one (DQS-06)."""
        self.search_calls = 0
        """The basic searches the scan made, across the pages (DQS-02)."""
        self.rules: dict[str, dict[str, Any]] = {}
        """The rule entities the bulk read answers, by guid."""
        self.fields: dict[str, dict[str, Any]] = {}
        """The field entities the bulk read answers, by guid."""
        self._rules_pages: list[list[dict[str, Any]]] = []
        """The rule headers, one list per search page."""

    def add_rule_page(self, headers: list[dict[str, Any]]) -> None:
        """Load the next page of rule headers."""
        self._rules_pages.append(headers)

    def transport(self) -> httpx.MockTransport:
        """A transport that records requests and answers the scan's three calls."""

        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return self._handle(request)

        return httpx.MockTransport(handler)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == SEARCH_BASIC and request.method == "POST":
            return self._search(request)
        if path == ENTITY_BULK and request.method == "GET":
            return self._read_bulk(request)
        if path == ENTITY_BULK and request.method == "POST":
            return self._write_bulk(request)
        return httpx.Response(404, json={"errorCode": "ATLAS-404-00-001", "errorMessage": f"no route {path}"})

    def _search(self, request: httpx.Request) -> httpx.Response:
        self.search_calls += 1
        body = json.loads(request.content)
        offset = decode_marker(body.get("marker"))
        limit = int(body.get("limit") or 100)
        flat = [header for part in self._rules_pages for header in part]
        page = flat[offset : offset + limit]
        next_offset = offset + len(page)
        # SRC-08 parity: the server answers a next marker only for a request that carries one.
        next_marker = (
            None if body.get("marker") is None else (marker_for(next_offset) if next_offset < len(flat) else "-1")
        )
        return httpx.Response(200, json={"entities": page, "approximateCount": -1, "nextMarker": next_marker})

    def _read_bulk(self, request: httpx.Request) -> httpx.Response:
        guids = request.url.params.get_list("guid")
        entities = [self.rules.get(guid) or self.fields.get(guid) for guid in guids]
        found = [entity for entity in entities if entity is not None]
        if len(found) != len(guids):
            return httpx.Response(404, json={"errorCode": "ATLAS-400-00-001", "errorMessage": "entity not found"})
        return httpx.Response(200, json={"entities": found})

    def _write_bulk(self, request: httpx.Request) -> httpx.Response:
        self.write_requests += 1
        body = json.loads(request.content)
        self.written.extend(body.get("entities", []))
        return httpx.Response(200, json={})

    def written_by_key(self) -> dict[str, dict[str, Any]]:
        """The written entities by their ``scoreKey``, for a test's assertions (DQS-06)."""
        return {entity["attributes"]["scoreKey"]: entity for entity in self.written}
