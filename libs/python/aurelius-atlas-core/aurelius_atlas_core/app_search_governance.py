"""``GovernanceIndexer``: the governance verdicts of the entities, judged again when an entity's document or its
type's rules change (LAS-13, ASG-02 to ASG-06, DD-533 to DD-537).

A round reads every governance rule entity, reads each active one as a rule of the vocabulary or of the two
expression forms, and groups the rules by the type their qualified name names. Each type's rules have a digest of
what their verdicts check and copy. The store lists the entities whose document lacks their type's digest, and
those with verdicts no longer judged; each one's verdicts are written in place of those it had, then the entity
with its marks on the version read. One that changed in between waits for the next round (DD-535).

A rule reads a relationship attribute as the other ends of the entity's active relationships under it, and any
other name as the entity's attribute (DD-536).
"""  # noqa: D205 - one sentence

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from aurelius_atlas_model.instance import EntityStatus, RelationshipStatus
from aurelius_atlas_quality.atlas import rule_from_gov_attributes
from aurelius_atlas_quality.governance import GOV_KINDS, GovRule, evaluate_gov_entity
from aurelius_atlas_quality.rule import QualityRuleError
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_core.app_search_document import GOV_RULE_TYPE, attribute_value, document_name, governance_source
from aurelius_atlas_core.entity_documents import EntityDocuments, LinkedKind, VersionedEntity
from aurelius_atlas_core.graph_helper import collection_elements, referenced_end
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.stored_relationship import StoredRelationship

DEFAULT_BATCH_SIZE = 100
"""Entities per page."""

RULE_ATTRIBUTES = (
    "name",
    "qualifiedName",
    "expression",
    "ruleType",
    "ruleDescription",
    "qualityDimension",
    "dqcheckkind",
    "dqattribute",
    "dqanyOf",
    "compliantMessage",
    "nonCompliantMessage",
    "noncompliantMessage",
)
"""The attributes a governance rule is read from (GQ-07, ASG-02)."""


@dataclass(frozen=True)
class GovernanceRule:
    """A readable governance rule: its check, the type it is for, and the fields each of its verdicts copies."""

    check: GovRule
    type_name: str
    fields: Mapping[str, Any]


def governance_rule(entity: StoredEntity) -> GovernanceRule | None:
    """The rule an active rule entity reads as; none for an inactive or unread one, or one naming no type (ASG-02,
    ASG-03).
    """  # noqa: D205 - one sentence
    if (
        entity.type_name != GOV_RULE_TYPE
        or entity.state is not EntityStatus.ACTIVE
        or attribute_value(entity, "active") is False
    ):
        return None
    qualified_name = attribute_value(entity, "qualifiedName")
    type_name, separator, _ = str(qualified_name or "").partition("--")
    if not (type_name and separator):
        return None
    try:
        check = rule_from_gov_attributes(
            {"guid": entity.guid} | {name: attribute_value(entity, name) for name in RULE_ATTRIBUTES}
        )
    except QualityRuleError:
        return None
    fields = {
        "guid": entity.guid,
        "qualityqualifiedname": qualified_name,
        "name": document_name(entity) or "",
        "expression": attribute_value(entity, "expression") or "",
        "dataqualitytype": attribute_value(entity, "ruleType") or "",
        "dataqualityruledescription": attribute_value(entity, "ruleDescription") or "",
        "dataqualityruledimension": attribute_value(entity, "qualityDimension") or check.dimension.value.lower(),
        "noncompliant_message": check.non_compliant_message or GOV_KINDS[check.kind].reason,
        "usedattributes": [check.attribute],
        "result_id": "0",
        "business_rule_id": "1",
    }
    return GovernanceRule(check, type_name, fields)


def rules_digest(rules: Sequence[GovernanceRule]) -> str:
    """The SHA-256 of what a type's rules check and copy: a change of either judges its entities again (DD-535)."""
    made_of = sorted(
        json.dumps(
            [dict(rule.fields), rule.check.kind.value, rule.check.attribute, list(rule.check.any_of)],
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        for rule in rules
    )
    return hashlib.sha256("\n".join(made_of).encode()).hexdigest()


def _judged(entity: StoredEntity, rules: Mapping[str, Sequence[GovernanceRule]]) -> bool:
    """Whether the entity is judged: active, with a document, of a type with rules (ASG-03)."""
    return entity.state is EntityStatus.ACTIVE and entity.app_search is not None and entity.type_name in rules


class GovernanceIndexer:
    """Judges and writes the governance verdicts of ``documents``' entities (ASG-06)."""

    def __init__(
        self, documents: EntityDocuments, registry: TypeRegistry, *, batch_size: int = DEFAULT_BATCH_SIZE
    ) -> None:
        """An indexer over ``documents``, with ``registry``'s relationship attributes, ``batch_size`` at a time."""
        self._documents = documents
        self._registry = registry
        self._batch_size = batch_size

    async def run_once(self) -> int:
        """Judge page after page until none is left, or a page writes nothing; how many entities were written."""
        rules = await self.rules()
        digests = {type_name: rules_digest(found) for type_name, found in rules.items()}
        written = 0
        while True:
            page = await self._documents.to_govern(digests, self._batch_size)
            if not page:
                return written
            put = await self._write(page, rules, digests)
            written += put
            if put == 0 or len(page) < self._batch_size:
                return written

    async def rules(self) -> dict[str, list[GovernanceRule]]:
        """The readable active rules by the type they are for (ASG-02, ASG-03)."""
        by_type: dict[str, list[GovernanceRule]] = {}
        for found in await self._documents.governance_rules():
            if (rule := governance_rule(found.entity)) is not None:
                by_type.setdefault(rule.type_name, []).append(rule)
        return by_type

    async def verdicts(
        self, entities: Sequence[StoredEntity], rules: Mapping[str, Sequence[GovernanceRule]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Each entity's verdicts by GUID, one per rule of its type; none for an entity not judged (ASG-03, ASG-04)."""
        judged = [entity for entity in entities if _judged(entity, rules)]
        wanted = [guid for entity in judged for guid in entity.relationship_guids or []]
        linked = await self._documents.get_linked(LinkedKind.RELATIONSHIP, wanted) if wanted else {}
        found: dict[str, list[dict[str, Any]]] = {entity.guid: [] for entity in entities}
        for entity in judged:
            edges = [
                relationship
                for guid in entity.relationship_guids or []
                if guid in linked
                and isinstance(relationship := linked[guid][0], StoredRelationship)
                and relationship.state is RelationshipStatus.ACTIVE
            ]
            values = self._values(entity, edges, rules[entity.type_name])
            found[entity.guid] = [_verdict(rule, entity, values) for rule in rules[entity.type_name]]
        return found

    def _values(
        self, entity: StoredEntity, edges: list[StoredRelationship], rules: Sequence[GovernanceRule]
    ) -> dict[str, Any]:
        """The values the rules read: a relationship attribute's other ends, else the attribute (DD-536)."""
        entity_type = self._registry.entity_type(entity.type_name)
        relationship_attributes = entity_type.relationship_attributes if entity_type is not None else {}
        values: dict[str, Any] = {}
        for name in {name for rule in rules for name in (rule.check.attribute, *rule.check.any_of)}:
            by_relationship = relationship_attributes.get(name)
            if not by_relationship:
                values[name] = attribute_value(entity, name)
                continue
            ends = [
                {"guid": referenced_end(relationship, attribute.relationship_edge_direction, entity.guid)}
                for attribute in by_relationship.values()
                for relationship in collection_elements(entity.guid, edges, attribute)
            ]
            many = any(isinstance(attribute.attribute_type, ArrayType) for attribute in by_relationship.values())
            values[name] = ends if many else next(iter(ends), None)
        return values

    async def _write(
        self, page: list[VersionedEntity], rules: Mapping[str, Sequence[GovernanceRule]], digests: Mapping[str, str]
    ) -> int:
        """Write the page's verdicts, then each entity with its marks on the version read (DD-535)."""
        verdicts = await self.verdicts([found.entity for found in page], rules)
        await self._documents.replace_verdicts(verdicts)
        items = []
        for found in page:
            entity = found.entity
            document = entity.app_search
            judged = _judged(entity, rules)
            marks = (
                {"governed_by": digests[entity.type_name], "governed_source": governance_source(entity)}
                if judged
                else {"governed_by": None, "governed_source": None}
            )
            update: dict[str, Any] = {"governed": True if judged else None}
            if document is not None:
                update["app_search"] = document.model_copy(update=marks)
            items.append((entity.model_copy(update=update), found.version))
        results = await self._documents.write(items)
        return sum(1 for result in results if result.written)


def _verdict(rule: GovernanceRule, entity: StoredEntity, values: Mapping[str, Any]) -> dict[str, Any]:
    """The rule's verdict for the entity, as the engine's document (ASG-03)."""
    pair = f"{entity.guid}--{rule.fields['guid']}"
    compliant = evaluate_gov_entity(rule.check, values).compliant
    return {
        "id": pair,
        "qualifiedname": pair,
        **rule.fields,
        "dataqualityruletypename": entity.type_name,
        "entity_guid": entity.guid,
        "compliant": "1" if compliant else "0",
    }
