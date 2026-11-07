"""The suite's clean-up, against a recording fake of the server (ECU-01..04); no container is started."""

import json
import warnings
from typing import Any

import httpx2 as httpx
import pytest
from cleanup import ENTITY_BULK, PURGE, TYPEDEFS, Created, remove, warn_left

TYPEDEF = TYPEDEFS[:-1]


class FakeServer:
    """Answers the clean-up's requests from a dict of stored types; records every request."""

    def __init__(
        self, types: dict[str, str], *, batch_fails: bool = False, blocked: frozenset[str] = frozenset()
    ) -> None:
        self.types = dict(types)
        self.batch_fails = batch_fails
        self.blocked = blocked
        self.calls: list[tuple[str, str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:  # noqa: PLR0911 - one answer per case
        """Answer as the server would, and record the request."""
        body = json.loads(request.content) if request.content else None
        path = request.url.path
        self.calls.append((request.method, path, body or request.url.params.get_list("guid")))
        if path.startswith(f"{TYPEDEF}/name/"):
            name = path.rsplit("/", 1)[1]
            if name not in self.types:
                return httpx.Response(404)
            if request.method == "GET":
                return httpx.Response(200, json={"name": name, "category": self.types[name]})
            if name in self.blocked:
                return httpx.Response(409, json={"errorCode": "ATLAS-409-00-002"})
            del self.types[name]
            return httpx.Response(204)
        if path == TYPEDEFS:
            if self.batch_fails:
                return httpx.Response(409)
            for typedefs in (body or {}).values():
                for typedef in typedefs:
                    del self.types[typedef["name"]]
            return httpx.Response(204)
        return httpx.Response(200, json={})


def _client(server: FakeServer) -> httpx.Client:
    return httpx.Client(base_url="https://atlas", transport=httpx.MockTransport(server))


@pytest.mark.covers("cleanup.Created.record_response", "cleanup.Created.entity", rules=["ECU-01"])
def test__the_answers_of_writes_say_what_was_created() -> None:
    """CREATE guids, an import's entities, glossary and saved-search guids, and the POSTed types are recorded."""
    created = Created()
    created.record_response("POST", "/api/atlas/v2/entity", 200, {"mutatedEntities": {"CREATE": [{"guid": "e1"}]}})
    created.record_response("POST", "/api/atlas/v2/entity", 200, {"mutatedEntities": {"UPDATE": [{"guid": "u"}]}})
    created.record_response("POST", "/api/atlas/admin/importfile", 200, {"processedEntities": ["i1", "i2"]})
    created.record_response("POST", "/api/atlas/v2/glossary", 200, {"guid": "g1", "name": "glossary"})
    created.record_response("POST", "/api/atlas/v2/glossary/terms", 200, [{"guid": "t1"}, {"guid": "t2"}])
    created.record_response("POST", "/api/atlas/v2/search/saved", 200, {"guid": "s1"})
    created.record_response("POST", TYPEDEFS, 200, {"entityDefs": [{"name": "a"}], "relationshipDefs": [{"name": "r"}]})
    created.record_response("PUT", TYPEDEFS, 200, {"entityDefs": [{"name": "updated"}]})
    created.record_response("POST", "/api/atlas/v2/entity", 400, {"mutatedEntities": {"CREATE": [{"guid": "no"}]}})
    created.record_response("GET", "/api/atlas/v2/glossary", 200, [{"guid": "read"}])
    created.entity("server")

    assert list(created.entities) == ["e1", "i1", "i2", "g1", "t1", "t2", "s1", "server"]
    assert list(created.types) == ["a", "r"]


@pytest.mark.asyncio
@pytest.mark.covers("cleanup.Created.record", rules=["ECU-01"])
async def test__the_response_hook_reads_the_answer() -> None:
    """The hook reads a streamed answer before recording it, and skips a reading or an answer not JSON."""
    created = Created()
    answers = {"/api/atlas/v2/entity": {"mutatedEntities": {"CREATE": [{"guid": "e1"}]}}}

    def server(request: httpx.Request) -> httpx.Response:
        found = answers.get(request.url.path)
        return httpx.Response(200, json=found) if found else httpx.Response(200, text="not json")

    transport = httpx.MockTransport(server)
    async with httpx.AsyncClient(
        base_url="https://atlas", transport=transport, event_hooks={"response": [created.record]}
    ) as client:
        await client.post("/api/atlas/v2/entity", json={})
        await client.post("/api/atlas/admin/export", json={})
        await client.get("/api/atlas/v2/entity")

    assert list(created.entities) == ["e1"]


@pytest.mark.covers("cleanup.remove", rules=["ECU-02", "ECU-03"])
def test__entities_are_deleted_and_purged_then_the_types_left_deleted_at_once() -> None:
    """The guids deleted, then purged; the types still stored deleted in one request by category."""
    created = Created()
    for guid in ("e1", "e2"):
        created.entity(guid)
    created.types.update(dict.fromkeys(["gone", "table", "rel"]))
    server = FakeServer({"table": "ENTITY", "rel": "RELATIONSHIP", "other": "ENTITY"})

    with _client(server) as client:
        left = remove(client, created)

    writes = [call for call in server.calls if call[0] != "GET"]
    assert writes[:2] == [("DELETE", ENTITY_BULK, ["e1", "e2"]), ("PUT", PURGE, ["e1", "e2"])]
    assert writes[2:] == [
        (
            "DELETE",
            TYPEDEFS,
            {
                "entityDefs": [{"name": "table", "category": "ENTITY"}],
                "relationshipDefs": [{"name": "rel", "category": "RELATIONSHIP"}],
            },
        )
    ]
    assert (left, server.types) == ([], {"other": "ENTITY"})


@pytest.mark.covers("cleanup.remove", "cleanup.warn_left", rules=["ECU-03", "ECU-04"])
def test__a_refused_batch_falls_back_to_one_by_one_and_reports_what_stays() -> None:
    """The later created first, pass by pass; a type no pass deletes is reported, and warned of."""
    created = Created()
    created.types.update(dict.fromkeys(["base", "child", "stuck"]))
    server = FakeServer(
        {"base": "ENTITY", "child": "ENTITY", "stuck": "ENTITY"}, batch_fails=True, blocked=frozenset({"stuck"})
    )

    with _client(server) as client:
        left = remove(client, created)

    deletes = [call[1].rsplit("/", 1)[1] for call in server.calls if call[0] == "DELETE" and "/name/" in call[1]]
    assert deletes == ["stuck", "child", "base", "stuck"]
    assert server.types == {"stuck": "ENTITY"}
    assert left == ['type stuck: 409 {"errorCode":"ATLAS-409-00-002"}']
    with pytest.warns(UserWarning, match="type stuck: 409"):
        warn_left(left)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        warn_left([])
