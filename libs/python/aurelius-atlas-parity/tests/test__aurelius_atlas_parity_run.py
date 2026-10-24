from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_parity import Scenario, ScenarioError, ScenarioFailedError, load_scenarios, run_scenario
from aurelius_atlas_parity.run import check_response, substitute
from aurelius_atlas_parity.scenario import Response, read_scenario
from aurelius_atlas_parity.testing import SampleApp

type WriteScenario = Callable[[str, str], Path]

ROUND_TRIP = """
name: Create an entity, read it, delete it
source: [EntityREST.java#createOrUpdate]
stages:
  - name: create
    request: {method: POST, url: /api/entities, json: {name: table1}}
    response:
      status: 200
      headers: {Content-Type: application/json}
      json: {guid: "", name: table1, createTime: 0}
      volatile: [$.guid, $.createTime]
      save: {guid: $.guid, name: $.name}
  - name: read
    request: {method: GET, url: "/api/entities/{guid}"}
    response:
      status: 200
      json: {guid: "{guid}", name: "{name}", createTime: 0}
      volatile: [$.createTime]
  - name: delete
    request: {method: DELETE, url: "/api/entities/{guid}"}
    response: {status: 204}
  - name: gone
    request: {method: GET, url: "/api/entities/{guid}"}
    response:
      status: 404
      json: {errorCode: ATLAS-404-00-005, errorMessage: "{guid} not found"}
"""


def scenario_from(write_scenario: WriteScenario, text: str) -> Scenario:
    """Write one scenario file and read it back."""
    file = write_scenario("s.scenario.yaml", text)
    return read_scenario(file, file.parent)


@pytest.mark.covers("aurelius_atlas_parity.run.run_scenario", rules=["SCN-05", "SCN-06", "SCN-08", "SCN-09", "SCN-10"])
async def test__run_scenario_passes_a_matching_round_trip(
    write_scenario: WriteScenario, client: httpx.AsyncClient, app: SampleApp
) -> None:
    """Saved values flow into later URLs and expectations; volatile values and unlisted headers are not compared."""
    await run_scenario(scenario_from(write_scenario, ROUND_TRIP), client)

    assert app.requests == 4
    assert app.entities == {}


@pytest.mark.covers("aurelius_atlas_parity.run.run_scenario", rules=["SCN-02", "SCN-08"])
async def test__run_scenario_sends_params_headers_and_bodies(
    write_scenario: WriteScenario, client: httpx.AsyncClient
) -> None:
    """Query parameters (repeated too), headers and a text body reach the application."""
    scenario = scenario_from(
        write_scenario,
        """
        name: Echo
        source: [none]
        stages:
          - request: {method: GET, url: "/api/echo", params: {a: "1", b: ["2", "3"]}, headers: {X-Test: "yes"}}
            response: {status: 200, json: {params: {a: "1", b: "3"}, test: "yes"}}
          - request: {method: GET, url: /api/ping, text: "ignored"}
            response: {status: 200, text: pong, headers: {content-type: text/plain}}
        """,
    )

    await run_scenario(scenario, client)


@pytest.mark.covers("aurelius_atlas_parity.run.run_scenario", rules=["SCN-05", "SCN-11"])
async def test__run_scenario_lists_every_difference_and_stops(
    write_scenario: WriteScenario, client: httpx.AsyncClient, app: SampleApp
) -> None:
    """The failure names the scenario, stage and endpoint, lists each difference, and later stages do not run."""
    scenario = scenario_from(
        write_scenario,
        """
        name: Wrong expectations
        source: [AdminResource.java#getVersion]
        stages:
          - name: version
            request: {method: GET, url: /api/version}
            response:
              status: 201
              headers: {content-type: text/html}
              json: {Version: "2.3.0", Name: apache-atlas, Extra: 1}
          - request: {method: POST, url: /api/entities, json: {name: never}}
            response: {status: 200}
        """,
    )

    with pytest.raises(ScenarioFailedError) as raised:
        await run_scenario(scenario, client)

    assert str(raised.value).splitlines() == [
        "scenario s, stage 1 (version): GET /api/version",
        "  status: expected 201, got 200",
        "  header content-type: expected 'text/html', got 'application/json'",
        '  $.Version: expected "2.3.0", got "2.4.0"',
        "  $.Extra: expected 1, got (absent)",
        '  $.Description: expected (absent), got "Metadata"',
    ]
    assert app.requests == 1


@pytest.mark.covers("aurelius_atlas_parity.run.run_scenario", rules=["SCN-12"])
async def test__run_scenario_applies_deviations_to_the_expectation(
    write_scenario: WriteScenario, client: httpx.AsyncClient
) -> None:
    """The expectation holds the Atlas answer; deviations turn it into the Aurelius answer before comparing."""
    scenario = scenario_from(
        write_scenario,
        """
        name: Version with deviations
        source: [AdminResource.java#getVersion]
        stages:
          - request: {method: GET, url: /api/version}
            response:
              status: 200
              json: {Version: "2.4.0", Name: apache-atlas, Description: "Metadata Management", Revision: abc}
              deviations:
                - {id: DV-90, path: $.Description, value: Metadata}
                - {id: DV-91, path: $.Revision, absent: true}
        """,
    )

    await run_scenario(scenario, client)


@pytest.mark.covers("aurelius_atlas_parity.run.run_scenario", rules=["SCN-06", "SCN-07", "SCN-12"])
@pytest.mark.parametrize(
    ("response", "problem"),
    [
        (
            "{status: 200, json: {}, deviations: [{id: DV-01, path: $.nothing, absent: true}]}",
            "deviation DV-01 at $.nothing matches nothing in the expectation",
        ),
        ("{status: 200, json: {}, save: {x: $.missing}}", "$.Version: expected (absent)"),
        (
            '{status: 200, json: {Version: "2.4.0", Name: apache-atlas, Description: Metadata}, save: {x: "$[*]"}}',
            "save x: $[*] matches 3 values in the response, not one",
        ),
        ('{status: 200, json: "{unknown}"}', "{unknown} names no saved value; saved so far: nothing"),
    ],
)
async def test__run_scenario_fails_a_stage_that_cannot_be_checked(
    write_scenario: WriteScenario, client: httpx.AsyncClient, response: str, problem: str
) -> None:
    """Deviations matching nothing, ambiguous saves and unknown names fail the stage with a reason."""
    scenario = scenario_from(
        write_scenario,
        "name: Broken\nsource: [x]\nstages:\n"
        f"  - request: {{method: GET, url: /api/version}}\n    response: {response}\n",
    )

    with pytest.raises(ScenarioFailedError, match="stage 1") as raised:
        await run_scenario(scenario, client)

    assert problem in str(raised.value)


@pytest.mark.covers("aurelius_atlas_parity.run.check_response", rules=["SCN-09"])
@pytest.mark.parametrize(
    ("expected", "response", "problems"),
    [
        ({"status": 200, "json": {}}, httpx.Response(200, text="<html>"), ["the body is not JSON: '<html>'"]),
        ({"status": 200, "text": "a"}, httpx.Response(200, text="b"), ["body: expected 'a', got 'b'"]),
        ({"status": 204}, httpx.Response(204, text="x"), ["body: expected none, got 'x'"]),
        ({"status": 204}, httpx.Response(204), []),
        ({"status": 200, "json": None}, httpx.Response(200, content=b"null"), []),
        ({"status": 200, "headers": {"X-A": "1"}}, httpx.Response(200), ["header X-A: expected '1', got None"]),
    ],
)
def test__check_response_compares_bodies_by_kind(
    expected: dict[str, Any], response: httpx.Response, problems: list[str]
) -> None:
    """A JSON body must parse, a text body must be identical, no body means an empty one."""
    model = Response.model_validate(expected)
    expected_json = model.json_body if model.has_json else None

    assert [str(problem) for problem in check_response(model, expected_json, response)] == problems


@pytest.mark.covers("aurelius_atlas_parity.run.substitute", rules=["SCN-06"])
@pytest.mark.parametrize(
    ("value", "result"),
    [
        ("{guid}", "g-1"),
        ("{count}", 3),
        ("{entity}", {"a": [1]}),
        ("/entity/{guid}/n/{count}", "/entity/g-1/n/3"),
        ("{{guid}} {{literal}}", "{guid} {literal}"),
        ({"list": ["{count}", "x{guid}"]}, {"list": [3, "xg-1"]}),
        ("a {entity}", 'a {"a": [1]}'),
        (7, 7),
        (None, None),
    ],
)
def test__substitute_keeps_types_of_whole_placeholders(value: Any, result: Any) -> None:  # noqa: ANN401
    """A whole ``{name}`` takes the saved value as it is; inside text it is written in."""
    saved = {"guid": "g-1", "count": 3, "entity": {"a": [1]}}

    assert substitute(value, saved) == result


@pytest.mark.covers("aurelius_atlas_parity.run.substitute", rules=["SCN-07"])
def test__substitute_refuses_an_unknown_name() -> None:
    """An unknown name is an error that lists the names saved so far."""
    with pytest.raises(KeyError, match="saved so far: guid"):
        substitute("/x/{other}", {"guid": "g"})


@pytest.mark.covers("aurelius_atlas_parity.run.load_scenarios", rules=["SCN-03", "SCN-04"])
def test__load_scenarios_gives_one_parameter_per_file(write_scenario: WriteScenario, tmp_path: Path) -> None:
    """Files below the directory become parameters in path order; rules and covers become a covers marker."""
    write_scenario("b/second.scenario.yaml", "name: b\nsource: [x]\nrules: [ABC-01]\n" + STAGE)
    write_scenario("a.scenario.yaml", "name: a\nsource: [x]\ncovers: [m.f]\n" + STAGE)
    write_scenario("c.scenario.yaml", "name: c\nsource: [x]\n" + STAGE)
    write_scenario("notes.yaml", "not: a scenario\n")

    parameters = load_scenarios(tmp_path / "scenarios")

    assert [parameter.id for parameter in parameters] == ["a", "b/second", "c"]
    assert [[(mark.args, mark.kwargs) for mark in parameter.marks] for parameter in parameters] == [
        [(("m.f",), {"rules": []})],
        [((), {"rules": ["ABC-01"]})],
        [],
    ]


STAGE = "stages: [{request: {method: GET, url: /x}, response: {status: 200}}]\n"


@pytest.mark.covers("aurelius_atlas_parity.run.load_scenarios", rules=["SCN-03"])
def test__load_scenarios_fails_on_a_bad_file_or_directory(write_scenario: WriteScenario, tmp_path: Path) -> None:
    """One invalid file fails the whole load; a missing directory is an error too."""
    write_scenario("bad.scenario.yaml", "name: x\n")

    with pytest.raises(ScenarioError, match=r"bad\.scenario\.yaml: source: Field required"):
        load_scenarios(tmp_path / "scenarios")
    with pytest.raises(NotADirectoryError, match="is not a directory of scenarios"):
        load_scenarios(tmp_path / "missing")
