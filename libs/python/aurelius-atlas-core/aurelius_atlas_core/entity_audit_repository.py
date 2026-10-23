"""``EntityAuditRepository``: the audit events of entities, kept and listed (AUD-05, AUD-07, AUD-08, DD-082).

Atlas's ``EntityAuditRepository`` and its ``HBaseBasedAuditRepository``: events are written in batches and read
newest first by their HBase row key, the event key (DD-083); the sorted and paged listing sorts them in memory, as
``listEventsV2`` with a sort column does.
"""

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from aurelius_atlas_model import codec
from aurelius_atlas_model.audit import EntityAuditActionV2, EntityAuditEventV2
from elasticsearch import AsyncElasticsearch

from aurelius_atlas_core.entity_documents import INDEX_PREFIX

AUDIT_INDEX = f"{INDEX_PREFIX}-entity-audits"
"""The alias of the audit index (DD-082)."""

AUDIT_PAGE = 1000
"""How many events one search page holds."""

DEFAULT_LIMIT = 100
"""The events a sorted listing answers for a negative count (``listEventsV2``)."""

SORT_COLUMN_USER = "user"
SORT_COLUMN_ACTION = "action"
SORT_COLUMN_TIMESTAMP = "timestamp"

_KEYWORD = {"type": "keyword"}

AUDIT_MAPPING: dict[str, Any] = {
    "dynamic": False,
    "properties": {
        "auditId": _KEYWORD,
        "entityId": _KEYWORD,
        "timestamp": {"type": "long"},
        "user": _KEYWORD,
        "action": _KEYWORD,
        "eventKey": _KEYWORD,
    },
}
"""Events by entity, action and key; the details stored, not indexed (DD-082, DD-083)."""


@runtime_checkable
class EntityAuditRepository(Protocol):
    """Where audit events are kept: Elasticsearch in the server, memory in tests."""

    async def prepare(self) -> None:
        """Create what the events are kept in, unless it exists."""
        ...

    async def put_events(self, events: Sequence[EntityAuditEventV2]) -> None:
        """``putEventsV2``: keep the events, without their entity definitions (AUD-01)."""
        ...

    async def list_events(
        self, entity_id: str, action: EntityAuditActionV2 | None, start_key: str | None, count: int
    ) -> list[EntityAuditEventV2]:
        """``listEventsV2``: the entity's events, newest key first, from ``start_key`` on, that key included (AUD-08).

        Only those of ``action`` when given; at most ``count``, all for -1, none for any other negative count.
        """
        ...


class ElasticsearchEntityAuditRepository:
    """``EntityAuditRepository`` in an Elasticsearch index behind its alias (DD-082)."""

    def __init__(self, client: AsyncElasticsearch, prefix: str = INDEX_PREFIX) -> None:
        self._client = client
        self.alias = f"{prefix}-entity-audits"

    async def prepare(self) -> None:
        """Create the index behind its alias unless it exists."""
        if not await self._client.indices.exists_alias(name=self.alias):
            await self._client.indices.create(
                index=f"{self.alias}-000001", aliases={self.alias: {"is_write_index": True}}, mappings=AUDIT_MAPPING
            )

    async def put_events(self, events: Sequence[EntityAuditEventV2]) -> None:
        """Index each event as a new document, in one bulk request.

        Raises:
            RuntimeError: Elasticsearch did not keep an event.
        """
        if not events:
            return
        lines: list[bytes] = []
        for event in events:
            audit_id = str(uuid4())
            lines += [
                codec.dumps({"create": {"_index": self.alias, "_id": audit_id}}),
                codec.dumps(_document(event, audit_id)),
            ]
        body = b"\n".join(lines) + b"\n"  # NDJSON bytes: the transport sends them as they are
        response = await self._client.bulk(operations=body)  # pyright: ignore[reportArgumentType]
        if response.get("errors"):
            raise RuntimeError(PUT_FAILED.format(alias=self.alias))

    async def list_events(
        self, entity_id: str, action: EntityAuditActionV2 | None, start_key: str | None, count: int
    ) -> list[EntityAuditEventV2]:
        """Refresh the index, then page through the entity's events by event key, newest first (DD-083)."""
        if count == 0 or count < -1:
            return []
        await self._client.indices.refresh(index=self.alias)
        clauses: list[dict[str, Any]] = [{"term": {"entityId": entity_id}}]
        if action is not None:
            clauses.append({"term": {"action": action.value}})
        if start_key is not None:
            clauses.append({"range": {"eventKey": {"lte": start_key}}})
        found: list[EntityAuditEventV2] = []
        after: list[Any] | None = None
        while count == -1 or len(found) < count:
            size = AUDIT_PAGE if count == -1 else min(AUDIT_PAGE, count - len(found))
            response = await self._client.search(
                index=self.alias,
                size=size,
                query={"bool": {"filter": clauses}},
                sort=[{"eventKey": "desc"}, {"auditId": "desc"}],
                search_after=after,
            )
            hits = response["hits"]["hits"]
            found += [EntityAuditEventV2.model_validate(hit["_source"]) for hit in hits]
            if len(hits) < size:
                break
            after = hits[-1]["sort"]
        return found


PUT_FAILED = "The audit events could not all be written to {alias}"


def _document(event: EntityAuditEventV2, audit_id: str) -> dict[str, Any]:
    """The event as stored: its fields but the entity definition and type, and its document id (AUD-01)."""
    return {**event.to_json(), "entity": None, "type": None, "auditId": audit_id}


async def list_events_sorted(  # noqa: PLR0913 - listEventsV2's parameters
    repository: EntityAuditRepository,
    entity_id: str,
    action: EntityAuditActionV2 | None,
    sort_by: str | None,
    *,
    descending: bool,
    offset: int,
    limit: int,
) -> list[EntityAuditEventV2]:
    """``listEventsV2`` with a sort column: every event of the entity sorted, then ``limit`` from ``offset`` (AUD-07).

    A negative offset reads as 0, a negative limit as 100, a limit of 0 as all.
    """
    events = sort_events(await repository.list_events(entity_id, action, None, -1), sort_by, descending=descending)
    start = min(len(events), max(offset, 0))
    limit = DEFAULT_LIMIT if limit < 0 else limit
    end = len(events) if limit == 0 else min(len(events), start + limit)
    return events[start:end]


def sort_events(
    events: Sequence[EntityAuditEventV2], sort_by: str | None, *, descending: bool
) -> list[EntityAuditEventV2]:
    """``EntityAuditEventV2.sortEvents``: by user or action ignoring case, then timestamp, else by timestamp (AUD-07).

    Stable over the given order; descending reverses the whole comparison, ties keeping their order.
    """
    column = (sort_by or SORT_COLUMN_TIMESTAMP).lower()
    if column == SORT_COLUMN_USER:
        key: Any = lambda event: (_case_insensitive(event.user), event.timestamp)  # noqa: E731
    elif column == SORT_COLUMN_ACTION:
        key = lambda event: (_case_insensitive(event.action), event.timestamp)  # noqa: E731
    else:
        key = lambda event: event.timestamp  # noqa: E731
    return sorted(events, key=key, reverse=descending)


def _case_insensitive(value: str | None) -> str:
    """``String.CASE_INSENSITIVE_ORDER``'s key: each character upper-cased, then lower-cased."""
    return "".join(character.upper().lower() for character in value or "")
