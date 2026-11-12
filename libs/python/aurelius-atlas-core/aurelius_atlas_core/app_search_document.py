"""What an entity's App Search document is made of, and the mapping it is searched by (LAS-01 to LAS-06, ASD-01).

ADR 060 keeps what the original webapp's ``atlas-dev`` engine held on the entity's own document (DD-498). Its own
fields come from the entity alone; its breadcrumb and derived relations from the entities around it, which
``AppSearchIndexer`` reads. These are the pure parts the store and the indexer share: which entities have a
document, the mapped types and their parents, the own fields, the source hash a write checks (DD-499), what a
document names and is known by (DD-519), and the mapping.
"""

import hashlib
import json
from typing import Any

from aurelius_atlas_model.instance import EntityStatus

from aurelius_atlas_core.stored_entity import StoredAppSearch, StoredEntity

APP_SEARCH_FIELD = "appSearch"
"""The entity document's field holding its App Search document (DD-498)."""

SOURCE_HASH_FIELD = f"{APP_SEARCH_FIELD}.sourceHash"
"""The field of the hash the document was derived with; an entity without it has no document."""

STALE_FIELD = f"{APP_SEARCH_FIELD}.stale"
"""The field a write sets when the entity's own fields changed since the document was derived (ASU-01, DD-518)."""

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

GUID_FIELDS = ("breadcrumbguid", *(f"{field}guid" for field in RELATION_FIELDS.values()))
"""The fields a document names other entities in, by GUID: its breadcrumb and its relations (ASU-03)."""

NAME_FIELDS = ("name", "referenceablequalifiedname", "definition", "breadcrumbname", *RELATION_FIELDS.values())
"""The document's fields of names and words, mapped as keywords with a text sub-field (ASD-02)."""

KEYWORD_FIELDS = ("email", "sourcetype", "breadcrumbtype", "parentguid", *GUID_FIELDS)
"""The document's other fields, its source hash aside, mapped as keywords only (ASD-02)."""

SCORE_TYPE = "m4i_dq_score"
"""The quality scanner's score entities, one per rule and dataset (DQS-06)."""

RULE_TYPE = "m4i_data_quality"
"""The data quality rules a score scores (DQS-02)."""

QUALITY_RESULT_FIELD = "qualityResult"
"""The entity document's field of a score entity's quality result (ASQ-02, DD-528)."""

QUALITY_TOTALS_FIELD = "qualityTotals"
"""The entity document's field of its App Search document's score totals (ASQ-04, DD-529)."""

DIMENSIONS = ("accuracy", "completeness", "timeliness", "uniqueness", "validity")
"""The data quality dimensions of the score fields (LAS-12)."""

QUALITY_TEXT_FIELDS = (
    "qualityqualifiedname",
    "name",
    "expression",
    "dataqualityruledescription",
    "dataqualityruledimension",
    "fieldqualifiedname",
    "datadomainname",
)
"""A quality result's fields of names and words, mapped as keywords with a text sub-field (ASQ-03)."""

QUALITY_KEYWORD_FIELDS = ("qualityguid", "fieldguid")
QUALITY_NUMBER_FIELDS = ("businessruleid", "dqscore")

GOV_RULE_TYPE = "m4i_gov_data_quality"
"""The governance rules, each for the entity type its qualified name starts with (LAS-13, ASG-03)."""

GOVERNED_BY_FIELD = f"{APP_SEARCH_FIELD}.governedBy"
"""The field of the digest of the type's governance rules the entity was judged by (DD-535)."""

GOVERNED_FIELD = "governed"
"""The entity document's field set while the entity has governance verdicts (DD-535)."""

VERDICT_FIELDS = (
    "id",
    "qualifiedname",
    "guid",
    "qualityqualifiedname",
    "name",
    "expression",
    "dataqualitytype",
    "dataqualityruledescription",
    "dataqualityruledimension",
    "noncompliant_message",
    "usedattributes",
    "dataqualityruletypename",
    "entity_guid",
    "compliant",
    "result_id",
    "business_rule_id",
)
"""A governance verdict's fields, each a document's field of the verdicts' index (LAS-13, ASG-03, DD-534)."""

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


def governance_source(entity: StoredEntity) -> str:
    """The SHA-256 of what a governance verdict reads on the entity (ASG-04, DD-535).

    Its type, state, every attribute's value and the relationships it lists, sorted.
    """
    made_of: list[Any] = [
        entity.type_name,
        entity.state.value,
        sorted(entity.attributes.items()),
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
    """The entity, its document marked stale unless derived from its current own fields (ASU-01, DD-518), and
    without its governance marks unless judged with what its verdicts read now (DD-535).
    """  # noqa: D205 - one sentence
    document = entity.app_search
    if document is None:
        return entity
    update: dict[str, object] = {}
    if not document.stale and document.source_hash != source_hash(entity):
        update["stale"] = True
    if document.governed_source is not None and document.governed_source != governance_source(entity):
        update |= {"governed_by": None, "governed_source": None}
    return entity.model_copy(update={"app_search": document.model_copy(update=update)}) if update else entity


def ungoverned(document: StoredAppSearch | None) -> StoredAppSearch | None:
    """The document without its governance marks: what the indexer derives (DD-535)."""
    if document is None or document.governed_source is None:
        return document
    return document.model_copy(update={"governed_by": None, "governed_source": None})


def named_guids(document: StoredAppSearch | None) -> list[str]:
    """The GUIDs the document names in its breadcrumb and relations, once each (ASU-03)."""
    if document is None:
        return []
    return list(dict.fromkeys(guid for field in GUID_FIELDS for guid in getattr(document, field)))


def identity(document: StoredAppSearch | None) -> tuple[object, ...] | None:
    """What other documents know the entity by: its name, breadcrumb and relations' GUIDs (ASU-03, DD-519).

    A change of anything else, as the definition, shows on the entity's own document only.
    """
    if document is None:
        return None
    return (document.name, document.breadcrumbname, *(getattr(document, field) for field in GUID_FIELDS))


_KEYWORD = {"type": "keyword"}
_NAME = {"type": "keyword", "ignore_above": 8191, "fields": {"text": {"type": "text"}}}


def app_search_mapping() -> dict[str, Any]:
    """The mapping of the entity document's App Search document: keywords, names also as text (ASD-02); the stale
    flag a boolean (ASU-01).
    """  # noqa: D205 - one sentence
    keywords = ("sourceHash", "governedBy", "governedSource", *KEYWORD_FIELDS)
    properties = dict.fromkeys(NAME_FIELDS, _NAME) | dict.fromkeys(keywords, _KEYWORD) | {"stale": {"type": "boolean"}}
    return {"properties": properties}


_NUMBER = {"type": "double"}


def quality_result_mapping() -> dict[str, Any]:
    """The mapping of a quality result: names also as text, GUIDs as keywords, numbers as doubles (ASQ-03)."""
    return {
        "properties": dict.fromkeys(QUALITY_TEXT_FIELDS, _NAME)
        | dict.fromkeys(QUALITY_KEYWORD_FIELDS, _KEYWORD)
        | dict.fromkeys(QUALITY_NUMBER_FIELDS, _NUMBER)
    }


def quality_totals_mapping() -> dict[str, Any]:
    """The mapping of a document's score totals: each dimension's and the overall numbers, and rule GUIDs."""
    return {
        "properties": {
            name: {"properties": {"total": _NUMBER, "count": _NUMBER, "score": _NUMBER, "rules": _KEYWORD}}
            for name in (*DIMENSIONS, "overall")
        }
    }


def verdict_mapping() -> dict[str, Any]:
    """The mapping of the verdicts' index: each field a keyword with a text sub-field (ASG-05, DD-534)."""
    return {"dynamic": False, "properties": dict.fromkeys(VERDICT_FIELDS, _NAME)}
