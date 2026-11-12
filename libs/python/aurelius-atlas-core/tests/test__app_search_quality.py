"""The quality results of the score entities and the score totals of the App Search documents (LAS-11, LAS-12,
ASQ-02, ASQ-04, ASQ-05, ASQ-07, DD-528, DD-529, DD-532), on the fake client.

Each test writes a small catalogue through the store, indexes its documents, writes the scores the quality scanner
would, and runs the quality round. The sample catalogue, with a score for each legacy result, rolls up as
``atlas-dev`` did.
"""  # noqa: D205 - one sentence

import asyncio
import json
from collections import Counter
from typing import Any

import pytest
from aurelius_atlas_core.app_search_document import DIMENSIONS, quality_result_mapping, quality_totals_mapping
from aurelius_atlas_core.app_search_engine import FIELDS
from aurelius_atlas_core.app_search_indexer import AppSearchIndexer
from aurelius_atlas_core.app_search_quality import QualityIndexer
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR, M4I_MODELS_DIR, ModelLoader
from aurelius_atlas_core.stored_entity import StoredEntity, StoredQualityResult, StoredQualityTotals
from aurelius_atlas_core.testing.memory import MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, AtlasObjectId
from aurelius_atlas_store_es.testing.fake import FakeClient
from aurelius_atlas_typesystem.registry import TypeRegistry
from test__app_search_engine import FIXTURES, indexed_sample, legacy

Q = "aurelius_atlas_core.app_search_quality.QualityIndexer"
D = "aurelius_atlas_core.entity_documents.ElasticsearchEntityDocuments"

_LOADED: dict[str, TypedefStore] = {}


async def m4i_types() -> TypedefStore:
    """A typedef store with Atlas's and the data dictionary's models (ADR 058), loaded once for the module."""
    if "m4i" not in _LOADED:
        types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
        await types.load()
        for models_dir in (BUILTIN_MODELS_DIR, M4I_MODELS_DIR):
            assert (await ModelLoader(types).load(models_dir)).failed_files == []
        _LOADED["m4i"] = types
    return _LOADED["m4i"]


def m4i(type_name: str, key: str, values: dict[str, Any] | None = None, **relations: list[str]) -> AtlasEntity:
    """An entity named after ``key`` with ``values``, and relationship attributes naming others of the request."""
    return AtlasEntity(
        type_name=type_name,
        guid=f"-{key}",
        attributes={"qualifiedName": key, "name": key.upper()} | (values or {}),
        relationship_attributes={
            name: [AtlasObjectId(guid=f"-{other}") for other in others] for name, others in relations.items()
        },
    )


def rule(key: str, dimension: str, *fields: str, **attributes: Any) -> AtlasEntity:  # noqa: ANN401
    """An active data quality rule over ``fields``, of ``dimension``, its expression and description after its key."""
    defaults = {
        "qualityDimension": dimension,
        "expression": f"check({key})",
        "ruleDescription": f"About {key}",
        "id": 1,
        "active": True,
    }
    return m4i("m4i_data_quality", key, defaults | attributes, fields=list(fields))


def catalogue_entities() -> list[AtlasEntity]:
    """A domain, entity and attribute over field ``f``; dataset ``s`` holds ``f`` and ``g``, dataset ``t`` ``h``.

    Rule ``r`` (accuracy) covers ``f``, ``g`` and ``h``; rule ``p`` (validity) covers ``f``.
    """
    return [
        m4i("m4i_data_domain", "d"),
        m4i("m4i_data_entity", "e", dataDomain=["d"]),
        m4i("m4i_data_attribute", "a", dataEntity=["e"]),
        m4i("m4i_dataset", "s"),
        m4i("m4i_dataset", "t"),
        m4i("m4i_field", "f", datasets=["s"], attributes=["a"]),
        m4i("m4i_field", "g", datasets=["s"]),
        m4i("m4i_field", "h", datasets=["t"]),
        rule("r", "Accuracy", "f", "g", "h", id=7),
        rule("p", "Validity", "f"),
    ]


class Catalogue:
    """A small catalogue written through the store on the fake client, its documents indexed, each known by key."""

    def __init__(self, types: TypedefStore) -> None:
        self.documents = ElasticsearchEntityDocuments(FakeClient())  # type: ignore[arg-type]
        self.store = EntityStore(types.registry, self.documents)
        self.indexer = AppSearchIndexer(self.documents, types.registry)
        self.quality = QualityIndexer(self.documents, batch_size=2)
        self.writer = EntityWriter(self.store, user="u")
        self.guids: dict[str, str] = {}

    @classmethod
    async def indexed(cls, *entities: AtlasEntity) -> Catalogue:
        """The entities, created in one request, and a round of the document indexer."""
        catalogue = cls(await m4i_types())
        await catalogue.store.prepare()
        await catalogue.create(*entities)
        return catalogue

    async def create(self, *entities: AtlasEntity) -> None:
        """Create or update the entities, then a round of the document indexer."""
        response = await self.writer.create_or_update(AtlasEntitiesWithExtInfo(entities=list(entities)))
        self.guids |= {key.removeprefix("-"): guid for key, guid in (response.guid_assignments or {}).items()}
        await self.indexer.run_once()

    def score(self, key: str, rule_key: str | None, dataset: str, value: float, verdict: str = "PASS") -> AtlasEntity:
        """The scanner's score of ``rule_key`` over ``dataset``; no rule is a dataset's summary."""
        attributes = {
            "scoreKey": key,
            "verdict": verdict,
            "score": value,
            "ruleGuid": self.guids[rule_key] if rule_key is not None else None,
            "datasetGuid": self.guids[dataset],
        }
        return AtlasEntity(type_name="m4i_dq_score", guid=f"-{key}", attributes={"qualifiedName": key} | attributes)

    async def entity(self, key: str) -> StoredEntity:
        """The key's stored entity."""
        guid = self.guids[key]
        return (await self.documents.get([guid]))[guid].entity

    async def result(self, key: str) -> StoredQualityResult | None:
        """The key's stored quality result."""
        return (await self.entity(key)).quality_result

    async def totals(self, key: str) -> StoredQualityTotals | None:
        """The key's stored score totals."""
        return (await self.entity(key)).quality_totals

    async def score_fields(self, key: str) -> dict[str, Any]:
        """The key's ``atlas-dev`` score fields, as the engine reads them from its totals."""
        return _score_fields(await self.entity(key))

    async def holders(self) -> set[str]:
        """The keys of the entities holding a result or totals."""
        by_guid = {guid: key for key, guid in self.guids.items()}
        return {by_guid[found.entity.guid] for found in await self.documents.quality_holders()}


def _score_fields(entity: StoredEntity) -> dict[str, Any]:
    """The entity's ``atlas-dev`` score fields, as the engine reads them from its source."""
    totals = entity.quality_totals.model_dump() if entity.quality_totals is not None else None
    source = {"guid": entity.guid} | ({"qualityTotals": totals} if totals is not None else {})
    return {name: field.value(source) for name, field in FIELDS.items() if name.startswith(("dqscore", "qualityguid"))}


@pytest.mark.covers(f"{Q}.run_once", rules=["ASQ-02", "LAS-11"])
@pytest.mark.covers(f"{Q}.results", rules=["ASQ-02"])
@pytest.mark.covers(f"{D}.scores", rules=["ASQ-02"])
async def test__a_result_reads_its_score_rule_the_rule_s_fields_in_the_dataset_and_their_documents() -> None:
    """Rule ``r`` over dataset ``s``: its fields ``f`` and ``g`` there, not ``h``; the domain above ``f``."""
    catalogue = await Catalogue.indexed(*catalogue_entities())
    await catalogue.create(catalogue.score("rs", "r", "s", 0.75))

    written = await catalogue.quality.run_once()

    guids = catalogue.guids
    expected = StoredQualityResult(
        qualityguid=guids["r"],
        qualityqualifiedname="r",
        name="R",
        expression="check(r)",
        dataqualityruledescription="About r",
        dataqualityruledimension="Accuracy",
        businessruleid=7.0,
        fieldguid=[guids["f"], guids["g"]],
        fieldqualifiedname=["f", "g"],
        datadomainname="D",
        dqscore=0.75,
    )
    assert await catalogue.result("rs") == expected
    assert await catalogue.quality.results([await catalogue.entity("rs")]) == {guids["rs"]: expected}
    assert [found.entity.guid for found in await catalogue.documents.scores()] == [guids["rs"]]
    assert written == len(await catalogue.holders())


@pytest.mark.covers(f"{Q}.results", rules=["ASQ-02"])
async def test__a_rule_without_a_name_id_text_or_domain_answers_the_defaults() -> None:
    """A stored rule without ``name``, ``id``, expression or description, over a field without a data attribute:
    its qualified name, 0, empty texts, no domain.
    """  # noqa: D205 - one sentence
    catalogue = await Catalogue.indexed(
        m4i("m4i_dataset", "s"),
        m4i("m4i_field", "g", datasets=["s"]),
        rule("r", "Uniqueness", "g", expression=None, ruleDescription=None),
    )
    found = (await catalogue.documents.get([catalogue.guids["r"]]))[catalogue.guids["r"]]
    bare = {key: None if key.endswith((".name", ".id")) else value for key, value in found.entity.attributes.items()}
    await catalogue.documents.write([(found.entity.model_copy(update={"attributes": bare}), found.version)])
    await catalogue.create(catalogue.score("rs", "r", "s", 1.0))

    await catalogue.quality.run_once()

    result = await catalogue.result("rs")
    assert result is not None
    assert (result.name, result.businessruleid, result.datadomainname) == ("r", 0.0, "")
    assert (result.expression, result.dataqualityruledescription) == ("", "")


@pytest.mark.covers(f"{Q}.run_once", rules=["ASQ-02", "DD-532"])
async def test__no_result_for_an_error_a_summary_an_inactive_or_deleted_rule_or_a_dataset_without_its_fields() -> None:
    """Only the score of an active rule over a dataset holding one of its fields has a result."""
    catalogue = await Catalogue.indexed(
        *catalogue_entities(),
        rule("off", "Accuracy", "f", active=False),
        rule("gone", "Accuracy", "f"),
        m4i("m4i_dataset", "u"),
    )
    await catalogue.create(
        catalogue.score("kept", "r", "s", 0.5),
        catalogue.score("error", "r", "t", 0.0, verdict="ERROR"),
        catalogue.score("summary", None, "s", 0.5),
        catalogue.score("inactive", "off", "s", 0.5),
        catalogue.score("deleted", "gone", "s", 0.5),
        catalogue.score("elsewhere", "p", "u", 0.5),
        catalogue.score("dropped", "r", "t", 0.5),
    )
    await catalogue.writer.delete_by_id(catalogue.guids["gone"])
    await catalogue.writer.delete_by_id(catalogue.guids["dropped"])

    await catalogue.quality.run_once()

    with_result = {key for key in catalogue.guids if (await catalogue.entity(key)).quality_result is not None}
    assert with_result == {"kept"}


@pytest.mark.covers(f"{Q}.run_once", rules=["ASQ-04", "ASQ-05", "LAS-12"])
async def test__a_field_s_totals_reach_its_data_attribute_and_both_breadcrumbs() -> None:
    """``f`` holds both rules; ``g`` the accuracy one; ``a``, ``e``, ``d`` and ``s`` add them up."""
    catalogue = await Catalogue.indexed(*catalogue_entities())
    await catalogue.create(catalogue.score("rs", "r", "s", 0.5), catalogue.score("ps", "p", "s", 1.0))

    await catalogue.quality.run_once()

    field = await catalogue.score_fields("f")
    assert (field["dqscoresum_accuracy"], field["dqscorecnt_accuracy"], field["dqscore_accuracy"]) == (0.5, 1, 0.5)
    assert (field["dqscoresum_validity"], field["dqscorecnt_validity"], field["dqscore_validity"]) == (1.0, 1, 1.0)
    assert (field["dqscoresum_overall"], field["dqscorecnt_overall"], field["dqscore_overall"]) == (1.5, 2, 0.75)
    assert field["qualityguid_accuracy"] == [catalogue.guids["r"]]
    assert field["qualityguid_validity"] == [catalogue.guids["p"]]
    for key in ("a", "e", "d"):
        above = await catalogue.score_fields(key)
        assert (above["dqscoresum_overall"], above["dqscorecnt_overall"]) == (1.5, 2), key
        assert above["qualityguid_accuracy"] == [], key
    dataset = await catalogue.score_fields("s")
    assert (dataset["dqscoresum_accuracy"], dataset["dqscorecnt_accuracy"], dataset["dqscore_accuracy"]) == (1, 2, 0.5)
    assert (dataset["dqscoresum_overall"], dataset["dqscorecnt_overall"]) == (2.0, 3)
    assert await catalogue.holders() == {"rs", "ps", "f", "g", "a", "e", "d", "s"}


@pytest.mark.covers(f"{Q}.run_once", rules=["ASQ-04", "DD-532"])
async def test__a_result_of_another_dimension_is_answered_and_adds_to_no_total() -> None:
    """A rule of dimension ``Consistency``: its result, and no totals anywhere."""
    catalogue = await Catalogue.indexed(*catalogue_entities(), rule("c", "Consistency", "g"))
    await catalogue.create(catalogue.score("cs", "c", "s", 0.5))

    await catalogue.quality.run_once()

    result = await catalogue.result("cs")
    assert result is not None
    assert result.dataqualityruledimension == "Consistency"
    assert await catalogue.holders() == {"cs"}
    assert all(not value for value in (await catalogue.score_fields("g")).values())


@pytest.mark.covers(f"{Q}.run_once", rules=["ASQ-07", "DD-529"])
@pytest.mark.covers(f"{D}.quality_holders", rules=["ASQ-07"])
async def test__a_second_round_writes_nothing_and_a_change_shows_after_the_next() -> None:
    """A changed score, a deleted one, and a field moved to another dataset, each corrected by one round."""
    catalogue = await Catalogue.indexed(*catalogue_entities())
    await catalogue.create(catalogue.score("rs", "r", "s", 0.5), catalogue.score("ps", "p", "s", 1.0))
    assert await catalogue.quality.run_once() > 0

    assert await catalogue.quality.run_once() == 0

    await catalogue.writer.update_attribute_by_guid(catalogue.guids["rs"], "score", 0.25)
    assert await catalogue.quality.run_once() > 0
    assert (await catalogue.score_fields("g"))["dqscoresum_accuracy"] == 0.25

    await catalogue.writer.delete_by_id(catalogue.guids["ps"])
    await catalogue.quality.run_once()
    assert await catalogue.result("ps") is None
    assert (await catalogue.score_fields("f"))["dqscorecnt_validity"] == 0

    moved = m4i("m4i_field", "g").model_copy(
        update={
            "guid": catalogue.guids["g"],
            "relationship_attributes": {"datasets": [AtlasObjectId(guid=catalogue.guids["t"])]},
        }
    )
    await catalogue.create(moved)
    await catalogue.quality.run_once()
    rs = await catalogue.result("rs")
    assert rs is not None
    assert rs.fieldguid == [catalogue.guids["f"]]
    assert await catalogue.totals("g") is None
    assert await catalogue.holders() == {"rs", "f", "a", "e", "d", "s"}
    assert await catalogue.quality.run_once() == 0


@pytest.mark.covers(f"{Q}.run_once", rules=["ASQ-07"])
async def test__a_write_that_meets_a_change_in_between_waits_for_the_next_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A score changed between the round's read and its write: not overwritten, corrected in the next round."""
    catalogue = await Catalogue.indexed(*catalogue_entities())
    await catalogue.create(catalogue.score("rs", "r", "s", 0.5))
    documents = catalogue.documents
    read = documents.get
    changed: list[bool] = []

    async def get_then_change(guids: list[str]) -> Any:  # noqa: ANN401 - the store's answer
        found = await read(guids)
        if not changed and catalogue.guids["rs"] in guids:
            changed.append(True)
            versioned = found[catalogue.guids["rs"]]
            entity = versioned.entity
            moved = entity.model_copy(update={"attributes": entity.attributes | {"m4i_dq_score.score": 0.25}})
            await documents.write([(moved, versioned.version)])
        return found

    monkeypatch.setattr(documents, "get", get_then_change)
    await catalogue.quality.run_once()
    monkeypatch.undo()

    assert changed
    await catalogue.quality.run_once()
    assert (await catalogue.score_fields("g"))["dqscoresum_accuracy"] == 0.25


@pytest.mark.covers("aurelius_atlas_core.app_search_document.quality_result_mapping", rules=["ASQ-03"])
@pytest.mark.covers("aurelius_atlas_core.app_search_document.quality_totals_mapping", rules=["ASQ-04"])
def test__the_mappings_keep_names_as_text_guids_as_keywords_and_numbers_as_doubles() -> None:
    """A result's names have a text sub-field; its GUIDs are keywords; the totals are numbers and rule GUIDs."""
    result = quality_result_mapping()["properties"]
    totals = quality_totals_mapping()["properties"]

    assert result["name"]["fields"]["text"]["type"] == "text"
    assert result["fieldguid"]["type"] == "keyword"
    assert result["dqscore"]["type"] == result["businessruleid"]["type"] == "double"
    assert set(totals) == {*DIMENSIONS, "overall"}
    assert totals["overall"]["properties"]["score"] == {"type": "double"}
    assert totals["accuracy"]["properties"]["rules"]["type"] == "keyword"


def sample_totals() -> dict[str, dict[str, Any]]:
    """The sample catalogue with a PASS score for each legacy result, over the dataset of its field, rolled up."""

    async def build() -> dict[str, dict[str, Any]]:
        documents = await indexed_sample()
        by_guid = {document["guid"]: document for document in legacy()}
        scores = [
            StoredEntity(
                guid=f"score-{index}",
                type_name="m4i_dq_score",
                attributes={
                    "Referenceable.qualifiedName": f"score-{index}",
                    "m4i_dq_score.verdict": "PASS",
                    "m4i_dq_score.score": result["dqscore"],
                    "m4i_dq_score.ruleGuid": result["qualityguid"],
                    "m4i_dq_score.datasetGuid": by_guid[result["fieldguid"]]["deriveddatasetguid"][0],
                },
            )
            for index, result in enumerate(legacy_results())
        ]
        await documents.write([(score, None) for score in scores])
        await QualityIndexer(documents).run_once()
        found = await documents.get(list(by_guid))
        return {guid: _score_fields(versioned.entity) for guid, versioned in found.items()}

    return asyncio.run(build())


def legacy_results() -> list[dict[str, Any]]:
    """``atlas-dev-quality``'s documents."""
    return json.loads(FIXTURES.joinpath("legacy-app-search-atlas-dev-quality.json").read_text())


INACTIVE_RULE = "5e4bce72-89e5-47f9-b498-cf1d53036522"
"""The one rule of the legacy results whose ``active`` is ``false``: it has no result (DD-532)."""


@pytest.mark.covers(f"{Q}.run_once", rules=["LAS-12", "ASQ-04", "ASQ-05", "DD-532"])
def test__the_sample_s_scores_roll_up_as_atlas_dev_s_but_the_inactive_rule_s() -> None:
    """All 23 score fields and the rule GUIDs of all 684 documents as the legacy ones, where the inactive rule's
    result is not counted: on each document it reached, its score taken away as often as it arrived there.
    """  # noqa: D205 - one sentence
    (inactive,) = [result for result in legacy_results() if result["qualityguid"] == INACTIVE_RULE]
    dimension = inactive["dataqualityruledimension"].lower()
    reached = reached_by(inactive["fieldguid"])
    totals = sample_totals()

    for document in legacy():
        derived = totals[document["guid"]]
        expected = {name: document[name] for name in derived}
        if times := reached[document["guid"]]:
            expected[f"qualityguid_{dimension}"] = [
                guid for guid in expected[f"qualityguid_{dimension}"] if guid != INACTIVE_RULE
            ]
            for name in (dimension, "overall"):
                expected[f"dqscoresum_{name}"] -= times * inactive["dqscore"]
                expected[f"dqscorecnt_{name}"] -= times
                count = expected[f"dqscorecnt_{name}"]
                expected[f"dqscore_{name}"] = expected[f"dqscoresum_{name}"] / count if count else 0.0
        for name, value in derived.items():
            if isinstance(value, list):
                assert sorted(value) == sorted(expected[name]), (document["guid"], name)
            else:
                assert value == pytest.approx(expected[name]), (document["guid"], name)

    assert len(totals) == 684
    assert (len(reached), reached.total()) == (10, 12)


def reached_by(field_guid: str) -> Counter[str]:
    """How often a field's result reaches each legacy document: the field and its data attributes once, each
    entity of their breadcrumbs once per breadcrumb (LAS-12).
    """  # noqa: D205 - one sentence
    by_guid = {document["guid"]: document for document in legacy()}
    field = by_guid[field_guid]
    attributes = field["deriveddataattributeguid"]
    return Counter(
        [
            field_guid,
            *attributes,
            *field["breadcrumbguid"],
            *(guid for attribute in attributes for guid in by_guid[attribute]["breadcrumbguid"]),
        ]
    )
