"""The rules door: the paged read, the cache, the assembly, the breaker (VEV-02/03/05/06; DD-498, DD-500).

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
        "active": True,
        "dqcheckkind": "ATTRIBUTE_PRESENT",
        "dqattribute": "name",
        "compliantMessage": "This entity has a name",
    },
)
INACTIVE_RULE = rule_entity(
    "rule-inactive",
    "Turned off",
    {"name": "Turned off", "active": False, "dqcheckkind": "ATTRIBUTE_PRESENT", "dqattribute": "owner"},
)
EXPRESSION_RULE = rule_entity(
    "rule-expression",
    "Legacy expression",
    {"name": "Legacy expression", "expression": "uniqueness('qualifiedName')"},
)
WRONG_KIND_RULE = rule_entity(
    "rule-wrong-kind",
    "Unknown kind",
    {"name": "Unknown kind", "dqcheckkind": "REGEX_MATCH", "dqattribute": "name"},
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

    answer = await engine.evaluate_draft({"name": "Sales Orders"})
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

    answer = await engine.evaluate_draft({"name": "x"})
    await http.aclose()

    assert [verdict.rule_guid for verdict in answer.verdicts] == ["rule-name"]
    assert answer.unread_rules == []


@pytest.mark.covers("aurelius_atlas_validate_entity.verdicts.VerdictEngine.rules", rules=["VEV-03"])
async def test__an_unread_rule_rides_the_unread_list_never_executed(engine_settings: ValidateEntitySettings) -> None:
    """The stored expression rule and the foreign kind are recorded with the cause, not run (VEV-03, DV-146)."""
    catalogue = FakeCatalogue()
    _one_page(catalogue, EXPRESSION_RULE, WRONG_KIND_RULE)
    engine, http = _engine(catalogue, engine_settings)

    answer = await engine.evaluate_draft({"name": "x"})
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

    rules = await engine.rules()
    await http.aclose()

    assert len(rules.rules) == 1
    assert len(rules.unread) == 1
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

    missing = await engine.evaluate_draft({})
    filled = await engine.evaluate_draft({"name": "x"})
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
    assert rules.rules == ()


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
