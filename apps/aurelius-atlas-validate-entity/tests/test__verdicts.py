"""The rules door: the read, the cache, the assembly, the breaker (VEV-02..08; DD-498, DD-631/632).

The fake catalogue answers the search; the breaker is the app's real one with
its test-sized bounds. No issuer and no HTTP server: the door speaks to the
client it is handed (DD-200's seam).
"""

import json
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_server_client.client import AtlasClient
from aurelius_atlas_validate_entity.errors import UpstreamError
from aurelius_atlas_validate_entity.models import DraftEntity
from aurelius_atlas_validate_entity.providers import server_breaker
from aurelius_atlas_validate_entity.settings import ValidateEntitySettings
from aurelius_atlas_validate_entity.verdicts import RULE_ATTRIBUTES, VerdictEngine, is_active
from fake_catalogue import FakeCatalogue, rule_entity, search_result
from pydantic import HttpUrl

NAME_RULE = rule_entity(
    "rule-name",
    "Name present",
    {
        "name": "Name present",
        "qualifiedName": "m4i_dataset--name-present",
        "active": True,
        "dqcheckkind": "ATTRIBUTE_PRESENT",
        "dqattribute": "name",
        "compliantMessage": "This entity has a name",
    },
)
SYSTEM_NAME_RULE = rule_entity(
    "rule-system-name",
    "System name present",
    {
        "name": "System name present",
        "qualifiedName": "m4i_system--name",
        "active": True,
        "dqcheckkind": "ATTRIBUTE_PRESENT",
        "dqattribute": "name",
        "compliantMessage": "This system has a name",
    },
)
"""A readable rule of another type (VEV-07): it judges a system, never a dataset draft."""

UNPREFIXED_RULE = rule_entity(
    "rule-unprefixed",
    "Breaks the convention",
    {
        "name": "Breaks the convention",
        "qualifiedName": "nobody-owns-me",
        "active": True,
        "dqcheckkind": "ATTRIBUTE_PRESENT",
        "dqattribute": "name",
    },
)
"""A readable rule whose qualified name names no type (VEV-07): it enters no call at all."""

INACTIVE_RULE = rule_entity(
    "rule-inactive",
    "Turned off",
    {
        "name": "Turned off",
        "qualifiedName": "m4i_dataset--turned-off",
        "active": False,
        "dqcheckkind": "ATTRIBUTE_PRESENT",
        "dqattribute": "owner",
    },
)
EXPRESSION_RULE = rule_entity(
    "rule-expression",
    "Legacy expression",
    {
        "name": "Legacy expression",
        "qualifiedName": "m4i_dataset--legacy-expression",
        "expression": "uniqueness('qualifiedName')",
    },
)
WRONG_KIND_RULE = rule_entity(
    "rule-wrong-kind",
    "Unknown kind",
    {
        "name": "Unknown kind",
        "qualifiedName": "m4i_dataset--wrong-kind",
        "dqcheckkind": "REGEX_MATCH",
        "dqattribute": "name",
    },
)
SYSTEM_EXPRESSION_RULE = rule_entity(
    "rule-system-expression",
    "System legacy expression",
    {
        "name": "System legacy expression",
        "qualifiedName": "m4i_system--kafkaClusters",
        "expression": "uniqueness('qualifiedName')",
    },
)
"""An unread rule of another type (VEV-07): unread for its own drafts, silent for the rest."""

FIELDS_RULE = rule_entity(
    "rule-fields",
    "Dataset has a field",
    {
        "name": "Dataset has a field",
        "qualifiedName": "m4i_dataset--fields",
        "active": True,
        "dqcheckkind": "ATTRIBUTE_NOT_EMPTY",
        "dqattribute": "fields",
        "compliantMessage": "This dataset has at least one field",
        "nonCompliantMessage": "This dataset should have at least one field",
    },
)
"""A rule over a relationship attribute (VEV-08, DD-632): the draft's picks answer it."""

CHILD_RULE = rule_entity(
    "rule-child",
    "Dataset has a child",
    {
        "name": "Dataset has a child",
        "qualifiedName": "m4i_dataset--childDataset",
        "active": True,
        "dqcheckkind": "ATTRIBUTE_PRESENT",
        "dqattribute": "childDataset",
        "ruleDescription": "childDataset is not None and is not empty",
        "compliantMessage": "This entity has a childDataset",
        "nonCompliantMessage": "This entity is missing a childDataset",
    },
)
"""The corpus's ``completeness('childDataset')`` shape: a PRESENCE rule over a relationship
attribute. An empty picker is no value, so the rule misses it (VEV-08, DD-634)."""

PAIR_RULE = rule_entity(
    "rule-fields-pair",
    "Dataset has a field or a child dataset",
    {
        "name": "Dataset has a field or a child dataset",
        "qualifiedName": "m4i_dataset--fields",
        "active": True,
        "expression": "length('fields', 1) | length('childDataset', 1)",
        "ruleDescription": "A dataset should have at least one field or a child dataset",
        "compliantMessage": "This dataset has a field or a child dataset",
        "nonCompliantMessage": "This dataset should have a field or a child dataset",
    },
)
"""The sample corpus's paired fields rule (DV-171): the stored ``|`` expression reads as
attribute ``fields`` with ``childDataset`` among its alternatives (VEV-09, GQ-06, ASG-02)."""


def _draft(
    attributes: dict[str, Any],
    *,
    type_name: str | None = "m4i_dataset",
    relationships: dict[str, Any] | None = None,
) -> DraftEntity:
    """One browser draft, as the model parses it (VEV-01 amended): keys as the wire names them."""
    return DraftEntity.model_validate(
        {
            "attributes": attributes,
            **({"typeName": type_name} if type_name is not None else {}),
            **({"relationshipAttributes": relationships} if relationships is not None else {}),
        }
    )


def _engine(catalogue: FakeCatalogue, settings: ValidateEntitySettings) -> tuple[VerdictEngine, httpx.AsyncClient]:
    """The door under test, speaking to the fake catalogue through its own pool (DD-200's seam)."""
    http = httpx.AsyncClient(base_url="http://catalogue.test", transport=catalogue.transport())
    breaker = server_breaker(settings)
    return VerdictEngine(AtlasClient(http, "app-identity"), breaker, settings.rules_cache_seconds), http


def _one_page(catalogue: FakeCatalogue, *entities: dict[str, Any]) -> None:
    """The fake answers the walk with one page and the end marker."""
    catalogue.handler = lambda request: FakeCatalogue.json(
        200, search_result(list(entities), "-1" if json.loads(request.content).get("marker") == "*" else None)
    )


@pytest.fixture
def engine_settings() -> ValidateEntitySettings:
    """Settings for the door: fake catalogue, default cache window, test breaker bounds."""
    return ValidateEntitySettings(
        auth_server_url=HttpUrl("http://issuer.test"),
        server_base_url=HttpUrl("http://catalogue.test"),
        breaker_fail_max=2,
    )


@pytest.mark.covers("aurelius_atlas_validate_entity.verdicts.VerdictEngine.evaluate_draft", rules=["VEV-02"])
async def test__one_rule_answers_one_verdict(engine_settings: ValidateEntitySettings) -> None:
    """The verdict names its rule, its attribute and its dimension, with the engine's line (VEV-02, DD-498)."""
    catalogue = FakeCatalogue()
    _one_page(catalogue, NAME_RULE)
    engine, http = _engine(catalogue, engine_settings)

    answer = await engine.evaluate_draft(_draft({"name": "Sales Orders"}))
    await http.aclose()

    (verdict,) = answer.verdicts
    assert (verdict.rule_guid, verdict.rule_name, verdict.attribute) == ("rule-name", "Name present", "name")
    assert verdict.dimension == "COMPLETENESS"
    assert verdict.compliant is True
    assert verdict.message == "This entity has a name"
    assert answer.unread_rules == []


@pytest.mark.covers("aurelius_atlas_validate_entity.verdicts.is_active", rules=["VEV-03"])
@pytest.mark.parametrize(
    ("stored", "active"),
    [(True, True), (False, False), (None, True), ("false", True), ({"raw": False}, False)],
)
def test__only_a_plain_false_deactivates_a_rule(stored: object, active: bool) -> None:  # noqa: FBT001 - the parametrised pair
    """12.2's reading, wrapped values included: a missing or text flag is active (VEV-03)."""
    attributes: dict[str, Any] = {} if stored is None else {"active": stored}

    assert is_active(attributes) is active


@pytest.mark.covers("aurelius_atlas_validate_entity.verdicts.VerdictEngine.rules", rules=["VEV-03"])
async def test__inactive_rules_neither_run_nor_ride_unread(engine_settings: ValidateEntitySettings) -> None:
    """An inactive rule answers nothing at all: not a verdict, not news (VEV-03)."""
    catalogue = FakeCatalogue()
    _one_page(catalogue, NAME_RULE, INACTIVE_RULE)
    engine, http = _engine(catalogue, engine_settings)

    answer = await engine.evaluate_draft(_draft({"name": "x"}))
    await http.aclose()

    assert [verdict.rule_guid for verdict in answer.verdicts] == ["rule-name"]
    assert answer.unread_rules == []


@pytest.mark.covers(
    "aurelius_atlas_validate_entity.verdicts.VerdictEngine.evaluate_draft",
    "aurelius_atlas_validate_entity.verdicts._rule_type",
    rules=["VEV-07"],
)
async def test__another_types_rule_answers_nothing_at_all(
    engine_settings: ValidateEntitySettings,
) -> None:
    """The draft is judged by its own type's rules: a foreign verdict and unread ride nothing (VEV-07, DD-631).

    The store holds one rule per type (LAS-13): the m4i_system name rule is a system's,
    the m4i_system expression rule unread for systems. Over a dataset draft both are
    silent — no verdict, no unread entry — while the dataset's own rules answer.
    """
    catalogue = FakeCatalogue()
    _one_page(catalogue, NAME_RULE, SYSTEM_NAME_RULE, EXPRESSION_RULE, SYSTEM_EXPRESSION_RULE)
    engine, http = _engine(catalogue, engine_settings)

    answer = await engine.evaluate_draft(_draft({"name": "Sales Orders"}))
    await http.aclose()

    assert [verdict.rule_guid for verdict in answer.verdicts] == ["rule-name"]
    assert [entry.rule_guid for entry in answer.unread_rules] == ["rule-expression"]


@pytest.mark.covers(
    "aurelius_atlas_validate_entity.verdicts.VerdictEngine.evaluate_draft",
    "aurelius_atlas_validate_entity.verdicts._rule_type",
    rules=["VEV-07"],
)
async def test__a_rule_naming_no_type_judges_nothing(engine_settings: ValidateEntitySettings) -> None:
    """A qualified name without the ``--`` names no type: the rule answers no draft, and is no news (VEV-07).

    The details box hides the same rule from its rows (DET-42's prefix search), so both
    surfaces keep it silent — a broken convention goes nowhere, everywhere.
    """
    catalogue = FakeCatalogue()
    _one_page(catalogue, UNPREFIXED_RULE)
    engine, http = _engine(catalogue, engine_settings)

    answer = await engine.evaluate_draft(_draft({"name": "Sales Orders"}))
    await http.aclose()

    assert answer.verdicts == []
    assert answer.unread_rules == []


@pytest.mark.covers("aurelius_atlas_validate_entity.verdicts.VerdictEngine.evaluate_draft", rules=["VEV-07"])
async def test__a_draft_without_a_type_is_judged_by_nothing(engine_settings: ValidateEntitySettings) -> None:
    """No type, no join: the readable rules of the read answer nothing (VEV-07)."""
    catalogue = FakeCatalogue()
    _one_page(catalogue, NAME_RULE, EXPRESSION_RULE)
    engine, http = _engine(catalogue, engine_settings)

    answer = await engine.evaluate_draft(_draft({"name": "Sales Orders"}, type_name=None))
    await http.aclose()

    assert answer.verdicts == []
    assert answer.unread_rules == []


@pytest.mark.covers("aurelius_atlas_validate_entity.verdicts.VerdictEngine.rules", rules=["VEV-03"])
async def test__an_unread_rule_rides_the_unread_list_never_executed(engine_settings: ValidateEntitySettings) -> None:
    """The stored expression rule and the foreign kind are recorded with the cause, not run (VEV-03, DV-146)."""
    catalogue = FakeCatalogue()
    _one_page(catalogue, EXPRESSION_RULE, WRONG_KIND_RULE)
    engine, http = _engine(catalogue, engine_settings)

    answer = await engine.evaluate_draft(_draft({"name": "x"}))
    await http.aclose()

    assert answer.verdicts == []
    assert {entry.rule_guid for entry in answer.unread_rules} == {"rule-expression", "rule-wrong-kind"}
    by_guid = {entry.rule_guid: entry for entry in answer.unread_rules}
    assert "dqcheckkind" in by_guid["rule-expression"].error
    assert "REGEX_MATCH" in by_guid["rule-wrong-kind"].error


@pytest.mark.covers("aurelius_atlas_validate_entity.verdicts.VerdictEngine.rules", rules=["VEV-03"])
async def test__the_search_walk_pages_to_the_end_marker(engine_settings: ValidateEntitySettings) -> None:
    """The walk starts at ``*``, follows the server's markers, and stops at ``-1`` (VEV-03, SRC-08)."""
    catalogue = FakeCatalogue()
    pages = iter(
        [
            FakeCatalogue.json(200, search_result([NAME_RULE], "second")),
            FakeCatalogue.json(200, search_result([EXPRESSION_RULE], "-1")),
        ]
    )
    catalogue.handler = lambda _request: next(pages)
    engine, http = _engine(catalogue, engine_settings)

    entries = await engine.rules()
    await http.aclose()

    assert sum(1 for entry in entries if entry.check is not None) == 1
    assert sum(1 for entry in entries if entry.check is None) == 1
    markers = [json.loads(request.content)["marker"] for request in catalogue.searches()]
    assert markers == ["*", "second"]


@pytest.mark.covers("aurelius_atlas_validate_entity.verdicts.VerdictEngine.rules", rules=["VEV-03"])
async def test__the_search_asks_the_governance_type_and_its_attributes(
    engine_settings: ValidateEntitySettings,
) -> None:
    """The request names the type and exactly the attributes the vocabulary reads (VEV-03)."""
    catalogue = FakeCatalogue()
    _one_page(catalogue)
    engine, http = _engine(catalogue, engine_settings)

    await engine.rules()
    await http.aclose()

    body = json.loads(catalogue.searches()[0].content)
    assert body["typeName"] == "m4i_gov_data_quality"
    assert body["attributes"] == list(RULE_ATTRIBUTES)
    assert body["includeSubTypes"] is False


@pytest.mark.covers("aurelius_atlas_validate_entity.verdicts.VerdictEngine.rules", rules=["VEV-05"])
async def test__a_fresh_cache_window_answers_without_reading(engine_settings: ValidateEntitySettings) -> None:
    """Two calls in one window read once; the drafts still answer live each time (VEV-05)."""
    catalogue = FakeCatalogue()
    _one_page(catalogue, NAME_RULE)
    engine, http = _engine(catalogue, engine_settings)

    missing = await engine.evaluate_draft(_draft({}))
    filled = await engine.evaluate_draft(_draft({"name": "x"}))
    await http.aclose()

    assert len(catalogue.searches()) == 1
    assert missing.verdicts[0].compliant is False
    assert filled.verdicts[0].compliant is True


@pytest.mark.covers("aurelius_atlas_validate_entity.verdicts.VerdictEngine.rules", rules=["VEV-05"])
async def test__a_zero_window_reads_every_time() -> None:
    """``RULES_CACHE_SECONDS=0`` turns the cache off: every call reads again (VEV-05)."""
    settings = ValidateEntitySettings(
        auth_server_url=HttpUrl("http://issuer.test"),
        server_base_url=HttpUrl("http://catalogue.test"),
        rules_cache_seconds=0,
    )
    catalogue = FakeCatalogue()
    _one_page(catalogue, NAME_RULE)
    engine, http = _engine(catalogue, settings)

    await engine.rules()
    await engine.rules()
    await http.aclose()

    assert len(catalogue.searches()) == 2


@pytest.mark.covers("aurelius_atlas_validate_entity.verdicts.VerdictEngine.rules", rules=["VEV-05", "VEV-06"])
async def test__a_failed_read_caches_nothing_and_answers_502(engine_settings: ValidateEntitySettings) -> None:
    """A refused search is the 502 of VEV-06, and the next call reads again (VEV-05)."""
    catalogue = FakeCatalogue()
    answers = iter([FakeCatalogue.json(500, {}), FakeCatalogue.json(200, search_result([], "-1"))])
    catalogue.handler = lambda _request: next(answers)
    engine, http = _engine(catalogue, engine_settings)

    with pytest.raises(UpstreamError) as raised:
        await engine.rules()
    rules = await engine.rules()
    await http.aclose()

    assert raised.value.status_code == 502
    assert len(catalogue.searches()) == 2
    assert rules == ()


@pytest.mark.covers("aurelius_atlas_validate_entity.verdicts.VerdictEngine.rules", rules=["VEV-06"])
async def test__outages_open_the_circuit_and_a_fact_resets_the_count(engine_settings: ValidateEntitySettings) -> None:
    """Outages count toward the open circuit; a 4xx fact answers and resets the count (VEV-06, DD-500).

    With fail_max at two: the outage that crosses the threshold opens the circuit and is itself
    answered as fast-failing (pybreaker replaces the failure it opens on), and the open circuit
    answers without calling. A 400 fact is excluded: refused, and back to one outage short.
    """
    catalogue = FakeCatalogue()
    mode = {"value": "outage"}
    catalogue.handler = lambda _request: {"outage": FakeCatalogue.json(500, {}), "fact": FakeCatalogue.json(400, {})}[
        mode["value"]
    ]
    engine, http = _engine(catalogue, engine_settings)

    with pytest.raises(UpstreamError) as raised:  # one outage short: refused, counted
        await engine.rules()
    assert "fast-failing" not in str(raised.value)
    mode["value"] = "fact"
    with pytest.raises(UpstreamError):  # the 400 answers as a fact: refused, and the count resets (excluded)
        await engine.rules()
    mode["value"] = "outage"
    with pytest.raises(UpstreamError) as raised:  # one short again — the fact reset it, not two counted
        await engine.rules()
    assert "fast-failing" not in str(raised.value)
    with pytest.raises(UpstreamError) as raised:  # crossing fail_max: this outage opens the circuit
        await engine.rules()
    assert "fast-failing" in str(raised.value)
    calls_before = len(catalogue.searches())
    with pytest.raises(UpstreamError) as raised:
        await engine.rules()
    await http.aclose()

    assert "fast-failing" in str(raised.value)
    assert len(catalogue.searches()) == calls_before  # the open circuit answered without calling


@pytest.mark.covers(
    "aurelius_atlas_validate_entity.verdicts._draft_record",
    rules=["VEV-08"],
)
async def test__the_picks_landed_on_a_picker_answer_its_rule(engine_settings: ValidateEntitySettings) -> None:
    """The draft's relationship picks ride the record the check reads (VEV-08, DD-632).

    The corpus's ``length('fields', 1)`` shape: a list of entries holds content by
    its length and a cleared picker (``null``) holds none — ASG-04's reading of a
    stored entity's ends, kept for the draft's own picks. A key the draft does not
    carry is a missing value, and an empty list stays no content: the picker's
    answer changes with what the person picks (EDT-23's trigger).
    """
    catalogue = FakeCatalogue()
    _one_page(catalogue, FIELDS_RULE)
    engine, http = _engine(catalogue, engine_settings)

    empty = await engine.evaluate_draft(_draft({"name": "Sales Orders"}))
    picked = await engine.evaluate_draft(
        _draft({"name": "Sales Orders"}, relationships={"fields": [{"guid": "f1", "typeName": "m4i_field"}]})
    )
    cleared = await engine.evaluate_draft(_draft({"name": "Sales Orders"}, relationships={"fields": None}))
    zero = await engine.evaluate_draft(_draft({"name": "Sales Orders"}, relationships={"fields": []}))
    await http.aclose()

    assert [verdict.compliant for verdict in empty.verdicts] == [False]
    assert [verdict.compliant for verdict in picked.verdicts] == [True]
    assert [verdict.compliant for verdict in cleared.verdicts] == [False]
    assert [verdict.compliant for verdict in zero.verdicts] == [False]
    assert picked.verdicts[0].message == "This dataset has at least one field"


@pytest.mark.covers(
    "aurelius_atlas_validate_entity.verdicts._draft_record",
    rules=["VEV-08"],
)
async def test__a_draft_value_carried_wrapped_reads_bare(engine_settings: ValidateEntitySettings) -> None:
    """A ``{"raw": …}`` draft value is the value: the unwrapping the rule read always applied (VEV-08, DD-632).

    A wrapped empty used to count as content (a non-empty dict), flipping compliance —
    the same DV-132 wrapper the rule attributes read bare since 12.7.
    """
    catalogue = FakeCatalogue()
    _one_page(catalogue, FIELDS_RULE)
    engine, http = _engine(catalogue, engine_settings)

    wrapped_empty = await engine.evaluate_draft(_draft({"name": "x"}, relationships={"fields": {"raw": []}}))
    wrapped_one = await engine.evaluate_draft(
        _draft({"name": "x"}, relationships={"fields": {"raw": [{"guid": "f1"}]}})
    )
    await http.aclose()

    assert [verdict.compliant for verdict in wrapped_empty.verdicts] == [False]
    assert [verdict.compliant for verdict in wrapped_one.verdicts] == [True]


@pytest.mark.covers(
    "aurelius_atlas_validate_entity.verdicts._draft_record",
    rules=["VEV-08"],
)
async def test__a_relationship_without_picks_is_no_value_for_a_presence_rule(
    engine_settings: ValidateEntitySettings,
) -> None:
    """The empty picker answers its presence rule as absent: the childDataset case (VEV-08, DD-634).

    The corpus rule reads ``completeness('childDataset')`` and its own description says
    "is not None and is not empty". The empty section of the opened view rides the draft
    as ``[]`` (DD-632), which 12.7a first shipped as a value, so the drawer painted
    "This entity has a childDataset" under a picker holding nothing. An empty list — and
    a wrapped empty — carries no value: the rule misses, and the line rides only once a
    child is actually picked.
    """
    catalogue = FakeCatalogue()
    _one_page(catalogue, CHILD_RULE)
    engine, http = _engine(catalogue, engine_settings)

    empty = await engine.evaluate_draft(_draft({"name": "Sales Orders"}, relationships={"childDataset": []}))
    wrapped_empty = await engine.evaluate_draft(
        _draft({"name": "Sales Orders"}, relationships={"childDataset": {"raw": []}}),
    )
    cleared = await engine.evaluate_draft(_draft({"name": "Sales Orders"}, relationships={"childDataset": None}))
    picked = await engine.evaluate_draft(
        _draft({"name": "Sales Orders"}, relationships={"childDataset": [{"guid": "c-1", "typeName": "m4i_dataset"}]}),
    )
    await http.aclose()

    assert [verdict.compliant for verdict in empty.verdicts] == [False]
    assert empty.verdicts[0].message == "This entity is missing a childDataset"
    assert [verdict.compliant for verdict in wrapped_empty.verdicts] == [False]
    assert [verdict.compliant for verdict in cleared.verdicts] == [False]
    assert [verdict.compliant for verdict in picked.verdicts] == [True]
    assert picked.verdicts[0].message == "This entity has a childDataset"


@pytest.mark.covers(
    "aurelius_atlas_validate_entity.verdicts.VerdictEngine.evaluate_draft",
    rules=["VEV-09"],
)
async def test__the_alternatives_of_an_or_rule_travel_on_its_verdict(
    engine_settings: ValidateEntitySettings,
) -> None:
    """The paired corpus rule answers once by either name and carries the other to the screen (VEV-09, DV-171).

    ``length('fields', 1) | length('childDataset', 1)`` reads as GQ-06's anyOf pair:
    the draft with no field and one picked child passes, and the verdict names
    ``fields`` with ``childDataset`` among its alternatives, so the editor paints the
    one line under both pickers.
    """
    catalogue = FakeCatalogue()
    _one_page(catalogue, PAIR_RULE)
    engine, http = _engine(catalogue, engine_settings)

    bare = await engine.evaluate_draft(_draft({"name": "Sales Orders"}))
    child = await engine.evaluate_draft(
        _draft({"name": "Sales Orders"}, relationships={"childDataset": [{"guid": "c-1", "typeName": "m4i_dataset"}]}),
    )
    await http.aclose()

    assert [verdict.compliant for verdict in bare.verdicts] == [False]
    assert bare.verdicts[0].attribute == "fields"
    assert bare.verdicts[0].any_of == ["childDataset"]
    assert [verdict.compliant for verdict in child.verdicts] == [True]
    assert child.verdicts[0].message == "This dataset has a field or a child dataset"
