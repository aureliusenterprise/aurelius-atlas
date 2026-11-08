"""What a session of the suite creates on the shared dev store, recorded as it goes and removed at its end (ECU-01..04).

The dev store is shared with ``nx serve`` and the other suites (DD-223): a session removes only what its own
requests created, never by a name pattern, so a parallel run's writes stay as they are.
"""

# ruff: noqa: INP001 - a helper module beside the e2e tests, imported by them
import warnings
from collections.abc import Sequence
from itertools import batched
from typing import Any

import httpx2 as httpx

API = "/api/atlas"
TYPEDEFS = f"{API}/v2/types/typedefs"
ENTITY_BULK = f"{API}/v2/entity/bulk"
PURGE = f"{API}/admin/purge"
BATCH = 100
"""The guids per delete and purge request."""

DEF_LISTS = ("enumDefs", "structDefs", "classificationDefs", "entityDefs", "relationshipDefs", "businessMetadataDefs")
"""The lists of an ``AtlasTypesDef``, by its JSON names."""

_CATEGORY_LISTS = {
    "ENUM": "enumDefs",
    "STRUCT": "structDefs",
    "CLASSIFICATION": "classificationDefs",
    "ENTITY": "entityDefs",
    "RELATIONSHIP": "relationshipDefs",
    "BUSINESS_METADATA": "businessMetadataDefs",
}

_IMPORTS = (f"{API}/admin/import", f"{API}/admin/importfile")
_GLOSSARY = f"{API}/v2/glossary"
_SAVED_SEARCH = f"{API}/v2/search/saved"


class Created:
    """The entities and types a session's requests created, in the order they were created (ECU-01)."""

    def __init__(self) -> None:
        self.entities: dict[str, None] = {}
        self.types: dict[str, None] = {}

    def entity(self, guid: str) -> None:
        """Record an entity the server created as a side effect, such as an export's ``AtlasServer``."""
        self.entities[guid] = None

    def record_response(self, method: str, path: str, status: int, body: Any) -> None:  # noqa: ANN401 - any JSON
        """Record what a successful write's answer says it created (ECU-01).

        Entities: ``mutatedEntities.CREATE``, an import's ``processedEntities``, a glossary's, term's or
        category's ``guid``, and a saved search's. Types: every definition a ``POST`` of typedefs answers.
        """
        if method not in {"POST", "PUT"} or not 200 <= status < 300 or not isinstance(body, dict | list):  # noqa: PLR2004 - the 2xx range
            return
        if isinstance(body, dict):
            self._mutated(method, path, body)
        if method == "POST" and (path.startswith(_GLOSSARY) or path == _SAVED_SEARCH):
            for item in body if isinstance(body, list) else [body]:
                self._guid(item)

    def _mutated(self, method: str, path: str, body: dict[str, Any]) -> None:
        for created in (body.get("mutatedEntities") or {}).get("CREATE") or []:
            self._guid(created)
        if path in _IMPORTS:
            for guid in body.get("processedEntities") or []:
                self.entities[str(guid)] = None
        if method == "POST" and path == TYPEDEFS:
            for name in DEF_LISTS:
                for typedef in body.get(name) or []:
                    self.types[str(typedef["name"])] = None

    async def record(self, response: httpx.Response) -> None:
        """An httpx response hook: read the answer and record what it created."""
        request = response.request
        if request.method not in {"POST", "PUT"} or not response.is_success:
            return
        await response.aread()
        try:
            body = response.json()
        except ValueError:
            return
        self.record_response(request.method, request.url.path, response.status_code, body)

    def _guid(self, item: Any) -> None:  # noqa: ANN401 - any JSON
        if isinstance(item, dict) and isinstance(item.get("guid"), str) and not item["guid"].startswith("-"):
            self.entities[item["guid"]] = None


def remove(client: httpx.Client, created: Created) -> list[str]:
    """Delete and purge the recorded entities, then delete the recorded types that are left (ECU-02, ECU-03).

    Returns:
        What could not be removed, one line each; empty when the store holds nothing the session created.
    """
    left = _remove_entities(client, list(created.entities))
    return left + _remove_types(client, list(created.types))


def _remove_entities(client: httpx.Client, guids: Sequence[str]) -> list[str]:
    left: list[str] = []
    for batch in batched(guids, BATCH, strict=False):
        if not client.delete(ENTITY_BULK, params={"guid": list(batch)}).is_success:
            for guid in batch:
                client.delete(ENTITY_BULK, params={"guid": [guid]})
        purged = client.put(PURGE, json=list(batch))
        if not purged.is_success:
            left.append(f"purge of {len(batch)} entities: {purged.status_code} {purged.text[:200]}")
    return left


def _remove_types(client: httpx.Client, names: Sequence[str]) -> list[str]:
    stored = [found.json() for name in names if (found := client.get(f"{TYPEDEFS[:-1]}/name/{name}")).is_success]
    if not stored:
        return []
    batch: dict[str, list[dict[str, Any]]] = {}
    for typedef in stored:
        batch.setdefault(_CATEGORY_LISTS[typedef["category"]], []).append(typedef)
    if client.request("DELETE", TYPEDEFS, json=batch).is_success:
        return []
    # One definition the batch cannot delete fails it whole: delete one by one, the later created first, as
    # long as each pass deletes one more.
    remaining = [str(typedef["name"]) for typedef in reversed(stored)]
    while remaining:
        failed = {}
        for name in remaining:
            answer = client.delete(f"{TYPEDEFS[:-1]}/name/{name}")
            if not answer.is_success and answer.status_code != 404:  # noqa: PLR2004 - gone already
                failed[name] = f"type {name}: {answer.status_code} {answer.text[:200]}"
        if len(failed) == len(remaining):
            return list(failed.values())
        remaining = list(failed)
    return []


def warn_left(left: Sequence[str]) -> None:
    """Report, without failing the session, what the clean-up left on the dev store (ECU-04)."""
    if left:
        warnings.warn("the e2e clean-up left on the dev store:\n" + "\n".join(left), stacklevel=2)
