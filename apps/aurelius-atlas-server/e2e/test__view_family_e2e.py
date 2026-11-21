"""The view family's doors through the client library, against the container (AVR-01, AVR-08, AVR-10, CLV).

A results page's request (query, type filter, facets, a sort) through the client's search door, and the
details read of one of its cards through the client's read door: the same entity, answering the same fields
(AVR-08, ADR 064), each answer parsed into ``aurelius-atlas-model``'s card and view models (DD-309, CL-11).
The entities are namespaced to the run and removed with the session's other writes (ECU-01).
"""

import uuid
from collections.abc import Callable

import pytest
from aurelius_atlas_model.instance import AtlasEntity, AtlasEntityWithExtInfo, EntityOperation
from aurelius_atlas_server_client import AtlasClient, AtlasClientError, ViewSearchRequest

NIL = "00000000-0000-0000-0000-000000000000"

SHARED = (
    "guid",
    "type_name",
    "super_type_names",
    "name",
    "qualified_name",
    "display_text",
    "type_alias",
    "status",
    "labels",
)
"""The fields both doors answer, in the model library's names (AVR-08)."""


async def make(api: AtlasClient, type_name: str, run: str, **attributes: str) -> str:
    """An entity of ``type_name`` named for ``run``, created as the writer; its GUID."""
    body = AtlasEntityWithExtInfo(
        entity=AtlasEntity(type_name=type_name, attributes={"qualifiedName": f"{run}.{type_name}", **attributes})
    )
    created = await api.entity.create_or_update(body)
    header = created.get_first_entity_by_operation(EntityOperation.CREATE)
    assert header is not None
    assert header.guid is not None
    return header.guid


# impact=severe, likelihood=low (the spine path moves rarely between increments)
@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_server_client.client.ViewApi.search",
    "aurelius_atlas_server.routes.view_search.search",
    rules=["AVR-01", "AVR-08", "CLV-04"],
)
async def test__a_results_request_answers_cards_facets_and_a_total(
    api: AtlasClient, anonymous_api: AtlasClient, reader_token: Callable[[], str]
) -> None:
    """The dev store's door: words of a run's name, typed out, faceted and sorted; a reader reads; an anonymous 401."""
    run = uuid.uuid4().hex
    domain = await make(api, "m4i_data_domain", run, name=f"view door {run}", definition="orders of the door")
    table = await make(api, "Asset", run, name=f"view asset {run}")

    answer = await api.view.search(
        ViewSearchRequest(
            query=run,
            filters={"typeName": ["m4i_data_domain", "Asset"]},
            facets=["typeName"],
            sort={"createTime": "desc"},
        )
    )

    assert answer.total == 2
    assert {card.guid for card in answer.cards} == {domain, table}
    assert answer.cards[0].create_time is not None
    assert answer.cards[1].create_time is not None
    assert answer.cards[0].create_time >= answer.cards[1].create_time
    assert {entry["value"]: entry["count"] for entry in answer.facets["typeName"]} == {
        "m4i_data_domain": 1,
        "Asset": 1,
    }

    typed = await api.view.search(ViewSearchRequest(filters={"typeName": "m4i_data_domain"}, query=run))
    assert [card.guid for card in typed.cards] == [domain]

    reader = api.with_token(reader_token)
    assert (await reader.view.search(ViewSearchRequest(limit=1))).total >= 0
    with pytest.raises(AtlasClientError) as refused:
        await anonymous_api.view.search(ViewSearchRequest())
    assert refused.value.status_code == 401


# impact=severe, likelihood=low (the spine path moves rarely between increments)
@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_server_client.client.ViewApi.search",
    "aurelius_atlas_server_client.client.ViewApi.read",
    "aurelius_atlas_server.routes.view_search.search",
    "aurelius_atlas_server.routes.view_entity.read",
    rules=["AVR-08", "AVR-10", "MMS-09", "CLV-01", "CLV-04"],
)
async def test__the_details_read_of_a_card_agrees_with_the_search_door(
    api: AtlasClient, reader_token: Callable[[], str]
) -> None:
    """One entity read through both doors: the same shared fields; a GUID of none answers the Atlas 404 (AVR-10)."""
    run = uuid.uuid4().hex
    guid = await make(
        api,
        "m4i_data_entity",
        run,
        name=f"view read {run}",
        definition="read through one door",
        typeAlias="Viewed entity",  # the alias rides both doors (MMS-09, DD-721)
    )

    answer = await api.view.search(ViewSearchRequest(query=run))
    (card,) = answer.cards
    assert card.guid == guid

    view = await api.view.read(guid)
    assert {field: getattr(card, field) for field in SHARED} == {field: getattr(view, field) for field in SHARED}
    assert view.attributes["definition"] == "read through one door"

    reader = api.with_token(reader_token)
    assert (await reader.view.read(guid)).guid == guid

    with pytest.raises(AtlasClientError) as missing:
        await api.view.read(NIL)
    assert missing.value.status_code == 404
    assert missing.value.info is not None
    assert missing.value.info.error_code == "ATLAS-404-00-005"
