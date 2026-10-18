"""Running a scenario: send each stage's request, compare its response, save values (SCN-05 to SCN-12)."""

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import httpx
import pytest

from aurelius_atlas_parity.compare import Difference, apply_deviation, compare, mask_volatile
from aurelius_atlas_parity.path import parse_path
from aurelius_atlas_parity.scenario import SCENARIO_SUFFIX, Request, Response, Scenario, Stage, read_scenario

_PLACEHOLDER = re.compile(r"\{\{|\}\}|\{([A-Za-z_]\w*)\}")
_WHOLE_PLACEHOLDER = re.compile(r"\{([A-Za-z_]\w*)\}")

UNKNOWN_NAME_ERROR = "{{{name}}} names no saved value; saved so far: {saved}"
SAVE_NOT_ONE_ERROR = "save {name}: {path} matches {count} values in the response, not one"
NOT_JSON_ERROR = "the body is not JSON: {body!r}"
NO_DIRECTORY_ERROR = "{directory} is not a directory of scenarios"
FAILURE_HEADER = "scenario {scenario}, stage {number} ({name}): {endpoint}"
NEEDS_AUTH_SKIP = "{scenario} needs an installation with authentication on (needs_auth: true, SCN-16)"


class ScenarioFailedError(AssertionError):
    """A stage's response differs from its expectation; the message lists every difference (SCN-11)."""


class _StageError(Exception):
    """Something in a stage, other than a difference, that fails it: a missing name or a bad save path."""


def load_scenarios(directory: Path, *, authenticated_run: bool = False) -> list[Any]:
    """Read every ``*.scenario.yaml`` below a directory as pytest parameters, one test per scenario (SCN-04).

    Use it with ``pytest.mark.parametrize("scenario", load_scenarios(...))``. A scenario's ``rules`` and
    ``covers`` become a ``covers`` marker of its test. A scenario with ``needs_auth: true`` gets a skip mark
    unless the caller declares an authenticated run (SCN-16): only a guard-on installation can answer it,
    and the plain (unit) harness runs the guard-off application (AUTH-01).

    Raises:
        ScenarioError: A file does not parse or does not match the format (SCN-03).
        NotADirectoryError: The directory does not exist.
    """
    if not directory.is_dir():
        raise NotADirectoryError(NO_DIRECTORY_ERROR.format(directory=directory))
    parameters: list[Any] = []
    for file in sorted(directory.rglob(f"*{SCENARIO_SUFFIX}")):
        scenario = read_scenario(file, directory)
        named = scenario.rules or scenario.covers
        marks = [pytest.mark.covers(*scenario.covers, rules=scenario.rules)] if named else []
        if scenario.needs_auth and not authenticated_run:
            marks.append(pytest.mark.skip(NEEDS_AUTH_SKIP.format(scenario=scenario.id)))
        parameters.append(pytest.param(scenario, id=scenario.id, marks=marks))
    return parameters


def substitute(value: Any, saved: Mapping[str, Any]) -> Any:  # noqa: ANN401 - any JSON value
    """Replace ``{name}`` by saved values in every string of a JSON value (SCN-06).

    A string that is exactly ``{name}`` becomes the saved value with its JSON type; elsewhere the value is
    written into the string. ``{{`` and ``}}`` stand for literal braces.

    Raises:
        KeyError: A name was not saved by an earlier stage.
    """
    if isinstance(value, dict):
        return {key: substitute(item, saved) for key, item in value.items()}
    if isinstance(value, list):
        return [substitute(item, saved) for item in value]
    if not isinstance(value, str):
        return value
    whole = _WHOLE_PLACEHOLDER.fullmatch(value)
    if whole is not None:
        return _saved(whole[1], saved)

    def replace(match: re.Match[str]) -> str:
        if match[1] is None:
            return match[0][0]
        found = _saved(match[1], saved)
        return found if isinstance(found, str) else json.dumps(found)

    return _PLACEHOLDER.sub(replace, value)


def _saved(name: str, saved: Mapping[str, Any]) -> Any:  # noqa: ANN401 - any JSON value
    if name not in saved:
        raise KeyError(UNKNOWN_NAME_ERROR.format(name=name, saved=", ".join(saved) or "nothing"))
    return saved[name]


async def run_scenario(
    scenario: Scenario, client: httpx.AsyncClient, *, saved: Mapping[str, Any] | None = None
) -> None:
    """Run a scenario's stages in order through the client (SCN-05).

    Args:
        scenario: The scenario, as ``load_scenarios`` gives it.
        client: Talks to the application under test, in-process or over HTTP; the caller owns it.
        saved: Values the caller supplies for the stages' ``{name}`` placeholders before stage 1 (6.1:
            an authenticated scenario's bearer token, which only the caller can mint). Stages' ``save``
            entries add to and override these.

    Raises:
        ScenarioFailedError: A stage's response differs from its expectation, or the stage cannot run; later
            stages do not run.
    """
    seeded: dict[str, Any] = dict(saved or {})
    for number, stage in enumerate(scenario.stages, start=1):
        differences: list[str | Difference]
        try:
            response = await client.send(_build_request(client, stage.request, seeded))
            await response.aread()
            expected = substitute(stage.response.json_body, seeded) if stage.response.has_json else None
            differences = check_response(stage.response, expected, response)
            if not differences:
                seeded.update(_save(stage.response, response))
        except (KeyError, _StageError, ValueError) as error:
            differences = [str(error.args[0]) if error.args else str(error)]
        if differences:
            raise ScenarioFailedError(_failure_message(scenario, number, stage, differences))


def _build_request(client: httpx.AsyncClient, request: Request, saved: Mapping[str, Any]) -> httpx.Request:
    body: dict[str, Any] = {}
    if request.has_json:
        body["json"] = substitute(request.json_body, saved)
    elif request.text is not None:
        body["content"] = substitute(request.text, saved)
    return client.build_request(
        request.method,
        substitute(request.url, saved),
        params=substitute(request.params, saved),
        headers=substitute(request.headers, saved),
        **body,
    )


def check_response(expected: Response, expected_json: Any, response: httpx.Response) -> list[str | Difference]:  # noqa: ANN401
    """Compare a response with a stage's expectation and return every difference (SCN-08 to SCN-12).

    Args:
        expected: The stage's response section.
        expected_json: Its ``json`` body with saved values substituted, or None for a ``text`` or empty body.
        response: The response the application gave.

    Raises:
        ValueError: A deviation's path matches nothing in the expectation.
    """
    problems: list[str | Difference] = []
    if response.status_code != expected.status:
        problems.append(f"status: expected {expected.status}, got {response.status_code}")
    for name, value in expected.headers.items():
        actual = response.headers.get(name)
        if actual != value:
            problems.append(f"header {name}: expected {value!r}, got {actual!r}")
    if expected.has_json:
        try:
            actual_json = response.json()
        except ValueError:
            problems.append(NOT_JSON_ERROR.format(body=response.text[:200]))
            return problems
        for deviation in expected.deviations:
            expected_json = apply_deviation(
                expected_json,
                id=deviation.id,
                path=deviation.json_path,
                value=deviation.value,
                absent=deviation.absent,
            )
        volatile = [parse_path(path) for path in expected.volatile]
        problems.extend(compare(mask_volatile(expected_json, volatile), mask_volatile(actual_json, volatile)))
    elif expected.text is not None:
        if response.text != expected.text:
            problems.append(f"body: expected {expected.text!r}, got {response.text!r}")
    elif response.content:
        problems.append(f"body: expected none, got {response.text[:200]!r}")
    return problems


def _save(expected: Response, response: httpx.Response) -> dict[str, Any]:
    saved: dict[str, Any] = {}
    if not expected.save:
        return saved
    document = response.json()
    for name, path in expected.save.items():
        matches = parse_path(path).find(document)
        if len(matches) != 1:
            raise _StageError(SAVE_NOT_ONE_ERROR.format(name=name, path=path, count=len(matches)))
        saved[name] = matches[0][1]
    return saved


def _failure_message(scenario: Scenario, number: int, stage: Stage, problems: Sequence[str | Difference]) -> str:
    header = FAILURE_HEADER.format(
        scenario=scenario.id, number=number, name=stage.name or "unnamed", endpoint=stage.request.endpoint
    )
    return "\n".join([header, *(f"  {problem}" for problem in problems)])
