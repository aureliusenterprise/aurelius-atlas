"""The scenario format: ``*.scenario.yaml`` files, read and validated (SCN-01 to SCN-03; DD-012)."""

from pathlib import Path
from typing import Annotated, Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError, field_validator, model_validator

from aurelius_atlas_parity.path import JsonPath, PathError, parse_path

SCENARIO_SUFFIX = ".scenario.yaml"

ENDPOINT_PROPERTY = "parity.endpoint"
DEVIATION_PROPERTY = "parity.deviation"
"""Names of the test properties a scenario test carries (SCN-14; DD-014)."""

ONE_BODY_ERROR = "give at most one of 'json' and 'text'"
VALUE_OR_ABSENT_ERROR = "give either 'value' or 'absent: true'"
NEEDS_JSON_ERROR = "'volatile', 'save' and 'deviations' need a 'json' body"
NOT_A_MAPPING_ERROR = "a scenario is a mapping of keys to values"
DUPLICATE_KEY_ERROR = "duplicate key {key!r}"
INVALID_FILE_ERROR = "{file}: {problems}"
ID_IS_THE_PATH_ERROR = "id: a scenario's id is its path, it cannot be set"


class ScenarioError(ValueError):
    """A scenario file does not parse or does not match the format (SCN-03)."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _check_path(text: str) -> str:
    try:
        parse_path(text)
    except PathError as error:
        raise ValueError(str(error)) from error
    return text


type PathText = Annotated[str, Field(min_length=1)]


class _Body(_Strict):
    """A ``json`` or ``text`` body; ``json: null`` is a body, a missing key is none."""

    json_body: JsonValue = Field(default=None, alias="json")
    text: str | None = None

    @model_validator(mode="after")
    def _one_body(self) -> Self:
        if "json_body" in self.model_fields_set and self.text is not None:
            raise ValueError(ONE_BODY_ERROR)
        return self

    @property
    def has_json(self) -> bool:
        """Whether the body is JSON."""
        return "json_body" in self.model_fields_set


class Request(_Body):
    """What a stage sends."""

    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
    url: Annotated[str, Field(pattern=r"^/")]
    params: dict[str, str | list[str]] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)

    @property
    def endpoint(self) -> str:
        """The method and the URL before substitution, without its query: ``GET /api/atlas/v2/entity/guid/{guid}``."""
        return f"{self.method} {self.url.split('?', 1)[0]}"


class Deviation(_Strict):
    """A deliberate difference from the Atlas response, with its recorded deviation (SCN-12)."""

    id: Annotated[str, Field(pattern=r"^DV-\d{2,3}$")]
    path: PathText
    value: JsonValue = None
    absent: bool = False

    _check = field_validator("path")(_check_path)

    @model_validator(mode="after")
    def _value_or_absent(self) -> Self:
        if ("value" in self.model_fields_set) == self.absent:
            raise ValueError(VALUE_OR_ABSENT_ERROR)
        return self

    @property
    def json_path(self) -> JsonPath:
        """The parsed path."""
        return parse_path(self.path)


class Response(_Body):
    """What a stage expects back: the Atlas response, adjusted by its deviations."""

    status: Annotated[int, Field(ge=100, le=599)]
    headers: dict[str, str] = Field(default_factory=dict)
    volatile: list[PathText] = Field(default_factory=list)
    save: dict[Annotated[str, Field(pattern=r"^[A-Za-z_]\w*$")], PathText] = Field(default_factory=dict)
    deviations: list[Deviation] = Field(default_factory=list)

    @field_validator("volatile")
    @classmethod
    def _volatile_paths(cls, paths: list[str]) -> list[str]:
        return [_check_path(path) for path in paths]

    @field_validator("save")
    @classmethod
    def _save_paths(cls, save: dict[str, str]) -> dict[str, str]:
        return {name: _check_path(path) for name, path in save.items()}

    @model_validator(mode="after")
    def _paths_need_json(self) -> Self:
        if (self.volatile or self.save or self.deviations) and not self.has_json:
            raise ValueError(NEEDS_JSON_ERROR)
        return self


class Stage(_Strict):
    """One request and the response it must get."""

    name: str | None = None
    request: Request
    response: Response


class Scenario(_Strict):
    """One scenario file (SCN-01)."""

    id: str = Field(exclude=True)
    """The path below the scenario directory without the suffix, set when the file is read (SCN-04)."""
    name: Annotated[str, Field(min_length=1)]
    source: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1)]
    """Where in Atlas 2.4.0 the expectation was read: files, classes, methods or Atlas test fixtures."""
    rules: list[str] = Field(default_factory=list)
    covers: list[str] = Field(default_factory=list)
    needs_auth: bool = False
    """Whether only an installation with authentication on can answer it (SCN-16; DD-038)."""
    stages: Annotated[list[Stage], Field(min_length=1)]

    def __str__(self) -> str:
        return self.id

    def properties(self) -> list[tuple[str, str]]:
        """The test properties of this scenario: each endpoint once, then each deviation id once (SCN-14)."""
        endpoints = dict.fromkeys(stage.request.endpoint for stage in self.stages)
        deviations = dict.fromkeys(deviation.id for stage in self.stages for deviation in stage.response.deviations)
        return [(ENDPOINT_PROPERTY, endpoint) for endpoint in endpoints] + [
            (DEVIATION_PROPERTY, deviation) for deviation in deviations
        ]


class _UniqueKeyLoader(yaml.SafeLoader):
    """A safe YAML loader that refuses a key given twice in one mapping, instead of keeping the last."""


def _construct_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode) -> dict[Any, Any]:
    keys: set[Any] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node)
        if key in keys:
            raise yaml.constructor.ConstructorError(
                None, None, DUPLICATE_KEY_ERROR.format(key=key), key_node.start_mark
            )
        keys.add(key)
    return loader.construct_mapping(node, deep=True)


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _problems(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(step) for step in problem['loc']) or 'scenario'}: {problem['msg']}"
        for problem in error.errors()
    )


def read_scenario(file: Path, directory: Path) -> Scenario:
    """Read and validate one scenario file.

    Args:
        file: The ``*.scenario.yaml`` file.
        directory: The scenario directory; the scenario id is the file's path below it.

    Raises:
        ScenarioError: The file does not parse or does not match the format; the message names the file.
    """
    scenario_id = file.relative_to(directory).as_posix().removesuffix(SCENARIO_SUFFIX)
    try:
        document = yaml.load(file.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)  # noqa: S506 - a safe loader
    except yaml.YAMLError as error:
        raise ScenarioError(INVALID_FILE_ERROR.format(file=file, problems=error)) from error
    if not isinstance(document, dict):
        raise ScenarioError(INVALID_FILE_ERROR.format(file=file, problems=NOT_A_MAPPING_ERROR))
    if "id" in document:
        raise ScenarioError(INVALID_FILE_ERROR.format(file=file, problems=ID_IS_THE_PATH_ERROR))
    try:
        return Scenario.model_validate({**document, "id": scenario_id})
    except ValidationError as error:
        raise ScenarioError(INVALID_FILE_ERROR.format(file=file, problems=_problems(error))) from error
