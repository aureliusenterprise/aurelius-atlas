"""``view_derivation``: the card and the view of one stored entity, from its document alone (AVS-02, AVS-08, DD-581).

The one derivation the view family's doors share (ADR 064, DD-581): the search door cards each hit, the read
door answers its one read, the write door answers a save, all through ``view_of`` and ``card_of``. A view reads
the entity document only: its own fields, its stored App Search document of 14.2 and its stored search fields.
Nothing is walked and nothing is joined — the breadcrumb and the derived relations are what the indexer
stored (AVS-08), and a related end keeps the name its document gave it, none where the end went nameless
(ASU-02). A door that read an end's entity passes it in ``ends``; the derivation itself reads nothing.
``read_ends`` is that read, for the door that answers its entity's own relationship ends (VDR-02, DD-604).
"""

from collections.abc import Mapping, Sequence
from typing import Any

from aurelius_atlas_model.instance import RelationshipStatus
from aurelius_atlas_model.views import (
    CardBreadcrumb,
    CardQuality,
    EntityCard,
    EntityRelation,
    EntityView,
    RelationEntity,
)
from aurelius_atlas_typesystem.entity_type import EntityType

from aurelius_atlas_core.app_search_document import RELATION_FIELDS, awaits_document
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.graph_helper import collection_elements, other_end, relationship_type_name
from aurelius_atlas_core.search_fields import TRAIT_NAMES
from aurelius_atlas_core.stored_entity import StoredAppSearch, StoredEntity, StoredQualityTotals

QUALITY_DIMENSIONS = ("accuracy", "completeness", "timeliness", "uniqueness", "validity", "overall")
"""The quality entries a card carries, in this order (AVS-01, LAS-12)."""

type RelationEnds = Mapping[str, Sequence[StoredEntity]]
"""The ends of relationship attributes, by attribute name: what a door that read them passes in (AVS-04)."""


def card_of(view: EntityView) -> EntityCard:
    """The card of a view: the shared fields, the entity's own values and sections left out (DD-581)."""
    return EntityCard.of(view)


def view_of(stored: StoredEntity, entity_type: EntityType, *, ends: RelationEnds | None = None) -> EntityView:
    """The view of one stored entity: its fields, its document's derived fields, and its sections (AVS-01, AVS-04).

    ``entity_type`` names the attributes (the store keeps values by qualified name, AVS-04) and the business
    attributes; both are what a read of the type costs the door, not a join per entity. ``ends`` carries the
    entities of relationship attributes the door read, by attribute name; without them the sections hold the
    document's stored pairs only (AVS-08).
    """
    document = stored.app_search
    stale = bool(document.stale) if document else awaits_document(stored)
    fields: dict[str, Any] = {
        "guid": stored.guid,
        "type_name": stored.type_name,
        "super_type_names": list(stored.super_type_names),
        "name": _text(stored.attributes, entity_type, "name"),
        "qualified_name": _text(stored.attributes, entity_type, "qualifiedName"),
        "display_text": _display_text(stored, entity_type),
        "definition": _text(stored.attributes, entity_type, "definition"),
        "status": stored.state,
        "create_time": stored.create_time,
        "update_time": stored.update_time,
        "created_by": stored.created_by,
        "updated_by": stored.updated_by,
        "classification_names": _classification_names(stored),
        "labels": list(stored.labels or []),
        "breadcrumb": _breadcrumb(document) if document else [],
        "relations": _relations(document) if document else [],
        "quality": _quality(stored.quality_totals) if stored.quality_totals else [],
        "governed": stored.governed,
        "stale": stale,
        "attributes": _own_attributes(stored, entity_type),
        "business_metadata": _business_metadata(stored, entity_type),
        "sections": _sections(document, ends),
    }
    return EntityView.model_validate(fields)


def _text(attributes: dict[str, Any], entity_type: EntityType, name: str) -> str | None:
    """The entity's value of the attribute ``name``, whichever type defines it, or none."""
    for attribute in entity_type.all_attributes.values():
        if str(attribute.name) == name and attributes.get(attribute.qualified_name) is not None:
            return str(attributes[attribute.qualified_name])
    return None


def _display_text(stored: StoredEntity, entity_type: EntityType) -> str:
    """The name, or the qualified name when there is no name (AVS-03)."""
    return _text(stored.attributes, entity_type, "name") or _text(stored.attributes, entity_type, "qualifiedName") or ""


def _classification_names(stored: StoredEntity) -> list[str]:
    """The names of the classifications attached to the entity, from its stored search fields (DD-090).

    Propagated names are not included: they belong to their source, as DD-326's client rule leaves them and
    AVW-08's server rule protects them.
    """
    names = (stored.search or {}).get(TRAIT_NAMES)
    return [str(name) for name in names] if isinstance(names, list) else []


def _breadcrumb(document: StoredAppSearch) -> list[CardBreadcrumb]:
    """The stored arrays, zipped into crumbs in their stored order, top-down (AVS-02, LAS-04)."""
    return [
        CardBreadcrumb(guid=guid, name=name, type_name=_at(document.breadcrumbtype, index))
        for index, (guid, name) in enumerate(zip(document.breadcrumbguid, document.breadcrumbname, strict=False))
    ]


def _at(values: list[Any], index: int) -> Any:  # noqa: ANN401 - a stored array element
    """The value at ``index``, or none where the arrays came apart (LAS-04 keeps them parallel)."""
    return values[index] if index < len(values) else None


def _relations(document: StoredAppSearch) -> list[EntityRelation]:
    """The stored relation pairs, per field in RELATION_FIELDS' order, empty fields left out (AVS-02, LAS-05)."""
    relations = []
    for attribute, field in RELATION_FIELDS.items():
        names: list[str | None] = getattr(document, field)
        guids: list[str] = getattr(document, f"{field}guid")
        entities = [RelationEntity(guid=guid, name=name) for guid, name in zip(guids, names, strict=False)]
        if entities:
            relations.append(EntityRelation(attribute=attribute, entities=entities))
    return relations


def _quality(totals: StoredQualityTotals) -> list[CardQuality]:
    """The stored roll-up, one entry per dimension and overall, in QUALITY_DIMENSIONS' order (AVS-01, ASQ-04)."""
    entries = []
    for dimension in QUALITY_DIMENSIONS:
        found: Any = getattr(totals, dimension)
        entries.append(
            CardQuality(
                dimension=dimension,
                score=found.score,
                count=found.count,
                total=found.total,
                rule_guids=list(found.rules),
            )
        )
    return entries


def _own_attributes(stored: StoredEntity, entity_type: EntityType) -> dict[str, Any]:
    """The entity's attribute values under their attribute names (AVS-04, ERD-03's reading).

    ``all_attributes`` are the plain attributes — business attributes live apart, as ERD-03 reads them — so
    ``businessMetadata`` never repeats a value shown here. A stored value whose attribute the type no longer
    has is left out, as ``to_entity`` leaves it (DD-043).
    """
    return {
        str(attribute.name): stored.attributes[attribute.qualified_name]
        for attribute in entity_type.all_attributes.values()
        if attribute.qualified_name in stored.attributes
    }


def _business_metadata(stored: StoredEntity, entity_type: EntityType) -> dict[str, dict[str, Any]] | None:
    """The business attribute values with a value, by business metadata, or none (AVS-04, BMD-02's reading)."""
    found: dict[str, dict[str, Any]] = {}
    for metadata, attributes in entity_type.business_attributes.items():
        for attribute in attributes.values():
            value = stored.attributes.get(attribute.qualified_name)
            if value is not None:
                found.setdefault(metadata, {})[str(attribute.name)] = value
    return found or None


def _sections(document: StoredAppSearch | None, ends: RelationEnds | None) -> list[EntityRelation]:
    """One entry per attribute with ends: stored pairs first, read ends filling in, each stored end once (AVS-04).

    A stored pair carries the name the document gave the end (none once the end went nameless, ASU-02); an end
    the door read carries its type and state and wins the place, so a stored end never shows twice. A read end
    is keyed by relationship attribute and a stored pair by the end's type, so the two can name one GUID apart
    (VDR-02, DD-604): an end a door read is dropped from any stored pair naming it, and the pair keeps its
    other ends. Read sections keep every end the door read — one entity can sit under two attributes at once
    (the process that is both producer and consumer of a dataset, REL-17), and each of them answers it.
    """
    sections: dict[str, dict[str, RelationEntity]] = {}
    stored: dict[str, dict[str, RelationEntity]] = {}
    if document is not None:
        for relation in _relations(document):
            sections[relation.attribute] = {entity.guid: entity for entity in relation.entities}
            stored[relation.attribute] = sections[relation.attribute]
    for attribute, entities in (ends or {}).items():
        if attribute not in stored:  # the read end wins the GUID's stored place (VDR-02)
            for pair in stored.values():
                for entity in entities:
                    pair.pop(entity.guid, None)
        merged = sections.setdefault(attribute, {})
        for entity in entities:
            merged[entity.guid] = RelationEntity.model_validate(
                {"guid": entity.guid, "name": _end_name(entity), "type_name": entity.type_name, "status": entity.state}
            )
    return [
        EntityRelation.model_validate({"attribute": attribute, "entities": list(by_guid.values())})
        for attribute, by_guid in sections.items()
        if by_guid
    ]


def _end_name(entity: StoredEntity) -> str | None:
    """An end's name: its ``name`` attribute, whichever type defines it, or none."""
    for key in sorted(key for key in entity.attributes if key.rsplit(".", 1)[-1] == "name"):
        value = entity.attributes[key]
        if value is not None:
            return str(value)
    return None


async def read_ends(store: EntityStore, stored: StoredEntity, entity_type: EntityType) -> RelationEnds:
    """The entities at the other ends of ``stored``'s relationship attributes, by attribute name (VDR-02, DD-604).

    The 2.3 read's own machinery answers them (REL-17): the entity's listed relationships through
    ``relationship_type_name`` and ``collection_elements``, so an edge belongs to an attribute exactly as the
    Apache Atlas read says it does, and a ``DELETED`` edge answers nothing. Every end GUID of the entity is
    read in one ``get_many`` — one entity, its own attributes, one round, not the walk ADR 064 R1 rejects. An
    end the store no longer has is left out, as ``mapVertexToRelatedObjectId`` leaves it.
    """
    listed = stored.relationship_guids or []
    found = await store.get_relationships(listed)
    relationships = [found[guid].relationship for guid in listed if guid in found]
    active = [edge for edge in relationships if edge.state is RelationshipStatus.ACTIVE]
    guids_by_attribute: dict[str, list[str]] = {}
    for name in entity_type.relationship_attributes:
        type_name = relationship_type_name(stored.guid, relationships, entity_type, name)
        attribute = entity_type.relationship_attribute(name, type_name)
        if attribute is None:  # pragma: no cover - the registry added the attribute for this name
            continue
        ends = [other_end(edge, stored.guid) for edge in collection_elements(stored.guid, active, attribute)]
        if ends:
            guids_by_attribute[name] = ends
    if not guids_by_attribute:
        return {}
    entities = await store.get_many([guid for ends in guids_by_attribute.values() for guid in ends])
    return {
        name: [found.entity for guid in dict.fromkeys(ends) if (found := entities.get(guid)) is not None]
        for name, ends in guids_by_attribute.items()
    }
