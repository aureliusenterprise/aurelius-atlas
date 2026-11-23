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
    ClassificationSource,
    EntityCard,
    EntityRelation,
    EntityView,
    RelationEntity,
)
from aurelius_atlas_typesystem.entity_type import EntityType

from aurelius_atlas_core.app_search_document import RELATION_FIELDS, ROLE_FIELDS, awaits_document
from aurelius_atlas_core.entity_store import WriteStore
from aurelius_atlas_core.graph_helper import collection_elements, other_end, relationship_type_name
from aurelius_atlas_core.search_fields import own_classifications
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_entity import StoredAppSearch, StoredEntity, StoredQualityTotals

QUALITY_DIMENSIONS = ("accuracy", "completeness", "timeliness", "uniqueness", "validity", "overall")
"""The quality entries a card carries, in this order (AVS-01, LAS-12)."""

type RelationEnds = Mapping[str, Sequence[StoredEntity]]
"""The ends of relationship attributes, by attribute name: what a door that read them passes in (AVS-04)."""

type Propagations = Sequence[tuple[str, Sequence[StoredEntity]]]
"""The propagated classifications and their source entities, in the order the entity lists them (VDR-05).

``read_propagations`` answers this for the door that reads them; a door that answers none passes nothing, and
the view then holds the field empty."""


def card_of(view: EntityView) -> EntityCard:
    """The card of a view: the shared fields, the entity's own values and sections left out (DD-581)."""
    return EntityCard.of(view)


def view_of(
    stored: StoredEntity,
    entity_type: EntityType,
    *,
    ends: RelationEnds | None = None,
    propagated: Propagations | None = None,
) -> EntityView:
    """The view of one stored entity: its fields, its document's derived fields, and its sections (AVS-01, AVS-04).

    ``entity_type`` names the attributes (the store keeps values by qualified name, AVS-04) and the business
    attributes; both are what a read of the type costs the door, not a join per entity. ``ends`` carries the
    entities of relationship attributes the door read, by attribute name; without them the sections hold the
    document's stored pairs only (AVS-08). ``propagated`` carries the propagated classifications and their
    source entities the door read; without them the view answers none (VDR-05, DD-835).
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
        "type_alias": _text(stored.attributes, entity_type, "typeAlias") or None,
        "definition": _card_definition(stored, entity_type),
        "status": stored.state,
        "create_time": stored.create_time,
        "update_time": stored.update_time,
        "created_by": stored.created_by,
        "updated_by": stored.updated_by,
        "classification_names": own_classifications(stored),
        "labels": list(stored.labels or []),
        "breadcrumb": _breadcrumb(document) if document else [],
        "relations": _relations(document) if document else [],
        "quality": _quality(stored.quality_totals) if stored.quality_totals else [],
        "governed": stored.governed,
        "stale": stale,
        "has_parent": bool(document.hasparent) if document else False,
        "attributes": _own_attributes(stored, entity_type),
        "business_metadata": _business_metadata(stored, entity_type),
        "sections": _sections(document, ends),
        "propagated_classifications": _propagated(propagated),
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


def _card_definition(stored: StoredEntity, entity_type: EntityType) -> str | None:
    """The card's description text (AVS-03, DD-614 as amended by 18.8/SPA-05): the entity's ``description``.

    Increment 18.8 retires the m4i dictionary's ``definition``, so the card reads the one prose attribute the
    shipped model has. The card keeps its ``definition`` field name (DD-833): the 16.x card family reads it.
    """
    return _text(stored.attributes, entity_type, "description")


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
    """The card's relations: the stored type-keyed pairs, then the role pairs in ROLE_FIELDS' order.

    The type-keyed pairs come first in RELATION_FIELDS' order (AVS-02, LAS-05); the role pairs follow,
    each keyed by its relationship attribute (AVS-10, ASD-06). A pair whose end the store no longer has
    keeps the document's stored name, as every stored pair does (ASU-02).
    """
    return _pairs(document, RELATION_FIELDS) + _pairs(document, ROLE_FIELDS)


def _pairs(document: StoredAppSearch, fields: Mapping[str, str]) -> list[EntityRelation]:
    """The stored pairs of ``fields``, per field in its order, empty ones left out (AVS-02, LAS-05)."""
    relations = []
    for attribute, field in fields.items():
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
        for relation in _pairs(document, RELATION_FIELDS):  # the role pairs ride the card, not the sections (AVS-10)
            sections[relation.attribute] = {entity.guid: entity for entity in relation.entities}
            stored[relation.attribute] = sections[relation.attribute]
    for attribute, entities in (ends or {}).items():
        if attribute not in stored:  # the read end wins the GUID's stored place (VDR-02)
            for pair in stored.values():
                _drop_ends(pair, entities)
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


def _drop_ends(pair: dict[str, RelationEntity], entities: Sequence[StoredEntity]) -> None:
    """Drop the read ends from one stored pair, so a read end never shows as a stored one too (VDR-02)."""
    for entity in entities:
        pair.pop(entity.guid, None)


def _end_name(entity: StoredEntity) -> str | None:
    """An end's name: its ``name`` attribute, whichever type defines it, or none."""
    for key in sorted(key for key in entity.attributes if key.rsplit(".", 1)[-1] == "name"):
        value = entity.attributes[key]
        if value is not None:
            return str(value)
    return None


def _propagated(propagated: Propagations | None) -> list[ClassificationSource]:
    """One entry per propagated classification, with the entities it came from, in the listed order (VDR-05).

    The door read the sources; this groups them under their classification's type name, keeping the order the
    entity lists its instances in (CLS-02). Two instances of one type on two different sources answer one entry
    with both sources, as the legacy header counted them (DD-834). A name whose source the store no longer has
    keeps its entry with no entities: the tag is still the entity's to show, only its origin is unknown. Each
    source read with a document that has parents carries its stored trail, so a row can name where the source
    sits; one read without, or with none, carries no crumbs (VDR-12, DD-836).
    """
    entries: dict[str, dict[str, RelationEntity]] = {}
    for type_name, sources in propagated or []:
        by_guid = entries.setdefault(type_name, {})
        for entity in sources:
            crumbs = _breadcrumb(entity.app_search) if entity.app_search else []
            by_guid[entity.guid] = RelationEntity.model_validate(
                {
                    "guid": entity.guid,
                    "name": _end_name(entity),
                    "type_name": entity.type_name,
                    "status": entity.state,
                    **({"breadcrumb": crumbs} if crumbs else {}),
                }
            )
    return [
        ClassificationSource.model_validate({"type_name": type_name, "entities": list(by_guid.values())})
        for type_name, by_guid in entries.items()
    ]


async def read_ends(store: WriteStore, stored: StoredEntity, entity_type: EntityType) -> RelationEnds:
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


async def read_propagations(store: WriteStore, stored: StoredEntity) -> Propagations:
    """The classifications propagated onto ``stored``, each with the entities it came from (VDR-05, DD-835).

    ``stored`` lists every classification instance it carries, attached or propagated (DD-090); the ones whose
    ``entityGuid`` names another entity are the propagated ones (the same split ``search_fields`` writes into
    ``__propagatedTraitNames``). Their sources are read in one ``get_many``, the seam ``read_ends`` set: one
    entity, its own instances, one round. A classification attached to the entity itself answers nothing, and a
    source the store no longer has answers that name with no entity.
    """
    listed = stored.classification_guids or []
    found = await store.get_classifications(listed) if listed else {}
    instances: list[StoredClassification] = [
        found[guid].classification
        for guid in listed
        if guid in found and found[guid].classification.entity_guid not in (None, stored.guid)
    ]
    if not instances:
        return []
    sources = await store.get_many(list(dict.fromkeys(i.entity_guid for i in instances if i.entity_guid)))
    return [
        (instance.type_name, [sources[instance.entity_guid].entity] if instance.entity_guid in sources else [])
        for instance in instances
    ]


async def read_page_propagations(store: WriteStore, stored: Sequence[StoredEntity]) -> dict[str, Propagations]:
    """The propagated classifications of many entities at once, keyed by GUID (VDR-12, DD-836).

    A page of cards asks what ``read_propagations`` asks for one entity, and the same two reads answer it for
    the whole page: one ``get_classifications`` of every instance the page lists, and one ``get_many`` of the
    sources those instances name. The door that already has the documents in hand passes them here, so a card
    carries what the header shows (DD-836); an entity that lists no instance, or lists only its own, answers
    nothing and costs nothing beyond the one classifications read.
    """
    listed = list(dict.fromkeys(guid for entity in stored for guid in entity.classification_guids or []))
    if not listed:
        return {}
    found = await store.get_classifications(listed)
    per_entity = {
        entity.guid: [
            found[guid].classification
            for guid in entity.classification_guids or []
            if guid in found and found[guid].classification.entity_guid not in (None, entity.guid)
        ]
        for entity in stored
    }
    with_any = {guid: instances for guid, instances in per_entity.items() if instances}
    guids = list(dict.fromkeys(i.entity_guid for instances in with_any.values() for i in instances if i.entity_guid))
    read = await store.get_many(guids) if guids else {}
    return {
        guid: [
            (instance.type_name, [read[instance.entity_guid].entity] if instance.entity_guid in read else [])
            for instance in instances
        ]
        for guid, instances in with_any.items()
    }
