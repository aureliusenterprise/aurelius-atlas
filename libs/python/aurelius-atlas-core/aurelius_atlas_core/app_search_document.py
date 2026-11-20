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

from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.instance import EntityStatus
from pydantic import ConfigDict, Field

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

ROLE_FIELDS = {
    "domainLead": "deriveddomainlead",
    "businessOwner": "deriveddataowner",
    "steward": "deriveddatasteward",
}
"""The role relationship attributes and the field their ends are listed in, GUIDs in ``<field>guid`` (ASD-06).

The legacy mapping declared the three GUID fields and its pipeline never filled them; the name lists are
ours, because the door answers a card's people from the document alone (DD-626, DD-627).
"""

ROLE_NAME_FIELDS = tuple(ROLE_FIELDS.values())
"""The document's role name lists, mapped as keywords with a text sub-field like the other names (ASD-06)."""

ROLE_GUID_FIELDS = tuple(f"{field}guid" for field in ROLE_FIELDS.values())
"""The document's role GUID lists, mapped as keywords like the other relation GUIDs (ASD-06)."""

DERIVATION_VERSION = 3
"""The derivation rules an index round writes documents under: 16.5f's, with the role fields and ``hasparent``.

Version 1 is 14.2's hash, which carries no version and no role fields; version 2 is 16.5f's, before the
parent flag (RPS-06, DD-758); a document of another version than this one is what the round derives again.
"""

DERIVATION_VERSION_FIELD = f"{APP_SEARCH_FIELD}.derivationVersion"
"""The field of the derivation version the document was made under, the round's staleness query (ASD-07)."""

PARENTS = {
    "m4i_data_entity": ("parentEntity", "dataDomain"),
    "m4i_data_attribute": ("dataEntity",),
    "m4i_system": ("parentSystem",),
    "m4i_collection": ("systems",),
    "m4i_dataset": ("parentDataset", "collections"),
    "m4i_field": ("parentField", "datasets"),
}
"""Each mapped type's parent attributes, in the order the first parent is looked for (LAS-04)."""

GUID_FIELDS = (
    "breadcrumbguid",
    *(f"{field}guid" for field in RELATION_FIELDS.values()),
    *ROLE_GUID_FIELDS,
)
"""The fields a document names other entities in, by GUID: its breadcrumb, its relations and its role ends.

What a write looks a changed entity up in, and what an identity is made of (ASU-03, DD-519); the role GUID
fields are part of it since 16.5f, so a role end's name stays fresh in every document naming it (ASD-06).
"""

NAME_FIELDS = ("name", "referenceablequalifiedname", "definition", "breadcrumbname", *RELATION_FIELDS.values())
"""The fields ``atlas-dev``'s engine reads as names, and the index maps as keywords with a text sub-field (ASD-02).

The role name lists are ours, not ``atlas-dev``'s: the engine keeps its legacy field set and reads the role
GUIDs as constants until 16.6; the index maps the role lists through ``MAPPING_NAME_FIELDS`` (DD-626).
"""

MAPPING_NAME_FIELDS = (*NAME_FIELDS, *ROLE_NAME_FIELDS)
"""Every name list the entity index maps, the role lists included (ASD-02, ASD-06)."""

KEYWORD_FIELDS = (
    "email",
    "sourcetype",
    "breadcrumbtype",
    "parentguid",
    "breadcrumbguid",
    *(f"{field}guid" for field in RELATION_FIELDS.values()),
)
"""The fields ``atlas-dev``'s engine reads as stored keywords, its source hash aside (ASD-02).

The role GUID lists are ours, not ``atlas-dev``'s: the engine keeps its legacy field set and answers the
role GUIDs as constants until 16.6; the index maps them through ``MAPPING_KEYWORD_FIELDS`` (LAS-07, DD-626).
"""

MAPPING_KEYWORD_FIELDS = (*KEYWORD_FIELDS, *ROLE_GUID_FIELDS)
"""Every keyword field the entity index maps, the role GUID lists included (ASD-02, ASD-06)."""

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


class StoredVerdict(AtlasModel):
    """One document of the verdicts' index: a rule's judgement of one entity (ASG-03, DD-534).

    The legacy engine's field names, underscores and all, so the index's mapping and the webapp's reads stay
    those of ``atlas-dev-gov-quality``; the model's own names are the wire names (DD-560). ``compliant`` is
    ``"1"`` or ``"0"``, as the legacy documents hold it. The fields a verdict copies from its rule default to
    what a rule without them answers, so a verdict names the rule, the entity and the judgement at least.
    """

    model_config = ConfigDict(alias_generator=None)

    id: str
    entity_guid: str
    qualifiedname: str = ""
    guid: str = ""
    name: str = ""
    compliant: str = ""
    qualityqualifiedname: str = ""
    expression: str = ""
    dataqualitytype: str = ""
    dataqualityruledescription: str = ""
    dataqualityruledimension: str = ""
    noncompliant_message: str = ""
    usedattributes: list[str] = Field(default_factory=list)
    dataqualityruletypename: str = ""
    result_id: str = "0"
    business_rule_id: str = "1"


VERDICT_FIELDS = tuple(StoredVerdict.model_fields)
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


def awaits_document(entity: StoredEntity) -> bool:
    """Whether the indexer has a document to derive for the entity: one it should have and lacks, a stale one,
    or one derived under older rules (ASD-04, ASD-07, ASU-02, EMC-04).
    """  # noqa: D205 - one sentence
    document = entity.app_search
    if document is None:
        return has_document(entity)
    return document.stale or document.derivation_version != DERIVATION_VERSION


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

    Its type, state, own attributes' values, the relationships it lists, sorted, and the derivation version,
    so a document derived under older rules is stale once the version moves (ASD-07, DD-628).
    """
    made_of: list[Any] = [
        entity.type_name,
        entity.state.value,
        [attribute_value(entity, name) for name in OWN_ATTRIBUTES],
        sorted(entity.relationship_guids or []),
        DERIVATION_VERSION,
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
        derivation_version=DERIVATION_VERSION,
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
    keywords = ("sourceHash", "governedBy", "governedSource", *MAPPING_KEYWORD_FIELDS)
    properties = (
        dict.fromkeys(MAPPING_NAME_FIELDS, _NAME)
        | dict.fromkeys(keywords, _KEYWORD)
        | {
            "stale": {"type": "boolean"},
            "hasparent": {"type": "boolean"},
            "derivationVersion": {"type": "integer"},
        }
    )
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
