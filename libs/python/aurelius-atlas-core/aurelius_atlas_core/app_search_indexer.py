"""``AppSearchIndexer``: derives the App Search documents the store's entities lack, and keeps them up to date
(LAS-01 to LAS-10, ASD-04, ASU-02 to ASU-05).

Each round asks the store for a page of entities that should have a document and have none, or have a stale one
(DD-518), and a page of relationships deleted or restored since their ends' documents saw them (DD-520). It
derives each entity's document from the entities around it. An entity whose document goes, or that other
documents now know by another name, breadcrumb or relations, affects the documents that name it; those are
derived again and written first, if they changed (DD-519). Then each entity is written with its document, and
each relationship with its state recorded. Whole writes on the version read, as the embedding indexer's
(DD-436): an entity changed in between keeps its write and waits for a later round.

A document's breadcrumb follows the first active parent up (LAS-04); its derived relations are the other ends of
its active relationships, and, for datasets and data entities, the pairs a field joins (LAS-05, LAS-06). The
entities and relationships a page reads are read once for the page.
"""  # noqa: D205 - one sentence

from collections.abc import Iterable, Sequence

from aurelius_atlas_model.instance import RelationshipStatus
from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_core.app_search_document import (
    PARENTS,
    RELATION_FIELDS,
    document_name,
    has_document,
    identity,
    mapped,
    named_guids,
    own_document,
)
from aurelius_atlas_core.entity_documents import (
    EntityDocuments,
    LinkedKind,
    LinkedWrite,
    VersionedEntity,
    VersionedRelationship,
)
from aurelius_atlas_core.graph_helper import collection_elements, other_end, referenced_end
from aurelius_atlas_core.stored_entity import StoredAppSearch, StoredEntity
from aurelius_atlas_core.stored_relationship import StoredRelationship

DEFAULT_BATCH_SIZE = 100
"""Entities, and relationships, per page."""

_JOINS = {
    "m4i_dataset": ("m4i_field", "m4i_data_attribute", "m4i_data_entity"),
    "m4i_data_entity": ("m4i_data_attribute", "m4i_field", "m4i_dataset"),
}
"""The paths a field joins a dataset and a data entity by, from each end (LAS-06)."""


class _Catalogue:
    """The entities and their active relationships, each read once, and what LAS-04 to LAS-06 read of them."""

    def __init__(self, documents: EntityDocuments, registry: TypeRegistry) -> None:
        self._documents = documents
        self._registry = registry
        self._entities: dict[str, StoredEntity | None] = {}
        self._edges: dict[str, list[StoredRelationship]] = {}

    def add(self, entities: Iterable[StoredEntity]) -> None:
        """Entities already read."""
        self._entities.update((entity.guid, entity) for entity in entities)

    async def load(self, guids: Sequence[str]) -> None:
        """Read the entities not read yet, and the relationships of those read; one request for each."""
        missing = [guid for guid in dict.fromkeys(guids) if guid not in self._entities]
        if missing:
            found = await self._documents.get(missing)
            self._entities.update((guid, found[guid].entity if guid in found else None) for guid in missing)
        listing = [
            entity
            for guid in guids
            if guid not in self._edges and (entity := self._entities.get(guid)) is not None and mapped(entity)
        ]
        wanted = [guid for entity in listing for guid in entity.relationship_guids or []]
        linked = await self._documents.get_linked(LinkedKind.RELATIONSHIP, wanted) if wanted else {}
        for entity in listing:
            self._edges[entity.guid] = [
                relationship
                for guid in entity.relationship_guids or []
                if guid in linked
                and isinstance(relationship := linked[guid][0], StoredRelationship)
                and relationship.state is RelationshipStatus.ACTIVE
            ]

    def entity(self, guid: str) -> StoredEntity | None:
        """The entity, if read and active and of a mapped type."""
        entity = self._entities.get(guid)
        return entity if entity is not None and mapped(entity) else None

    async def related(self, guid: str, type_name: str | None = None) -> list[str]:
        """The other ends of the entity's active relationships that are active and mapped, once each (LAS-05)."""
        await self.load([guid])
        ends = list(dict.fromkeys(other_end(relationship, guid) for relationship in self._edges.get(guid, [])))
        await self.load(ends)
        return [
            end
            for end in ends
            if end != guid
            and (other := self.entity(end)) is not None
            and (type_name is None or other.type_name == type_name)
        ]

    async def first_parent(self, guid: str) -> str | None:
        """The first active parent in the type's parents' order (LAS-04)."""
        entity = self.entity(guid)
        entity_type = None if entity is None else self._registry.entity_type(entity.type_name)
        if entity is None or entity_type is None:
            return None
        await self.load([guid])
        candidates = [
            referenced_end(relationship, attribute.relationship_edge_direction, guid)
            for name in PARENTS.get(entity.type_name, ())
            for attribute in entity_type.relationship_attributes.get(name, {}).values()
            for relationship in collection_elements(guid, self._edges.get(guid, []), attribute)
        ]
        await self.load(candidates)
        return next((candidate for candidate in candidates if self.entity(candidate) is not None), None)

    async def breadcrumb(self, guid: str) -> list[StoredEntity]:
        """The entities above, from the top: the first parent's breadcrumb, then that parent (LAS-04).

        An entity already in the chain ends it.
        """
        chain = [guid]
        while (parent := await self.first_parent(chain[-1])) is not None and parent not in chain:
            chain.append(parent)
        return [entity for guid in reversed(chain[1:]) if (entity := self.entity(guid)) is not None]

    async def joined(self, guid: str, path: Sequence[str]) -> list[str]:
        """The entities reached along ``path``'s types, one relation at a time (LAS-06)."""
        reached = [guid]
        for type_name in path:
            reached = list(dict.fromkeys([end for found in reached for end in await self.related(found, type_name)]))
        return reached


class AppSearchIndexer:
    """Derives and writes the App Search documents of ``documents``' entities that lack a current one."""

    def __init__(
        self, documents: EntityDocuments, registry: TypeRegistry, *, batch_size: int = DEFAULT_BATCH_SIZE
    ) -> None:
        """An indexer over ``documents``, with ``registry``'s relationship attributes, ``batch_size`` at a time."""
        self._documents = documents
        self._registry = registry
        self._batch_size = batch_size

    async def run_once(self) -> int:
        """Derive page after page until none is left, or a page writes nothing; how many entities and relationships
        were written.
        """  # noqa: D205 - one sentence
        written = 0
        while True:
            page = await self._documents.without_app_search(self._batch_size)
            relationships = await self._documents.unseen_relationships(self._batch_size)
            if not page and not relationships:
                return written
            put = await self._write(page, relationships)
            written += put
            if put == 0 or max(len(page), len(relationships)) < self._batch_size:
                return written

    async def derive(self, entities: Sequence[StoredEntity]) -> dict[str, StoredAppSearch | None]:
        """The entities' documents by GUID, none for one without (LAS-01), as the store holds the rest now."""
        catalogue = _Catalogue(self._documents, self._registry)
        catalogue.add(entities)
        return {entity.guid: await _document(catalogue, entity) for entity in entities}

    async def _write(self, page: list[VersionedEntity], relationships: list[VersionedRelationship]) -> int:
        """Write the documents the page affects, then, if all were written, the page's own (ASU-05)."""
        catalogue = _Catalogue(self._documents, self._registry)
        catalogue.add(found.entity for found in page)
        documents = {found.entity.guid: await _document(catalogue, found.entity) for found in page}
        changed = [
            found.entity
            for found in page
            if found.entity.app_search is not None
            and identity(found.entity.app_search) != identity(documents[found.entity.guid])
        ]
        named = [guid for entity in changed for guid in named_guids(entity.app_search)]
        named += [guid for entity in changed for guid in named_guids(documents[entity.guid])]
        named += [end for found in relationships for end in found.relationship.ends()]
        affected = await self._affected(catalogue, [entity.guid for entity in changed], named, set(documents))
        if affected:
            results = await self._documents.write(
                [
                    (found.entity.model_copy(update={"app_search": document}), found.version)
                    for found, document in affected
                ]
            )
            if not all(result.written for result in results):
                return sum(1 for result in results if result.written)
        seen = [
            (found.relationship.model_copy(update={"app_search_state": found.relationship.state}), found.version)
            for found in relationships
        ]
        results = await self._documents.write(
            [
                (found.entity.model_copy(update={"app_search": documents[found.entity.guid]}), found.version)
                for found in page
            ],
            linked={LinkedKind.RELATIONSHIP: LinkedWrite(written=seen)} if seen else None,
        )
        return len(affected) + sum(1 for result in results if result.written)

    async def _affected(
        self, catalogue: _Catalogue, changed: list[str], named: list[str], skip: set[str]
    ) -> list[tuple[VersionedEntity, StoredAppSearch | None]]:
        """The current documents that name a changed entity, or that one names, derived again where they differ.

        One whose name, breadcrumb or relations' GUIDs change is a changed entity in turn (ASU-03, DD-519). A
        missing or stale document is left to its own listing, as are the ``skip`` ones.
        """
        affected: list[tuple[VersionedEntity, StoredAppSearch | None]] = []
        seen = set(skip)
        while changed or named:
            found = {versioned.entity.guid: versioned for versioned in await self._documents.naming(changed)}
            rest = [guid for guid in dict.fromkeys(named) if guid not in found and guid not in seen]
            found |= await self._documents.get(rest)
            changed, named = [], []
            for guid, versioned in found.items():
                old = versioned.entity.app_search
                if guid in seen or old is None or old.stale:
                    continue
                seen.add(guid)
                catalogue.add([versioned.entity])
                new = await _document(catalogue, versioned.entity)
                if new == old:
                    continue
                affected.append((versioned, new))
                if identity(new) != identity(old):
                    changed.append(guid)
                    named += named_guids(old) + named_guids(new)
        return affected


async def _document(catalogue: _Catalogue, entity: StoredEntity) -> StoredAppSearch | None:
    """The entity's document: its own fields, then its breadcrumb and derived relations if of a mapped type; none
    for an entity without (LAS-01).

    A relation field lists the entity's relationships in the order it lists them, then the joins, once (DD-501).
    """  # noqa: D205 - one sentence
    if not has_document(entity):
        return None
    document = own_document(entity)
    if not mapped(entity):
        return document
    breadcrumb = await catalogue.breadcrumb(entity.guid)
    update: dict[str, object] = {
        "breadcrumbguid": [above.guid for above in breadcrumb],
        "breadcrumbname": [document_name(above) for above in breadcrumb],
        "breadcrumbtype": [above.type_name for above in breadcrumb],
        "parentguid": breadcrumb[-1].guid if breadcrumb else None,
    }
    related = await catalogue.related(entity.guid)
    if path := _JOINS.get(entity.type_name):
        related += await catalogue.joined(entity.guid, path)
    relations: dict[str, list[str | None]] = {}
    for other in (catalogue.entity(guid) for guid in dict.fromkeys(related)):
        if other is not None:
            field = RELATION_FIELDS[other.type_name]
            relations.setdefault(field, []).append(document_name(other))
            relations.setdefault(f"{field}guid", []).append(other.guid)
    return document.model_copy(update=update | relations)
