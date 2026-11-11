"""The tree: topic list and field trees to catalogue entities (13.1, KSC-03, KSC-07).

The tree hangs the way the legacy scanner hung it (KSC-03): the configured System, one Collection
named for the broker's cluster id, one Dataset per topic, and the field tree under each dataset.
The qualified names follow the legacy rule exactly — the component lowercased, ``&`` and ``-``
removed, whitespace runs replaced by ``-``, the parts joined by ``--`` — so a topic registered by
the legacy job is updated by this one rather than duplicated (KSC-07: a re-scan resolves by
those names).

Each entity carries a request-local temporary guid (the model's own :func:`next_internal_id`),
and the relationship ends ride ``relationshipAttributes`` through those guids: the webapp suite's
idiom, which the store resolves in one pass (EWR-11, DD-466). One bulk request then holds the
whole tree, and a re-scan of an unchanged cluster is skipped whole (EWR-08).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from aurelius_atlas_model.instance import AtlasEntity, next_internal_id

from aurelius_atlas_kafka_scanner.fields import FieldSpec

SYSTEM_TYPE = "m4i_system"
COLLECTION_TYPE = "m4i_collection"
DATASET_TYPE = "m4i_dataset"
FIELD_TYPE = "m4i_field"
"""The m4i types of the tree (1.5b's model, loaded by DD-362)."""

DELIMITER = "--"
"""The legacy qualified-name delimiter, joining the sanitized components (KSC-03)."""

ILLEGAL_CHARACTERS = re.compile("[&-]+")
"""The characters the legacy rule removes from a component: the two it lists, ``&`` and ``-``."""

WHITE_SPACE = re.compile(r"\s+")
"""Whitespace runs the legacy rule replaces with a single ``-`` (KSC-03)."""

DEFAULT_CLUSTER = "default-cluster"
"""The Collection's name when the broker answers no cluster id (KSC-03)."""


def qualified_component(name: str) -> str:
    """One qualified-name component, by the legacy rule (KSC-03).

    Lowercase first, then ``&`` and ``-`` are removed, then whitespace becomes ``-`` — that
    order, because a hyphen the whitespace rule introduces must survive the removal. It is the
    legacy ``get_qualified_name``'s order, and it is what makes ``Kafka Broker`` read
    ``kafka-broker``, as the spec's example names it.
    """
    without_illegal = ILLEGAL_CHARACTERS.sub("", name.lower())
    return WHITE_SPACE.sub("-", without_illegal)


def join_qualified(*components: str) -> str:
    """The components joined by ``--``, empty ones dropped — the legacy concatenation (KSC-03).

    Each component arrives already sanitized, or already a qualified name of deeper parts; it is
    never sanitized a second time, because the second pass would eat the delimiter's own hyphens.
    """
    return DELIMITER.join(component for component in components if component)


def default_cluster(cluster_id: str | None) -> str:
    """The Collection's name: the broker's cluster id, or the fallback (KSC-03)."""
    return cluster_id or DEFAULT_CLUSTER


@dataclass(frozen=True)
class TopicTree:
    """One topic and the field tree the read answered for it (KSC-04, KSC-05): empty fields is the field-less case."""

    topic: str
    """The topic's own name — the dataset's ``name`` attribute (KSC-03)."""

    fields: tuple[FieldSpec, ...] = ()
    """The field tree, from :mod:`~aurelius_atlas_kafka_scanner.fields`; empty when the read answered none."""


def dataset_qualified_name(system_qualified_name: str, cluster_id: str | None, topic: str) -> str:
    """The qualified name of one topic's dataset (KSC-03): ``<system>--<collection>--<topic>``."""
    collection = join_qualified(system_qualified_name, qualified_component(default_cluster(cluster_id)))
    return join_qualified(collection, qualified_component(topic))


def build_graph(*, system_name: str, cluster_id: str | None, trees: Sequence[TopicTree]) -> list[AtlasEntity]:
    """The whole scan's entities, in one list for one bulk request (KSC-03, KSC-07).

    The System holds the Collection; the Collection holds every dataset; each dataset holds its
    fields; a nested field holds its ``parentField`` end toward its parent. Every end rides
    ``relationshipAttributes`` through request-local temp guids (DD-466); every entity resolves
    on re-scan by its unique qualified name (EWR-11), so the same scan twice updates in place and
    skips the unchanged tree whole (KSC-07, EWR-08).

    Args:
        system_name: The System entity's name (KSC-03's ``SYSTEM_NAME``).
        cluster_id: The broker's cluster id, or ``None`` for the fallback name.
        trees: One :class:`TopicTree` per topic to register, in scan order.

    Returns:
        The entities: System, Collection, one Dataset per topic, then each topic's field tree
        parents before children. Empty trees hold no fields and still get a dataset (KSC-05).
    """
    system_guid = next_internal_id()
    collection_guid = next_internal_id()
    system_qualified = qualified_component(system_name)
    cluster = default_cluster(cluster_id)
    collection_qualified = join_qualified(system_qualified, qualified_component(cluster))

    dataset_guids: list[str] = []
    datasets: list[AtlasEntity] = []
    fields: list[AtlasEntity] = []
    for tree in trees:
        dataset_guid = next_internal_id()
        dataset_guids.append(dataset_guid)
        dataset_qualified = join_qualified(collection_qualified, qualified_component(tree.topic))
        field_guids: list[dict[str, str]] = []
        for spec in tree.fields:
            field_guids.extend(_add_field_fields(spec, dataset_guid, dataset_qualified, None, fields))
        datasets.append(
            AtlasEntity(
                guid=dataset_guid,
                type_name=DATASET_TYPE,
                attributes={"name": tree.topic, "qualifiedName": dataset_qualified},
                relationship_attributes={
                    "collections": [{"guid": collection_guid, "typeName": COLLECTION_TYPE}],
                    "fields": field_guids,
                },
            )
        )

    collection = AtlasEntity(
        guid=collection_guid,
        type_name=COLLECTION_TYPE,
        attributes={"name": cluster, "qualifiedName": collection_qualified},
        relationship_attributes={
            "systems": [{"guid": system_guid, "typeName": SYSTEM_TYPE}],
            "datasets": [{"guid": guid, "typeName": DATASET_TYPE} for guid in dataset_guids],
        },
    )
    system = AtlasEntity(
        guid=system_guid,
        type_name=SYSTEM_TYPE,
        attributes={"name": system_name, "qualifiedName": system_qualified},
        relationship_attributes={"collections": [{"guid": collection_guid, "typeName": COLLECTION_TYPE}]},
    )
    return [system, collection, *datasets, *fields]


def _add_field_fields(
    spec: FieldSpec,
    dataset_guid: str,
    dataset_qualified: str,
    parent: tuple[str, str] | None,
    into: list[AtlasEntity],
) -> list[dict[str, str]]:
    """One field node and its subtree, appended to ``into`` parents-first (KSC-06, KSC-07).

    ``parent`` is the parent field's ``(guid, qualifiedName)`` when nested; a root field hangs
    its ``datasets`` end on the dataset alone. Returns the end-reference of every top node added,
    which the parent's or the dataset's end list carries.
    """
    guid = next_internal_id()
    qualified = join_qualified(parent[1] if parent else dataset_qualified, qualified_component(spec.name))
    ends: dict[str, list[dict[str, str]]] = {"datasets": [{"guid": dataset_guid, "typeName": DATASET_TYPE}]}
    if parent is not None:
        ends["parentField"] = [{"guid": parent[0], "typeName": FIELD_TYPE}]
    attributes: dict[str, str] = {"name": spec.name, "qualifiedName": qualified, "fieldType": spec.type_name}
    if spec.definition is not None:
        attributes["definition"] = spec.definition
    node = AtlasEntity(
        guid=guid,
        type_name=FIELD_TYPE,
        attributes=attributes,
        relationship_attributes=ends,
    )
    into.append(node)
    references = [{"guid": guid, "typeName": FIELD_TYPE}]
    for child in spec.children:
        references.extend(_add_field_fields(child, dataset_guid, dataset_qualified, (guid, qualified), into))
    return references


def entity_line(entity: AtlasEntity) -> str:
    """The dry-run's one line per entity (KSC-08): its type and its qualified name."""
    attributes = entity.attributes or {}
    return f"{entity.type_name} {attributes.get('qualifiedName', '?')}"
