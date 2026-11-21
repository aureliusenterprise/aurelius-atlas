"""``EntityAuditRepository``: the audit events of entities, kept and listed (AUD-05, AUD-07, AUD-08, DD-082).

Atlas's ``EntityAuditRepository`` and its ``HBaseBasedAuditRepository``: events are written in batches and read
newest first by their HBase row key, the event key (DD-083); the sorted and paged listing asks the store for that
order, as ``listEventsV2`` with a sort column does (AUD-07, DD-710).
"""

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from aurelius_atlas_model import codec
from aurelius_atlas_model.audit import EntityAuditActionV2, EntityAuditEventV2
from aurelius_atlas_model.audit_reduction import AtlasAuditAgingType
from elasticsearch import AsyncElasticsearch

from aurelius_atlas_core import es_clauses
from aurelius_atlas_core.index_setup import INDEX_PREFIX, WRITE_REFRESH
from aurelius_atlas_core.typedef_document import INDEX_SETTINGS, ensure_index

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

SORT_KEY_FIELDS: dict[str, Any] = {"userKey": _KEYWORD, "actionKey": _KEYWORD}
"""The folded keywords a sorted listing sorts on: Elasticsearch cannot ignore case in a field sort (DD-710)."""

AUDIT_MAPPING: dict[str, Any] = {
    "dynamic": False,
    "properties": {
        "auditId": _KEYWORD,
        "entityId": _KEYWORD,
        "timestamp": {"type": "long"},
        "user": _KEYWORD,
        "action": _KEYWORD,
        "eventKey": _KEYWORD,
        **SORT_KEY_FIELDS,
    },
}
"""Events by entity, action and key; the details stored, not indexed (DD-082, DD-083, DD-710)."""


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

    async def list_sorted(  # noqa: PLR0913 - listEventsV2's parameters
        self,
        entity_id: str,
        action: EntityAuditActionV2 | None,
        sort_by: str | None,
        *,
        descending: bool,
        offset: int,
        limit: int,
    ) -> list[EntityAuditEventV2]:
        """``listEventsV2`` with a sort column: the entity's events in that order, ``limit`` from ``offset`` (AUD-07).

        Order of ``user`` or ``action`` ignoring case, then timestamp, else of timestamp; the whole order reversed
        when ``descending``. A negative offset reads as 0, a negative limit as 100, a limit of 0 as all.
        """
        ...

    async def delete_events(self, entity_id: str, event_keys: Sequence[str]) -> None:
        """Remove the entity's events of these keys (AGE-04)."""
        ...

    async def entities_with_tag_changes(self, from_timestamp: int, to_timestamp: int) -> list[str]:
        """``getEntitiesWithTagChanges``: entities with a classification event from the one time to before the other.

        Events of ``TAG_ACTIONS`` only, as HBase's prefix filter ``CLASSIFICATION_`` finds them (CAU-07).
        """
        ...


class ElasticsearchEntityAuditRepository:
    """``EntityAuditRepository`` in an Elasticsearch index behind its alias (DD-082)."""

    def __init__(self, client: AsyncElasticsearch, prefix: str = INDEX_PREFIX) -> None:
        self._client = client
        self.alias = f"{prefix}-entity-audits"

    async def prepare(self) -> None:
        """Create the index behind its alias unless it exists; an existing one gets a new one's settings (IDX-02).

        A create lost to a server booting on the same store takes the existing-index path too (DD-508).
        """
        if not await self._client.indices.exists_alias(name=self.alias):
            made = await ensure_index(
                self._client,
                index=f"{self.alias}-000001",
                aliases={self.alias: {"is_write_index": True}},
                mappings=AUDIT_MAPPING,
                settings=INDEX_SETTINGS,
            )
            if made:
                return
        await self._client.indices.put_settings(index=self.alias, settings=INDEX_SETTINGS)
        await self._fold_sort_keys()

    async def _fold_sort_keys(self) -> None:
        """Give the folded sort keys to every event stored before they existed (DD-710).

        An alias created here already holds them; an existing one predates them, so its mapping gains the two
        fields and its events are rewritten whole with the fold of their user and action. A server starting on a
        prepared store finds none and does nothing but the mapping, which Elasticsearch accepts as it is.
        """
        await self._client.indices.put_mapping(index=self.alias, properties=SORT_KEY_FIELDS)
        while True:
            response = await self._client.search(
                index=self.alias,
                size=AUDIT_PAGE,
                query=es_clauses.must_not([es_clauses.exists("userKey")]),
            )
            hits = response["hits"]["hits"]
            if not hits:
                return
            lines: list[bytes] = []
            for hit in hits:
                source = hit["_source"]
                folded = {
                    **source,
                    "userKey": _case_insensitive(source.get("user")),
                    "actionKey": _case_insensitive(source.get("action")),
                }
                lines += [
                    codec.dumps({"index": {"_index": self.alias, "_id": hit["_id"]}}),
                    codec.dumps(folded),
                ]
            # The rewrite refreshes, so the next search finds only the events left unfolded.
            await self._client.bulk(operations=b"\n".join(lines) + b"\n", refresh=WRITE_REFRESH)  # pyright: ignore[reportArgumentType]

    async def put_events(self, events: Sequence[EntityAuditEventV2]) -> None:
        """Index each event as a new document, in one bulk request.

        The append refreshes the index, so the listing that follows it is current (ENS-11, IDX-01).

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
        response = await self._client.bulk(operations=body, refresh=WRITE_REFRESH)  # pyright: ignore[reportArgumentType]
        if response.get("errors"):
            raise RuntimeError(PUT_FAILED.format(alias=self.alias))

    async def list_events(
        self, entity_id: str, action: EntityAuditActionV2 | None, start_key: str | None, count: int
    ) -> list[EntityAuditEventV2]:
        """Page through the entity's events by event key, newest first (DD-083).

        Appends refresh, so a listed event is current (ENS-11).
        """
        if count == 0 or count < -1:
            return []
        clauses: list[dict[str, Any]] = [es_clauses.term("entityId", entity_id)]
        if action is not None:
            clauses.append(es_clauses.term("action", action.value))
        if start_key is not None:
            clauses.append(es_clauses.range_("eventKey", {"lte": start_key}))
        found: list[EntityAuditEventV2] = []
        after: list[Any] | None = None
        while count == -1 or len(found) < count:
            size = AUDIT_PAGE if count == -1 else min(AUDIT_PAGE, count - len(found))
            response = await self._client.search(
                index=self.alias,
                size=size,
                query=es_clauses.filter_(clauses),
                sort=[{"eventKey": "desc"}, {"auditId": "desc"}],
                search_after=after,
            )
            hits = response["hits"]["hits"]
            found += [EntityAuditEventV2.model_validate(hit["_source"]) for hit in hits]
            if len(hits) < size:
                break
            after = hits[-1]["sort"]
        return found

    async def list_sorted(  # noqa: PLR0913 - listEventsV2's parameters
        self,
        entity_id: str,
        action: EntityAuditActionV2 | None,
        sort_by: str | None,
        *,
        descending: bool,
        offset: int,
        limit: int,
    ) -> list[EntityAuditEventV2]:
        """Ask the index for the asked order and answer ``limit`` of it from ``offset`` (AUD-07, DD-710).

        The sort keys hold the folded user and action, so the index sort is Java's case-insensitive one; the tail
        breaks ties by event key descending, the newest-key-first order Java keeps ties in, both directions. The
        window is paged with ``search_after`` and sliced here, as the route's ``offset`` needs no second sort.
        """
        offset = max(offset, 0)
        if limit < 0:
            limit = DEFAULT_LIMIT
        clauses: list[dict[str, Any]] = [es_clauses.term("entityId", entity_id)]
        if action is not None:
            clauses.append(es_clauses.term("action", action.value))
        keys = _sort_keys((sort_by or SORT_COLUMN_TIMESTAMP).lower(), descending=descending)
        found: list[EntityAuditEventV2] = []
        after: list[Any] | None = None
        while limit == 0 or len(found) < offset + limit:
            size = AUDIT_PAGE if limit == 0 else min(AUDIT_PAGE, offset + limit - len(found))
            response = await self._client.search(
                index=self.alias,
                size=size,
                query=es_clauses.filter_(clauses),
                sort=keys,
                search_after=after,
            )
            hits = response["hits"]["hits"]
            found += [EntityAuditEventV2.model_validate(hit["_source"]) for hit in hits]
            if len(hits) < size:
                break
            after = hits[-1]["sort"]
        return found[offset:]

    async def delete_events(self, entity_id: str, event_keys: Sequence[str]) -> None:
        """Delete the entity's events of these keys by query, refreshed so the next listing misses them (AGE-04)."""
        if not event_keys:
            return
        query = es_clauses.filter_(
            [es_clauses.term("entityId", entity_id), es_clauses.terms("eventKey", list(event_keys))]
        )
        await self._client.delete_by_query(index=self.alias, query=query, refresh=True, conflicts="proceed")

    async def entities_with_tag_changes(self, from_timestamp: int, to_timestamp: int) -> list[str]:
        """Page through the classification events of the time range (ENS-11: appends refresh)."""
        query = es_clauses.filter_(
            [
                es_clauses.terms("action", [action.value for action in TAG_ACTIONS]),
                es_clauses.range_("timestamp", {"gte": from_timestamp, "lt": to_timestamp}),
            ]
        )
        found: dict[str, None] = {}
        after: list[Any] | None = None
        while True:
            response = await self._client.search(
                index=self.alias,
                size=AUDIT_PAGE,
                query=query,
                sort=[{"eventKey": "desc"}, {"auditId": "desc"}],
                search_after=after,
            )
            hits = response["hits"]["hits"]
            found.update(dict.fromkeys(hit["_source"]["entityId"] for hit in hits))
            if len(hits) < AUDIT_PAGE:
                return list(found)
            after = hits[-1]["sort"]


PUT_FAILED = "The audit events could not all be written to {alias}"

TAG_ACTIONS = (
    EntityAuditActionV2.CLASSIFICATION_ADD,
    EntityAuditActionV2.CLASSIFICATION_DELETE,
    EntityAuditActionV2.CLASSIFICATION_UPDATE,
)
"""The actions whose names start with ``CLASSIFICATION_``; the propagated ones do not (CAU-07)."""


def _document(event: EntityAuditEventV2, audit_id: str) -> dict[str, Any]:
    """The event as stored: its fields but the entity definition and type, its document id, and the folded keys.

    Elasticsearch ignores no case in a field sort, so ``userKey`` and ``actionKey`` hold ``_case_insensitive`` of
    the user and the action, folded once on the write rather than on every sort (DD-710).
    """
    return {
        **event.to_json(),
        "entity": None,
        "type": None,
        "auditId": audit_id,
        "userKey": _case_insensitive(event.user),
        "actionKey": _case_insensitive(event.action),
    }


def _sort_keys(column: str, *, descending: bool) -> list[dict[str, Any]]:
    """The Elasticsearch sort keys of a sort column (AUD-07, DD-710).

    ``user`` and ``action`` sort on their folded key then the timestamp; a key stored before the fold sorts as the
    empty fold, where Java's ``CASE_INSENSITIVE_ORDER`` puts a null, in both directions. The tail of event key and
    audit id, both descending, keeps ties in the newest-key-first order Java's scan gives them, which a reversed
    comparison holds in both directions.
    """
    order = "desc" if descending else "asc"
    if column == SORT_COLUMN_USER:
        head: list[dict[str, Any]] = [
            {"userKey": {"order": order, "missing": ""}},
            {"timestamp": {"order": order}},
        ]
    elif column == SORT_COLUMN_ACTION:
        head = [{"actionKey": {"order": order, "missing": ""}}, {"timestamp": {"order": order}}]
    else:
        head = [{"timestamp": {"order": order}}]
    return [*head, {"eventKey": "desc"}, {"auditId": "desc"}]


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
    """``listEventsV2`` with a sort column: every event of the entity in that order, then ``limit`` from ``offset``.

    The repository answers the order; the Elasticsearch one sorts in the index rather than reading the entity
    whole (AUD-07, DD-710). A negative offset reads as 0, a negative limit as 100, a limit of 0 as all.
    """
    return await repository.list_sorted(entity_id, action, sort_by, descending=descending, offset=offset, limit=limit)


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


CREATE_ACTIONS = frozenset({EntityAuditActionV2.ENTITY_CREATE, EntityAuditActionV2.ENTITY_IMPORT_CREATE})
"""The events an aging keeps unless it may age out creations."""
DAY_MILLISECONDS = 86_400_000


def events_to_age_out(  # noqa: PLR0913 - deleteEventsV2's parameters
    events: Sequence[EntityAuditEventV2],
    actions: Sequence[EntityAuditActionV2],
    count: int,
    ttl_in_days: int,
    *,
    create_events_ageout_allowed: bool,
    aging_type: AtlasAuditAgingType,
    now: int,
) -> list[EntityAuditEventV2]:
    """``HBaseBasedAuditRepository.deleteEventsV2``: the events of one entity an aging removes (AGE-04).

    Of each action asked (or of all), creations left out unless allowed, newest first: past the ``count`` newest
    they age out when a count is given or the aging sweeps. Of those kept, the newest ``count`` of them all stay
    for a default aging or one of all actions, and any older than ``ttl_in_days`` ages out.
    """
    by_count = count > 0 or aging_type is AtlasAuditAgingType.SWEEP
    eligible: list[EntityAuditEventV2] = []
    kept: list[EntityAuditEventV2] = []
    for action in sorted(actions) or [None]:
        listed = sort_events(
            [
                event
                for event in events
                if (action is None or event.action is action)
                and (create_events_ageout_allowed or event.action not in CREATE_ACTIONS)
            ],
            SORT_COLUMN_TIMESTAMP,
            descending=True,
        )
        if not by_count:
            kept += listed
            continue
        offset = min(len(listed), max(count, 0))
        kept += listed[:offset]
        eligible += listed[offset:]
    if not kept:
        return eligible
    if by_count and (aging_type is AtlasAuditAgingType.DEFAULT or not actions):
        kept = sort_events(kept, SORT_COLUMN_TIMESTAMP, descending=True)
        if count < len(kept):
            eligible += kept[count:]
            kept = kept[:count]
    if ttl_in_days > 0:
        cutoff = now - ttl_in_days * DAY_MILLISECONDS
        eligible += [event for event in kept if event.timestamp < cutoff]
    return eligible


async def delete_events_v2(  # noqa: PLR0913 - deleteEventsV2's parameters
    repository: EntityAuditRepository,
    entity_id: str,
    actions: Sequence[EntityAuditActionV2],
    count: int,
    ttl_in_days: int,
    *,
    create_events_ageout_allowed: bool,
    aging_type: AtlasAuditAgingType,
    now: int,
) -> list[EntityAuditEventV2]:
    """``deleteEventsV2``: the entity's events :func:`events_to_age_out` names, removed and answered (AGE-04)."""
    events = await repository.list_events(entity_id, None, None, -1)
    removed = events_to_age_out(
        events,
        actions,
        count,
        ttl_in_days,
        create_events_ageout_allowed=create_events_ageout_allowed,
        aging_type=aging_type,
        now=now,
    )
    await repository.delete_events(entity_id, [str(event.event_key) for event in removed])
    return removed
