"""What an entity's App Search document is made of, and the mapping it is searched by (LAS-01 to LAS-06, ASD-01).

ADR 060 keeps what the original webapp's ``atlas-dev`` engine held on the entity's own document (DD-498). Its own
fields come from the entity alone; its breadcrumb and derived relations from the entities around it, which
``AppSearchIndexer`` reads. These are the pure parts the store and the indexer share: which entities have a
document, the mapped types and their parents, the own fields, the source hash a write checks (DD-499), and the
mapping.
"""

import hashlib
import json
from typing import Any

from aurelius_atlas_model.instance import EntityStatus

from aurelius_atlas_core.stored_entity import StoredAppSearch, StoredEntity

APP_SEARCH_FIELD = "appSearch"
"""The entity document's field holding its App Search document (DD-498)."""

SOURCE_HASH_FIELD = f"{APP_SEARCH_FIELD}.sourceHash"
"""The field of the hash the document was derived with; an entity without it has no current document."""

M4I_PREFIX = "m4i_"
"""The data dictionary's types (ADR 058) are the ones with a document."""

WITHOUT_DOCUMENT = frozenset({"m4i_source", "m4i_dq_score"})
"""The m4i types without a document: sources, as the legacy pipeline left out, and quality scores (DD-500)."""

RELATION_FIELDS = {
    "m4i_data_domain": "deriveddatadomain",
    "m4i_data_entity": "deriveddataentity",
    "m4i_data_attribute": "deriveddataattribute",
    "m4i_field": "derivedfield",
    "m4i_dataset": "deriveddataset",
    "m4i_collection": "derivedcollection",
    "m4i_system": "derivedsystem",
    "m4i_person": "derivedperson",
    "m4i_generic_process": "derivedprocess",
}
"""The mapped types and the field a relation to one of them is listed in, its GUIDs in ``<field>guid`` (LAS-05)."""

PARENTS = {
    "m4i_data_entity": ("parentEntity", "dataDomain"),
    "m4i_data_attribute": ("dataEntity",),
    "m4i_system": ("parentSystem",),
    "m4i_collection": ("systems",),
    "m4i_dataset": ("parentDataset", "collections"),
    "m4i_field": ("parentField", "datasets"),
}
"""Each mapped type's parent attributes, in the order the first parent is looked for (LAS-04)."""

TECHNICAL = frozenset({"m4i_system", "m4i_collection", "m4i_dataset", "m4i_field"})
BUSINESS = frozenset({"m4i_data_domain", "m4i_data_entity", "m4i_data_attribute"})

OWN_ATTRIBUTES = ("name", "qualifiedName", "definition", "email")
"""The attributes a document's own fields come from, by their name after the defining type (DD-437)."""


def has_document(entity: StoredEntity) -> bool:
    """Whether the entity has a document: an active one of an m4i type but sources and scores (LAS-01, DD-500)."""
    return (
        entity.state is EntityStatus.ACTIVE
        and entity.type_name.startswith(M4I_PREFIX)
        and entity.type_name not in WITHOUT_DOCUMENT
    )


def mapped(entity: StoredEntity) -> bool:
    """Whether the entity is active and of a mapped type, so has a breadcrumb and derived relations (LAS-04)."""
    return entity.state is EntityStatus.ACTIVE and entity.type_name in RELATION_FIELDS


def attribute_value(entity: StoredEntity, name: str) -> Any:  # noqa: ANN401 - an attribute's JSON value
    """The value of the entity's attribute ``name``, whichever type defines it; within one name, by sorted key."""
    for key in sorted(key for key in entity.attributes if key.rsplit(".", 1)[-1] == name):
        if entity.attributes[key] is not None:
            return entity.attributes[key]
    return None


def document_name(entity: StoredEntity) -> str | None:
    """The name a document gives the entity: its ``name``, else its qualified name (LAS-02)."""
    return attribute_value(entity, "name") or attribute_value(entity, "qualifiedName")


def source_type(type_name: str) -> str:
    """``Technical``, ``Business`` or ``""``, by the type (LAS-03)."""
    return "Technical" if type_name in TECHNICAL else "Business" if type_name in BUSINESS else ""


def source_hash(entity: StoredEntity) -> str:
    """The SHA-256 of what the document's own fields and relations are read from on the entity (ASD-03, DD-499).

    Its type, state, own attributes' values and the relationships it lists, sorted.
    """
    made_of: list[Any] = [
        entity.type_name,
        entity.state.value,
        [attribute_value(entity, name) for name in OWN_ATTRIBUTES],
        sorted(entity.relationship_guids or []),
    ]
    return hashlib.sha256(json.dumps(made_of, ensure_ascii=False, default=str).encode()).hexdigest()


def own_document(entity: StoredEntity) -> StoredAppSearch:
    """The document with the entity's own fields only: no breadcrumb, no relations (LAS-02, LAS-03)."""
    return StoredAppSearch(
        source_hash=source_hash(entity),
        name=document_name(entity),
        referenceablequalifiedname=attribute_value(entity, "qualifiedName") or entity.guid,
        definition=attribute_value(entity, "definition") or "",
        email=attribute_value(entity, "email") if entity.type_name == "m4i_person" else None,
        sourcetype=source_type(entity.type_name),
    )


def with_current_app_search(entity: StoredEntity) -> StoredEntity:
    """The entity, without its document unless that was derived from its current own fields (ASD-03, DD-499)."""
    if entity.app_search is None or entity.app_search.source_hash == source_hash(entity):
        return entity
    return entity.model_copy(update={"app_search": None})


_KEYWORD = {"type": "keyword"}
_NAME = {"type": "keyword", "ignore_above": 8191, "fields": {"text": {"type": "text"}}}


def app_search_mapping() -> dict[str, Any]:
    """The mapping of the entity document's App Search document: keywords, names also as text (ASD-02)."""
    names = ["name", "referenceablequalifiedname", "definition", "breadcrumbname", *RELATION_FIELDS.values()]
    keywords = ["sourceHash", "email", "sourcetype", "breadcrumbguid", "breadcrumbtype", "parentguid"]
    keywords += [f"{field}guid" for field in RELATION_FIELDS.values()]
    return {"properties": dict.fromkeys(names, _NAME) | dict.fromkeys(keywords, _KEYWORD)}
