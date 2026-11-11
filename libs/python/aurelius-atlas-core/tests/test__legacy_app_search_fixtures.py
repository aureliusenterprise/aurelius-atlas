"""The legacy App Search documents obey 14.1's rules, as far as they and the sample catalogue show them.

The fixtures are the original Aurelius Atlas's three engines for ``data/atlas-sample/sample_data.zip`` (DD-484).
These tests read both, with no store: they prove the rules that series 14 implements are the legacy pipeline's,
and that the differences the spec lists are the only ones (DD-485).
"""

import json
import re
import zipfile
from functools import cache
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = Path(__file__).parents[4] / "data" / "atlas-sample" / "sample_data.zip"

DIMENSIONS: tuple[str, ...] = ("accuracy", "completeness", "timeliness", "validity", "uniqueness")
TECHNICAL = {"m4i_system", "m4i_collection", "m4i_dataset", "m4i_field"}
BUSINESS = {"m4i_data_domain", "m4i_data_entity", "m4i_data_attribute"}
NEVER_FILLED = (
    "businessruleid",
    "classificationstext",
    "deriveddataownerguid",
    "deriveddatastewardguid",
    "deriveddomainleadguid",
    "deriveddatasetguids",
    "deriveddatasetnames",
    "derivedentityguids",
    "derivedentitynames",
    "entityname",
)

Document = dict[str, Any]


@cache
def entities() -> dict[str, Document]:
    """The sample catalogue's entities by GUID."""
    found: dict[str, Document] = {}
    with zipfile.ZipFile(SAMPLE) as archive:
        for name in archive.namelist():
            content = json.loads(archive.read(name))
            if "entity" in content:
                found[content["entity"]["guid"]] = content["entity"]
    return found


@cache
def engine(name: str) -> tuple[Document, ...]:
    """One legacy engine's documents."""
    return tuple(json.loads((FIXTURES / f"legacy-app-search-{name}.json").read_text()))


def attribute(guid: str, name: str) -> object:
    """An attribute of a catalogue entity."""
    return entities()[guid]["attributes"].get(name)


def mismatches(field: str, expected: dict[str, object]) -> dict[str, str]:
    """The ``atlas-dev`` documents whose ``field`` is not the expected value, by GUID, with their type."""
    return {
        document["guid"]: document["typename"]
        for document in engine("atlas-dev")
        if (document[field] or None) != (expected[document["guid"]] or None)
    }


@pytest.mark.covers(rules=["LAS-01"])
def test__one_document_per_m4i_entity_but_the_sources() -> None:
    """Every entity has its document, under its GUID, except the three ``m4i_source`` entities."""
    documents = engine("atlas-dev")
    without = set(entities()) - {document["guid"] for document in documents}

    assert len(documents) == len({document["guid"] for document in documents}) == 684
    assert all(document["id"] == document["guid"] for document in documents)
    assert all(entity["status"] == "ACTIVE" for entity in entities().values())
    assert {entities()[guid]["typeName"] for guid in without} == {"m4i_source"}
    assert len(without) == 3


@pytest.mark.covers(rules=["LAS-02"])
def test__the_identity_fields_are_the_entity_s_but_the_listed_differences() -> None:
    """Type, super types and email hold everywhere; name, qualified name and definition but for DD-485's list."""
    documents = engine("atlas-dev")
    names = {guid: attribute(guid, "name") or attribute(guid, "qualifiedName") for guid in entities()}
    qualified = {guid: attribute(guid, "qualifiedName") or guid for guid in entities()}
    definitions = {guid: attribute(guid, "definition") for guid in entities()}

    assert all(document["typename"] == entities()[document["guid"]]["typeName"] for document in documents)
    assert all(document["supertypenames"] == [document["typename"]] for document in documents)
    assert all(
        document["email"] == attribute(document["guid"], "email")
        for document in documents
        if document["typename"] == "m4i_person"
    )
    assert list(mismatches("name", names).values()) == ["m4i_gov_data_quality"]
    assert sorted(mismatches("referenceablequalifiedname", qualified).values()) == [
        *["m4i_generic_process"] * 19,
        "m4i_gov_data_quality",
    ]
    assert all(
        document["referenceablequalifiedname"] == document["guid"]
        for document in documents
        if document["typename"] == "m4i_generic_process"
    )
    lost = mismatches("definition", definitions)
    assert len(lost) == 87
    assert {guid for guid, typename in lost.items() if typename not in BUSINESS} == {
        guid for guid in lost if not definitions[guid]
    }


@pytest.mark.covers(rules=["LAS-03"])
def test__the_source_type_follows_the_type() -> None:
    """Technical for the four technical types, Business for the three business ones, empty for the rest."""
    for document in engine("atlas-dev"):
        typename = document["typename"]
        expected = "Technical" if typename in TECHNICAL else "Business" if typename in BUSINESS else ""
        assert (document["sourcetype"] or "") == expected, document["guid"]


@pytest.mark.covers(rules=["LAS-07"])
def test__the_fields_the_pipeline_never_filled_are_empty() -> None:
    """Present on every document, and empty."""
    for document in engine("atlas-dev"):
        assert all(not document[field] for field in NEVER_FILLED), document["guid"]


Totals = dict[str, dict[str, float]]


def totals() -> tuple[Totals, Totals]:
    """LAS-12's sums and counts per document and dimension: the results on their fields, then rolled up."""
    documents = {document["guid"]: document for document in engine("atlas-dev")}
    sums = {guid: dict.fromkeys(DIMENSIONS, 0.0) for guid in documents}
    counts = {guid: dict.fromkeys(DIMENSIONS, 0.0) for guid in documents}

    def add(downstream: str, upstream: str) -> None:
        for dimension in DIMENSIONS:
            sums[upstream][dimension] += sums[downstream][dimension]
            counts[upstream][dimension] += counts[downstream][dimension]

    for result in engine("atlas-dev-quality"):
        dimension = result["dataqualityruledimension"].lower()
        sums[result["fieldguid"]][dimension] += result["dqscore"]
        counts[result["fieldguid"]][dimension] += 1
    for guid, document in documents.items():
        if document["typename"] == "m4i_field":
            for attribute_guid in document["deriveddataattributeguid"]:
                add(guid, attribute_guid)
    for guid, document in documents.items():
        if document["typename"] in ("m4i_data_attribute", "m4i_field"):
            for ancestor in document["breadcrumbguid"]:
                add(guid, ancestor)
    return sums, counts


def rolled_up() -> Totals:
    """LAS-12's score fields of every ``atlas-dev`` document, from the quality documents and the breadcrumbs."""
    sums, counts = totals()
    scores: Totals = {}
    for guid in sums:
        own = scores[guid] = {}
        for dimension in DIMENSIONS:
            own[f"dqscoresum_{dimension}"] = sums[guid][dimension]
            own[f"dqscorecnt_{dimension}"] = counts[guid][dimension]
        own["dqscoresum_overall"] = sum(sums[guid].values())
        own["dqscorecnt_overall"] = sum(counts[guid].values())
        for name in (*DIMENSIONS, "overall"):
            count = own[f"dqscorecnt_{name}"]
            own[f"dqscore_{name}"] = own[f"dqscoresum_{name}"] / count if count else 0.0
    return scores


@pytest.mark.covers(rules=["LAS-12"])
def test__the_scores_roll_up_from_fields_to_attributes_and_breadcrumbs() -> None:
    """All 23 score fields of all 684 documents, and each dimension's rule GUIDs on the fields."""
    scores = rolled_up()
    rules: dict[tuple[str, str], list[str]] = {}
    for result in engine("atlas-dev-quality"):
        key = (result["fieldguid"], result["dataqualityruledimension"].lower())
        rules.setdefault(key, []).append(result["qualityguid"])

    for document in engine("atlas-dev"):
        for field, value in scores[document["guid"]].items():
            assert document[field] == pytest.approx(value), (document["guid"], field)
        for dimension in DIMENSIONS:
            expected = rules.get((document["guid"], dimension), [])
            assert sorted(document[f"qualityguid_{dimension}"]) == sorted(expected), document["guid"]


@pytest.mark.covers(rules=["LAS-11"])
def test__a_quality_result_names_its_rule_and_a_field_of_it() -> None:
    """Identity, dimension and field hold for all 42; the rule's text differs in 15, shape only (DD-484)."""
    results = engine("atlas-dev-quality")
    rule_text_differs = 0
    for result in results:
        rule, field = result["qualityguid"], result["fieldguid"]
        assert entities()[rule]["typeName"] == "m4i_data_quality"
        assert result["id"] == result["qualityqualifiedname"] == attribute(rule, "qualifiedName")
        assert result["guid"] == rule
        assert result["dataqualityruledimension"] == attribute(rule, "qualityDimension")
        assert field in {end["guid"] for end in entities()[rule]["relationshipAttributes"]["fields"]}
        assert result["fieldqualifiedname"] == attribute(field, "qualifiedName")
        assert 0 <= result["dqscore"] <= 1
        assert {"name", "businessruleid", "datadomainname"} <= result.keys()
        rule_text_differs += (result["expression"], result["dataqualityruledescription"]) != (
            attribute(rule, "expression"),
            attribute(rule, "ruleDescription"),
        )

    assert len(results) == len({result["qualityguid"] for result in results}) == 42
    assert rule_text_differs == 15


@pytest.mark.covers(rules=["LAS-13"])
def test__a_governance_verdict_names_its_entity_and_a_rule_for_its_type() -> None:
    """Identity, type and the rule's kind, description and dimension hold for all 1,628 verdicts."""
    verdicts = engine("atlas-dev-gov-quality")
    for verdict in verdicts:
        rule, entity = verdict["guid"], verdict["entity_guid"]
        assert entities()[rule]["typeName"] == "m4i_gov_data_quality"
        assert verdict["id"] == verdict["qualifiedname"] == f"{entity}--{rule}"
        assert verdict["dataqualityruletypename"] == entities()[entity]["typeName"]
        assert str(attribute(rule, "qualifiedName")).startswith(f"{verdict['dataqualityruletypename']}--")
        assert verdict["dataqualitytype"] == attribute(rule, "ruleType")
        assert verdict["dataqualityruledescription"] == attribute(rule, "ruleDescription")
        assert verdict["dataqualityruledimension"] == attribute(rule, "qualityDimension")
        assert (verdict["result_id"], verdict["business_rule_id"]) == ("0", "1")
        assert verdict["compliant"] in ("0", "1")

    used = [re.search(r"'(.*?)'", verdict["expression"]) for verdict in verdicts]
    disagree = sum(
        verdict["usedattributes"] != [match.group(1)] for verdict, match in zip(verdicts, used, strict=True) if match
    )
    assert len(verdicts) == len({verdict["id"] for verdict in verdicts}) == 1628
    assert disagree == 199
