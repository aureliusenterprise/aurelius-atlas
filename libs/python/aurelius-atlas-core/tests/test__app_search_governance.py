"""The governance verdicts of the entities (LAS-13, ASG-02 to ASG-06, DD-533 to DD-536), on the fake client.

Each test writes a small catalogue through the store, indexes its documents and runs the governance round. The
sample catalogue gives each legacy verdict of a rule that reads back.
"""

import asyncio
import json
from collections import Counter
from typing import Any

import pytest
from aurelius_atlas_core.app_search_document import VERDICT_FIELDS, own_document, verdict_mapping
from aurelius_atlas_core.app_search_governance import GovernanceIndexer, governance_rule, rules_digest
from aurelius_atlas_core.app_search_indexer import AppSearchIndexer
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR, M4I_MODELS_DIR, ModelLoader
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments, MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, AtlasObjectId, EntityStatus
from aurelius_atlas_store_es.testing.fake import FakeClient
from aurelius_atlas_typesystem.registry import TypeRegistry
from test__app_search_engine import FIXTURES, indexed_sample

G = "aurelius_atlas_core.app_search_governance"
X = f"{G}.GovernanceIndexer"
D = "aurelius_atlas_core.entity_documents.ElasticsearchEntityDocuments"
M = "aurelius_atlas_core.testing.memory.MemoryEntityDocuments"
VERDICTS = "aurelius-atlas-gov-quality"

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


def rule(type_name: str, key: str, expression: str | None = None, **attributes: Any) -> AtlasEntity:  # noqa: ANN401
    """An active governance rule for ``type_name`` with its legacy fields, of ``expression`` unless of the
    vocabulary.
    """  # noqa: D205 - one sentence
    values = {
        "qualifiedName": f"{type_name}--{key}",
        "name": f"Rule {key}",
        "ruleType": "attribute",
        "ruleDescription": f"About {key}",
        "qualityDimension": "completeness",
        "nonCompliantMessage": f"Misses {key}",
        "active": True,
        "id": 1,
    }
    if expression is not None:
        values["expression"] = expression
    return m4i("m4i_gov_data_quality", key, values | attributes)


def catalogue_entities() -> list[AtlasEntity]:
    """Domain ``d`` with a definition, ``x`` without; entity ``e`` in ``d``, ``o`` in none; rules over both types.

    ``named`` needs a definition, ``domained`` a domain or a parent entity, ``defined`` (of the vocabulary, no
    message, no dimension) a definition that is not empty.
    """
    return [
        m4i("m4i_data_domain", "d", {"definition": "Sales"}),
        m4i("m4i_data_domain", "x", {"definition": ""}),
        m4i("m4i_data_entity", "e", dataDomain=["d"]),
        m4i("m4i_data_entity", "o"),
        rule("m4i_data_domain", "named", "completeness('definition')"),
        rule(
            "m4i_data_entity",
            "domained",
            "length('dataDomain', 1) | length('parentEntity', 1)",
            ruleType="relationship",
        ),
        rule(
            "m4i_data_domain",
            "defined",
            dqcheckkind="ATTRIBUTE_NOT_EMPTY",
            dqattribute="definition",
            qualityDimension=None,
            nonCompliantMessage=None,
        ),
    ]


class Catalogue:
    """A small catalogue written through the store on the fake client, its documents indexed, each known by key."""

    def __init__(self, types: TypedefStore) -> None:
        self.client = FakeClient()
        self.documents = ElasticsearchEntityDocuments(self.client)  # type: ignore[arg-type]
        self.store = EntityStore(types.registry, self.documents)
        self.indexer = AppSearchIndexer(self.documents, types.registry)
        self.governance = GovernanceIndexer(self.documents, types.registry, batch_size=2)
        self.writer = EntityWriter(self.store, user="u")
        self.guids: dict[str, str] = {}

    @classmethod
    async def judged(cls, *entities: AtlasEntity) -> Catalogue:
        """The entities, created in one request, a round of the document indexer and one of the governance's."""
        catalogue = cls(await m4i_types())
        await catalogue.store.prepare()
        await catalogue.create(*entities)
        return catalogue

    async def create(self, *entities: AtlasEntity) -> None:
        """Create or update the entities, then a round of the document indexer and one of the governance's."""
        response = await self.writer.create_or_update(AtlasEntitiesWithExtInfo(entities=list(entities)))
        self.guids |= {key.removeprefix("-"): guid for key, guid in (response.guid_assignments or {}).items()}
        await self.round()

    async def round(self) -> int:
        """A round of the document indexer, then one of the governance's: how many entities the second wrote."""
        await self.indexer.run_once()
        return await self.governance.run_once()

    def moved(self, type_name: str, key: str, **relations: list[str]) -> AtlasEntity:
        """The key's entity again, by its GUID, with these relationship attributes."""
        return m4i(type_name, key).model_copy(
            update={
                "guid": self.guids[key],
                "relationship_attributes": {
                    name: [AtlasObjectId(guid=self.guids[other]) for other in others]
                    for name, others in relations.items()
                },
            }
        )

    async def change(self, key: str, name: str, value: object) -> None:
        """Change the key's attribute, then a round of each."""
        await self.writer.update_attribute_by_guid(self.guids[key], name, value)
        await self.round()

    def verdicts(self) -> dict[tuple[str, str], dict[str, Any]]:
        """The stored verdicts by entity key and rule key."""
        keys = {guid: key for key, guid in self.guids.items()}
        return {
            (keys[source["entity_guid"]], keys[source["guid"]]): source
            for source, _ in self.client._index_of(VERDICTS).values()  # noqa: SLF001 - the fake's documents
        }

    def compliant(self) -> dict[tuple[str, str], str]:
        """Each stored verdict's ``compliant`` by entity key and rule key."""
        return {pair: verdict["compliant"] for pair, verdict in self.verdicts().items()}


@pytest.mark.covers(f"{X}.run_once", rules=["ASG-03", "LAS-13"])
@pytest.mark.covers(f"{X}.rules", rules=["ASG-03"])
@pytest.mark.covers(f"{G}.governance_rule", rules=["ASG-02", "ASG-03"])
@pytest.mark.covers(f"{D}.governance_rules", rules=["ASG-03"])
@pytest.mark.covers(f"{D}.replace_verdicts", rules=["ASG-03"])
async def test__a_verdict_copies_its_rule_and_names_its_entity() -> None:
    """Every field of the legacy document: the pair, the rule's fields, the entity's type and GUID."""
    catalogue = await Catalogue.judged(*catalogue_entities())
    pair = f"{catalogue.guids['d']}--{catalogue.guids['named']}"

    verdict = catalogue.verdicts()[("d", "named")]

    assert set(verdict) == set(VERDICT_FIELDS)
    assert verdict == {
        "id": pair,
        "qualifiedname": pair,
        "guid": catalogue.guids["named"],
        "qualityqualifiedname": "m4i_data_domain--named",
        "name": "Rule named",
        "expression": "completeness('definition')",
        "dataqualitytype": "attribute",
        "dataqualityruledescription": "About named",
        "dataqualityruledimension": "completeness",
        "noncompliant_message": "Misses named",
        "usedattributes": ["definition"],
        "dataqualityruletypename": "m4i_data_domain",
        "entity_guid": catalogue.guids["d"],
        "compliant": "1",
        "result_id": "0",
        "business_rule_id": "1",
    }


@pytest.mark.covers(f"{G}.governance_rule", rules=["ASG-02", "ASG-03"])
async def test__a_vocabulary_rule_without_message_or_dimension_answers_its_kind_s() -> None:
    """No expression, the kind's dimension in lower case and its reason as the message."""
    catalogue = await Catalogue.judged(*catalogue_entities())

    verdict = catalogue.verdicts()[("x", "defined")]

    assert (verdict["expression"], verdict["dataqualityruledimension"]) == ("", "completeness")
    assert verdict["noncompliant_message"] == "the attribute holds no value to show"
    assert verdict["usedattributes"] == ["definition"]


@pytest.mark.covers(f"{X}.verdicts", rules=["ASG-04"])
async def test__each_kind_meets_and_misses_its_attribute_or_relationship() -> None:
    """An empty definition is present but empty; a domain or, failing it, a parent entity; neither misses."""
    catalogue = await Catalogue.judged(*catalogue_entities())

    assert catalogue.compliant() == {
        ("d", "named"): "1",
        ("x", "named"): "1",
        ("d", "defined"): "1",
        ("x", "defined"): "0",
        ("e", "domained"): "1",
        ("o", "domained"): "0",
    }

    child = m4i("m4i_data_entity", "c")
    child.relationship_attributes = {"parentEntity": [AtlasObjectId(guid=catalogue.guids["o"])]}
    await catalogue.create(child)
    assert catalogue.compliant()[("c", "domained")] == "1"


@pytest.mark.covers(f"{X}.run_once", rules=["ASG-03"])
async def test__no_verdict_for_an_unread_inactive_or_deleted_rule_another_type_or_an_entity_without_a_document() -> (
    None
):
    """Another expression, a mixed pair, ``active`` false, a deleted rule, a rule for ``Asset`` (a super type of a
    domain's), and a source, which has no document: none judges.
    """  # noqa: D205 - one sentence
    catalogue = await Catalogue.judged(
        m4i("m4i_data_domain", "d"),
        m4i("m4i_source", "src"),
        rule("m4i_data_domain", "unique", "uniqueness('qualifiedName')"),
        rule("m4i_data_domain", "mixed", "completeness('name') | length('name', 1)"),
        rule("m4i_data_domain", "off", "completeness('name')", active=False),
        rule("m4i_data_domain", "gone", "completeness('name')"),
        rule("Asset", "super", "completeness('name')"),
        rule("m4i_source", "sourced", "completeness('name')"),
        rule("m4i_data_domain", "kept", "completeness('name')"),
    )
    await catalogue.writer.delete_by_id(catalogue.guids["gone"])
    await catalogue.round()

    assert catalogue.compliant() == {("d", "kept"): "1"}


@pytest.mark.covers(f"{X}.run_once", rules=["ASG-06"])
@pytest.mark.covers(f"{D}.to_govern", rules=["ASG-06"])
async def test__a_second_round_writes_nothing_and_each_change_shows_after_the_next() -> None:
    """A changed attribute, a new and a deleted relationship, a changed and a deactivated rule, each judged again."""
    catalogue = await Catalogue.judged(*catalogue_entities())
    assert await catalogue.round() == 0

    await catalogue.change("x", "definition", "Finance")
    assert catalogue.compliant()[("x", "defined")] == "1"

    await catalogue.create(catalogue.moved("m4i_data_entity", "o", dataDomain=["x"]))
    assert catalogue.compliant()[("o", "domained")] == "1"

    await catalogue.create(catalogue.moved("m4i_data_entity", "e", dataDomain=[]))
    assert catalogue.compliant()[("e", "domained")] == "0"

    await catalogue.change("named", "nonCompliantMessage", "Needs a definition")
    assert {
        verdict["noncompliant_message"] for (_, key), verdict in catalogue.verdicts().items() if key == "named"
    } == {"Needs a definition"}

    await catalogue.change("defined", "active", value=False)
    assert {key for _, key in catalogue.verdicts()} == {"named", "domained"}
    assert await catalogue.round() == 0


@pytest.mark.covers(f"{X}.run_once", rules=["ASG-06"])
@pytest.mark.covers(f"{D}.write", rules=["ASG-06"])
async def test__a_deleted_and_a_purged_entity_lose_their_verdicts() -> None:
    """Deleted, its document goes and a round takes its verdicts; purged at once, the purge takes them."""
    catalogue = await Catalogue.judged(*catalogue_entities())

    await catalogue.writer.delete_by_id(catalogue.guids["x"])
    await catalogue.round()
    assert {entity for entity, _ in catalogue.verdicts()} == {"d", "e", "o"}
    assert not (await catalogue.documents.get([catalogue.guids["x"]]))[catalogue.guids["x"]].entity.governed

    await catalogue.writer.delete_by_id(catalogue.guids["o"])
    await catalogue.writer.purge_by_ids([catalogue.guids["o"]])
    assert {entity for entity, _ in catalogue.verdicts()} == {"d", "e"}
    assert await catalogue.round() == 0


@pytest.mark.covers(f"{X}.run_once", rules=["ASG-06"])
async def test__a_write_that_meets_a_change_in_between_waits_for_the_next_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An entity changed between the round's listing and its write keeps the change and is judged again later."""
    catalogue = await Catalogue.judged(
        m4i("m4i_data_domain", "x", {"definition": ""}),
        rule("m4i_data_domain", "defined", dqcheckkind="ATTRIBUTE_NOT_EMPTY", dqattribute="definition"),
    )
    documents = catalogue.documents
    listed = documents.to_govern
    changed: list[bool] = []

    async def list_then_change(digests: Any, limit: int) -> Any:  # noqa: ANN401 - the store's answer
        found = await listed(digests, limit)
        if not changed and found:
            changed.append(True)
            await catalogue.writer.update_attribute_by_guid(catalogue.guids["x"], "definition", "Sales")
        return found

    monkeypatch.setattr(documents, "to_govern", list_then_change)
    await catalogue.change("defined", "name", "Defined")
    monkeypatch.undo()

    assert changed
    assert catalogue.compliant() == {("x", "defined"): "0"}
    await catalogue.round()
    assert catalogue.compliant() == {("x", "defined"): "1"}


def stored_rule(guid: str, **attributes: Any) -> StoredEntity:  # noqa: ANN401 - the attributes' values
    """A stored governance rule for data domains over their name, with ``attributes``."""
    values = {"qualifiedName": f"m4i_data_domain--{guid}", "expression": "completeness('name')"} | attributes
    return StoredEntity(guid=guid, type_name="m4i_gov_data_quality", attributes=values)


@pytest.mark.covers(f"{G}.rules_digest", rules=["ASG-06"])
def test__a_type_s_digest_follows_what_its_rules_check_and_copy_not_their_order() -> None:
    """The same rules in another order digest alike; a message or an attribute changed digests otherwise."""
    first, second = governance_rule(stored_rule("a")), governance_rule(stored_rule("b"))
    reworded = governance_rule(stored_rule("a", nonCompliantMessage="Needs a name"))
    elsewhere = governance_rule(stored_rule("a", expression="completeness('definition')"))
    assert first is not None
    assert second is not None
    assert reworded is not None
    assert elsewhere is not None

    assert rules_digest([first, second]) == rules_digest([second, first])
    assert (
        len({rules_digest([first, second]), rules_digest([reworded, second]), rules_digest([elsewhere, second])}) == 3
    )


@pytest.mark.covers(f"{M}.governance_rules", rules=["ASG-03"])
@pytest.mark.covers(f"{M}.to_govern", rules=["ASG-06"])
@pytest.mark.covers(f"{M}.replace_verdicts", rules=["ASG-06"])
@pytest.mark.covers(f"{M}.write", rules=["ASG-06"])
async def test__the_memory_documents_list_and_replace_as_elasticsearch_s() -> None:
    """The rules; an entity without its type's digest; one governed no longer judged; verdicts replaced, purged."""
    documents = MemoryEntityDocuments()
    judged = indexed_entity("j", governed_by="old")
    current = indexed_entity("c", governed_by="new")
    lost = indexed_entity("l").model_copy(update={"state": EntityStatus.DELETED, "governed": True})
    await documents.write([(stored_rule("r"), None), (judged, None), (current, None), (lost, None)])
    await documents.replace_verdicts(
        {"j": [{"id": "j--r", "entity_guid": "j"}], "l": [{"id": "l--r", "entity_guid": "l"}]}
    )
    await documents.replace_verdicts({"j": [{"id": "j--s", "entity_guid": "j"}]})

    assert [found.entity.guid for found in await documents.governance_rules()] == ["r"]
    assert [found.entity.guid for found in await documents.to_govern({"m4i_data_domain": "new"}, 10)] == ["j", "l"]
    assert set(documents.verdicts) == {"j--s", "l--r"}
    (versioned,) = (await documents.get(["l"])).values()
    await documents.write([], removed=[("l", versioned.version)])
    assert set(documents.verdicts) == {"j--s"}


def indexed_entity(guid: str, **document: object) -> StoredEntity:
    """A data domain with its own document and ``document``'s marks."""
    entity = StoredEntity(guid=guid, type_name="m4i_data_domain", attributes={"qualifiedName": guid})
    return entity.model_copy(update={"app_search": own_document(entity).model_copy(update=document)})


@pytest.mark.covers("aurelius_atlas_core.app_search_document.verdict_mapping", rules=["ASG-05"])
def test__the_verdicts_mapping_keeps_each_field_a_keyword_with_a_text_sub_field() -> None:
    """Every field of a verdict, keyword and text; nothing else mapped."""
    mapping = verdict_mapping()

    assert mapping["dynamic"] is False
    assert set(mapping["properties"]) == set(VERDICT_FIELDS)
    assert all(
        field["type"] == "keyword" and field["fields"]["text"]["type"] == "text"
        for field in mapping["properties"].values()
    )


def sample_verdicts() -> tuple[int, int, dict[str, dict[str, Any]]]:
    """The sample catalogue judged: the rules read, the rule entities, and the verdicts by id."""

    async def build() -> tuple[int, int, dict[str, dict[str, Any]]]:
        documents = await indexed_sample()
        governance = GovernanceIndexer(documents, (await m4i_types()).registry)
        read = sum(len(rules) for rules in (await governance.rules()).values())
        assert await governance.run_once() > 0
        assert await governance.run_once() == 0
        held = documents._client._index_of(VERDICTS)  # type: ignore[attr-defined] # noqa: SLF001 - the fake's
        return read, len(await documents.governance_rules()), {key: source for key, (source, _) in held.items()}

    return asyncio.run(build())


@pytest.mark.covers(f"{X}.run_once", rules=["LAS-13", "ASG-02", "ASG-03", "ASG-04"])
def test__the_sample_s_verdicts_are_the_legacy_ones_of_the_rules_that_read() -> None:
    """47 of 95 rules read; 2,602 verdicts; each of the 1,612 legacy verdicts of a rule that reads as it was, and
    none of the 16 of the rule whose expression is now ``conditional_value(...)`` (DV-160).
    """  # noqa: D205 - one sentence
    read, rules, verdicts = sample_verdicts()
    legacy = json.loads(FIXTURES.joinpath("legacy-app-search-atlas-dev-gov-quality.json").read_text())

    assert (read, rules) == (47, 95)
    assert (len(verdicts), Counter(verdict["compliant"] for verdict in verdicts.values())) == (
        2602,
        Counter({"1": 1782, "0": 820}),
    )
    kept = [document for document in legacy if document["id"] in verdicts]
    assert len(kept) == 1612
    assert all(verdicts[document["id"]]["compliant"] == document["compliant"] for document in kept)
    assert {document["guid"] for document in legacy if document["id"] not in verdicts} == {
        "3cb9ab0b-050c-40db-9f12-f136045a77a0"
    }
    for document in kept:
        mine = verdicts[document["id"]]
        assert {
            field: mine[field] for field in ("qualifiedname", "guid", "entity_guid", "dataqualityruletypename")
        } == {field: document[field] for field in ("qualifiedname", "guid", "entity_guid", "dataqualityruletypename")}
