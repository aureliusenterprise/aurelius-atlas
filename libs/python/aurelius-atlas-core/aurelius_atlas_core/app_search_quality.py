"""``QualityIndexer``: the quality results of the score entities and the score totals of the App Search documents,
derived again in full each round (LAS-11, LAS-12, ASQ-02, ASQ-04, ASQ-05, ASQ-07, DD-528, DD-529).

A round lists every score and every entity holding a result or totals. It reads the scores' rules, the rules'
fields and the documents of those fields and their data attributes, and derives each score's result and each
document's totals from them. Each entity whose result or totals differ from what it holds is read again and
written on that version; one that changed in between waits for the next round.

A field's own totals are its results' (ASQ-04); a data attribute's are its fields'; each field and data attribute
adds its own to every entity of its breadcrumb (ASQ-05).
"""  # noqa: D205 - one sentence

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from aurelius_atlas_model.instance import EntityStatus, RelationshipStatus

from aurelius_atlas_core.app_search_document import (
    DIMENSIONS,
    RULE_TYPE,
    attribute_value,
    document_name,
    has_document,
)
from aurelius_atlas_core.entity_documents import EntityDocuments, LinkedKind, VersionedEntity
from aurelius_atlas_core.graph_helper import other_end
from aurelius_atlas_core.stored_entity import (
    StoredDimensionTotals,
    StoredEntity,
    StoredQualityResult,
    StoredQualityTotals,
)
from aurelius_atlas_core.stored_relationship import StoredRelationship

DEFAULT_BATCH_SIZE = 100
"""Entities per write."""

SCORED_VERDICTS = frozenset({"PASS", "FAIL"})
"""The verdicts of a score; an ERROR has none (DQS-07, DQS-08, DD-532)."""

FIELD_TYPE = "m4i_field"
DOMAIN_TYPE = "m4i_data_domain"


@dataclass
class _Sums:
    """One dimension's sum, count and, on a field, rule GUIDs, while the totals add up."""

    total: float = 0.0
    count: float = 0.0
    rules: list[str] = field(default_factory=list)

    def add(self, other: _Sums) -> None:
        self.total += other.total
        self.count += other.count


def _active_rule(entity: StoredEntity | None) -> bool:
    """Whether the entity is an active rule: not deleted, ``active`` not ``false`` (DD-532)."""
    return (
        entity is not None
        and entity.type_name == RULE_TYPE
        and entity.state is EntityStatus.ACTIVE
        and attribute_value(entity, "active") is not False
    )


def _scored(score: StoredEntity) -> bool:
    """Whether the score entity scores a rule: a verdict of a score, a number, a rule (ASQ-02, DD-532)."""
    value = attribute_value(score, "score")
    return (
        attribute_value(score, "verdict") in SCORED_VERDICTS
        and isinstance(value, int | float | Decimal)
        and not isinstance(value, bool)
        and isinstance(attribute_value(score, "ruleGuid"), str)
    )


class _Reads:
    """The entities and relationships a round reads, each once."""

    def __init__(self, documents: EntityDocuments) -> None:
        self._documents = documents
        self._entities: dict[str, StoredEntity | None] = {}

    async def load(self, guids: Iterable[str]) -> None:
        missing = [guid for guid in dict.fromkeys(guids) if guid not in self._entities]
        if missing:
            found = await self._documents.get(missing)
            self._entities.update((guid, found[guid].entity if guid in found else None) for guid in missing)

    def entity(self, guid: str) -> StoredEntity | None:
        return self._entities.get(guid)

    async def fields(self, rules: Sequence[StoredEntity]) -> dict[str, list[StoredEntity]]:
        """Each rule's active fields at the other end of its active relationships, in the rule's order."""
        wanted = [guid for rule in rules for guid in rule.relationship_guids or []]
        linked = await self._documents.get_linked(LinkedKind.RELATIONSHIP, wanted) if wanted else {}
        ends: dict[str, list[str]] = {}
        for rule in rules:
            ends[rule.guid] = [
                other_end(relationship, rule.guid)
                for guid in rule.relationship_guids or []
                if guid in linked
                and isinstance(relationship := linked[guid][0], StoredRelationship)
                and relationship.state is RelationshipStatus.ACTIVE
            ]
        await self.load(guid for guids in ends.values() for guid in guids)
        return {
            rule: [
                entity
                for guid in dict.fromkeys(guids)
                if (entity := self.entity(guid)) is not None
                and entity.type_name == FIELD_TYPE
                and entity.state is EntityStatus.ACTIVE
            ]
            for rule, guids in ends.items()
        }


class QualityIndexer:
    """Derives and writes the quality results and score totals of ``documents``' entities (ASQ-07)."""

    def __init__(self, documents: EntityDocuments, *, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
        """An indexer over ``documents``, writing ``batch_size`` entities at a time."""
        self._documents = documents
        self._batch_size = batch_size

    async def run_once(self) -> int:
        """Derive every result and total, and write the entities whose differ; how many were written."""
        scores = [found.entity for found in await self._documents.scores()]
        holders = {found.entity.guid: found.entity for found in await self._documents.quality_holders()}
        reads = _Reads(self._documents)
        results = await self._results(reads, scores)
        totals = await self._totals(reads, results.values())
        wanted: dict[str, dict[str, object]] = {}
        for score in scores:
            if score.quality_result != results.get(score.guid):
                wanted.setdefault(score.guid, {})["quality_result"] = results.get(score.guid)
        for guid, holder in holders.items():
            if holder.quality_result is not None and guid not in results:
                wanted.setdefault(guid, {})["quality_result"] = None
            if holder.quality_totals is not None and guid not in totals:
                wanted.setdefault(guid, {})["quality_totals"] = None
        for guid, total in totals.items():
            held = holders.get(guid)
            if (held.quality_totals if held is not None else None) != total:
                wanted.setdefault(guid, {})["quality_totals"] = total
        return await self._write(wanted)

    async def results(self, scores: Sequence[StoredEntity]) -> dict[str, StoredQualityResult]:
        """The scores' quality results by the score's GUID, as the store holds the rest now (ASQ-02)."""
        return await self._results(_Reads(self._documents), scores)

    async def _results(self, reads: _Reads, scores: Sequence[StoredEntity]) -> dict[str, StoredQualityResult]:
        scored = [score for score in scores if score.state is EntityStatus.ACTIVE and _scored(score)]
        await reads.load(str(attribute_value(score, "ruleGuid")) for score in scored)
        rules = {
            rule.guid: rule
            for score in scored
            if _active_rule(rule := reads.entity(str(attribute_value(score, "ruleGuid")))) and rule is not None
        }
        fields = await reads.fields(list(rules.values()))
        await reads.load(
            guid
            for found in fields.values()
            for entity in found
            for guid in (entity.app_search.deriveddataattributeguid if entity.app_search is not None else [])
        )
        results = {}
        for score in scored:
            rule = rules.get(str(attribute_value(score, "ruleGuid")))
            dataset = attribute_value(score, "datasetGuid")
            if rule is None:
                continue
            held = [
                entity
                for entity in fields[rule.guid]
                if entity.app_search is not None and dataset in entity.app_search.deriveddatasetguid
            ]
            if held:
                results[score.guid] = _result(reads, score, rule, held)
        return results

    async def _totals(self, reads: _Reads, results: Iterable[StoredQualityResult]) -> dict[str, StoredQualityTotals]:
        """Each document's totals that a result reaches: the fields', their data attributes', their breadcrumbs'
        (ASQ-04, ASQ-05).
        """  # noqa: D205 - one sentence
        own = _field_sums(results)
        await reads.load(own)
        for guid in list(own):
            for attribute in _document_guids(reads.entity(guid), "deriveddataattributeguid"):
                _add_all(own.setdefault(attribute, {}), own[guid])
        await reads.load(own)
        added = {
            guid: {dimension: _Sums(sums.total, sums.count, list(sums.rules)) for dimension, sums in dimensions.items()}
            for guid, dimensions in own.items()
        }
        for guid, dimensions in own.items():
            for above in _document_guids(reads.entity(guid), "breadcrumbguid"):
                _add_all(added.setdefault(above, {}), dimensions)
        return {guid: _stored_totals(dimensions) for guid, dimensions in added.items()}

    async def _write(self, wanted: dict[str, dict[str, object]]) -> int:
        """Write each entity with its new result or totals on the version read now, ``batch_size`` at a time."""
        guids = list(wanted)
        written = 0
        for start in range(0, len(guids), self._batch_size):
            found = await self._documents.get(guids[start : start + self._batch_size])
            items = [
                (versioned.entity.model_copy(update=update), versioned.version)
                for guid, versioned in found.items()
                if _writable(versioned, update := wanted[guid])
            ]
            if items:
                results = await self._documents.write(items)
                written += sum(1 for result in results if result.written)
        return written


def _field_sums(results: Iterable[StoredQualityResult]) -> dict[str, dict[str, _Sums]]:
    """Each field's own sums per dimension: its results' scores, their count, the rules once each (ASQ-04)."""
    own: dict[str, dict[str, _Sums]] = {}
    for result in results:
        dimension = result.dataqualityruledimension.lower()
        if dimension not in DIMENSIONS:
            continue
        for guid in result.fieldguid:
            sums = own.setdefault(guid, {}).setdefault(dimension, _Sums())
            sums.total += result.dqscore
            sums.count += 1
            if result.qualityguid not in sums.rules:
                sums.rules.append(result.qualityguid)
    return own


def _add_all(into: dict[str, _Sums], sums: dict[str, _Sums]) -> None:
    """Add each dimension's sum and count, not its rules (ASQ-05)."""
    for dimension, added in sums.items():
        into.setdefault(dimension, _Sums()).add(added)


def _document_guids(entity: StoredEntity | None, name: str) -> list[str]:
    """The GUIDs the entity's App Search document lists in the field ``name``, none without one."""
    if entity is None or entity.app_search is None:
        return []
    return list(getattr(entity.app_search, name))


def _writable(versioned: VersionedEntity, update: dict[str, object]) -> bool:
    """Whether the entity read now still differs, and may hold totals: one with a document (ASQ-04)."""
    entity = versioned.entity
    if update.get("quality_totals") is not None and not has_document(entity):
        return False
    return any(getattr(entity, name) != value for name, value in update.items())


def _result(reads: _Reads, score: StoredEntity, rule: StoredEntity, fields: list[StoredEntity]) -> StoredQualityResult:
    """The score's result: the rule's fields, the fields in the dataset, the data domain above them (ASQ-02)."""
    business_id = attribute_value(rule, "id")
    return StoredQualityResult(
        qualityguid=rule.guid,
        qualityqualifiedname=attribute_value(rule, "qualifiedName") or "",
        name=document_name(rule) or "",
        expression=attribute_value(rule, "expression") or "",
        dataqualityruledescription=attribute_value(rule, "ruleDescription") or "",
        dataqualityruledimension=attribute_value(rule, "qualityDimension") or "",
        businessruleid=float(business_id)
        if isinstance(business_id, int | float | Decimal) and not isinstance(business_id, bool)
        else 0.0,
        fieldguid=[entity.guid for entity in fields],
        fieldqualifiedname=[attribute_value(entity, "qualifiedName") or "" for entity in fields],
        datadomainname=_domain_name(reads, fields),
        dqscore=float(attribute_value(score, "score")),
    )


def _domain_name(reads: _Reads, fields: list[StoredEntity]) -> str:
    """The first data domain in the breadcrumbs of the fields' data attributes, else empty (ASQ-02)."""
    for entity in fields:
        for guid in entity.app_search.deriveddataattributeguid if entity.app_search is not None else []:
            attribute = reads.entity(guid)
            document = attribute.app_search if attribute is not None else None
            if document is None:
                continue
            for name, type_name in zip(document.breadcrumbname, document.breadcrumbtype, strict=False):
                if type_name == DOMAIN_TYPE and name:
                    return name
    return ""


def _stored_totals(dimensions: dict[str, _Sums]) -> StoredQualityTotals:
    """The totals as stored: each dimension's score its sum over its count, the overall the five's (ASQ-05)."""
    stored: dict[str, StoredDimensionTotals] = {}
    overall = _Sums()
    for dimension in DIMENSIONS:
        sums = dimensions.get(dimension, _Sums())
        overall.add(sums)
        stored[dimension] = _dimension(sums)
    stored["overall"] = _dimension(overall)
    return StoredQualityTotals.model_validate(stored)


def _dimension(sums: _Sums) -> StoredDimensionTotals:
    return StoredDimensionTotals(
        total=sums.total,
        count=sums.count,
        score=sums.total / sums.count if sums.count else 0.0,
        rules=sums.rules,
    )
