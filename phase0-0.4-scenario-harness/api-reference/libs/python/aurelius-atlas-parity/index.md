# aurelius-atlas-parity

Parity scenarios for Aurelius Atlas: the scenario format, the runner and the comparison.

## Installation

Part of the workspace dev group, which loads the pytest plugin into every test run.

```
[dependency-groups]
dev = ["aurelius-atlas-parity"]

[tool.uv.sources.aurelius-atlas-parity]
workspace = true
```

## Documentation

## aurelius\_atlas\_parity

Parity scenarios: requests with the responses Apache Atlas 2.4.0 gives, run against Aurelius Atlas (ADR 052).

Modules:

- **`compare`** –

  The exact comparison of a response body with its expectation (SCN-09, SCN-10, SCN-12; DD-013).
- **`path`** –

  Paths into a JSON document: the JSONPath subset `$`, `.name`, `['name']`, `[n]` and `[*]` (SCN-07).
- **`plugin`** –

  The pytest plugin: gives each scenario test its endpoints and deviations as test properties (SCN-14; DD-014).
- **`run`** –

  Running a scenario: send each stage's request, compare its response, save values (SCN-05 to SCN-12).
- **`scenario`** –

  The scenario format: `*.scenario.yaml` files, read and validated (SCN-01 to SCN-03; DD-012).
- **`testing`** –

  A sample ASGI application for this library's own tests.

Classes:

- **`Scenario`** –

  One scenario file (SCN-01).
- **`ScenarioError`** –

  A scenario file does not parse or does not match the format (SCN-03).
- **`ScenarioFailedError`** –

  A stage's response differs from its expectation; the message lists every difference (SCN-11).

Functions:

- **`load_scenarios`** –

  Read every `*.scenario.yaml` below a directory as pytest parameters, one test per scenario (SCN-04).
- **`run_scenario`** –

  Run a scenario's stages in order through the client (SCN-05).

### \_\_all\_\_

```
__all__ = ['Scenario', 'ScenarioError', 'ScenarioFailedError', 'load_scenarios', 'run_scenario']
```

### Scenario

Bases: `_Strict`

One scenario file (SCN-01).

**Show JSON schema:**

```
{
  "$defs": {
    "Deviation": {
      "additionalProperties": false,
      "description": "A deliberate difference from the Atlas response, with its recorded deviation (SCN-12).",
      "properties": {
        "id": {
          "pattern": "^DV-\\d{2,3}$",
          "title": "Id",
          "type": "string"
        },
        "path": {
          "$ref": "#/$defs/PathText"
        },
        "value": {
          "$ref": "#/$defs/JsonValue",
          "default": null
        },
        "absent": {
          "default": false,
          "title": "Absent",
          "type": "boolean"
        }
      },
      "required": [
        "id",
        "path"
      ],
      "title": "Deviation",
      "type": "object"
    },
    "JsonValue": {},
    "PathText": {
      "minLength": 1,
      "type": "string"
    },
    "Request": {
      "additionalProperties": false,
      "description": "What a stage sends.",
      "properties": {
        "json": {
          "$ref": "#/$defs/JsonValue",
          "default": null
        },
        "text": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Text"
        },
        "method": {
          "enum": [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "HEAD",
            "OPTIONS"
          ],
          "title": "Method",
          "type": "string"
        },
        "url": {
          "pattern": "^/",
          "title": "Url",
          "type": "string"
        },
        "params": {
          "additionalProperties": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "items": {
                  "type": "string"
                },
                "type": "array"
              }
            ]
          },
          "title": "Params",
          "type": "object"
        },
        "headers": {
          "additionalProperties": {
            "type": "string"
          },
          "title": "Headers",
          "type": "object"
        }
      },
      "required": [
        "method",
        "url"
      ],
      "title": "Request",
      "type": "object"
    },
    "Response": {
      "additionalProperties": false,
      "description": "What a stage expects back: the Atlas response, adjusted by its deviations.",
      "properties": {
        "json": {
          "$ref": "#/$defs/JsonValue",
          "default": null
        },
        "text": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Text"
        },
        "status": {
          "maximum": 599,
          "minimum": 100,
          "title": "Status",
          "type": "integer"
        },
        "headers": {
          "additionalProperties": {
            "type": "string"
          },
          "title": "Headers",
          "type": "object"
        },
        "volatile": {
          "items": {
            "$ref": "#/$defs/PathText"
          },
          "title": "Volatile",
          "type": "array"
        },
        "save": {
          "patternProperties": {
            "^[A-Za-z_]\\w*$": {
              "$ref": "#/$defs/PathText"
            }
          },
          "title": "Save",
          "type": "object"
        },
        "deviations": {
          "items": {
            "$ref": "#/$defs/Deviation"
          },
          "title": "Deviations",
          "type": "array"
        }
      },
      "required": [
        "status"
      ],
      "title": "Response",
      "type": "object"
    },
    "Stage": {
      "additionalProperties": false,
      "description": "One request and the response it must get.",
      "properties": {
        "name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Name"
        },
        "request": {
          "$ref": "#/$defs/Request"
        },
        "response": {
          "$ref": "#/$defs/Response"
        }
      },
      "required": [
        "request",
        "response"
      ],
      "title": "Stage",
      "type": "object"
    }
  },
  "additionalProperties": false,
  "description": "One scenario file (SCN-01).",
  "properties": {
    "id": {
      "title": "Id",
      "type": "string"
    },
    "name": {
      "minLength": 1,
      "title": "Name",
      "type": "string"
    },
    "source": {
      "items": {
        "minLength": 1,
        "type": "string"
      },
      "minItems": 1,
      "title": "Source",
      "type": "array"
    },
    "rules": {
      "items": {
        "type": "string"
      },
      "title": "Rules",
      "type": "array"
    },
    "covers": {
      "items": {
        "type": "string"
      },
      "title": "Covers",
      "type": "array"
    },
    "stages": {
      "items": {
        "$ref": "#/$defs/Stage"
      },
      "minItems": 1,
      "title": "Stages",
      "type": "array"
    }
  },
  "required": [
    "id",
    "name",
    "source",
    "stages"
  ],
  "title": "Scenario",
  "type": "object"
}
```

Fields:

- `id` (`str`)
- `name` (`str`)
- `source` (`list[str]`)
- `rules` (`list[str]`)
- `covers` (`list[str]`)
- `stages` (`list[Stage]`)

#### covers

```
covers: list[str]
```

#### id

```
id: str
```

The path below the scenario directory without the suffix, set when the file is read (SCN-04).

#### model\_config

```
model_config = ConfigDict(extra='forbid', frozen=True)
```

#### name

```
name: str
```

#### rules

```
rules: list[str]
```

#### source

```
source: list[str]
```

Where in Atlas 2.4.0 the expectation was read: files, classes, methods or Atlas test fixtures.

#### stages

```
stages: list[Stage]
```

#### \_\_str\_\_

```
__str__() -> str
```

#### properties

```
properties() -> list[tuple[str, str]]
```

The test properties of this scenario: each endpoint once, then each deviation id once (SCN-14).

### ScenarioError

Bases: `ValueError`

A scenario file does not parse or does not match the format (SCN-03).

### ScenarioFailedError

Bases: `AssertionError`

A stage's response differs from its expectation; the message lists every difference (SCN-11).

### load\_scenarios

```
load_scenarios(directory: Path) -> list[Any]
```

Read every `*.scenario.yaml` below a directory as pytest parameters, one test per scenario (SCN-04).

Use it with `pytest.mark.parametrize("scenario", load_scenarios(...))`. A scenario's `rules` and `covers` become a `covers` marker of its test.

Raises:

- `ScenarioError` –

  A file does not parse or does not match the format (SCN-03).
- `NotADirectoryError` –

  The directory does not exist.

### run\_scenario

```
run_scenario(scenario: Scenario, client: AsyncClient) -> None
```

Run a scenario's stages in order through the client (SCN-05).

Parameters:

- #### **`scenario`**

  (`Scenario`) –

  The scenario, as `load_scenarios` gives it.
- #### **`client`**

  (`AsyncClient`) –

  Talks to the application under test, in-process or over HTTP; the caller owns it.

Raises:

- `ScenarioFailedError` –

  A stage's response differs from its expectation, or the stage cannot run; later stages do not run.

## aurelius\_atlas\_parity.scenario

The scenario format: `*.scenario.yaml` files, read and validated (SCN-01 to SCN-03; DD-012).

Type Aliases:

- **`PathText`** –

Classes:

- **`Deviation`** –

  A deliberate difference from the Atlas response, with its recorded deviation (SCN-12).
- **`Request`** –

  What a stage sends.
- **`Response`** –

  What a stage expects back: the Atlas response, adjusted by its deviations.
- **`Scenario`** –

  One scenario file (SCN-01).
- **`ScenarioError`** –

  A scenario file does not parse or does not match the format (SCN-03).
- **`Stage`** –

  One request and the response it must get.

Functions:

- **`read_scenario`** –

  Read and validate one scenario file.

Attributes:

- **`DEVIATION_PROPERTY`** –

  Names of the test properties a scenario test carries (SCN-14; DD-014).
- **`DUPLICATE_KEY_ERROR`** –
- **`ENDPOINT_PROPERTY`** –
- **`ID_IS_THE_PATH_ERROR`** –
- **`INVALID_FILE_ERROR`** –
- **`NEEDS_JSON_ERROR`** –
- **`NOT_A_MAPPING_ERROR`** –
- **`ONE_BODY_ERROR`** –
- **`SCENARIO_SUFFIX`** –
- **`VALUE_OR_ABSENT_ERROR`** –

### DEVIATION\_PROPERTY

```
DEVIATION_PROPERTY = 'parity.deviation'
```

Names of the test properties a scenario test carries (SCN-14; DD-014).

### DUPLICATE\_KEY\_ERROR

```
DUPLICATE_KEY_ERROR = 'duplicate key {key!r}'
```

### ENDPOINT\_PROPERTY

```
ENDPOINT_PROPERTY = 'parity.endpoint'
```

### ID\_IS\_THE\_PATH\_ERROR

```
ID_IS_THE_PATH_ERROR = "id: a scenario's id is its path, it cannot be set"
```

### INVALID\_FILE\_ERROR

```
INVALID_FILE_ERROR = '{file}: {problems}'
```

### NEEDS\_JSON\_ERROR

```
NEEDS_JSON_ERROR = "'volatile', 'save' and 'deviations' need a 'json' body"
```

### NOT\_A\_MAPPING\_ERROR

```
NOT_A_MAPPING_ERROR = 'a scenario is a mapping of keys to values'
```

### ONE\_BODY\_ERROR

```
ONE_BODY_ERROR = "give at most one of 'json' and 'text'"
```

### SCENARIO\_SUFFIX

```
SCENARIO_SUFFIX = '.scenario.yaml'
```

### VALUE\_OR\_ABSENT\_ERROR

```
VALUE_OR_ABSENT_ERROR = "give either 'value' or 'absent: true'"
```

### PathText

```
PathText = str
```

### Deviation

Bases: `_Strict`

A deliberate difference from the Atlas response, with its recorded deviation (SCN-12).

**Show JSON schema:**

```
{
  "$defs": {
    "JsonValue": {},
    "PathText": {
      "minLength": 1,
      "type": "string"
    }
  },
  "additionalProperties": false,
  "description": "A deliberate difference from the Atlas response, with its recorded deviation (SCN-12).",
  "properties": {
    "id": {
      "pattern": "^DV-\\d{2,3}$",
      "title": "Id",
      "type": "string"
    },
    "path": {
      "$ref": "#/$defs/PathText"
    },
    "value": {
      "$ref": "#/$defs/JsonValue",
      "default": null
    },
    "absent": {
      "default": false,
      "title": "Absent",
      "type": "boolean"
    }
  },
  "required": [
    "id",
    "path"
  ],
  "title": "Deviation",
  "type": "object"
}
```

Fields:

- `id` (`str`)
- `path` (`PathText`)
- `value` (`JsonValue`)
- `absent` (`bool`)

Validators:

- `_value_or_absent`

#### absent

```
absent: bool = False
```

#### id

```
id: str
```

#### json\_path

```
json_path: JsonPath
```

The parsed path.

#### model\_config

```
model_config = ConfigDict(extra='forbid', frozen=True)
```

#### path

```
path: PathText
```

#### value

```
value: JsonValue = None
```

### Request

Bases: `_Body`

What a stage sends.

**Show JSON schema:**

```
{
  "$defs": {
    "JsonValue": {}
  },
  "additionalProperties": false,
  "description": "What a stage sends.",
  "properties": {
    "json": {
      "$ref": "#/$defs/JsonValue",
      "default": null
    },
    "text": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Text"
    },
    "method": {
      "enum": [
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "HEAD",
        "OPTIONS"
      ],
      "title": "Method",
      "type": "string"
    },
    "url": {
      "pattern": "^/",
      "title": "Url",
      "type": "string"
    },
    "params": {
      "additionalProperties": {
        "anyOf": [
          {
            "type": "string"
          },
          {
            "items": {
              "type": "string"
            },
            "type": "array"
          }
        ]
      },
      "title": "Params",
      "type": "object"
    },
    "headers": {
      "additionalProperties": {
        "type": "string"
      },
      "title": "Headers",
      "type": "object"
    }
  },
  "required": [
    "method",
    "url"
  ],
  "title": "Request",
  "type": "object"
}
```

Fields:

- `json_body` (`JsonValue`)
- `text` (`str | None`)
- `method` (`Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']`)
- `url` (`str`)
- `params` (`dict[str, str | list[str]]`)
- `headers` (`dict[str, str]`)

Validators:

- `_one_body`

#### endpoint

```
endpoint: str
```

The method and the URL before substitution, without its query: `GET /api/atlas/v2/entity/guid/{guid}`.

#### has\_json

```
has_json: bool
```

Whether the body is JSON.

#### headers

```
headers: dict[str, str]
```

#### json\_body

```
json_body: JsonValue = None
```

#### method

```
method: Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
```

#### model\_config

```
model_config = ConfigDict(extra='forbid', frozen=True)
```

#### params

```
params: dict[str, str | list[str]]
```

#### text

```
text: str | None = None
```

#### url

```
url: str
```

### Response

Bases: `_Body`

What a stage expects back: the Atlas response, adjusted by its deviations.

**Show JSON schema:**

```
{
  "$defs": {
    "Deviation": {
      "additionalProperties": false,
      "description": "A deliberate difference from the Atlas response, with its recorded deviation (SCN-12).",
      "properties": {
        "id": {
          "pattern": "^DV-\\d{2,3}$",
          "title": "Id",
          "type": "string"
        },
        "path": {
          "$ref": "#/$defs/PathText"
        },
        "value": {
          "$ref": "#/$defs/JsonValue",
          "default": null
        },
        "absent": {
          "default": false,
          "title": "Absent",
          "type": "boolean"
        }
      },
      "required": [
        "id",
        "path"
      ],
      "title": "Deviation",
      "type": "object"
    },
    "JsonValue": {},
    "PathText": {
      "minLength": 1,
      "type": "string"
    }
  },
  "additionalProperties": false,
  "description": "What a stage expects back: the Atlas response, adjusted by its deviations.",
  "properties": {
    "json": {
      "$ref": "#/$defs/JsonValue",
      "default": null
    },
    "text": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Text"
    },
    "status": {
      "maximum": 599,
      "minimum": 100,
      "title": "Status",
      "type": "integer"
    },
    "headers": {
      "additionalProperties": {
        "type": "string"
      },
      "title": "Headers",
      "type": "object"
    },
    "volatile": {
      "items": {
        "$ref": "#/$defs/PathText"
      },
      "title": "Volatile",
      "type": "array"
    },
    "save": {
      "patternProperties": {
        "^[A-Za-z_]\\w*$": {
          "$ref": "#/$defs/PathText"
        }
      },
      "title": "Save",
      "type": "object"
    },
    "deviations": {
      "items": {
        "$ref": "#/$defs/Deviation"
      },
      "title": "Deviations",
      "type": "array"
    }
  },
  "required": [
    "status"
  ],
  "title": "Response",
  "type": "object"
}
```

Fields:

- `json_body` (`JsonValue`)
- `text` (`str | None`)
- `status` (`int`)
- `headers` (`dict[str, str]`)
- `volatile` (`list[PathText]`)
- `save` (`dict[str, PathText]`)
- `deviations` (`list[Deviation]`)

Validators:

- `_one_body`
- `_volatile_paths` → `volatile`
- `_save_paths` → `save`
- `_paths_need_json`

#### deviations

```
deviations: list[Deviation]
```

#### has\_json

```
has_json: bool
```

Whether the body is JSON.

#### headers

```
headers: dict[str, str]
```

#### json\_body

```
json_body: JsonValue = None
```

#### model\_config

```
model_config = ConfigDict(extra='forbid', frozen=True)
```

#### save

```
save: dict[str, PathText]
```

#### status

```
status: int
```

#### text

```
text: str | None = None
```

#### volatile

```
volatile: list[PathText]
```

### Scenario

Bases: `_Strict`

One scenario file (SCN-01).

**Show JSON schema:**

```
{
  "$defs": {
    "Deviation": {
      "additionalProperties": false,
      "description": "A deliberate difference from the Atlas response, with its recorded deviation (SCN-12).",
      "properties": {
        "id": {
          "pattern": "^DV-\\d{2,3}$",
          "title": "Id",
          "type": "string"
        },
        "path": {
          "$ref": "#/$defs/PathText"
        },
        "value": {
          "$ref": "#/$defs/JsonValue",
          "default": null
        },
        "absent": {
          "default": false,
          "title": "Absent",
          "type": "boolean"
        }
      },
      "required": [
        "id",
        "path"
      ],
      "title": "Deviation",
      "type": "object"
    },
    "JsonValue": {},
    "PathText": {
      "minLength": 1,
      "type": "string"
    },
    "Request": {
      "additionalProperties": false,
      "description": "What a stage sends.",
      "properties": {
        "json": {
          "$ref": "#/$defs/JsonValue",
          "default": null
        },
        "text": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Text"
        },
        "method": {
          "enum": [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "HEAD",
            "OPTIONS"
          ],
          "title": "Method",
          "type": "string"
        },
        "url": {
          "pattern": "^/",
          "title": "Url",
          "type": "string"
        },
        "params": {
          "additionalProperties": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "items": {
                  "type": "string"
                },
                "type": "array"
              }
            ]
          },
          "title": "Params",
          "type": "object"
        },
        "headers": {
          "additionalProperties": {
            "type": "string"
          },
          "title": "Headers",
          "type": "object"
        }
      },
      "required": [
        "method",
        "url"
      ],
      "title": "Request",
      "type": "object"
    },
    "Response": {
      "additionalProperties": false,
      "description": "What a stage expects back: the Atlas response, adjusted by its deviations.",
      "properties": {
        "json": {
          "$ref": "#/$defs/JsonValue",
          "default": null
        },
        "text": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Text"
        },
        "status": {
          "maximum": 599,
          "minimum": 100,
          "title": "Status",
          "type": "integer"
        },
        "headers": {
          "additionalProperties": {
            "type": "string"
          },
          "title": "Headers",
          "type": "object"
        },
        "volatile": {
          "items": {
            "$ref": "#/$defs/PathText"
          },
          "title": "Volatile",
          "type": "array"
        },
        "save": {
          "patternProperties": {
            "^[A-Za-z_]\\w*$": {
              "$ref": "#/$defs/PathText"
            }
          },
          "title": "Save",
          "type": "object"
        },
        "deviations": {
          "items": {
            "$ref": "#/$defs/Deviation"
          },
          "title": "Deviations",
          "type": "array"
        }
      },
      "required": [
        "status"
      ],
      "title": "Response",
      "type": "object"
    },
    "Stage": {
      "additionalProperties": false,
      "description": "One request and the response it must get.",
      "properties": {
        "name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Name"
        },
        "request": {
          "$ref": "#/$defs/Request"
        },
        "response": {
          "$ref": "#/$defs/Response"
        }
      },
      "required": [
        "request",
        "response"
      ],
      "title": "Stage",
      "type": "object"
    }
  },
  "additionalProperties": false,
  "description": "One scenario file (SCN-01).",
  "properties": {
    "id": {
      "title": "Id",
      "type": "string"
    },
    "name": {
      "minLength": 1,
      "title": "Name",
      "type": "string"
    },
    "source": {
      "items": {
        "minLength": 1,
        "type": "string"
      },
      "minItems": 1,
      "title": "Source",
      "type": "array"
    },
    "rules": {
      "items": {
        "type": "string"
      },
      "title": "Rules",
      "type": "array"
    },
    "covers": {
      "items": {
        "type": "string"
      },
      "title": "Covers",
      "type": "array"
    },
    "stages": {
      "items": {
        "$ref": "#/$defs/Stage"
      },
      "minItems": 1,
      "title": "Stages",
      "type": "array"
    }
  },
  "required": [
    "id",
    "name",
    "source",
    "stages"
  ],
  "title": "Scenario",
  "type": "object"
}
```

Fields:

- `id` (`str`)
- `name` (`str`)
- `source` (`list[str]`)
- `rules` (`list[str]`)
- `covers` (`list[str]`)
- `stages` (`list[Stage]`)

#### covers

```
covers: list[str]
```

#### id

```
id: str
```

The path below the scenario directory without the suffix, set when the file is read (SCN-04).

#### model\_config

```
model_config = ConfigDict(extra='forbid', frozen=True)
```

#### name

```
name: str
```

#### rules

```
rules: list[str]
```

#### source

```
source: list[str]
```

Where in Atlas 2.4.0 the expectation was read: files, classes, methods or Atlas test fixtures.

#### stages

```
stages: list[Stage]
```

#### \_\_str\_\_

```
__str__() -> str
```

#### properties

```
properties() -> list[tuple[str, str]]
```

The test properties of this scenario: each endpoint once, then each deviation id once (SCN-14).

### ScenarioError

Bases: `ValueError`

A scenario file does not parse or does not match the format (SCN-03).

### Stage

Bases: `_Strict`

One request and the response it must get.

**Show JSON schema:**

```
{
  "$defs": {
    "Deviation": {
      "additionalProperties": false,
      "description": "A deliberate difference from the Atlas response, with its recorded deviation (SCN-12).",
      "properties": {
        "id": {
          "pattern": "^DV-\\d{2,3}$",
          "title": "Id",
          "type": "string"
        },
        "path": {
          "$ref": "#/$defs/PathText"
        },
        "value": {
          "$ref": "#/$defs/JsonValue",
          "default": null
        },
        "absent": {
          "default": false,
          "title": "Absent",
          "type": "boolean"
        }
      },
      "required": [
        "id",
        "path"
      ],
      "title": "Deviation",
      "type": "object"
    },
    "JsonValue": {},
    "PathText": {
      "minLength": 1,
      "type": "string"
    },
    "Request": {
      "additionalProperties": false,
      "description": "What a stage sends.",
      "properties": {
        "json": {
          "$ref": "#/$defs/JsonValue",
          "default": null
        },
        "text": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Text"
        },
        "method": {
          "enum": [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "HEAD",
            "OPTIONS"
          ],
          "title": "Method",
          "type": "string"
        },
        "url": {
          "pattern": "^/",
          "title": "Url",
          "type": "string"
        },
        "params": {
          "additionalProperties": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "items": {
                  "type": "string"
                },
                "type": "array"
              }
            ]
          },
          "title": "Params",
          "type": "object"
        },
        "headers": {
          "additionalProperties": {
            "type": "string"
          },
          "title": "Headers",
          "type": "object"
        }
      },
      "required": [
        "method",
        "url"
      ],
      "title": "Request",
      "type": "object"
    },
    "Response": {
      "additionalProperties": false,
      "description": "What a stage expects back: the Atlas response, adjusted by its deviations.",
      "properties": {
        "json": {
          "$ref": "#/$defs/JsonValue",
          "default": null
        },
        "text": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Text"
        },
        "status": {
          "maximum": 599,
          "minimum": 100,
          "title": "Status",
          "type": "integer"
        },
        "headers": {
          "additionalProperties": {
            "type": "string"
          },
          "title": "Headers",
          "type": "object"
        },
        "volatile": {
          "items": {
            "$ref": "#/$defs/PathText"
          },
          "title": "Volatile",
          "type": "array"
        },
        "save": {
          "patternProperties": {
            "^[A-Za-z_]\\w*$": {
              "$ref": "#/$defs/PathText"
            }
          },
          "title": "Save",
          "type": "object"
        },
        "deviations": {
          "items": {
            "$ref": "#/$defs/Deviation"
          },
          "title": "Deviations",
          "type": "array"
        }
      },
      "required": [
        "status"
      ],
      "title": "Response",
      "type": "object"
    }
  },
  "additionalProperties": false,
  "description": "One request and the response it must get.",
  "properties": {
    "name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Name"
    },
    "request": {
      "$ref": "#/$defs/Request"
    },
    "response": {
      "$ref": "#/$defs/Response"
    }
  },
  "required": [
    "request",
    "response"
  ],
  "title": "Stage",
  "type": "object"
}
```

Fields:

- `name` (`str | None`)
- `request` (`Request`)
- `response` (`Response`)

#### model\_config

```
model_config = ConfigDict(extra='forbid', frozen=True)
```

#### name

```
name: str | None = None
```

#### request

```
request: Request
```

#### response

```
response: Response
```

### read\_scenario

```
read_scenario(file: Path, directory: Path) -> Scenario
```

Read and validate one scenario file.

Parameters:

- #### **`file`**

  (`Path`) –

  The `*.scenario.yaml` file.
- #### **`directory`**

  (`Path`) –

  The scenario directory; the scenario id is the file's path below it.

Raises:

- `ScenarioError` –

  The file does not parse or does not match the format; the message names the file.

## aurelius\_atlas\_parity.run

Running a scenario: send each stage's request, compare its response, save values (SCN-05 to SCN-12).

Classes:

- **`ScenarioFailedError`** –

  A stage's response differs from its expectation; the message lists every difference (SCN-11).

Functions:

- **`check_response`** –

  Compare a response with a stage's expectation and return every difference (SCN-08 to SCN-12).
- **`load_scenarios`** –

  Read every `*.scenario.yaml` below a directory as pytest parameters, one test per scenario (SCN-04).
- **`run_scenario`** –

  Run a scenario's stages in order through the client (SCN-05).
- **`substitute`** –

  Replace `{name}` by saved values in every string of a JSON value (SCN-06).

Attributes:

- **`FAILURE_HEADER`** –
- **`NOT_JSON_ERROR`** –
- **`NO_DIRECTORY_ERROR`** –
- **`SAVE_NOT_ONE_ERROR`** –
- **`UNKNOWN_NAME_ERROR`** –

### FAILURE\_HEADER

```
FAILURE_HEADER = 'scenario {scenario}, stage {number} ({name}): {endpoint}'
```

### NOT\_JSON\_ERROR

```
NOT_JSON_ERROR = 'the body is not JSON: {body!r}'
```

### NO\_DIRECTORY\_ERROR

```
NO_DIRECTORY_ERROR = '{directory} is not a directory of scenarios'
```

### SAVE\_NOT\_ONE\_ERROR

```
SAVE_NOT_ONE_ERROR = 'save {name}: {path} matches {count} values in the response, not one'
```

### UNKNOWN\_NAME\_ERROR

```
UNKNOWN_NAME_ERROR = '{{{name}}} names no saved value; saved so far: {saved}'
```

### ScenarioFailedError

Bases: `AssertionError`

A stage's response differs from its expectation; the message lists every difference (SCN-11).

### check\_response

```
check_response(expected: Response, expected_json: Any, response: Response) -> list[str | Difference]
```

Compare a response with a stage's expectation and return every difference (SCN-08 to SCN-12).

Parameters:

- #### **`expected`**

  (`Response`) –

  The stage's response section.
- #### **`expected_json`**

  (`Any`) –

  Its `json` body with saved values substituted, or None for a `text` or empty body.
- #### **`response`**

  (`Response`) –

  The response the application gave.

Raises:

- `ValueError` –

  A deviation's path matches nothing in the expectation.

### load\_scenarios

```
load_scenarios(directory: Path) -> list[Any]
```

Read every `*.scenario.yaml` below a directory as pytest parameters, one test per scenario (SCN-04).

Use it with `pytest.mark.parametrize("scenario", load_scenarios(...))`. A scenario's `rules` and `covers` become a `covers` marker of its test.

Raises:

- `ScenarioError` –

  A file does not parse or does not match the format (SCN-03).
- `NotADirectoryError` –

  The directory does not exist.

### run\_scenario

```
run_scenario(scenario: Scenario, client: AsyncClient) -> None
```

Run a scenario's stages in order through the client (SCN-05).

Parameters:

- #### **`scenario`**

  (`Scenario`) –

  The scenario, as `load_scenarios` gives it.
- #### **`client`**

  (`AsyncClient`) –

  Talks to the application under test, in-process or over HTTP; the caller owns it.

Raises:

- `ScenarioFailedError` –

  A stage's response differs from its expectation, or the stage cannot run; later stages do not run.

### substitute

```
substitute(value: Any, saved: Mapping[str, Any]) -> Any
```

Replace `{name}` by saved values in every string of a JSON value (SCN-06).

A string that is exactly `{name}` becomes the saved value with its JSON type; elsewhere the value is written into the string. `{{` and `}}` stand for literal braces.

Raises:

- `KeyError` –

  A name was not saved by an earlier stage.

## aurelius\_atlas\_parity.compare

The exact comparison of a response body with its expectation (SCN-09, SCN-10, SCN-12; DD-013).

Classes:

- **`Difference`** –

  One place where a response differs from its expectation.
- **`Marker`** –

  Values that stand in for something that is not a JSON value.

Functions:

- **`apply_deviation`** –

  Return a copy of the expectation with the Aurelius value, or no value, at the path (SCN-12).
- **`compare`** –

  Return every difference between two JSON values (SCN-09).
- **`mask_volatile`** –

  Return a copy of the document with the value at every match of the paths replaced by `Marker.VOLATILE`.

Attributes:

- **`DEVIATION_MATCHES_NOTHING_ERROR`** –

### DEVIATION\_MATCHES\_NOTHING\_ERROR

```
DEVIATION_MATCHES_NOTHING_ERROR = 'deviation {id} at {path} matches nothing in the expectation'
```

### Difference

```
Difference(location: Location, expected: Any, actual: Any)
```

One place where a response differs from its expectation.

Methods:

- **`__str__`** –

Attributes:

- **`actual`** (`Any`) –
- **`expected`** (`Any`) –
- **`location`** (`Location`) –

#### actual

```
actual: Any
```

#### expected

```
expected: Any
```

#### location

```
location: Location
```

#### \_\_str\_\_

```
__str__() -> str
```

### Marker

Bases: `Enum`

Values that stand in for something that is not a JSON value.

Attributes:

- **`ABSENT`** –

  The field or element is not there.
- **`VOLATILE`** –

  The value is not compared (SCN-10).

#### ABSENT

```
ABSENT = '(absent)'
```

The field or element is not there.

#### VOLATILE

```
VOLATILE = '(volatile)'
```

The value is not compared (SCN-10).

### apply\_deviation

```
apply_deviation(expected: object, *, id: str, path: JsonPath, value: object = None, absent: bool = False) -> object
```

Return a copy of the expectation with the Aurelius value, or no value, at the path (SCN-12).

A key that the expectation does not have is added when a value is given, so a deviation can declare a field Aurelius returns and Atlas does not.

Raises:

- `ValueError` –

  The path matches nothing to change in the expectation.

### compare

```
compare(expected: Any, actual: Any) -> list[Difference]
```

Return every difference between two JSON values (SCN-09).

Objects must have the same keys, arrays the same length and order, and scalars the same JSON type and value. `Marker.VOLATILE` equals only itself.

### mask\_volatile

```
mask_volatile(document: Any, paths: list[JsonPath]) -> Any
```

Return a copy of the document with the value at every match of the paths replaced by `Marker.VOLATILE`.

## aurelius\_atlas\_parity.path

Paths into a JSON document: the JSONPath subset `$`, `.name`, `['name']`, `[n]` and `[*]` (SCN-07).

Type Aliases:

- **`Location`** –

  Where one value sits in a document: the keys and indexes leading to it.
- **`Segment`** –

Classes:

- **`JsonPath`** –

  A parsed path: the segments after `$`.
- **`PathError`** –

  A path is not in the supported JSONPath subset.
- **`Wildcard`** –

  `[*]`: every element of an array or every value of an object.

Functions:

- **`format_location`** –

  Write a location as a path, for messages: `$.entities[0].guid`.
- **`parse_path`** –

  Parse a path such as `$.entities[*].guid`.

Attributes:

- **`NOT_A_PATH_ERROR`** –

### NOT\_A\_PATH\_ERROR

```
NOT_A_PATH_ERROR = "{text!r} is not a path: it must start with '$' and continue with .name, ['name'], [n] or [*]"
```

### Location

```
Location = tuple[str | int, ...]
```

Where one value sits in a document: the keys and indexes leading to it.

### Segment

```
Segment = str | int | Wildcard
```

### JsonPath

```
JsonPath(text: str, segments: tuple[Segment, ...])
```

A parsed path: the segments after `$`.

Methods:

- **`find`** –

  Return the location and value of every match in the document, in document order.

Attributes:

- **`parent`** (`JsonPath`) –

  The path without its last segment; the root's parent is the root.
- **`segments`** (`tuple[Segment, ...]`) –
- **`text`** (`str`) –

#### parent

```
parent: JsonPath
```

The path without its last segment; the root's parent is the root.

#### segments

```
segments: tuple[Segment, ...]
```

#### text

```
text: str
```

#### find

```
find(document: Any) -> list[tuple[Location, Any]]
```

Return the location and value of every match in the document, in document order.

### PathError

Bases: `ValueError`

A path is not in the supported JSONPath subset.

### Wildcard

```
Wildcard()
```

`[*]`: every element of an array or every value of an object.

### format\_location

```
format_location(location: Location) -> str
```

Write a location as a path, for messages: `$.entities[0].guid`.

### parse\_path

```
parse_path(text: str) -> JsonPath
```

Parse a path such as `$.entities[*].guid`.

Raises:

- `PathError` –

  The text is not in the supported subset.
