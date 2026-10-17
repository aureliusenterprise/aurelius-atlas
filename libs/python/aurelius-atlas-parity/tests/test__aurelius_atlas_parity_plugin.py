import textwrap

import pytest

SCENARIO = """
name: Version
source: [AdminResource.java#getVersion]
rules: [ABC-01]
stages:
  - request: {method: GET, url: /api/version}
    response:
      status: 200
      json: {Version: "2.4.0"}
      deviations: [{id: DV-01, path: $.Version, value: "1.0"}]
  - request: {method: GET, url: "/api/version?again=1"}
    response: {status: 200}
"""

TEST_MODULE = """
from pathlib import Path

import pytest
from aurelius_atlas_parity import load_scenarios

@pytest.mark.parametrize("scenario", load_scenarios(Path(__file__).parent / "scenarios"))
def test__scenario(scenario):
    pass

@pytest.mark.parametrize("value", [1])
def test__other(value):
    pass

def test__plain():
    pass
"""


@pytest.mark.covers("aurelius_atlas_parity.plugin.pytest_itemcollected", rules=["SCN-04", "SCN-14"])
def test__scenario_tests_carry_their_endpoints_and_deviations(pytester: pytest.Pytester) -> None:
    """Each scenario test has its properties and covers marker at collection; other tests get nothing."""
    pytester.makepyprojecttoml('[tool.pytest.ini_options]\nasyncio_default_fixture_loop_scope = "function"\n')
    (pytester.path / "scenarios").mkdir()
    (pytester.path / "scenarios" / "version.scenario.yaml").write_text(textwrap.dedent(SCENARIO))
    pytester.makepyfile(test__sample=TEST_MODULE)

    items = {item.name: item for item in pytester.getitems(pytester.path / "test__sample.py")}

    assert items["test__scenario[version]"].user_properties == [
        ("parity.endpoint", "GET /api/version"),
        ("parity.deviation", "DV-01"),
    ]
    assert [mark.kwargs for mark in items["test__scenario[version]"].iter_markers("covers")] == [{"rules": ["ABC-01"]}]
    assert items["test__other[1]"].user_properties == []
    assert items["test__plain"].user_properties == []
