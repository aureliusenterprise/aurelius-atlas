"""The catalogue door (DQS-02, DQS-03, DQS-06): paging, the ACTIVE filter, the binding walk, one write."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_model.instance import AtlasEntity
from aurelius_atlas_quality import rule_from_atlas_attributes
from aurelius_atlas_quality_scanner.catalogue import (
    RULE_ATTRIBUTES,
    bind_datasets,
    fetch_rules,
    is_active,
    rule_attributes,
    write_scores,
)
from aurelius_atlas_quality_scanner.records import score_entity
from aurelius_atlas_quality_scanner.settings import ScannerSettings
from aurelius_atlas_server_client import AtlasClient
from fake_catalogue import FakeCatalogue, entity_with_fields, field_with_datasets, related, rule_header


def _attrs(name: str = "rule", **extra: Any) -> dict[str, Any]:  # noqa: ANN401 - attribute values are untyped JSON
    """A stored rule's attributes: an ACTIVE ``not_null`` over ``total``, plus what a test names."""
    values: dict[str, Any] = {
        "name": name,
        "active": True,
        "dqcheckkind": "COLUMN_NOT_NULL_RATIO",
        "dqcolumn": "total",
    }
    values.update(extra)
    return values


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue.fetch_rules", rules=["DQS-02"])
async def test_the_rules_arrive_paged_to_the_end(
    client: AtlasClient, catalogue: FakeCatalogue, settings: Callable[..., ScannerSettings]
) -> None:
    """DQS-02: the search is followed by marker until the end marker, across every page."""
    catalogue.add_rule_page([rule_header("r1", _attrs("r1"))])
    catalogue.add_rule_page([rule_header("r2", _attrs("r2")), rule_header("r3", _attrs("r3"))])
    entries = await fetch_rules(client, settings(search_limit=2))
    assert [entry.guid for entry in entries] == ["r1", "r2", "r3"]
    assert catalogue.search_calls == 2  # two pages for three rules at a page of two


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue.fetch_rules", rules=["DQS-02"])
async def test_the_end_marker_alone_ends_the_walk(
    client: AtlasClient, catalogue: FakeCatalogue, settings: Callable[..., ScannerSettings]
) -> None:
    """DQS-02: the server's ``-1`` after the last page stops the walk; a page never re-reads."""
    catalogue.add_rule_page([rule_header("r1", _attrs())])
    entries = await fetch_rules(client, settings())
    assert len(entries) == 1
    assert catalogue.search_calls == 1  # the short page answers "-1": no second search


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue.fetch_rules", rules=["DQS-02"])
async def test_a_rule_of_no_next_marker_page_is_still_read(settings: Callable[..., ScannerSettings]) -> None:
    """DQS-02: a search that answers no marker ends the walk too — both stop shapes are read."""

    class NoEndMarker(FakeCatalogue):
        def _search(self, request: httpx.Request) -> httpx.Response:
            response = super()._search(request)
            body = response.json() if request.method == "POST" else {}
            body["nextMarker"] = None
            return httpx.Response(200, json=body)

    fake = NoEndMarker()
    fake.add_rule_page([rule_header("r1", _attrs())])
    http = httpx.AsyncClient(base_url="http://atlas.test", transport=fake.transport())
    entries = await fetch_rules(AtlasClient(http, "token"), settings())
    assert [entry.guid for entry in entries] == ["r1"]
    assert fake.search_calls == 1


@pytest.mark.parametrize(
    ("active", "expected"),
    [(True, True), (False, False), (None, True), ("false", True), ({"raw": False}, False)],
)
@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue.is_active", rules=["DQS-02"])
def test_only_the_boolean_false_is_not_active(
    active: Any,  # noqa: ANN401 - attribute values are untyped JSON
    expected: bool,  # noqa: FBT001 - the parametrised pair is (given, expected)
) -> None:
    """DQS-02: a missing, text or wrapped-active rule still runs; only the boolean false does not."""
    attributes = _attrs() if active is None else _attrs(active=active)
    assert is_active(attributes) is expected


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue.fetch_rules", rules=["DQS-02"])
async def test_an_inactive_rule_comes_back_neither_parsed_nor_scannable(
    client: AtlasClient, catalogue: FakeCatalogue, settings: Callable[..., ScannerSettings]
) -> None:
    """DQS-02: the search answers inactive rules too; the door marks them left out, not errors."""
    catalogue.add_rule_page([rule_header("r1", _attrs("r1", active=False))])
    entries = await fetch_rules(client, settings())
    assert entries[0].active is False
    assert entries[0].rule is None
    assert entries[0].parse_error is None


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue.fetch_rules", rules=["DQS-02", "DQS-08"])
async def test_a_rule_the_vocabulary_cannot_read_carries_its_error(
    client: AtlasClient, catalogue: FakeCatalogue, settings: Callable[..., ScannerSettings]
) -> None:
    """DQS-02/DQS-08: a rule with no kind still comes back, with the cause to name in its ERROR."""
    catalogue.add_rule_page([rule_header("r1", {"name": "legacy", "active": True})])
    entries = await fetch_rules(client, settings())
    assert entries[0].active is True
    assert entries[0].rule is None
    assert "vocabulary" in (entries[0].parse_error or "")


@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue.rule_attributes", rules=["DQS-02"])
def test_the_stored_defaults_of_foreign_kind_parameters_are_left_out() -> None:
    """DQS-02/DD-461: the store stamps every primitive (EWR-09); a known kind keeps only its own."""
    stamped = _attrs("r1", dqmin=0.0, dqmax=0.0, dqmaxAgeHours=0.0, dqminColumns=0, dqpattern="", dqotherColumn="")
    plain = rule_attributes(stamped)
    assert plain["dqcolumn"] == "total"  # the kind's own parameter stays
    for foreign in ("dqmin", "dqmax", "dqmaxAgeHours", "dqminColumns", "dqpattern", "dqotherColumn"):
        assert foreign not in plain
    rule = rule_from_atlas_attributes(plain)  # the bridge reads it: a rule, not an ERROR
    assert rule.kind.value == "COLUMN_NOT_NULL_RATIO"
    assert dict(rule.params) == {"column": "total"}


@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue.rule_attributes", rules=["DQS-08"])
def test_an_unknown_kind_keeps_every_attribute_for_the_bridges_error() -> None:
    """DQS-08/DD-461: nothing is dropped for a kind the vocabulary does not know — the cause stays the bridge's."""
    plain = rule_attributes({"name": "x", "dqcheckkind": "COLUMN_WEIRD", "dqmin": 3.0})
    assert plain["dqmin"] == 3.0
    assert "dqmin" in json.dumps(plain)


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue.fetch_rules", rules=["DQS-02"])
async def test_the_search_asks_only_for_attributes_the_type_holds(
    client: AtlasClient, catalogue: FakeCatalogue, settings: Callable[..., ScannerSettings]
) -> None:
    """DQS-02: the store refuses a search for an attribute the type lacks, so none is asked (DD-454)."""
    catalogue.add_rule_page([rule_header("r1", _attrs())])
    await fetch_rules(client, settings())
    body = json.loads(catalogue.requests[0].content)
    assert set(body["attributes"]) == set(RULE_ATTRIBUTES)
    assert "fields" not in body["attributes"]  # DQS-03: the bulk read is the door to the rule's fields


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue.bind_datasets", rules=["DQS-03"])
async def test_a_rule_reaches_its_datasets_through_its_fields(
    client: AtlasClient, catalogue: FakeCatalogue, settings: Callable[..., ScannerSettings]
) -> None:
    """DQS-03: rule -> ``fields`` -> each field's ``datasets``, first-seen, with the qualified names."""
    catalogue.add_rule_page([rule_header("r1", _attrs())])
    catalogue.rules["r1"] = entity_with_fields("r1", [related("f1", "/d3.total")])
    catalogue.fields["f1"] = field_with_datasets("f1", [related("d2", "/d2"), related("d1", "/d1")])
    entries = await fetch_rules(client, settings())
    datasets = await bind_datasets(client, entries)
    assert entries[0].datasets == [datasets["d2"], datasets["d1"]]  # first-seen order, not sorted
    assert {ref.qualified_name for ref in datasets.values()} == {"/d1", "/d2"}


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue.bind_datasets", rules=["DQS-03"])
async def test_a_dataset_reached_by_two_fields_is_held_once(
    client: AtlasClient, catalogue: FakeCatalogue, settings: Callable[..., ScannerSettings]
) -> None:
    """DQS-03: two fields of one rule that reach the same dataset bind it once."""
    catalogue.add_rule_page([rule_header("r1", _attrs())])
    catalogue.rules["r1"] = entity_with_fields("r1", [related("f1", "a"), related("f2", "b")])
    catalogue.fields["f1"] = field_with_datasets("f1", [related("d3", "/d3")])
    catalogue.fields["f2"] = field_with_datasets("f2", [related("d3", "/d3")])
    entries = await fetch_rules(client, settings())
    await bind_datasets(client, entries)
    assert [ref.guid for ref in entries[0].datasets] == ["d3"]


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue.bind_datasets", rules=["DQS-03"])
async def test_a_rule_with_no_fields_stays_unbound(
    client: AtlasClient, catalogue: FakeCatalogue, settings: Callable[..., ScannerSettings]
) -> None:
    """DQS-03: a rule that reaches no dataset through its fields binds nothing; the scan skips it."""
    catalogue.add_rule_page([rule_header("r1", _attrs())])
    catalogue.rules["r1"] = entity_with_fields("r1", [])
    entries = await fetch_rules(client, settings())
    datasets = await bind_datasets(client, entries)
    assert entries[0].datasets == []
    assert datasets == {}


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue.write_scores", rules=["DQS-06"])
async def test_the_scores_leave_in_one_bulk_write(client: AtlasClient, catalogue: FakeCatalogue) -> None:
    """DQS-06: every entity of the run leaves through one bulk write, keys and all."""
    entities = [
        score_entity({"ruleGuid": "r1", "datasetGuid": "d3", "runId": "x", "runAtMs": 1, "score": 1.0, "passed": True}),
        score_entity({"ruleGuid": None, "datasetGuid": "d3", "runId": "x", "runAtMs": 1, "score": 1.0}),
    ]
    await write_scores(client, entities)
    assert catalogue.write_requests == 1
    assert set(catalogue.written_by_key()) == {"d3/r1", "d3/overall"}


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue.write_scores", rules=["DQS-06"])
async def test_nothing_is_written_for_no_entities(client: AtlasClient, catalogue: FakeCatalogue) -> None:
    """DQS-06: a scan with nothing to store sends no write at all."""
    await write_scores(client, [])
    assert catalogue.write_requests == 0


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue._by_guids", rules=["DQS-03"])
async def test_no_guids_means_no_bulk_read(client: AtlasClient, catalogue: FakeCatalogue) -> None:
    """DQS-03: the bulk route refuses an empty GUID list, so no read is sent for no rules."""
    from aurelius_atlas_quality_scanner.catalogue import _by_guids  # noqa: PLC0415 - the door under test

    assert await _by_guids(client, []) == []
    assert catalogue.requests == []


@pytest.mark.asyncio
@pytest.mark.covers("aurelius_atlas_quality_scanner.catalogue.bind_datasets", rules=["DQS-03"])
async def test_a_dangling_relationship_fails_the_run(
    client: AtlasClient, catalogue: FakeCatalogue, settings: Callable[..., ScannerSettings]
) -> None:
    """DQS-03/DD-457: a field the catalogue no longer holds fails its bulk read — a catalogue fault, not a skip."""
    from aurelius_atlas_server_client import AtlasClientError  # noqa: PLC0415 - the failure under test

    catalogue.add_rule_page([rule_header("r1", _attrs())])
    catalogue.rules["r1"] = entity_with_fields("r1", [related("f1", "gone")])  # f1 is not in the catalogue
    entries = await fetch_rules(client, settings())
    with pytest.raises(AtlasClientError):
        await bind_datasets(client, entries)


def test_a_score_document_survives_the_client_write_model() -> None:
    """DQS-06: the entity the door writes serialises the way the bulk route reads it — no GUID, attributes whole."""
    entity = score_entity(
        {"ruleGuid": "r1", "datasetGuid": "d3", "runId": "x", "runAtMs": 1, "score": 0.5, "passed": False}
    )
    assert isinstance(entity, AtlasEntity)
    wire = entity.to_json()
    assert wire["attributes"]["scoreKey"] == "d3/r1"
    assert str(wire["guid"]).startswith("-")  # DQS-06: a temp internal id; the store resolves it by the unique key
    assert wire["typeName"] == "m4i_dq_score"
