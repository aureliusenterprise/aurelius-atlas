# aurelius-atlas-data2model-client

The contract and the async client of the data2model extraction API (8.4, DD-203, DD-204): the rules family the legacy chain evolved (AURELIUS-RULES), the extraction request/response, and the `Data2ModelClient` that posts them. The `aurelius-atlas-data2model` app imports its own contract from here.

## Installation

```
[project.dependencies]
aurelius-atlas-data2model-client = "*"

[tool.uv.sources.aurelius-atlas-data2model-client]
workspace = true
```

## Documentation

## aurelius\_atlas\_data2model\_client.models

The `/extract` request contract as pydantic models (DTM-01, DTM-11, DTM-12; DD-198).

The legacy chain built these from `m4i-analytics` dict adapters (`ConceptDefinition` and subclasses, `**kwargs`-tolerant); the port states the same fields as pydantic models, so FastAPI validates the public request at the boundary: an unknown concept or relationship type, a missing required key, or a dangling rule reference is a 400 (DTM-11), not a 500 as in the legacy.

The legacy adapters normalise `None` prefixes/keys to `''` — the lineage caller sends nulls for them — so the string fields accept `None` and normalise to `''`; extra keys (`alias`, `description`, `include`, …) are ignored, as the `**kwargs` did. The tabular `data` stays a plain list of row maps: the columns are the rules' keys, so the rows are a mapping, not a model (DD-198).

Classes:

- **`ElementRule`** –

  An element rule (legacy `ElementDefinition`): one node per row of `id_key`.
- **`ExtractionRequest`** –

  The `POST /extract` body: `{data: [row…], rules: {...}}`.
- **`ExtractionResponse`** –

  The `POST /extract` answer: `{metadata: […], model: "<ar3 JSON string>"}`.
- **`MappingEntry`** –

  One `{key, value}`: attach column `value` as metadata attribute `key`.
- **`MetadataEntry`** –

  One `{id, data}` metadata entry of the extraction answer.
- **`RelationRule`** –

  A relation rule (legacy `RelationshipDefinition`): one edge per row.
- **`RulesDef`** –

  The `rules` body: elements, relations, views, in rule order.
- **`ViewEdgeRule`** –

  A view edge entry: includes the referenced relation rule's edges.
- **`ViewNodeRule`** –

  A view node entry: includes the referenced element rule's nodes.
- **`ViewRule`** –

  A view rule (legacy `ViewDefinition`): one diagram per layout match.

Attributes:

- **`LegacyStr`** –

  A legacy string field: null arrives as `''`, as the legacy adapters normalise it.
- **`UNKNOWN_CONCEPT_TYPE_ERROR`** –

  A concept\_type outside the ported type table (DTM-11).
- **`UNKNOWN_ELEMENT_RULE_ERROR`** –

  A relation rule's dangling source/target reference (DTM-11).
- **`UNKNOWN_RELATIONSHIP_TYPE_ERROR`** –

  A relationship\_type outside the ported shorthand table (DTM-11).
- **`UNKNOWN_VIEW_EDGE_RULE_ERROR`** –

  A view rule's dangling view\_edges reference (DTM-11).
- **`UNKNOWN_VIEW_NODE_RULE_ERROR`** –

  A view rule's dangling view\_nodes reference (DTM-11).

### LegacyStr

```
LegacyStr = str
```

A legacy string field: null arrives as `''`, as the legacy adapters normalise it.

### UNKNOWN\_CONCEPT\_TYPE\_ERROR

```
UNKNOWN_CONCEPT_TYPE_ERROR = 'unknown concept type: {value!r}'
```

A concept\_type outside the ported type table (DTM-11).

### UNKNOWN\_ELEMENT\_RULE\_ERROR

```
UNKNOWN_ELEMENT_RULE_ERROR = 'relation rule {rule!r} names an unknown element rule as {side}: {ref!r}'
```

A relation rule's dangling source/target reference (DTM-11).

### UNKNOWN\_RELATIONSHIP\_TYPE\_ERROR

```
UNKNOWN_RELATIONSHIP_TYPE_ERROR = 'unknown relationship type: {value!r}'
```

A relationship\_type outside the ported shorthand table (DTM-11).

### UNKNOWN\_VIEW\_EDGE\_RULE\_ERROR

```
UNKNOWN_VIEW_EDGE_RULE_ERROR = 'view rule {rule!r} names an unknown relation rule: {ref!r}'
```

A view rule's dangling view\_edges reference (DTM-11).

### UNKNOWN\_VIEW\_NODE\_RULE\_ERROR

```
UNKNOWN_VIEW_NODE_RULE_ERROR = 'view rule {rule!r} names an unknown element rule: {ref!r}'
```

A view rule's dangling view\_nodes reference (DTM-11).

### ElementRule

Bases: `_Rule`

An element rule (legacy `ElementDefinition`): one node per row of `id_key`.

**Show JSON schema:**

```
{
  "$defs": {
    "MappingEntry": {
      "description": "One ``{key, value}``: attach column ``value`` as metadata attribute ``key``.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "key": {
          "description": "The metadata attribute's name.",
          "title": "Key",
          "type": "string"
        },
        "value": {
          "description": "The source column's name.",
          "title": "Value",
          "type": "string"
        }
      },
      "required": [
        "key",
        "value"
      ],
      "title": "MappingEntry",
      "type": "object"
    }
  },
  "description": "An element rule (legacy ``ElementDefinition``): one node per row of ``id_key``.",
  "properties": {
    "id": {
      "default": "",
      "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
      "title": "Id",
      "type": "string"
    },
    "id_key": {
      "description": "The column holding each node's id; rows with a null id are dropped, first row per id wins.",
      "title": "Id Key",
      "type": "string"
    },
    "concept_type": {
      "description": "The node's Archimate element type tag, e.g. ``lineage_dataset`` or ``lineage_process``.",
      "title": "Concept Type",
      "type": "string"
    },
    "id_prefix": {
      "default": "",
      "description": "The prefix of each node id.",
      "title": "Id Prefix",
      "type": "string"
    },
    "concept_name_prefix": {
      "default": "",
      "description": "The prefix of each node name.",
      "title": "Concept Name Prefix",
      "type": "string"
    },
    "concept_name_key": {
      "default": "",
      "description": "The column holding the node name; empty means the name is ``''``.",
      "title": "Concept Name Key",
      "type": "string"
    },
    "concept_label_prefix": {
      "default": "",
      "description": "The prefix of the node label; kept for the legacy contract, the ar3 writer ignores labels.",
      "title": "Concept Label Prefix",
      "type": "string"
    },
    "concept_label_key": {
      "default": "",
      "description": "The column holding the node label; the ar3 writer ignores labels.",
      "title": "Concept Label Key",
      "type": "string"
    },
    "mapping": {
      "description": "Metadata attributes to attach per row, each a key/value pair.",
      "items": {
        "$ref": "#/$defs/MappingEntry"
      },
      "title": "Mapping",
      "type": "array"
    }
  },
  "required": [
    "id_key",
    "concept_type"
  ],
  "title": "ElementRule",
  "type": "object"
}
```

Fields:

- `id` (`LegacyStr`)
- `id_key` (`str`)
- `concept_type` (`str`)
- `id_prefix` (`LegacyStr`)
- `concept_name_prefix` (`LegacyStr`)
- `concept_name_key` (`LegacyStr`)
- `concept_label_prefix` (`LegacyStr`)
- `concept_label_key` (`LegacyStr`)
- `mapping` (`list[MappingEntry]`)

Validators:

- `_known_concept_type` → `concept_type`

#### concept\_label\_key

```
concept_label_key: LegacyStr = ''
```

The column holding the node label; the ar3 writer ignores labels.

#### concept\_label\_prefix

```
concept_label_prefix: LegacyStr = ''
```

The prefix of the node label; kept for the legacy contract, the ar3 writer ignores labels.

#### concept\_name\_key

```
concept_name_key: LegacyStr = ''
```

The column holding the node name; empty means the name is `''`.

#### concept\_name\_prefix

```
concept_name_prefix: LegacyStr = ''
```

The prefix of each node name.

#### concept\_type

```
concept_type: str
```

The node's Archimate element type tag, e.g. `lineage_dataset` or `lineage_process`.

#### id

```
id: LegacyStr = ''
```

The rule's id — the reference relation and view rules use to name it.

#### id\_key

```
id_key: str
```

The column holding each node's id; rows with a null id are dropped, first row per id wins.

#### id\_prefix

```
id_prefix: LegacyStr = ''
```

The prefix of each node id.

#### mapping

```
mapping: list[MappingEntry]
```

Metadata attributes to attach per row, each a key/value pair.

#### model\_config

```
model_config = ConfigDict(extra='ignore', frozen=True)
```

### ExtractionRequest

Bases: `_Rule`

The `POST /extract` body: `{data: [row…], rules: {...}}`.

**Show JSON schema:**

```
{
  "$defs": {
    "ElementRule": {
      "description": "An element rule (legacy ``ElementDefinition``): one node per row of ``id_key``.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "id_key": {
          "description": "The column holding each node's id; rows with a null id are dropped, first row per id wins.",
          "title": "Id Key",
          "type": "string"
        },
        "concept_type": {
          "description": "The node's Archimate element type tag, e.g. ``lineage_dataset`` or ``lineage_process``.",
          "title": "Concept Type",
          "type": "string"
        },
        "id_prefix": {
          "default": "",
          "description": "The prefix of each node id.",
          "title": "Id Prefix",
          "type": "string"
        },
        "concept_name_prefix": {
          "default": "",
          "description": "The prefix of each node name.",
          "title": "Concept Name Prefix",
          "type": "string"
        },
        "concept_name_key": {
          "default": "",
          "description": "The column holding the node name; empty means the name is ``''``.",
          "title": "Concept Name Key",
          "type": "string"
        },
        "concept_label_prefix": {
          "default": "",
          "description": "The prefix of the node label; kept for the legacy contract, the ar3 writer ignores labels.",
          "title": "Concept Label Prefix",
          "type": "string"
        },
        "concept_label_key": {
          "default": "",
          "description": "The column holding the node label; the ar3 writer ignores labels.",
          "title": "Concept Label Key",
          "type": "string"
        },
        "mapping": {
          "description": "Metadata attributes to attach per row, each a key/value pair.",
          "items": {
            "$ref": "#/$defs/MappingEntry"
          },
          "title": "Mapping",
          "type": "array"
        }
      },
      "required": [
        "id_key",
        "concept_type"
      ],
      "title": "ElementRule",
      "type": "object"
    },
    "MappingEntry": {
      "description": "One ``{key, value}``: attach column ``value`` as metadata attribute ``key``.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "key": {
          "description": "The metadata attribute's name.",
          "title": "Key",
          "type": "string"
        },
        "value": {
          "description": "The source column's name.",
          "title": "Value",
          "type": "string"
        }
      },
      "required": [
        "key",
        "value"
      ],
      "title": "MappingEntry",
      "type": "object"
    },
    "RelationRule": {
      "description": "A relation rule (legacy ``RelationshipDefinition``): one edge per row.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "id_key": {
          "description": "The column holding each edge's id.",
          "title": "Id Key",
          "type": "string"
        },
        "relationship_type": {
          "description": "The Archimate relationship shorthand, e.g. ``lr`` for the lineage chain.",
          "title": "Relationship Type",
          "type": "string"
        },
        "source": {
          "default": "",
          "description": "The id of the element rule holding the source ids.",
          "title": "Source",
          "type": "string"
        },
        "target": {
          "default": "",
          "description": "The id of the element rule holding the target ids.",
          "title": "Target",
          "type": "string"
        },
        "id_prefix": {
          "default": "",
          "description": "The prefix of each edge id.",
          "title": "Id Prefix",
          "type": "string"
        },
        "relationship_name_key": {
          "default": "",
          "description": "The column holding the edge name; empty means the name is ``''``.",
          "title": "Relationship Name Key",
          "type": "string"
        },
        "relationship_label_key": {
          "default": "",
          "description": "The column holding the edge label; the ar3 writer ignores labels.",
          "title": "Relationship Label Key",
          "type": "string"
        },
        "mapping": {
          "description": "Metadata attributes to attach per row, each a key/value pair.",
          "items": {
            "$ref": "#/$defs/MappingEntry"
          },
          "title": "Mapping",
          "type": "array"
        }
      },
      "required": [
        "id_key",
        "relationship_type"
      ],
      "title": "RelationRule",
      "type": "object"
    },
    "RulesDef": {
      "description": "The ``rules`` body: elements, relations, views, in rule order.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "elements": {
          "description": "The element rules.",
          "items": {
            "$ref": "#/$defs/ElementRule"
          },
          "title": "Elements",
          "type": "array"
        },
        "relations": {
          "description": "The relation rules.",
          "items": {
            "$ref": "#/$defs/RelationRule"
          },
          "title": "Relations",
          "type": "array"
        },
        "views": {
          "description": "The view rules.",
          "items": {
            "$ref": "#/$defs/ViewRule"
          },
          "title": "Views",
          "type": "array"
        }
      },
      "title": "RulesDef",
      "type": "object"
    },
    "ViewEdgeRule": {
      "description": "A view edge entry: includes the referenced relation rule's edges.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "rule": {
          "description": "The id of the relation rule whose rows fill the view.",
          "title": "Rule",
          "type": "string"
        }
      },
      "required": [
        "rule"
      ],
      "title": "ViewEdgeRule",
      "type": "object"
    },
    "ViewNodeRule": {
      "description": "A view node entry: includes the referenced element rule's nodes.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "rule": {
          "description": "The id of the element rule whose rows fill the view.",
          "title": "Rule",
          "type": "string"
        }
      },
      "required": [
        "rule"
      ],
      "title": "ViewNodeRule",
      "type": "object"
    },
    "ViewRule": {
      "description": "A view rule (legacy ``ViewDefinition``): one diagram per layout match.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "view_layout": {
          "default": "",
          "description": "The layout name; a layout the registry does not know drops the view entirely.",
          "title": "View Layout",
          "type": "string"
        },
        "id_type": {
          "default": "dynamic",
          "description": "``static``: one view ided by ``id_value``; ``dynamic``: one view per value of ``id_key``.",
          "title": "Id Type",
          "type": "string"
        },
        "id_key": {
          "default": "",
          "description": "The grouping column for a dynamic view.",
          "title": "Id Key",
          "type": "string"
        },
        "id_value": {
          "default": "",
          "description": "The view id for a static view.",
          "title": "Id Value",
          "type": "string"
        },
        "id_prefix": {
          "default": "",
          "description": "The prefix of a dynamic view id.",
          "title": "Id Prefix",
          "type": "string"
        },
        "view_name_type": {
          "default": "dynamic",
          "description": "``static``: the name is ``view_name_value``; ``dynamic``: the name comes from ``view_name_key``.",
          "title": "View Name Type",
          "type": "string"
        },
        "view_name_key": {
          "default": "",
          "description": "The column holding the view name for a dynamic view.",
          "title": "View Name Key",
          "type": "string"
        },
        "view_name_value": {
          "default": "",
          "description": "The view name for a static view.",
          "title": "View Name Value",
          "type": "string"
        },
        "view_name_prefix": {
          "default": "",
          "description": "The prefix of a dynamic view name.",
          "title": "View Name Prefix",
          "type": "string"
        },
        "view_nodes": {
          "description": "The element rules whose nodes fill the view, in order.",
          "items": {
            "$ref": "#/$defs/ViewNodeRule"
          },
          "title": "View Nodes",
          "type": "array"
        },
        "view_edges": {
          "description": "The relation rules whose edges fill the view; empty means all model edges between the view nodes.",
          "items": {
            "$ref": "#/$defs/ViewEdgeRule"
          },
          "title": "View Edges",
          "type": "array"
        },
        "view_path": {
          "description": "Extra organization folders below ``Views`` (legacy ``ViewPathMapping``s; static entries only).",
          "items": {
            "type": "string"
          },
          "title": "View Path",
          "type": "array"
        },
        "mapping": {
          "description": "Metadata attributes to attach per view; unused by the writer, kept for the contract.",
          "items": {
            "$ref": "#/$defs/MappingEntry"
          },
          "title": "Mapping",
          "type": "array"
        }
      },
      "title": "ViewRule",
      "type": "object"
    }
  },
  "description": "The ``POST /extract`` body: ``{data: [row\u2026], rules: {...}}``.",
  "properties": {
    "id": {
      "default": "",
      "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
      "title": "Id",
      "type": "string"
    },
    "data": {
      "description": "The tabular rows; each row is a plain map of column names to values.",
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "title": "Data",
      "type": "array"
    },
    "rules": {
      "$ref": "#/$defs/RulesDef",
      "description": "The element, relation, and view rules that build the model."
    }
  },
  "title": "ExtractionRequest",
  "type": "object"
}
```

Fields:

- `id` (`LegacyStr`)
- `data` (`list[dict[str, Any]]`)
- `rules` (`RulesDef`)

#### data

```
data: list[dict[str, Any]]
```

The tabular rows; each row is a plain map of column names to values.

#### id

```
id: LegacyStr = ''
```

The rule's id — the reference relation and view rules use to name it.

#### model\_config

```
model_config = ConfigDict(extra='ignore', frozen=True)
```

#### rules

```
rules: RulesDef
```

The element, relation, and view rules that build the model.

### ExtractionResponse

Bases: `BaseModel`

The `POST /extract` answer: `{metadata: […], model: "<ar3 JSON string>"}`.

**Show JSON schema:**

```
{
  "$defs": {
    "MetadataEntry": {
      "description": "One ``{id, data}`` metadata entry of the extraction answer.",
      "properties": {
        "id": {
          "description": "The element, edge, or view id the entry describes, with its rule's prefix.",
          "title": "Id",
          "type": "string"
        },
        "data": {
          "additionalProperties": true,
          "description": "The provenance and mapped attributes, as open key/value maps.",
          "title": "Data",
          "type": "object"
        }
      },
      "required": [
        "id"
      ],
      "title": "MetadataEntry",
      "type": "object"
    }
  },
  "description": "The ``POST /extract`` answer: ``{metadata: [\u2026], model: \"<ar3 JSON string>\"}``.",
  "properties": {
    "metadata": {
      "description": "One entry per element/edge row and per view.",
      "items": {
        "$ref": "#/$defs/MetadataEntry"
      },
      "title": "Metadata",
      "type": "array"
    },
    "model": {
      "description": "The ar3 model, JSON-encoded as a string; the browser draws it.",
      "title": "Model",
      "type": "string"
    }
  },
  "required": [
    "model"
  ],
  "title": "ExtractionResponse",
  "type": "object"
}
```

Config:

- `extra`: `ignore`
- `frozen`: `True`

Fields:

- `metadata` (`list[MetadataEntry]`)
- `model` (`str`)

#### metadata

```
metadata: list[MetadataEntry]
```

One entry per element/edge row and per view.

#### model

```
model: str
```

The ar3 model, JSON-encoded as a string; the browser draws it.

#### model\_config

```
model_config = ConfigDict(extra='ignore', frozen=True)
```

### MappingEntry

Bases: `_Rule`

One `{key, value}`: attach column `value` as metadata attribute `key`.

**Show JSON schema:**

```
{
  "description": "One ``{key, value}``: attach column ``value`` as metadata attribute ``key``.",
  "properties": {
    "id": {
      "default": "",
      "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
      "title": "Id",
      "type": "string"
    },
    "key": {
      "description": "The metadata attribute's name.",
      "title": "Key",
      "type": "string"
    },
    "value": {
      "description": "The source column's name.",
      "title": "Value",
      "type": "string"
    }
  },
  "required": [
    "key",
    "value"
  ],
  "title": "MappingEntry",
  "type": "object"
}
```

Fields:

- `id` (`LegacyStr`)
- `key` (`str`)
- `value` (`str`)

#### id

```
id: LegacyStr = ''
```

The rule's id — the reference relation and view rules use to name it.

#### key

```
key: str
```

The metadata attribute's name.

#### model\_config

```
model_config = ConfigDict(extra='ignore', frozen=True)
```

#### value

```
value: str
```

The source column's name.

### MetadataEntry

Bases: `BaseModel`

One `{id, data}` metadata entry of the extraction answer.

**Show JSON schema:**

```
{
  "description": "One ``{id, data}`` metadata entry of the extraction answer.",
  "properties": {
    "id": {
      "description": "The element, edge, or view id the entry describes, with its rule's prefix.",
      "title": "Id",
      "type": "string"
    },
    "data": {
      "additionalProperties": true,
      "description": "The provenance and mapped attributes, as open key/value maps.",
      "title": "Data",
      "type": "object"
    }
  },
  "required": [
    "id"
  ],
  "title": "MetadataEntry",
  "type": "object"
}
```

Config:

- `extra`: `ignore`
- `frozen`: `True`

Fields:

- `id` (`str`)
- `data` (`dict[str, Any]`)

#### data

```
data: dict[str, Any]
```

The provenance and mapped attributes, as open key/value maps.

#### id

```
id: str
```

The element, edge, or view id the entry describes, with its rule's prefix.

#### model\_config

```
model_config = ConfigDict(extra='ignore', frozen=True)
```

### RelationRule

Bases: `_Rule`

A relation rule (legacy `RelationshipDefinition`): one edge per row.

**Show JSON schema:**

```
{
  "$defs": {
    "MappingEntry": {
      "description": "One ``{key, value}``: attach column ``value`` as metadata attribute ``key``.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "key": {
          "description": "The metadata attribute's name.",
          "title": "Key",
          "type": "string"
        },
        "value": {
          "description": "The source column's name.",
          "title": "Value",
          "type": "string"
        }
      },
      "required": [
        "key",
        "value"
      ],
      "title": "MappingEntry",
      "type": "object"
    }
  },
  "description": "A relation rule (legacy ``RelationshipDefinition``): one edge per row.",
  "properties": {
    "id": {
      "default": "",
      "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
      "title": "Id",
      "type": "string"
    },
    "id_key": {
      "description": "The column holding each edge's id.",
      "title": "Id Key",
      "type": "string"
    },
    "relationship_type": {
      "description": "The Archimate relationship shorthand, e.g. ``lr`` for the lineage chain.",
      "title": "Relationship Type",
      "type": "string"
    },
    "source": {
      "default": "",
      "description": "The id of the element rule holding the source ids.",
      "title": "Source",
      "type": "string"
    },
    "target": {
      "default": "",
      "description": "The id of the element rule holding the target ids.",
      "title": "Target",
      "type": "string"
    },
    "id_prefix": {
      "default": "",
      "description": "The prefix of each edge id.",
      "title": "Id Prefix",
      "type": "string"
    },
    "relationship_name_key": {
      "default": "",
      "description": "The column holding the edge name; empty means the name is ``''``.",
      "title": "Relationship Name Key",
      "type": "string"
    },
    "relationship_label_key": {
      "default": "",
      "description": "The column holding the edge label; the ar3 writer ignores labels.",
      "title": "Relationship Label Key",
      "type": "string"
    },
    "mapping": {
      "description": "Metadata attributes to attach per row, each a key/value pair.",
      "items": {
        "$ref": "#/$defs/MappingEntry"
      },
      "title": "Mapping",
      "type": "array"
    }
  },
  "required": [
    "id_key",
    "relationship_type"
  ],
  "title": "RelationRule",
  "type": "object"
}
```

Fields:

- `id` (`LegacyStr`)
- `id_key` (`str`)
- `relationship_type` (`str`)
- `source` (`LegacyStr`)
- `target` (`LegacyStr`)
- `id_prefix` (`LegacyStr`)
- `relationship_name_key` (`LegacyStr`)
- `relationship_label_key` (`LegacyStr`)
- `mapping` (`list[MappingEntry]`)

Validators:

- `_known_relationship_type` → `relationship_type`

#### id

```
id: LegacyStr = ''
```

The rule's id — the reference relation and view rules use to name it.

#### id\_key

```
id_key: str
```

The column holding each edge's id.

#### id\_prefix

```
id_prefix: LegacyStr = ''
```

The prefix of each edge id.

#### mapping

```
mapping: list[MappingEntry]
```

Metadata attributes to attach per row, each a key/value pair.

#### model\_config

```
model_config = ConfigDict(extra='ignore', frozen=True)
```

#### relationship\_label\_key

```
relationship_label_key: LegacyStr = ''
```

The column holding the edge label; the ar3 writer ignores labels.

#### relationship\_name\_key

```
relationship_name_key: LegacyStr = ''
```

The column holding the edge name; empty means the name is `''`.

#### relationship\_type

```
relationship_type: str
```

The Archimate relationship shorthand, e.g. `lr` for the lineage chain.

#### source

```
source: LegacyStr = ''
```

The id of the element rule holding the source ids.

#### target

```
target: LegacyStr = ''
```

The id of the element rule holding the target ids.

### RulesDef

Bases: `_Rule`

The `rules` body: elements, relations, views, in rule order.

**Show JSON schema:**

```
{
  "$defs": {
    "ElementRule": {
      "description": "An element rule (legacy ``ElementDefinition``): one node per row of ``id_key``.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "id_key": {
          "description": "The column holding each node's id; rows with a null id are dropped, first row per id wins.",
          "title": "Id Key",
          "type": "string"
        },
        "concept_type": {
          "description": "The node's Archimate element type tag, e.g. ``lineage_dataset`` or ``lineage_process``.",
          "title": "Concept Type",
          "type": "string"
        },
        "id_prefix": {
          "default": "",
          "description": "The prefix of each node id.",
          "title": "Id Prefix",
          "type": "string"
        },
        "concept_name_prefix": {
          "default": "",
          "description": "The prefix of each node name.",
          "title": "Concept Name Prefix",
          "type": "string"
        },
        "concept_name_key": {
          "default": "",
          "description": "The column holding the node name; empty means the name is ``''``.",
          "title": "Concept Name Key",
          "type": "string"
        },
        "concept_label_prefix": {
          "default": "",
          "description": "The prefix of the node label; kept for the legacy contract, the ar3 writer ignores labels.",
          "title": "Concept Label Prefix",
          "type": "string"
        },
        "concept_label_key": {
          "default": "",
          "description": "The column holding the node label; the ar3 writer ignores labels.",
          "title": "Concept Label Key",
          "type": "string"
        },
        "mapping": {
          "description": "Metadata attributes to attach per row, each a key/value pair.",
          "items": {
            "$ref": "#/$defs/MappingEntry"
          },
          "title": "Mapping",
          "type": "array"
        }
      },
      "required": [
        "id_key",
        "concept_type"
      ],
      "title": "ElementRule",
      "type": "object"
    },
    "MappingEntry": {
      "description": "One ``{key, value}``: attach column ``value`` as metadata attribute ``key``.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "key": {
          "description": "The metadata attribute's name.",
          "title": "Key",
          "type": "string"
        },
        "value": {
          "description": "The source column's name.",
          "title": "Value",
          "type": "string"
        }
      },
      "required": [
        "key",
        "value"
      ],
      "title": "MappingEntry",
      "type": "object"
    },
    "RelationRule": {
      "description": "A relation rule (legacy ``RelationshipDefinition``): one edge per row.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "id_key": {
          "description": "The column holding each edge's id.",
          "title": "Id Key",
          "type": "string"
        },
        "relationship_type": {
          "description": "The Archimate relationship shorthand, e.g. ``lr`` for the lineage chain.",
          "title": "Relationship Type",
          "type": "string"
        },
        "source": {
          "default": "",
          "description": "The id of the element rule holding the source ids.",
          "title": "Source",
          "type": "string"
        },
        "target": {
          "default": "",
          "description": "The id of the element rule holding the target ids.",
          "title": "Target",
          "type": "string"
        },
        "id_prefix": {
          "default": "",
          "description": "The prefix of each edge id.",
          "title": "Id Prefix",
          "type": "string"
        },
        "relationship_name_key": {
          "default": "",
          "description": "The column holding the edge name; empty means the name is ``''``.",
          "title": "Relationship Name Key",
          "type": "string"
        },
        "relationship_label_key": {
          "default": "",
          "description": "The column holding the edge label; the ar3 writer ignores labels.",
          "title": "Relationship Label Key",
          "type": "string"
        },
        "mapping": {
          "description": "Metadata attributes to attach per row, each a key/value pair.",
          "items": {
            "$ref": "#/$defs/MappingEntry"
          },
          "title": "Mapping",
          "type": "array"
        }
      },
      "required": [
        "id_key",
        "relationship_type"
      ],
      "title": "RelationRule",
      "type": "object"
    },
    "ViewEdgeRule": {
      "description": "A view edge entry: includes the referenced relation rule's edges.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "rule": {
          "description": "The id of the relation rule whose rows fill the view.",
          "title": "Rule",
          "type": "string"
        }
      },
      "required": [
        "rule"
      ],
      "title": "ViewEdgeRule",
      "type": "object"
    },
    "ViewNodeRule": {
      "description": "A view node entry: includes the referenced element rule's nodes.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "rule": {
          "description": "The id of the element rule whose rows fill the view.",
          "title": "Rule",
          "type": "string"
        }
      },
      "required": [
        "rule"
      ],
      "title": "ViewNodeRule",
      "type": "object"
    },
    "ViewRule": {
      "description": "A view rule (legacy ``ViewDefinition``): one diagram per layout match.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "view_layout": {
          "default": "",
          "description": "The layout name; a layout the registry does not know drops the view entirely.",
          "title": "View Layout",
          "type": "string"
        },
        "id_type": {
          "default": "dynamic",
          "description": "``static``: one view ided by ``id_value``; ``dynamic``: one view per value of ``id_key``.",
          "title": "Id Type",
          "type": "string"
        },
        "id_key": {
          "default": "",
          "description": "The grouping column for a dynamic view.",
          "title": "Id Key",
          "type": "string"
        },
        "id_value": {
          "default": "",
          "description": "The view id for a static view.",
          "title": "Id Value",
          "type": "string"
        },
        "id_prefix": {
          "default": "",
          "description": "The prefix of a dynamic view id.",
          "title": "Id Prefix",
          "type": "string"
        },
        "view_name_type": {
          "default": "dynamic",
          "description": "``static``: the name is ``view_name_value``; ``dynamic``: the name comes from ``view_name_key``.",
          "title": "View Name Type",
          "type": "string"
        },
        "view_name_key": {
          "default": "",
          "description": "The column holding the view name for a dynamic view.",
          "title": "View Name Key",
          "type": "string"
        },
        "view_name_value": {
          "default": "",
          "description": "The view name for a static view.",
          "title": "View Name Value",
          "type": "string"
        },
        "view_name_prefix": {
          "default": "",
          "description": "The prefix of a dynamic view name.",
          "title": "View Name Prefix",
          "type": "string"
        },
        "view_nodes": {
          "description": "The element rules whose nodes fill the view, in order.",
          "items": {
            "$ref": "#/$defs/ViewNodeRule"
          },
          "title": "View Nodes",
          "type": "array"
        },
        "view_edges": {
          "description": "The relation rules whose edges fill the view; empty means all model edges between the view nodes.",
          "items": {
            "$ref": "#/$defs/ViewEdgeRule"
          },
          "title": "View Edges",
          "type": "array"
        },
        "view_path": {
          "description": "Extra organization folders below ``Views`` (legacy ``ViewPathMapping``s; static entries only).",
          "items": {
            "type": "string"
          },
          "title": "View Path",
          "type": "array"
        },
        "mapping": {
          "description": "Metadata attributes to attach per view; unused by the writer, kept for the contract.",
          "items": {
            "$ref": "#/$defs/MappingEntry"
          },
          "title": "Mapping",
          "type": "array"
        }
      },
      "title": "ViewRule",
      "type": "object"
    }
  },
  "description": "The ``rules`` body: elements, relations, views, in rule order.",
  "properties": {
    "id": {
      "default": "",
      "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
      "title": "Id",
      "type": "string"
    },
    "elements": {
      "description": "The element rules.",
      "items": {
        "$ref": "#/$defs/ElementRule"
      },
      "title": "Elements",
      "type": "array"
    },
    "relations": {
      "description": "The relation rules.",
      "items": {
        "$ref": "#/$defs/RelationRule"
      },
      "title": "Relations",
      "type": "array"
    },
    "views": {
      "description": "The view rules.",
      "items": {
        "$ref": "#/$defs/ViewRule"
      },
      "title": "Views",
      "type": "array"
    }
  },
  "title": "RulesDef",
  "type": "object"
}
```

Fields:

- `id` (`LegacyStr`)
- `elements` (`list[ElementRule]`)
- `relations` (`list[RelationRule]`)
- `views` (`list[ViewRule]`)

Validators:

- `_references_resolve`

#### elements

```
elements: list[ElementRule]
```

The element rules.

#### id

```
id: LegacyStr = ''
```

The rule's id — the reference relation and view rules use to name it.

#### model\_config

```
model_config = ConfigDict(extra='ignore', frozen=True)
```

#### relations

```
relations: list[RelationRule]
```

The relation rules.

#### views

```
views: list[ViewRule]
```

The view rules.

### ViewEdgeRule

Bases: `_Rule`

A view edge entry: includes the referenced relation rule's edges.

**Show JSON schema:**

```
{
  "description": "A view edge entry: includes the referenced relation rule's edges.",
  "properties": {
    "id": {
      "default": "",
      "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
      "title": "Id",
      "type": "string"
    },
    "rule": {
      "description": "The id of the relation rule whose rows fill the view.",
      "title": "Rule",
      "type": "string"
    }
  },
  "required": [
    "rule"
  ],
  "title": "ViewEdgeRule",
  "type": "object"
}
```

Fields:

- `id` (`LegacyStr`)
- `rule` (`str`)

#### id

```
id: LegacyStr = ''
```

The rule's id — the reference relation and view rules use to name it.

#### model\_config

```
model_config = ConfigDict(extra='ignore', frozen=True)
```

#### rule

```
rule: str
```

The id of the relation rule whose rows fill the view.

### ViewNodeRule

Bases: `_Rule`

A view node entry: includes the referenced element rule's nodes.

**Show JSON schema:**

```
{
  "description": "A view node entry: includes the referenced element rule's nodes.",
  "properties": {
    "id": {
      "default": "",
      "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
      "title": "Id",
      "type": "string"
    },
    "rule": {
      "description": "The id of the element rule whose rows fill the view.",
      "title": "Rule",
      "type": "string"
    }
  },
  "required": [
    "rule"
  ],
  "title": "ViewNodeRule",
  "type": "object"
}
```

Fields:

- `id` (`LegacyStr`)
- `rule` (`str`)

#### id

```
id: LegacyStr = ''
```

The rule's id — the reference relation and view rules use to name it.

#### model\_config

```
model_config = ConfigDict(extra='ignore', frozen=True)
```

#### rule

```
rule: str
```

The id of the element rule whose rows fill the view.

### ViewRule

Bases: `_Rule`

A view rule (legacy `ViewDefinition`): one diagram per layout match.

**Show JSON schema:**

```
{
  "$defs": {
    "MappingEntry": {
      "description": "One ``{key, value}``: attach column ``value`` as metadata attribute ``key``.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "key": {
          "description": "The metadata attribute's name.",
          "title": "Key",
          "type": "string"
        },
        "value": {
          "description": "The source column's name.",
          "title": "Value",
          "type": "string"
        }
      },
      "required": [
        "key",
        "value"
      ],
      "title": "MappingEntry",
      "type": "object"
    },
    "ViewEdgeRule": {
      "description": "A view edge entry: includes the referenced relation rule's edges.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "rule": {
          "description": "The id of the relation rule whose rows fill the view.",
          "title": "Rule",
          "type": "string"
        }
      },
      "required": [
        "rule"
      ],
      "title": "ViewEdgeRule",
      "type": "object"
    },
    "ViewNodeRule": {
      "description": "A view node entry: includes the referenced element rule's nodes.",
      "properties": {
        "id": {
          "default": "",
          "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
          "title": "Id",
          "type": "string"
        },
        "rule": {
          "description": "The id of the element rule whose rows fill the view.",
          "title": "Rule",
          "type": "string"
        }
      },
      "required": [
        "rule"
      ],
      "title": "ViewNodeRule",
      "type": "object"
    }
  },
  "description": "A view rule (legacy ``ViewDefinition``): one diagram per layout match.",
  "properties": {
    "id": {
      "default": "",
      "description": "The rule's id \u2014 the reference relation and view rules use to name it.",
      "title": "Id",
      "type": "string"
    },
    "view_layout": {
      "default": "",
      "description": "The layout name; a layout the registry does not know drops the view entirely.",
      "title": "View Layout",
      "type": "string"
    },
    "id_type": {
      "default": "dynamic",
      "description": "``static``: one view ided by ``id_value``; ``dynamic``: one view per value of ``id_key``.",
      "title": "Id Type",
      "type": "string"
    },
    "id_key": {
      "default": "",
      "description": "The grouping column for a dynamic view.",
      "title": "Id Key",
      "type": "string"
    },
    "id_value": {
      "default": "",
      "description": "The view id for a static view.",
      "title": "Id Value",
      "type": "string"
    },
    "id_prefix": {
      "default": "",
      "description": "The prefix of a dynamic view id.",
      "title": "Id Prefix",
      "type": "string"
    },
    "view_name_type": {
      "default": "dynamic",
      "description": "``static``: the name is ``view_name_value``; ``dynamic``: the name comes from ``view_name_key``.",
      "title": "View Name Type",
      "type": "string"
    },
    "view_name_key": {
      "default": "",
      "description": "The column holding the view name for a dynamic view.",
      "title": "View Name Key",
      "type": "string"
    },
    "view_name_value": {
      "default": "",
      "description": "The view name for a static view.",
      "title": "View Name Value",
      "type": "string"
    },
    "view_name_prefix": {
      "default": "",
      "description": "The prefix of a dynamic view name.",
      "title": "View Name Prefix",
      "type": "string"
    },
    "view_nodes": {
      "description": "The element rules whose nodes fill the view, in order.",
      "items": {
        "$ref": "#/$defs/ViewNodeRule"
      },
      "title": "View Nodes",
      "type": "array"
    },
    "view_edges": {
      "description": "The relation rules whose edges fill the view; empty means all model edges between the view nodes.",
      "items": {
        "$ref": "#/$defs/ViewEdgeRule"
      },
      "title": "View Edges",
      "type": "array"
    },
    "view_path": {
      "description": "Extra organization folders below ``Views`` (legacy ``ViewPathMapping``s; static entries only).",
      "items": {
        "type": "string"
      },
      "title": "View Path",
      "type": "array"
    },
    "mapping": {
      "description": "Metadata attributes to attach per view; unused by the writer, kept for the contract.",
      "items": {
        "$ref": "#/$defs/MappingEntry"
      },
      "title": "Mapping",
      "type": "array"
    }
  },
  "title": "ViewRule",
  "type": "object"
}
```

Fields:

- `id` (`LegacyStr`)
- `view_layout` (`LegacyStr`)
- `id_type` (`LegacyStr`)
- `id_key` (`LegacyStr`)
- `id_value` (`LegacyStr`)
- `id_prefix` (`LegacyStr`)
- `view_name_type` (`LegacyStr`)
- `view_name_key` (`LegacyStr`)
- `view_name_value` (`LegacyStr`)
- `view_name_prefix` (`LegacyStr`)
- `view_nodes` (`list[ViewNodeRule]`)
- `view_edges` (`list[ViewEdgeRule]`)
- `view_path` (`list[LegacyStr]`)
- `mapping` (`list[MappingEntry]`)

#### id

```
id: LegacyStr = ''
```

The rule's id — the reference relation and view rules use to name it.

#### id\_key

```
id_key: LegacyStr = ''
```

The grouping column for a dynamic view.

#### id\_prefix

```
id_prefix: LegacyStr = ''
```

The prefix of a dynamic view id.

#### id\_type

```
id_type: LegacyStr = 'dynamic'
```

`static`: one view ided by `id_value`; `dynamic`: one view per value of `id_key`.

#### id\_value

```
id_value: LegacyStr = ''
```

The view id for a static view.

#### mapping

```
mapping: list[MappingEntry]
```

Metadata attributes to attach per view; unused by the writer, kept for the contract.

#### model\_config

```
model_config = ConfigDict(extra='ignore', frozen=True)
```

#### view\_edges

```
view_edges: list[ViewEdgeRule]
```

The relation rules whose edges fill the view; empty means all model edges between the view nodes.

#### view\_layout

```
view_layout: LegacyStr = ''
```

The layout name; a layout the registry does not know drops the view entirely.

#### view\_name\_key

```
view_name_key: LegacyStr = ''
```

The column holding the view name for a dynamic view.

#### view\_name\_prefix

```
view_name_prefix: LegacyStr = ''
```

The prefix of a dynamic view name.

#### view\_name\_type

```
view_name_type: LegacyStr = 'dynamic'
```

`static`: the name is `view_name_value`; `dynamic`: the name comes from `view_name_key`.

#### view\_name\_value

```
view_name_value: LegacyStr = ''
```

The view name for a static view.

#### view\_nodes

```
view_nodes: list[ViewNodeRule]
```

The element rules whose nodes fill the view, in order.

#### view\_path

```
view_path: list[LegacyStr]
```

Extra organization folders below `Views` (legacy `ViewPathMapping`s; static entries only).

## aurelius\_atlas\_data2model\_client.types

The Archimate 3.0 concept types a rule may name (DTM-11), ported from `m4i-analytics`.

The legacy `ElementType` / `RelationshipType` enums (`metamodel/Concepts.py`) are tables of data; the port keeps the two columns the extractor needs — the ar3 `@xsi_type` tag, and for elements the layer that organises them (`ArchimateModel.organize`) and for relationships the type attributes the ar3 writer emits — and drops the enum machinery.

The tables are the request contract's validation domain (DTM-11), so they live with the contract in this library (CL-20, DD-203); the ar3 writer's layout constants stayed in the app's engine.

Attributes:

- **`ELEMENT_TYPE_LAYERS`** (`dict[str, str]`) –

  Element type tag → layer; the tags a rule's `concept_type` may name (the lineage chain uses the last pair).
- **`LAYOUT_NAMES`** –

  The view layouts the legacy registry knew (`m4i-graphviz-layouts`).
- **`RELATIONSHIP_SHORTHANDS`** (`dict[str, tuple[str, dict[str, str]]]`) –

  Relationship shorthand → (ar3 tag, ar3 attributes).

### ELEMENT\_TYPE\_LAYERS

```
ELEMENT_TYPE_LAYERS: dict[str, str] = {
    "ar3_AndJunction": "Other",
    "ar3_ApplicationCollaboration": "Application",
    "ar3_ApplicationComponent": "Application",
    "ar3_ApplicationEvent": "Application",
    "ar3_ApplicationFunction": "Application",
    "ar3_ApplicationInteraction": "Application",
    "ar3_ApplicationInterface": "Application",
    "ar3_ApplicationProcess": "Application",
    "ar3_ApplicationService": "Application",
    "ar3_Artifact": "Technology",
    "ar3_Assessment": "Motivation",
    "ar3_BusinessActor": "Business",
    "ar3_BusinessCollaboration": "Business",
    "ar3_BusinessEvent": "Business",
    "ar3_BusinessFunction": "Business",
    "ar3_BusinessInteraction": "Business",
    "ar3_BusinessInterface": "Business",
    "ar3_BusinessObject": "Business",
    "ar3_BusinessProcess": "Business",
    "ar3_BusinessRole": "Business",
    "ar3_BusinessService": "Business",
    "ar3_Capability": "Strategy",
    "ar3_CommunicationNetwork": "Technology",
    "ar3_Constraint": "Motivation",
    "ar3_Contract": "Business",
    "ar3_CourseOfAction": "Strategy",
    "ar3_DataObject": "Application",
    "ar3_Deliverable": "Implementation & Migration",
    "ar3_Device": "Technology",
    "ar3_DistributionNetwork": "Physical",
    "ar3_Driver": "Motivation",
    "ar3_Equipment": "Physical",
    "ar3_Facility": "Physical",
    "ar3_Gap": "Implementation & Migration",
    "ar3_Goal": "Motivation",
    "ar3_Grouping": "Composite",
    "ar3_ImplementationEvent": "Implementation & Migration",
    "ar3_Junction": "Other",
    "ar3_Location": "Composite",
    "ar3_Material": "Physical",
    "ar3_Meaning": "Motivation",
    "ar3_Node": "Technology",
    "ar3_OrJunction": "Other",
    "ar3_Outcome": "Motivation",
    "ar3_Path": "Technology",
    "ar3_Plateau": "Implementation & Migration",
    "ar3_Principle": "Motivation",
    "ar3_Product": "Business",
    "ar3_Representation": "Business",
    "ar3_Requirement": "Motivation",
    "ar3_Resource": "Strategy",
    "ar3_Stakeholder": "Motivation",
    "ar3_SystemSoftware": "Technology",
    "ar3_TechnologyCollaboration": "Technology",
    "ar3_TechnologyEvent": "Technology",
    "ar3_TechnologyFunction": "Technology",
    "ar3_TechnologyInteraction": "Technology",
    "ar3_TechnologyInterface": "Technology",
    "ar3_TechnologyProcess": "Technology",
    "ar3_TechnologyService": "Technology",
    "ar3_Unknown": "Other",
    "ar3_Value": "Motivation",
    "ar3_ValueStream": "Strategy",
    "ar3_WorkPackage": "Implementation & Migration",
    "lineage_dataset": "Other",
    "lineage_process": "Other",
}
```

Element type tag → layer; the tags a rule's `concept_type` may name (the lineage chain uses the last pair).

### LAYOUT\_NAMES

```
LAYOUT_NAMES = frozenset({'archimate_process', 'archimate_hierarchical'})
```

The view layouts the legacy registry knew (`m4i-graphviz-layouts`).

A view with any other layout is ignored (DTM-06).

### RELATIONSHIP\_SHORTHANDS

```
RELATIONSHIP_SHORTHANDS: dict[str, tuple[str, dict[str, str]]] = {
    "a": ("ar3_Access", {}),
    "aa": ("ar3_Access", {"accessType": "Access"}),
    "ar": ("ar3_Access", {"accessType": "Read"}),
    "aw": ("ar3_Access", {"accessType": "Write"}),
    "arw": ("ar3_Access", {"accessType": "ReadWrite"}),
    "g": ("ar3_Aggregation", {}),
    "i": ("ar3_Assignment", {}),
    "o": ("ar3_Association", {}),
    "do": ("ar3_Association", {"isDirected": "true"}),
    "c": ("ar3_Composition", {}),
    "f": ("ar3_Flow", {}),
    "n": ("ar3_Influence", {}),
    "lr": ("lineage_relation", {}),
    "r": ("ar3_Realization", {}),
    "v": ("ar3_Serving", {}),
    "s": ("ar3_Specialization", {}),
    "t": ("ar3_Triggering", {}),
}
```

Relationship shorthand → (ar3 tag, ar3 attributes).

The shorthands a rule's `relationship_type` may name.

## aurelius\_atlas\_data2model\_client.client

The async client for the data2model API (CL-01..CL-05, CL-21; DD-203, DD-204, DD-205).

The shared client conventions of increment 8.4: constructed from an externally built `httpx.AsyncClient` and a token source, reading no environment variables (CL-01) — the app builds the httpx client from its own settings and passes it in. The request path is relative, appended to that client's base URL, so a URL with a trailing slash — the `str()` of a pydantic `HttpUrl` — works as given (CL-01); the builder closes the pool, the API client never touches its lifecycle. Tests hand over one built on a `MockTransport` and no socket opens (CL-02); the bearer token goes on every call (CL-03); :class:`Data2ModelClientError` rises on a non-2xx answer, with the Atlas-shaped body when it parses (CL-04); an unreachable upstream propagates as `httpx`'s own error (CL-05).

`extract` posts an :class:`~aurelius_atlas_data2model_client.models.ExtractionRequest` — the same model class the server validates — and returns an :class:`~aurelius_atlas_data2model_client.models.ExtractionResponse`, so the 8.2 chain's payload and the 8.1 answer are one contract on both sides (CL-21).

Type Aliases:

- **`TokenSource`** –

  Where the bearer token comes from: a fixed token, or a callable that yields one (CL-03).

Classes:

- **`Data2ModelClient`** –

  The client for one data2model service (CL-21, DD-203, DD-205).
- **`Data2ModelClientError`** –

  A non-2xx answer from the data2model API, with the status and the error body (CL-04).

Attributes:

- **`CLIENT_ERROR`** –

  The status where an answer becomes an error: the client-error boundary (CL-04).
- **`DEFAULT_TIMEOUT_SECONDS`** –

  The suggested request timeout, seconds — for the httpx client an app builds (DD-200's bound).
- **`EXTRACT_PATH`** –

  The extraction endpoint of the data2model app (DTM-01), relative to the base URL (CL-01).

### CLIENT\_ERROR

```
CLIENT_ERROR = 400
```

The status where an answer becomes an error: the client-error boundary (CL-04).

### DEFAULT\_TIMEOUT\_SECONDS

```
DEFAULT_TIMEOUT_SECONDS = 10.0
```

The suggested request timeout, seconds — for the httpx client an app builds (DD-200's bound).

### EXTRACT\_PATH

```
EXTRACT_PATH = 'extract'
```

The extraction endpoint of the data2model app (DTM-01), relative to the base URL (CL-01).

### TokenSource

```
TokenSource = str | Callable[[], str]
```

Where the bearer token comes from: a fixed token, or a callable that yields one (CL-03).

### Data2ModelClient

```
Data2ModelClient(http: AsyncClient, token: TokenSource)
```

The client for one data2model service (CL-21, DD-203, DD-205).

Parameters:

- #### **`http`**

  (`AsyncClient`) –

  The `httpx.AsyncClient` to speak through, built by the caller — its builder owns its lifecycle, this client only speaks through it. Its base URL carries the service root; the path above is relative to it.
- #### **`token`**

  (`TokenSource`) –

  The bearer token source (CL-03) — 8.2 forwards the caller's own.

Methods:

- **`extract`** –

  `POST /extract`: the rows and rules in, the ar3 model and metadata out (DTM-01, CL-21).
- **`with_token`** –

  The same client speaking with `token` — sharing the connection pool (CL-03, LM-04).

#### extract

```
extract(request: ExtractionRequest) -> ExtractionResponse
```

`POST /extract`: the rows and rules in, the ar3 model and metadata out (DTM-01, CL-21).

Raises:

- `Data2ModelClientError` –

  The API answered 4xx/5xx (a 400 is the DTM-11 validation answer, with the Atlas-shaped body).

#### with\_token

```
with_token(token: TokenSource) -> Data2ModelClient
```

The same client speaking with `token` — sharing the connection pool (CL-03, LM-04).

### Data2ModelClientError

```
Data2ModelClientError(status_code: int, error_code: str | None, error_message: str | None)
```

Bases: `RuntimeError`

A non-2xx answer from the data2model API, with the status and the error body (CL-04).

Attributes:

- **`error_code`** –

  The `errorCode` of the Atlas-shaped body, when it parsed (DTM-11).
- **`error_message`** –

  The `errorMessage` of the Atlas-shaped body, when it parsed.
- **`status_code`** –

  The HTTP status the API answered with.

#### error\_code

```
error_code = error_code
```

The `errorCode` of the Atlas-shaped body, when it parsed (DTM-11).

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
