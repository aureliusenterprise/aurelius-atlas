# aurelius-atlas-validate-entity-client

[![SonarQube Cloud](<https://sonarcloud.io/images/project_badges/sonarcloud-light.svg>)](<https://sonarcloud.io/summary/new_code?id=aureliusenterprise_aurelius-atlas-validate-entity-client>)

The contract and the async client of the validate-entity API (8.4, DD-203, DD-204): the governance validation card the screen renders and the `ValidateEntityClient` that asks for it. The `aurelius-atlas-validate-entity` app imports its own response model from here.

## Installation

```
[project.dependencies]
aurelius-atlas-validate-entity-client = "*"

[tool.uv.sources.aurelius-atlas-validate-entity-client]
workspace = true
```

## Documentation

## aurelius\_atlas\_validate\_entity\_client.models

The governance-verdict answer of the validate-entity API (CL-40 as amended by 12.7; DD-498).

The body `POST /` answers since 12.7: the verdicts the app's own engine ran over the draft (VEV-02) and the rules the vocabulary could not read (VEV-03), stated as models so a caller parses them and the app's answer is checked against one shape. The four canned cards of the 8.3 mock retire with DV-67 (ADR 061): `compliant` is a JSON boolean, not the legacy's string `'0'`/`'1'`, and nothing of the legacy `AppSearchResult` document survives.

The field names are camelCase, the same house style the card document used; `verdicts` is a flat array and the banner groups it by `attribute` (DD-498 — keyed cards and parallel arrays were refused there).

Classes:

- **`GovernanceVerdict`** –

  One ACTIVE governance rule's answer about the draft (VEV-02).
- **`UnreadRule`** –

  A rule the vocabulary cannot read — recorded, never executed (VEV-03, DV-146).
- **`ValidationResponse`** –

  The `POST /` answer: the verdicts of the ACTIVE rules, and the unread ones.

### GovernanceVerdict

Bases: `BaseModel`

One ACTIVE governance rule's answer about the draft (VEV-02).

`compliant` is a JSON boolean — 12.6's verdict, not the mock's string flag — and `message` is the verdict line the engine carries: the rule's own sentence for its verdict, the kind's reason when the rule stores none (GQ-06).

**Show JSON schema:**

```
{
  "additionalProperties": false,
  "description": "One ACTIVE governance rule's answer about the draft (VEV-02).\n\n``compliant`` is a JSON boolean \u2014 12.6's verdict, not the mock's string flag \u2014 and\n``message`` is the verdict line the engine carries: the rule's own sentence for its\nverdict, the kind's reason when the rule stores none (GQ-06).",
  "properties": {
    "ruleGuid": {
      "description": "The catalogue guid of the rule that answered.",
      "title": "Ruleguid",
      "type": "string"
    },
    "ruleName": {
      "description": "The rule's name, as the catalogue holds it.",
      "title": "Rulename",
      "type": "string"
    },
    "attribute": {
      "description": "The entity attribute the rule measures: the banner groups by it.",
      "title": "Attribute",
      "type": "string"
    },
    "dimension": {
      "description": "The rule's quality dimension, e.g. ``COMPLETENESS``.",
      "title": "Dimension",
      "type": "string"
    },
    "compliant": {
      "description": "The verdict: whether the draft passes the rule.",
      "title": "Compliant",
      "type": "boolean"
    },
    "message": {
      "description": "The line to show: the rule's own sentence, or the kind's reason.",
      "title": "Message",
      "type": "string"
    }
  },
  "required": [
    "ruleGuid",
    "ruleName",
    "attribute",
    "dimension",
    "compliant",
    "message"
  ],
  "title": "GovernanceVerdict",
  "type": "object"
}
```

Config:

- `populate_by_name`: `True`
- `extra`: `forbid`
- `frozen`: `True`

Fields:

- `rule_guid` (`str`)
- `rule_name` (`str`)
- `attribute` (`str`)
- `dimension` (`str`)
- `compliant` (`StrictBool`)
- `message` (`str`)

#### attribute

```
attribute: str
```

The entity attribute the rule measures: the banner groups by it.

#### compliant

```
compliant: StrictBool
```

The verdict: whether the draft passes the rule.

#### dimension

```
dimension: str
```

The rule's quality dimension, e.g. `COMPLETENESS`.

#### message

```
message: str
```

The line to show: the rule's own sentence, or the kind's reason.

#### model\_config

```
model_config = ConfigDict(populate_by_name=True, extra='forbid', frozen=True)
```

#### rule\_guid

```
rule_guid: str
```

The catalogue guid of the rule that answered.

#### rule\_name

```
rule_name: str
```

The rule's name, as the catalogue holds it.

### UnreadRule

Bases: `BaseModel`

A rule the vocabulary cannot read — recorded, never executed (VEV-03, DV-146).

**Show JSON schema:**

```
{
  "additionalProperties": false,
  "description": "A rule the vocabulary cannot read \u2014 recorded, never executed (VEV-03, DV-146).",
  "properties": {
    "ruleGuid": {
      "description": "The catalogue guid of the unread rule.",
      "title": "Ruleguid",
      "type": "string"
    },
    "ruleName": {
      "description": "The rule's name, as the catalogue holds it.",
      "title": "Rulename",
      "type": "string"
    },
    "error": {
      "description": "Why the vocabulary cannot read it, e.g. a stored expression rule.",
      "title": "Error",
      "type": "string"
    }
  },
  "required": [
    "ruleGuid",
    "ruleName",
    "error"
  ],
  "title": "UnreadRule",
  "type": "object"
}
```

Config:

- `populate_by_name`: `True`
- `extra`: `forbid`
- `frozen`: `True`

Fields:

- `rule_guid` (`str`)
- `rule_name` (`str`)
- `error` (`str`)

#### error

```
error: str
```

Why the vocabulary cannot read it, e.g. a stored expression rule.

#### model\_config

```
model_config = ConfigDict(populate_by_name=True, extra='forbid', frozen=True)
```

#### rule\_guid

```
rule_guid: str
```

The catalogue guid of the unread rule.

#### rule\_name

```
rule_name: str
```

The rule's name, as the catalogue holds it.

### ValidationResponse

Bases: `BaseModel`

The `POST /` answer: the verdicts of the ACTIVE rules, and the unread ones.

**Show JSON schema:**

```
{
  "$defs": {
    "GovernanceVerdict": {
      "additionalProperties": false,
      "description": "One ACTIVE governance rule's answer about the draft (VEV-02).\n\n``compliant`` is a JSON boolean \u2014 12.6's verdict, not the mock's string flag \u2014 and\n``message`` is the verdict line the engine carries: the rule's own sentence for its\nverdict, the kind's reason when the rule stores none (GQ-06).",
      "properties": {
        "ruleGuid": {
          "description": "The catalogue guid of the rule that answered.",
          "title": "Ruleguid",
          "type": "string"
        },
        "ruleName": {
          "description": "The rule's name, as the catalogue holds it.",
          "title": "Rulename",
          "type": "string"
        },
        "attribute": {
          "description": "The entity attribute the rule measures: the banner groups by it.",
          "title": "Attribute",
          "type": "string"
        },
        "dimension": {
          "description": "The rule's quality dimension, e.g. ``COMPLETENESS``.",
          "title": "Dimension",
          "type": "string"
        },
        "compliant": {
          "description": "The verdict: whether the draft passes the rule.",
          "title": "Compliant",
          "type": "boolean"
        },
        "message": {
          "description": "The line to show: the rule's own sentence, or the kind's reason.",
          "title": "Message",
          "type": "string"
        }
      },
      "required": [
        "ruleGuid",
        "ruleName",
        "attribute",
        "dimension",
        "compliant",
        "message"
      ],
      "title": "GovernanceVerdict",
      "type": "object"
    },
    "UnreadRule": {
      "additionalProperties": false,
      "description": "A rule the vocabulary cannot read \u2014 recorded, never executed (VEV-03, DV-146).",
      "properties": {
        "ruleGuid": {
          "description": "The catalogue guid of the unread rule.",
          "title": "Ruleguid",
          "type": "string"
        },
        "ruleName": {
          "description": "The rule's name, as the catalogue holds it.",
          "title": "Rulename",
          "type": "string"
        },
        "error": {
          "description": "Why the vocabulary cannot read it, e.g. a stored expression rule.",
          "title": "Error",
          "type": "string"
        }
      },
      "required": [
        "ruleGuid",
        "ruleName",
        "error"
      ],
      "title": "UnreadRule",
      "type": "object"
    }
  },
  "additionalProperties": false,
  "description": "The ``POST /`` answer: the verdicts of the ACTIVE rules, and the unread ones.",
  "properties": {
    "verdicts": {
      "description": "One verdict per ACTIVE rule the vocabulary could read (VEV-02).",
      "items": {
        "$ref": "#/$defs/GovernanceVerdict"
      },
      "title": "Verdicts",
      "type": "array"
    },
    "unreadRules": {
      "description": "The rules the vocabulary could not read (VEV-03): shown, never executed.",
      "items": {
        "$ref": "#/$defs/UnreadRule"
      },
      "title": "Unreadrules",
      "type": "array"
    }
  },
  "title": "ValidationResponse",
  "type": "object"
}
```

Config:

- `populate_by_name`: `True`
- `extra`: `forbid`
- `frozen`: `True`

Fields:

- `verdicts` (`list[GovernanceVerdict]`)
- `unread_rules` (`list[UnreadRule]`)

#### model\_config

```
model_config = ConfigDict(populate_by_name=True, extra='forbid', frozen=True)
```

#### unread\_rules

```
unread_rules: list[UnreadRule]
```

The rules the vocabulary could not read (VEV-03): shown, never executed.

#### verdicts

```
verdicts: list[GovernanceVerdict]
```

One verdict per ACTIVE rule the vocabulary could read (VEV-02).

## aurelius\_atlas\_validate\_entity\_client.client

The async client for the validate-entity API (CL-01..CL-05; CL-40 as amended by 12.7; DD-203, DD-204, DD-205).

The shared client conventions of increment 8.4: constructed from an externally built `httpx.AsyncClient` and a token source, reading no environment variables (CL-01). The request path is relative, appended to that client's base URL, so a URL with a trailing slash — the `str()` of a pydantic `HttpUrl` — works as given (CL-01); the builder closes the pool, the API client never touches its lifecycle. Tests pass one built on a `MockTransport` and no socket opens (CL-02); the bearer goes on every call (CL-03); `ValidateEntityClientError` rises on a non-2xx answer (CL-04); `httpx`'s own error propagates on an unreachable upstream (CL-05).

`validate` posts the draft entity — the endpoint reads only its `attributes` (VEV-01), so the request is not a model — and parses the verdict document into a :class:`~aurelius_atlas_validate_entity_client.models.ValidationResponse` (CL-40).

Type Aliases:

- **`TokenSource`** –

  Where the bearer token comes from: a fixed token, or a callable that yields one (CL-03).

Classes:

- **`ValidateEntityClient`** –

  The client for one validate-entity service (CL-40, DD-203, DD-205).
- **`ValidateEntityClientError`** –

  A non-2xx answer from the validate-entity API, with the status (CL-04).

Attributes:

- **`CLIENT_ERROR`** –

  The status where an answer becomes an error: the client-error boundary (CL-04).
- **`DEFAULT_TIMEOUT_SECONDS`** –

  The suggested request timeout, seconds — for the httpx client an app builds for this one (CL-01).
- **`VALIDATE_PATH`** –

  The validation endpoint of the 8.3 app (VE-01): the service root, relative to the base URL (CL-01).

### CLIENT\_ERROR

```
CLIENT_ERROR = 400
```

The status where an answer becomes an error: the client-error boundary (CL-04).

### DEFAULT\_TIMEOUT\_SECONDS

```
DEFAULT_TIMEOUT_SECONDS = 10.0
```

The suggested request timeout, seconds — for the httpx client an app builds for this one (CL-01).

### VALIDATE\_PATH

```
VALIDATE_PATH = ''
```

The validation endpoint of the 8.3 app (VE-01): the service root, relative to the base URL (CL-01).

### TokenSource

```
TokenSource = str | Callable[[], str]
```

Where the bearer token comes from: a fixed token, or a callable that yields one (CL-03).

### ValidateEntityClient

```
ValidateEntityClient(http: AsyncClient, token: TokenSource)
```

The client for one validate-entity service (CL-40, DD-203, DD-205).

Parameters:

- #### **`http`**

  (`AsyncClient`) –

  The `httpx.AsyncClient` to speak through, built by the caller — its builder owns its lifecycle, this client only speaks through it. Its base URL carries the service root; the path above is relative to it.
- #### **`token`**

  (`TokenSource`) –

  The bearer token source (CL-03).

Methods:

- **`validate`** –

  `POST /`: the draft entity in, the governance verdicts out (VEV-01/02, CL-40).
- **`with_token`** –

  The same client speaking with `token` — sharing the connection pool (CL-03).

#### validate

```
validate(entity: Mapping[str, Any]) -> ValidationResponse
```

`POST /`: the draft entity in, the governance verdicts out (VEV-01/02, CL-40).

:param entity: the entity being edited; only its `attributes` are read (VEV-01).

Raises:

- `ValidateEntityClientError` –

  The API answered 4xx/5xx (a 401 is VE-03).

#### with\_token

```
with_token(token: TokenSource) -> ValidateEntityClient
```

The same client speaking with `token` — sharing the connection pool (CL-03).

### ValidateEntityClientError

```
ValidateEntityClientError(status_code: int, error_code: str | None, error_message: str | None)
```

Bases: `RuntimeError`

A non-2xx answer from the validate-entity API, with the status (CL-04).

Attributes:

- **`error_code`** –

  The `errorCode` of the Atlas-shaped body, when it parsed (VE-03's 401).
- **`error_message`** –

  The `errorMessage` of the Atlas-shaped body, when it parsed.
- **`status_code`** –

  The HTTP status the API answered with.

#### error\_code

```
error_code = error_code
```

The `errorCode` of the Atlas-shaped body, when it parsed (VE-03's 401).

#### error\_message

```
error_message = error_message
```

The `errorMessage` of the Atlas-shaped body, when it parsed.

#### status\_code

```
status_code = status_code
```

The HTTP status the API answered with.
