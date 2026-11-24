"""The entities' documents in Elasticsearch: entities, unique value reservations and the write journal (ENS-01).

The I/O behind ``EntityStore``: reads in real time, conditional writes, create-only reservations (DD-043 to DD-047).
Documents go to Elasticsearch as the bytes of Atlas's JSON codec, so values keep their digits (DD-039).
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from aurelius_atlas_model.base import AtlasModel
from pydantic import Field

from aurelius_atlas_core.app_search_document import (
    StoredVerdict,
)
from aurelius_atlas_core.index_setup import (
    ENTITY_DOCUMENTS,
    LINKED_MODELS,
    Linked,
    LinkedKind,
)
from aurelius_atlas_core.search_query import (
    SearchHits,
    SearchQuery,
)
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_entity import StoredEntity, StoredQualityResult
from aurelius_atlas_core.stored_relationship import StoredRelationship
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.typedef_document import DocumentVersion


@dataclass(frozen=True)
class VersionedEntity:
    """A stored entity and the version it was read in (DD-047)."""

    entity: StoredEntity
    version: DocumentVersion


@dataclass(frozen=True)
class TypeCount:
    """How many entities of a type are in a state, shells (``isIncomplete``) or not (MET-02)."""

    type_name: str
    state: str
    incomplete: bool
    count: int


@dataclass(frozen=True)
class VersionedRelationship:
    """A stored relationship and the version it was read in (DD-047, DD-061).

    None for one a write request creates and has not written yet (DD-068).
    """

    relationship: StoredRelationship
    version: DocumentVersion | None


@dataclass(frozen=True)
class VersionedClassification:
    """A stored classification instance and the version it was read in (DD-047, DD-070)."""

    classification: StoredClassification
    version: DocumentVersion


class Reservation(AtlasModel):
    """A unique value held by an entity: the key's id, the holder's GUID and the write that reserved it (DD-045).

    ``key`` is the document's id, not part of its source, so it stays out of ``to_json`` (DD-560).
    """

    key: str = Field(exclude=True)
    guid: str
    write_id: str


@dataclass(frozen=True)
class WriteResult:
    """How one entity of a bulk write ended: written, or failed by a version conflict or another error."""

    guid: str
    written: bool
    conflict: bool = False
    kind: LinkedKind | None = None


@dataclass(frozen=True)
class LinkedWrite:
    """What a write does to the documents of one ``LinkedKind``: written ones at a version or new, removed ones."""

    written: Sequence[tuple[Linked, DocumentVersion | None]] = ()
    removed: Sequence[tuple[str, DocumentVersion]] = ()


class JournalEntry(AtlasModel):
    """A write in flight: its id, lease, the entities' states before it, its reservations, releases and removals.

    DD-046, DD-056.
    """

    write_id: str
    lease_until: int
    before: dict[str, dict[str, Any] | None] = Field(default_factory=dict)
    reserved: list[str] = Field(default_factory=list)
    released: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    linked_before: dict[str, dict[str, dict[str, Any] | None]] = Field(default_factory=dict)
    removed_linked: dict[str, list[str]] = Field(default_factory=dict)
    committed: bool = False

    def before_entity(self, guid: str) -> StoredEntity | None:
        """The state of ``guid`` before the write, or None for an entity the write created."""
        source = self.before.get(guid)
        return None if source is None else StoredEntity.model_validate(source)

    def before_linked(self, kind: LinkedKind, guid: str) -> Linked | None:
        """The state of a linked document before the write, or None for one the write created (DD-062, DD-071)."""
        source = self.linked_before.get(kind, {}).get(guid)
        return None if source is None else LINKED_MODELS[kind].model_validate(source)


@runtime_checkable
class EntityDocuments(Protocol):
    """The documents the indexers and the doors reach (EDS-03, DD-791).

    A narrow contract on purpose: an indexer or a door reads entities and linked documents, finds the ones it
    has work for, and writes its results back — nothing else. ``StoreDocuments`` is the contract
    ``EntityStore`` is typed on, and it lists the rest.
    """

    async def get(self, guids: Sequence[str]) -> dict[str, VersionedEntity]:
        """The stored entities with these GUIDs, in real time; unknown GUIDs are left out."""
        ...

    async def get_linked(self, kind: LinkedKind, guids: Sequence[str]) -> dict[str, tuple[Linked, DocumentVersion]]:
        """The stored documents of a kind with these GUIDs, in real time; unknown GUIDs are left out (DD-061)."""
        ...

    async def without_app_search(self, limit: int) -> list[VersionedEntity]:
        """Up to ``limit`` entities that should have an App Search document and have none, or a stale one (ASD-04,
        ASU-02).
        """  # noqa: D205 - one sentence
        ...

    async def naming(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """The entities whose App Search document names one of these GUIDs in its breadcrumb or relations (ASU-03)."""
        ...

    async def unseen_relationships(self, limit: int) -> list[VersionedRelationship]:
        """Up to ``limit`` relationships deleted or restored since their ends' documents saw them (ASU-04)."""
        ...

    async def without_embedding(
        self, model: str, limit: int, *, wait_for_documents: bool = False
    ) -> list[VersionedEntity]:
        """Up to ``limit`` entities without an embedding of ``model``, internal types left out (VEC-06, DD-436);
        with ``wait_for_documents``, also those awaiting their App Search document (EMC-04, DD-540).
        """  # noqa: D205 - one sentence
        ...

    async def scores(self) -> list[VersionedEntity]:
        """Every active score entity, by GUID (ASQ-02)."""
        ...

    async def quality_holders(self) -> list[VersionedEntity]:
        """Every entity holding a quality result or score totals, by GUID (ASQ-07)."""
        ...

    async def results_by_field(self, field_guid: str) -> list[StoredQualityResult]:
        """The quality results of the active scores naming this field, in score GUID order (ASQ-09, DD-862).

        The same paged read ``scores()`` runs, filtered over ``qualityResult.fieldguid`` (ASQ-03's keyword);
        a score holding no result answers no row, and a field no score names answers the empty list. The read
        door joins these rows into a field's view (VDR-16).
        """
        ...

    async def governance_rules(self) -> list[VersionedEntity]:
        """The active governance rule entities, by GUID (ASG-03)."""
        ...

    async def to_govern(self, digests: Mapping[str, str], limit: int) -> list[VersionedEntity]:
        """The entities to judge, by GUID: those with a document of a type in ``digests`` judged by another digest
        or none, and those with verdicts no longer judged (ASG-06, DD-535).
        """  # noqa: D205 - one sentence
        ...

    async def replace_verdicts(self, verdicts: Mapping[str, Sequence[StoredVerdict]]) -> None:
        """Each entity's governance verdicts, by its GUID, in place of those it had (ASG-06, DD-534)."""
        ...

    async def verdicts_by_entity(self, entity_guids: Sequence[str]) -> dict[str, list[StoredVerdict]]:
        """The stored governance verdicts of these entities, grouped by entity GUID (ASG-08, DD-838).

        Each group is in document id order, and an entity with no verdicts has no key. The doors answer a
        card's ``verdicts`` from this read (VDR-13), so a whole page costs one paged search (DD-836's pattern).
        """
        ...

    async def verdicts_by_rule(self, rule_guid: str) -> list[StoredVerdict]:
        """The stored governance verdicts of one rule, in document id order (ASG-09, DD-845).

        The same paged read as ``verdicts_by_entity``, filtered over ``guid``; a rule with no verdict
        documents answers the empty list. The verdicts door answers its rows from this read (VDR-14).
        """
        ...

    async def write(
        self,
        items: Sequence[tuple[StoredEntity, DocumentVersion | None]],
        removed: Sequence[tuple[str, DocumentVersion]] = (),
        linked: Mapping[LinkedKind, LinkedWrite] | None = None,
    ) -> list[WriteResult]:
        """Write and remove entities and linked documents, new (no version) or at the version given.

        One bulk request; the results are in order: entities written, removed, then each kind's written, removed
        (DD-056, DD-062, DD-071).
        """
        ...


@runtime_checkable
class StoreDocuments(EntityDocuments, Protocol):
    """The documents ``EntityStore`` keeps: everything the narrow contract has, plus the store's reads.

    The store drives writes, reservations, the journal, the counts, and the searches the basic door answers, so
    it is typed on the wide contract; an indexer or a door stays on the narrow one (EDS-03, DD-791).
    """

    async def prepare(self) -> None:
        """Create the indices that are missing."""
        ...

    async def restore_linked(self, kind: LinkedKind, guid: str, before: Linked | None) -> None:
        """Put back a linked document's state before a write, or delete one the write created (DD-062)."""
        ...

    async def count_linked_type(self, kind: LinkedKind, type_name: str) -> int:
        """How many documents of the kind and type exist, in any state, as of now (REL-10, CLS-12)."""
        ...

    async def referring(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """The entities whose references name any of these GUIDs, as of now (DD-057)."""
        ...

    async def of_types(self, type_names: Sequence[str]) -> list[VersionedEntity]:
        """The entities of exactly these types, in any state, as of now (EXP-03)."""
        ...

    async def classified(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """The entities listing any of these classification instances, as of now (DD-076)."""
        ...

    async def list_tasks(self, *, open_only: bool) -> list[tuple[StoredTask, DocumentVersion]]:
        """Every task, or those ``PENDING`` or ``IN_PROGRESS``, oldest first, as of now (TSK-04, TSK-06)."""
        ...

    async def restore(self, guid: str, before: StoredEntity | None) -> None:
        """Put back an entity's state before a write, or delete one the write created."""
        ...

    async def reserve(self, reservation: Reservation) -> Reservation | None:
        """Make a reservation, create-only; the one holding the key when it is taken."""
        ...

    async def reservations(self, keys: Sequence[str]) -> dict[str, Reservation]:
        """The reservations of these keys that exist."""
        ...

    async def release(self, key: str, guid: str) -> None:
        """Delete the reservation of ``key`` if ``guid`` holds it."""
        ...

    async def put_journal(self, entry: JournalEntry) -> None:
        """Write a journal entry."""
        ...

    async def delete_journal(self, write_id: str) -> None:
        """Delete a journal entry."""
        ...

    async def journal(self) -> list[JournalEntry]:
        """Every journal entry, as the last refresh shows them."""
        ...

    async def get_journal(self, write_id: str) -> JournalEntry | None:
        """The journal entry of a write as of now, None when there is none."""
        ...

    async def count_type(self, type_name: str) -> int:
        """How many entities of exactly this type exist, in any state, as of now."""
        ...

    async def type_counts(self) -> list[TypeCount]:
        """How many entities there are of each type, state and shell flag, as of now (MET-02)."""
        ...

    async def linked_type_counts(self, kind: LinkedKind) -> dict[str, int]:
        """How many documents of the kind there are of each type, as of now (MET-02)."""
        ...

    async def search(self, query: SearchQuery) -> SearchHits:
        """The entities of the query's page, as of now, how many match it in all, their scores, and the query's
        facets (DD-089, DD-093).
        """  # noqa: D205 - one sentence
        ...

    async def terms(self, fields: Sequence[str], prefix: str) -> dict[str, list[tuple[str, int]]]:
        """Per search field, the 5 words of every entity's text in it that begin with ``prefix``, with how many
        entities hold each, most first, then by word (DD-094).
        """  # noqa: D205 - one sentence
        ...

    async def classifications_of_types(self, type_names: Collection[str] | None) -> list[StoredClassification]:
        """The classification instances of these types, or of every type for None, as of now (DD-090)."""
        ...


@runtime_checkable
class SearchDocuments(Protocol):
    """The one search the App Search engine and the view door run on (QRY-05, DD-770).

    A narrow contract on purpose: an App Search search needs the engine's field table, its nested index paths and
    its weighted vector scoring, so the in-memory store answers the basic search and the terms search it already
    answers and does not become a third query engine. Specs that drive an engine pass a small fake for this method,
    the pattern ``FakeEmbedder`` uses.
    """

    async def search_app_search(  # noqa: PLR0913 - Elasticsearch's search arguments; and the index
        self,
        *,
        query: dict[str, Any] | None,
        sort: list[dict[str, Any]],
        aggs: dict[str, Any],
        from_: int,
        size: int,
        index: str = ENTITY_DOCUMENTS,
        knn: dict[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """One search of an engine's index: hits with scores, the exact total, the aggregations (DD-523, DD-534)."""
        ...
