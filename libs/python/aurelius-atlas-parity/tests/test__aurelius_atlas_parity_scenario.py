from collections.abc import Callable
from pathlib import Path

import pytest
from aurelius_atlas_parity.scenario import (
    DEVIATION_PROPERTY,
    ENDPOINT_PROPERTY,
    Deviation,
    Request,
    ScenarioError,
    read_scenario,
)

type WriteScenario = Callable[[str, str], Path]

FULL = """
name: Create an entity and read it back
source:
  - webapp/src/main/java/org/apache/atlas/web/rest/EntityREST.java#createOrUpdate
  - webapp/src/main/java/org/apache/atlas/web/rest/EntityREST.java#getById
rules: [ABC-01]
covers: [aurelius_atlas_parity.run.run_scenario]
stages:
  - name: create
    request:
      method: POST
      url: /api/entities
      json: {name: x}
    response:
      status: 200
      headers: {content-type: application/json}
      json: {guid: "-", name: x, createTime: 0}
      volatile: [$.guid, $.createTime]
      save: {guid: $.guid}
  - request:
      method: GET
      url: /api/entities/{guid}?ignored=1
      params: {a: "1", b: ["2", "3"]}
      headers: {x-test: "yes"}
    response:
      status: 404
      json: null
      deviations:
        - {id: DV-01, path: $, value: {errorCode: ATLAS-404-00-005}}
        - {id: DV-02, path: $.errorMessage, absent: true}
        - {id: DV-01, path: $.other, value: 1}
  - request: {method: GET, url: /api/ping, text: hello}
    response: {status: 200, text: pong}
"""


@pytest.mark.covers("aurelius_atlas_parity.scenario.read_scenario", rules=["SCN-01", "SCN-02", "SCN-04"])
def test__read_scenario_reads_every_part(write_scenario: WriteScenario) -> None:
    """A full scenario reads into its model; its id is its path below the directory, without the suffix."""
    file = write_scenario("entity/create.scenario.yaml", FULL)

    scenario = read_scenario(file, file.parent.parent)

    assert scenario.id == "entity/create"
    assert str(scenario) == "entity/create"
    assert scenario.source[0].endswith("#createOrUpdate")
    assert scenario.rules == ["ABC-01"]
    assert scenario.covers == ["aurelius_atlas_parity.run.run_scenario"]
    create, read, ping = scenario.stages
    assert create.name == "create"
    assert create.request.json_body == {"name": "x"}
    assert create.response.volatile == ["$.guid", "$.createTime"]
    assert create.response.save == {"guid": "$.guid"}
    assert read.name is None
    assert read.request.params == {"a": "1", "b": ["2", "3"]}
    assert read.response.has_json
    assert read.response.json_body is None
    assert [deviation.id for deviation in read.response.deviations] == ["DV-01", "DV-02", "DV-01"]
    assert ping.request.text == "hello"
    assert not ping.response.has_json


@pytest.mark.covers(
    "aurelius_atlas_parity.scenario.Scenario.properties", "aurelius_atlas_parity.scenario.Request.endpoint"
)
def test__properties_name_each_endpoint_and_deviation_once(write_scenario: WriteScenario) -> None:
    """Endpoints keep the URL before substitution without its query; repeated ones appear once (SCN-14)."""
    file = write_scenario("create.scenario.yaml", FULL)

    assert read_scenario(file, file.parent).properties() == [
        (ENDPOINT_PROPERTY, "POST /api/entities"),
        (ENDPOINT_PROPERTY, "GET /api/entities/{guid}"),
        (ENDPOINT_PROPERTY, "GET /api/ping"),
        (DEVIATION_PROPERTY, "DV-01"),
        (DEVIATION_PROPERTY, "DV-02"),
    ]


@pytest.mark.covers("aurelius_atlas_parity.scenario.Request.endpoint", rules=["SCN-14"])
def test__request_endpoint_is_method_and_path() -> None:
    """The endpoint of a request is its method and its URL up to the query."""
    assert Request(method="DELETE", url="/v2/entity/guid/{guid}?purge=true").endpoint == "DELETE /v2/entity/guid/{guid}"


@pytest.mark.covers("aurelius_atlas_parity.scenario.Deviation.json_path")
def test__deviation_json_path_is_parsed() -> None:
    """A deviation's path is available parsed."""
    deviation = Deviation(id="DV-01", path="$.a[0]", absent=True)

    assert deviation.json_path.segments == ("a", 0)


MINIMAL_STAGE = "stages: [{request: {method: GET, url: /x}, response: {status: 200}}]\n"


@pytest.mark.covers("aurelius_atlas_parity.scenario.read_scenario", rules=["SCN-03"])
@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("name: x\n" + MINIMAL_STAGE, "source: Field required"),
        ("name: x\nsource: []\n" + MINIMAL_STAGE, "source: List should have at least 1 item"),
        ("name: x\nsource: [a]\nstages: []\n", "stages: List should have at least 1 item"),
        ("name: x\nsource: [a]\nowner: me\n" + MINIMAL_STAGE, "owner: Extra inputs are not permitted"),
        ("name: x\nsource: [a]\nid: other\n" + MINIMAL_STAGE, "id: a scenario's id is its path"),
        ("name: x\nname: y\nsource: [a]\n" + MINIMAL_STAGE, "duplicate key 'name'"),
        ("- just\n- a list\n", "a scenario is a mapping"),
        ("name: [unclosed\n", "expected ',' or ']'"),
        (
            "name: x\nsource: [a]\nstages: [{request: {method: FETCH, url: /x}, response: {status: 200}}]\n",
            "stages.0.request.method: Input should be 'GET'",
        ),
        (
            "name: x\nsource: [a]\nstages: [{request: {method: GET, url: x}, response: {status: 200}}]\n",
            "stages.0.request.url: String should match pattern",
        ),
        (
            (
                "name: x\nsource: [a]\nstages: [{request: {method: GET, url: /x, json: 1, text: a}, "
                "response: {status: 200}}]\n"
            ),
            "give at most one of 'json' and 'text'",
        ),
        (
            (
                "name: x\nsource: [a]\nstages: [{request: {method: GET, url: /x}, response: {status: 200, "
                "volatile: [$.a]}}]\n"
            ),
            "need a 'json' body",
        ),
        (
            (
                "name: x\nsource: [a]\nstages: [{request: {method: GET, url: /x}, response: {status: 200, json: {}, "
                "volatile: [guid]}}]\n"
            ),
            "'guid' is not a path",
        ),
        (
            (
                "name: x\nsource: [a]\nstages: [{request: {method: GET, url: /x}, response: {status: 200, json: {}, "
                "save: {guid: $..guid}}}]\n"
            ),
            "is not a path",
        ),
        (
            (
                "name: x\nsource: [a]\nstages: [{request: {method: GET, url: /x}, response: {status: 200, json: {}, "
                "deviations: [{id: DV-1, path: $, value: 1}]}}]\n"
            ),
            "deviations.0.id: String should match pattern",
        ),
        (
            (
                "name: x\nsource: [a]\nstages: [{request: {method: GET, url: /x}, response: {status: 200, json: {}, "
                "deviations: [{id: DV-01, path: $.a, value: 1, absent: true}]}}]\n"
            ),
            "give either 'value' or 'absent: true'",
        ),
        (
            (
                "name: x\nsource: [a]\nstages: [{request: {method: GET, url: /x}, response: {status: 200, json: {}, "
                "deviations: [{id: DV-01, path: x, absent: true}]}}]\n"
            ),
            "'x' is not a path",
        ),
        (
            (
                "name: x\nsource: [a]\nstages: [{request: {method: GET, url: /x}, response: {status: 200, "
                "json: {when: 2024-01-01}}}]\n"
            ),
            "stages.0.response.json",
        ),
        (
            "name: x\nsource: [a]\nstages: [{request: {method: GET, url: /x}, response: {status: 99}}]\n",
            "stages.0.response.status: Input should be greater than or equal to 100",
        ),
    ],
)
def test__read_scenario_names_the_file_and_the_problem(write_scenario: WriteScenario, text: str, problem: str) -> None:
    """Missing, empty, unknown or duplicate keys, bad paths and unquoted dates are refused with the file name."""
    file = write_scenario("bad.scenario.yaml", text)

    with pytest.raises(ScenarioError) as raised:
        read_scenario(file, file.parent)

    assert str(raised.value).startswith(f"{file}: ")
    assert problem in str(raised.value)
