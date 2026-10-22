# aurelius-atlas-model

Atlas data shapes for Aurelius Atlas, without I/O ([DD-002](<https://aureliusenterprise.github.io/phase3-3.1b-relationship-attributes/architecture/conversion/design-log/#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer>)). Since increment [1.1](<https://aureliusenterprise.github.io/phase3-3.1b-relationship-attributes/architecture/conversion/increments/1-1-typedef-models/index.md>): the Apache Atlas 2.4.0 type definitions (enum, struct, classification, entity, relationship and business metadata), their header and `AtlasTypesDef`, as Pydantic models that read and write Atlas's REST JSON. Since [1.5](<https://aureliusenterprise.github.io/phase3-3.1b-relationship-attributes/architecture/conversion/increments/1-5-builtin-models/index.md>): the patch record `AtlasPatch`. Since [2.1a](<https://aureliusenterprise.github.io/phase3-3.1b-relationship-attributes/architecture/conversion/increments/2-1-entity-models/index.md>): the entity models of `aurelius_atlas_model.instance`, one module per Atlas class (`AtlasEntity`, `AtlasEntityWithExtInfo`, `AtlasEntityHeader`, `AtlasClassification`, `AtlasObjectId`, `EntityMutationResponse`, …), and the JSON conventions all models share in `aurelius_atlas_model.base`. Since [2.1b](<https://aureliusenterprise.github.io/phase3-3.1b-relationship-attributes/architecture/conversion/increments/2-1-value-types/index.md>): Atlas's JSON codec, `aurelius_atlas_model.codec`, which keeps the digits of decimals.

```
from aurelius_atlas_model.typedef import AtlasTypesDef

types = AtlasTypesDef.model_validate(request_body)  # Atlas's normalisations apply
response_body = types.to_json()  # Java names, nulls left out, epoch-millisecond dates

from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo

entities = AtlasEntitiesWithExtInfo.model_validate(request_body)  # entities without a GUID get "-<n>"
```

## Installation

```
dependencies = ["aurelius-atlas-model"]

[tool.uv.sources.aurelius-atlas-model]
workspace = true
```

## Documentation

## aurelius\_atlas\_model.typedef

Atlas type definitions as Pydantic models that read and write Atlas's REST JSON (DD-020).

Ported from `org.apache.atlas.model.typedef` of Apache Atlas 2.4.0. Field names are snake\_case in Python and the Java getter names in JSON (TDM-01). The normalisations the Java setters and constructors apply run as validators, so they hold for request bodies and for models built in code alike.

Type Aliases:

- **`AttributeDefs`** –

  `attributeDefs`: never null, one definition per name (TDM-06, TDM-07).

Classes:

- **`AtlasAttributeDef`** –

  An attribute of a struct, classification, entity, relationship or business metadata type (TDM-10).
- **`AtlasBaseTypeDef`** –

  What every type definition has: identity, audit fields, name and options.
- **`AtlasBusinessMetadataDef`** –

  A business metadata type: attributes that apply to the entity types its options name.
- **`AtlasClassificationDef`** –

  A classification type: attributes, super types and the entity types it may be applied to.
- **`AtlasConstraintDef`** –

  A constraint on an attribute, such as `ownedRef` or `inverseRef`.
- **`AtlasEntityDef`** –

  An entity type.
- **`AtlasEnumDef`** –

  An enum type.
- **`AtlasEnumElementDef`** –

  One value of an enum type.
- **`AtlasRelationshipAttributeDef`** –

  An entity attribute that a relationship type adds; read-only, derived from the relationship types.
- **`AtlasRelationshipDef`** –

  A relationship type between two entity types (TDM-12).
- **`AtlasRelationshipEndDef`** –

  One end of a relationship type: the entity type there and the attribute it gets (TDM-12).
- **`AtlasStructDef`** –

  A struct type, and the base of the types that have attributes.
- **`AtlasTypeDefHeader`** –

  The identity of a type definition, as `/v2/types/typedefs/headers` lists it.
- **`AtlasTypesDef`** –

  Type definitions of every kind: the body of `/v2/types/typedefs` (TDM-13).
- **`Cardinality`** –

  How many values an attribute or relationship end holds.
- **`IndexType`** –

  How an attribute is indexed.
- **`PropagateTags`** –

  The direction in which classifications propagate over a relationship.
- **`RelationshipCategory`** –

  How the two ends of a relationship depend on each other.
- **`TypeCategory`** –

  The kinds of Atlas types (`org.apache.atlas.model.TypeCategory`).

Functions:

- **`array_type_name`** –

  The name of the array type of `element_type_name`: `array<T>` (TDM-19).
- **`find_attribute`** –

  The first attribute definition named `name`, compared without case, or None (TDM-16).
- **`map_type_name`** –

  The name of the map type from `key_type_name` to `value_type_name`: `map<K,V>` (TDM-19).

Attributes:

- **`ATLAS_BUILTIN_TYPES`** –

  Atlas's built-in type names (TDM-19).
- **`ATLAS_PRIMITIVE_TYPES`** –

  Atlas's primitive type names (TDM-19).
- **`ATLAS_RELATIONSHIP_ATTRIBUTE_TYPES`** –

  The type names a relationship attribute may have: the primitives and `date` (TDM-19).
- **`ATLAS_TYPE_ASSET`** –
- **`ATLAS_TYPE_BIGDECIMAL`** –
- **`ATLAS_TYPE_BIGINTEGER`** –
- **`ATLAS_TYPE_BOOLEAN`** –
- **`ATLAS_TYPE_BYTE`** –
- **`ATLAS_TYPE_DATASET`** –
- **`ATLAS_TYPE_DATE`** –
- **`ATLAS_TYPE_DOUBLE`** –
- **`ATLAS_TYPE_FLOAT`** –
- **`ATLAS_TYPE_INFRASTRUCTURE`** –
- **`ATLAS_TYPE_INT`** –
- **`ATLAS_TYPE_LONG`** –
- **`ATLAS_TYPE_OBJECT_ID`** –
- **`ATLAS_TYPE_PROCESS`** –
- **`ATLAS_TYPE_SHORT`** –
- **`ATLAS_TYPE_STRING`** –
- **`ATTRDEF_OPTION_APPEND_ON_PARTIAL_UPDATE`** –
- **`ATTRDEF_OPTION_SOFT_REFERENCE`** –
- **`ATTR_MAX_STRING_LENGTH`** –
- **`ATTR_OPTION_APPLICABLE_ENTITY_TYPES`** –
- **`ATTR_VALID_PATTERN`** –
- **`CONSTRAINT_PARAM_ATTRIBUTE`** –
- **`CONSTRAINT_TYPE_INVERSE_REF`** –
- **`CONSTRAINT_TYPE_OWNED_REF`** –
- **`COUNT_NOT_SET`** –
- **`DEFAULT_SEARCH_WEIGHT`** –
- **`OPTION_DISPLAY_TEXT_ATTRIBUTE`** –
- **`SERVICE_TYPE_ATLAS_CORE`** –
- **`TYPEDEF_OPTION_SUPPORTS_PROFILE`** –
- **`TYPEDEF_OPTION_SUPPORTS_SCHEMA`** –

### ATLAS\_BUILTIN\_TYPES

```
ATLAS_BUILTIN_TYPES = (*ATLAS_PRIMITIVE_TYPES, ATLAS_TYPE_DATE, ATLAS_TYPE_OBJECT_ID)
```

Atlas's built-in type names (TDM-19).

### ATLAS\_PRIMITIVE\_TYPES

```
ATLAS_PRIMITIVE_TYPES = (
    ATLAS_TYPE_BOOLEAN,
    ATLAS_TYPE_BYTE,
    ATLAS_TYPE_SHORT,
    ATLAS_TYPE_INT,
    ATLAS_TYPE_LONG,
    ATLAS_TYPE_FLOAT,
    ATLAS_TYPE_DOUBLE,
    ATLAS_TYPE_BIGINTEGER,
    ATLAS_TYPE_BIGDECIMAL,
    ATLAS_TYPE_STRING,
)
```

Atlas's primitive type names (TDM-19).

### ATLAS\_RELATIONSHIP\_ATTRIBUTE\_TYPES

```
ATLAS_RELATIONSHIP_ATTRIBUTE_TYPES = (*ATLAS_PRIMITIVE_TYPES, ATLAS_TYPE_DATE)
```

The type names a relationship attribute may have: the primitives and `date` (TDM-19).

### ATLAS\_TYPE\_ASSET

```
ATLAS_TYPE_ASSET = 'Asset'
```

### ATLAS\_TYPE\_BIGDECIMAL

```
ATLAS_TYPE_BIGDECIMAL = 'bigdecimal'
```

### ATLAS\_TYPE\_BIGINTEGER

```
ATLAS_TYPE_BIGINTEGER = 'biginteger'
```

### ATLAS\_TYPE\_BOOLEAN

```
ATLAS_TYPE_BOOLEAN = 'boolean'
```

### ATLAS\_TYPE\_BYTE

```
ATLAS_TYPE_BYTE = 'byte'
```

### ATLAS\_TYPE\_DATASET

```
ATLAS_TYPE_DATASET = 'DataSet'
```

### ATLAS\_TYPE\_DATE

```
ATLAS_TYPE_DATE = 'date'
```

### ATLAS\_TYPE\_DOUBLE

```
ATLAS_TYPE_DOUBLE = 'double'
```

### ATLAS\_TYPE\_FLOAT

```
ATLAS_TYPE_FLOAT = 'float'
```

### ATLAS\_TYPE\_INFRASTRUCTURE

```
ATLAS_TYPE_INFRASTRUCTURE = 'Infrastructure'
```

### ATLAS\_TYPE\_INT

```
ATLAS_TYPE_INT = 'int'
```

### ATLAS\_TYPE\_LONG

```
ATLAS_TYPE_LONG = 'long'
```

### ATLAS\_TYPE\_OBJECT\_ID

```
ATLAS_TYPE_OBJECT_ID = 'objectid'
```

### ATLAS\_TYPE\_PROCESS

```
ATLAS_TYPE_PROCESS = 'Process'
```

### ATLAS\_TYPE\_SHORT

```
ATLAS_TYPE_SHORT = 'short'
```

### ATLAS\_TYPE\_STRING

```
ATLAS_TYPE_STRING = 'string'
```

### ATTRDEF\_OPTION\_APPEND\_ON\_PARTIAL\_UPDATE

```
ATTRDEF_OPTION_APPEND_ON_PARTIAL_UPDATE = 'isAppendOnPartialUpdate'
```

### ATTRDEF\_OPTION\_SOFT\_REFERENCE

```
ATTRDEF_OPTION_SOFT_REFERENCE = 'isSoftReference'
```

### ATTR\_MAX\_STRING\_LENGTH

```
ATTR_MAX_STRING_LENGTH = 'maxStrLength'
```

### ATTR\_OPTION\_APPLICABLE\_ENTITY\_TYPES

```
ATTR_OPTION_APPLICABLE_ENTITY_TYPES = 'applicableEntityTypes'
```

### ATTR\_VALID\_PATTERN

```
ATTR_VALID_PATTERN = 'validPattern'
```

### CONSTRAINT\_PARAM\_ATTRIBUTE

```
CONSTRAINT_PARAM_ATTRIBUTE = 'attribute'
```

### CONSTRAINT\_TYPE\_INVERSE\_REF

```
CONSTRAINT_TYPE_INVERSE_REF = 'inverseRef'
```

### CONSTRAINT\_TYPE\_OWNED\_REF

```
CONSTRAINT_TYPE_OWNED_REF = 'ownedRef'
```

### COUNT\_NOT\_SET

```
COUNT_NOT_SET = -1
```

### DEFAULT\_SEARCH\_WEIGHT

```
DEFAULT_SEARCH_WEIGHT = -1
```

### OPTION\_DISPLAY\_TEXT\_ATTRIBUTE

```
OPTION_DISPLAY_TEXT_ATTRIBUTE = 'displayTextAttribute'
```

### SERVICE\_TYPE\_ATLAS\_CORE

```
SERVICE_TYPE_ATLAS_CORE = 'atlas_core'
```

### TYPEDEF\_OPTION\_SUPPORTS\_PROFILE

```
TYPEDEF_OPTION_SUPPORTS_PROFILE = 'supportsProfile'
```

### TYPEDEF\_OPTION\_SUPPORTS\_SCHEMA

```
TYPEDEF_OPTION_SUPPORTS_SCHEMA = 'supportsSchema'
```

### AttributeDefs

```
AttributeDefs = list[AtlasAttributeDef]
```

`attributeDefs`: never null, one definition per name (TDM-06, TDM-07).

### AtlasAttributeDef

Bases: `AtlasModel`

An attribute of a struct, classification, entity, relationship or business metadata type (TDM-10).

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasConstraintDef": {
      "description": "A constraint on an attribute, such as ``ownedRef`` or ``inverseRef``.",
      "properties": {
        "type": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Type"
        },
        "params": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Params"
        }
      },
      "title": "AtlasConstraintDef",
      "type": "object"
    },
    "Cardinality": {
      "description": "How many values an attribute or relationship end holds.",
      "enum": [
        "SINGLE",
        "LIST",
        "SET"
      ],
      "title": "Cardinality",
      "type": "string"
    },
    "IndexType": {
      "description": "How an attribute is indexed.",
      "enum": [
        "DEFAULT",
        "STRING"
      ],
      "title": "IndexType",
      "type": "string"
    },
    "JavaBool": {
      "type": "boolean"
    },
    "JavaInt": {
      "type": "integer"
    }
  },
  "description": "An attribute of a struct, classification, entity, relationship or business metadata type (TDM-10).",
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
    "typeName": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Typename"
    },
    "isOptional": {
      "$ref": "#/$defs/JavaBool",
      "default": false
    },
    "cardinality": {
      "anyOf": [
        {
          "$ref": "#/$defs/Cardinality"
        },
        {
          "type": "null"
        }
      ],
      "default": "SINGLE"
    },
    "valuesMinCount": {
      "$ref": "#/$defs/JavaInt",
      "default": -1
    },
    "valuesMaxCount": {
      "$ref": "#/$defs/JavaInt",
      "default": -1
    },
    "isUnique": {
      "$ref": "#/$defs/JavaBool",
      "default": false
    },
    "isIndexable": {
      "$ref": "#/$defs/JavaBool",
      "default": false
    },
    "includeInNotification": {
      "$ref": "#/$defs/JavaBool",
      "default": false
    },
    "defaultValue": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Defaultvalue"
    },
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "searchWeight": {
      "$ref": "#/$defs/JavaInt",
      "default": -1
    },
    "indexType": {
      "anyOf": [
        {
          "$ref": "#/$defs/IndexType"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "constraints": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/AtlasConstraintDef"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Constraints"
    },
    "options": {
      "anyOf": [
        {
          "additionalProperties": {
            "type": "string"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Options"
    },
    "displayName": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Displayname"
    }
  },
  "title": "AtlasAttributeDef",
  "type": "object"
}
```

Fields:

- `name` (`str | None`)
- `type_name` (`str | None`)
- `is_optional` (`JavaBool`)
- `cardinality` (`Cardinality | None`)
- `values_min_count` (`JavaInt`)
- `values_max_count` (`JavaInt`)
- `is_unique` (`JavaBool`)
- `is_indexable` (`JavaBool`)
- `include_in_notification` (`JavaBool`)
- `default_value` (`str | None`)
- `description` (`str | None`)
- `search_weight` (`JavaInt`)
- `index_type` (`IndexType | None`)
- `constraints` (`list[AtlasConstraintDef] | None`)
- `options` (`dict[str, str] | None`)
- `display_name` (`str | None`)

#### cardinality

```
cardinality: Cardinality | None = Cardinality.SINGLE
```

#### constraints

```
constraints: list[AtlasConstraintDef] | None = None
```

#### default\_value

```
default_value: str | None = None
```

#### description

```
description: str | None = None
```

#### display\_name

```
display_name: str | None = None
```

#### include\_in\_notification

```
include_in_notification: JavaBool = False
```

#### index\_type

```
index_type: IndexType | None = None
```

#### is\_indexable

```
is_indexable: JavaBool = False
```

#### is\_optional

```
is_optional: JavaBool = False
```

#### is\_unique

```
is_unique: JavaBool = False
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### name

```
name: str | None = None
```

#### options

```
options: dict[str, str] | None = None
```

#### search\_weight

```
search_weight: JavaInt = DEFAULT_SEARCH_WEIGHT
```

#### type\_name

```
type_name: str | None = None
```

#### values\_max\_count

```
values_max_count: JavaInt = COUNT_NOT_SET
```

#### values\_min\_count

```
values_min_count: JavaInt = COUNT_NOT_SET
```

#### add\_constraint

```
add_constraint(constraint: AtlasConstraintDef) -> None
```

Append a constraint.

#### get\_option

```
get_option(name: str) -> str | None
```

The value of option `name`, or None.

#### is\_append\_on\_partial\_update

```
is_append_on_partial_update() -> bool
```

Whether the `isAppendOnPartialUpdate` option is true.

#### is\_soft\_referenced

```
is_soft_referenced() -> bool
```

Whether the `isSoftReference` option is true.

#### set\_option

```
set_option(name: str, value: str) -> None
```

Set option `name` to `value`.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasBaseTypeDef

Bases: `AtlasModel`

What every type definition has: identity, audit fields, name and options.

**Show JSON schema:**

```
{
  "$defs": {
    "Timestamp": {
      "format": "date-time",
      "type": "string"
    }
  },
  "description": "What every type definition has: identity, audit fields, name and options.",
  "properties": {
    "guid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Guid"
    },
    "createdBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Createdby"
    },
    "updatedBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Updatedby"
    },
    "createTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "updateTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "version": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Version"
    },
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
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "typeVersion": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Typeversion"
    },
    "serviceType": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Servicetype"
    },
    "options": {
      "anyOf": [
        {
          "additionalProperties": {
            "type": "string"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Options"
    }
  },
  "title": "AtlasBaseTypeDef",
  "type": "object"
}
```

Fields:

- `guid` (`str | None`)
- `created_by` (`str | None`)
- `updated_by` (`str | None`)
- `create_time` (`Timestamp | None`)
- `update_time` (`Timestamp | None`)
- `version` (`int | None`)
- `name` (`str | None`)
- `description` (`str | None`)
- `type_version` (`str | None`)
- `service_type` (`str | None`)
- `options` (`dict[str, str] | None`)

#### CATEGORY

```
CATEGORY: TypeCategory
```

#### category

```
category: TypeCategory
```

The kind of this type definition, fixed by its class; never read from input (TDM-04).

#### create\_time

```
create_time: Timestamp | None = None
```

#### created\_by

```
created_by: str | None = None
```

#### description

```
description: str | None = None
```

#### guid

```
guid: str | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### name

```
name: str | None = None
```

#### options

```
options: dict[str, str] | None = None
```

#### service\_type

```
service_type: str | None = None
```

#### type\_version

```
type_version: str | None = None
```

#### update\_time

```
update_time: Timestamp | None = None
```

#### updated\_by

```
updated_by: str | None = None
```

#### version

```
version: int | None = None
```

#### get\_option

```
get_option(name: str) -> str | None
```

The value of option `name`, or None.

#### set\_option

```
set_option(name: str, value: str) -> None
```

Set option `name` to `value`.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasBusinessMetadataDef

Bases: `AtlasStructDef`

A business metadata type: attributes that apply to the entity types its options name.

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasAttributeDef": {
      "description": "An attribute of a struct, classification, entity, relationship or business metadata type (TDM-10).",
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
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "isOptional": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "cardinality": {
          "anyOf": [
            {
              "$ref": "#/$defs/Cardinality"
            },
            {
              "type": "null"
            }
          ],
          "default": "SINGLE"
        },
        "valuesMinCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "valuesMaxCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "isUnique": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "isIndexable": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "includeInNotification": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "defaultValue": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Defaultvalue"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "searchWeight": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "indexType": {
          "anyOf": [
            {
              "$ref": "#/$defs/IndexType"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "constraints": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasConstraintDef"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Constraints"
        },
        "options": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Options"
        },
        "displayName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displayname"
        }
      },
      "title": "AtlasAttributeDef",
      "type": "object"
    },
    "AtlasConstraintDef": {
      "description": "A constraint on an attribute, such as ``ownedRef`` or ``inverseRef``.",
      "properties": {
        "type": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Type"
        },
        "params": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Params"
        }
      },
      "title": "AtlasConstraintDef",
      "type": "object"
    },
    "AttributeDefs": {
      "items": {
        "$ref": "#/$defs/AtlasAttributeDef"
      },
      "type": "array"
    },
    "Cardinality": {
      "description": "How many values an attribute or relationship end holds.",
      "enum": [
        "SINGLE",
        "LIST",
        "SET"
      ],
      "title": "Cardinality",
      "type": "string"
    },
    "IndexType": {
      "description": "How an attribute is indexed.",
      "enum": [
        "DEFAULT",
        "STRING"
      ],
      "title": "IndexType",
      "type": "string"
    },
    "JavaBool": {
      "type": "boolean"
    },
    "JavaInt": {
      "type": "integer"
    },
    "Timestamp": {
      "format": "date-time",
      "type": "string"
    }
  },
  "description": "A business metadata type: attributes that apply to the entity types its options name.",
  "properties": {
    "guid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Guid"
    },
    "createdBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Createdby"
    },
    "updatedBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Updatedby"
    },
    "createTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "updateTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "version": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Version"
    },
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
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "typeVersion": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Typeversion"
    },
    "serviceType": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Servicetype"
    },
    "options": {
      "anyOf": [
        {
          "additionalProperties": {
            "type": "string"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Options"
    },
    "attributeDefs": {
      "$ref": "#/$defs/AttributeDefs"
    }
  },
  "title": "AtlasBusinessMetadataDef",
  "type": "object"
}
```

Fields:

- `guid` (`str | None`)
- `created_by` (`str | None`)
- `updated_by` (`str | None`)
- `create_time` (`Timestamp | None`)
- `update_time` (`Timestamp | None`)
- `version` (`int | None`)
- `name` (`str | None`)
- `description` (`str | None`)
- `type_version` (`str | None`)
- `service_type` (`str | None`)
- `options` (`dict[str, str] | None`)
- `attribute_defs` (`AttributeDefs`)

#### CATEGORY

```
CATEGORY: TypeCategory = TypeCategory.BUSINESS_METADATA
```

#### attribute\_defs

```
attribute_defs: AttributeDefs
```

#### category

```
category: TypeCategory
```

The kind of this type definition, fixed by its class; never read from input (TDM-04).

#### create\_time

```
create_time: Timestamp | None = None
```

#### created\_by

```
created_by: str | None = None
```

#### description

```
description: str | None = None
```

#### guid

```
guid: str | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### name

```
name: str | None = None
```

#### options

```
options: dict[str, str] | None = None
```

#### service\_type

```
service_type: str | None = None
```

#### type\_version

```
type_version: str | None = None
```

#### update\_time

```
update_time: Timestamp | None = None
```

#### updated\_by

```
updated_by: str | None = None
```

#### version

```
version: int | None = None
```

#### add\_attribute

```
add_attribute(attribute: AtlasAttributeDef) -> None
```

Add `attribute` at the end, replacing one with the same name (TDM-16).

#### get\_attribute

```
get_attribute(name: str | None) -> AtlasAttributeDef | None
```

The attribute definition named `name`, compared without case, or None (TDM-16).

#### get\_option

```
get_option(name: str) -> str | None
```

The value of option `name`, or None.

#### has\_attribute

```
has_attribute(name: str | None) -> bool
```

Whether an attribute definition is named `name`, compared without case (TDM-16).

#### remove\_attribute

```
remove_attribute(name: str | None) -> None
```

Remove the attribute definitions named `name`, compared without case (TDM-16).

#### set\_option

```
set_option(name: str, value: str) -> None
```

Set option `name` to `value`.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasClassificationDef

Bases: `AtlasStructDef`

A classification type: attributes, super types and the entity types it may be applied to.

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasAttributeDef": {
      "description": "An attribute of a struct, classification, entity, relationship or business metadata type (TDM-10).",
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
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "isOptional": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "cardinality": {
          "anyOf": [
            {
              "$ref": "#/$defs/Cardinality"
            },
            {
              "type": "null"
            }
          ],
          "default": "SINGLE"
        },
        "valuesMinCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "valuesMaxCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "isUnique": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "isIndexable": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "includeInNotification": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "defaultValue": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Defaultvalue"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "searchWeight": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "indexType": {
          "anyOf": [
            {
              "$ref": "#/$defs/IndexType"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "constraints": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasConstraintDef"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Constraints"
        },
        "options": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Options"
        },
        "displayName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displayname"
        }
      },
      "title": "AtlasAttributeDef",
      "type": "object"
    },
    "AtlasConstraintDef": {
      "description": "A constraint on an attribute, such as ``ownedRef`` or ``inverseRef``.",
      "properties": {
        "type": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Type"
        },
        "params": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Params"
        }
      },
      "title": "AtlasConstraintDef",
      "type": "object"
    },
    "AttributeDefs": {
      "items": {
        "$ref": "#/$defs/AtlasAttributeDef"
      },
      "type": "array"
    },
    "Cardinality": {
      "description": "How many values an attribute or relationship end holds.",
      "enum": [
        "SINGLE",
        "LIST",
        "SET"
      ],
      "title": "Cardinality",
      "type": "string"
    },
    "IndexType": {
      "description": "How an attribute is indexed.",
      "enum": [
        "DEFAULT",
        "STRING"
      ],
      "title": "IndexType",
      "type": "string"
    },
    "JavaBool": {
      "type": "boolean"
    },
    "JavaInt": {
      "type": "integer"
    },
    "NameSet": {
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "OptionalNameSet": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "Timestamp": {
      "format": "date-time",
      "type": "string"
    }
  },
  "description": "A classification type: attributes, super types and the entity types it may be applied to.",
  "properties": {
    "guid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Guid"
    },
    "createdBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Createdby"
    },
    "updatedBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Updatedby"
    },
    "createTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "updateTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "version": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Version"
    },
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
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "typeVersion": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Typeversion"
    },
    "serviceType": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Servicetype"
    },
    "options": {
      "anyOf": [
        {
          "additionalProperties": {
            "type": "string"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Options"
    },
    "attributeDefs": {
      "$ref": "#/$defs/AttributeDefs"
    },
    "superTypes": {
      "$ref": "#/$defs/NameSet"
    },
    "entityTypes": {
      "$ref": "#/$defs/NameSet"
    },
    "subTypes": {
      "$ref": "#/$defs/OptionalNameSet",
      "default": null
    }
  },
  "title": "AtlasClassificationDef",
  "type": "object"
}
```

Fields:

- `guid` (`str | None`)
- `created_by` (`str | None`)
- `updated_by` (`str | None`)
- `create_time` (`Timestamp | None`)
- `update_time` (`Timestamp | None`)
- `version` (`int | None`)
- `name` (`str | None`)
- `description` (`str | None`)
- `type_version` (`str | None`)
- `service_type` (`str | None`)
- `options` (`dict[str, str] | None`)
- `attribute_defs` (`AttributeDefs`)
- `super_types` (`NameSet`)
- `entity_types` (`NameSet`)
- `sub_types` (`OptionalNameSet`)

#### CATEGORY

```
CATEGORY: TypeCategory = TypeCategory.CLASSIFICATION
```

#### attribute\_defs

```
attribute_defs: AttributeDefs
```

#### category

```
category: TypeCategory
```

The kind of this type definition, fixed by its class; never read from input (TDM-04).

#### create\_time

```
create_time: Timestamp | None = None
```

#### created\_by

```
created_by: str | None = None
```

#### description

```
description: str | None = None
```

#### entity\_types

```
entity_types: NameSet
```

#### guid

```
guid: str | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### name

```
name: str | None = None
```

#### options

```
options: dict[str, str] | None = None
```

#### service\_type

```
service_type: str | None = None
```

#### sub\_types

```
sub_types: OptionalNameSet = None
```

Derived from the super types of all classifications; ignored on create and update.

#### super\_types

```
super_types: NameSet
```

#### type\_version

```
type_version: str | None = None
```

#### update\_time

```
update_time: Timestamp | None = None
```

#### updated\_by

```
updated_by: str | None = None
```

#### version

```
version: int | None = None
```

#### add\_attribute

```
add_attribute(attribute: AtlasAttributeDef) -> None
```

Add `attribute` at the end, replacing one with the same name (TDM-16).

#### add\_entity\_type

```
add_entity_type(name: str) -> None
```

Allow the classification on entity type `name` (TDM-16).

#### add\_super\_type

```
add_super_type(name: str) -> None
```

Add the super type `name` (TDM-16).

#### get\_attribute

```
get_attribute(name: str | None) -> AtlasAttributeDef | None
```

The attribute definition named `name`, compared without case, or None (TDM-16).

#### get\_option

```
get_option(name: str) -> str | None
```

The value of option `name`, or None.

#### has\_attribute

```
has_attribute(name: str | None) -> bool
```

Whether an attribute definition is named `name`, compared without case (TDM-16).

#### has\_entity\_type

```
has_entity_type(name: str) -> bool
```

Whether the classification may be applied to entity type `name`, compared exactly (TDM-16).

#### has\_super\_type

```
has_super_type(name: str) -> bool
```

Whether `name` is a super type, compared exactly (TDM-16).

#### remove\_attribute

```
remove_attribute(name: str | None) -> None
```

Remove the attribute definitions named `name`, compared without case (TDM-16).

#### remove\_entity\_type

```
remove_entity_type(name: str) -> None
```

No longer allow the classification on entity type `name` (TDM-16).

#### remove\_super\_type

```
remove_super_type(name: str) -> None
```

Remove the super type `name` (TDM-16).

#### set\_option

```
set_option(name: str, value: str) -> None
```

Set option `name` to `value`.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasConstraintDef

Bases: `AtlasModel`

A constraint on an attribute, such as `ownedRef` or `inverseRef`.

**Show JSON schema:**

```
{
  "description": "A constraint on an attribute, such as ``ownedRef`` or ``inverseRef``.",
  "properties": {
    "type": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Type"
    },
    "params": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Params"
    }
  },
  "title": "AtlasConstraintDef",
  "type": "object"
}
```

Fields:

- `type` (`str | None`)
- `params` (`dict[str, Any] | None`)

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### params

```
params: dict[str, Any] | None = None
```

#### type

```
type: str | None = None
```

#### get\_param

```
get_param(name: str) -> Any
```

The value of parameter `name`, or None.

#### is\_constraint\_type

```
is_constraint_type(name: str | None) -> bool
```

Whether this constraint is of type `name`, compared without case.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasEntityDef

Bases: `AtlasStructDef`

An entity type.

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasAttributeDef": {
      "description": "An attribute of a struct, classification, entity, relationship or business metadata type (TDM-10).",
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
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "isOptional": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "cardinality": {
          "anyOf": [
            {
              "$ref": "#/$defs/Cardinality"
            },
            {
              "type": "null"
            }
          ],
          "default": "SINGLE"
        },
        "valuesMinCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "valuesMaxCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "isUnique": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "isIndexable": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "includeInNotification": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "defaultValue": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Defaultvalue"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "searchWeight": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "indexType": {
          "anyOf": [
            {
              "$ref": "#/$defs/IndexType"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "constraints": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasConstraintDef"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Constraints"
        },
        "options": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Options"
        },
        "displayName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displayname"
        }
      },
      "title": "AtlasAttributeDef",
      "type": "object"
    },
    "AtlasConstraintDef": {
      "description": "A constraint on an attribute, such as ``ownedRef`` or ``inverseRef``.",
      "properties": {
        "type": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Type"
        },
        "params": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Params"
        }
      },
      "title": "AtlasConstraintDef",
      "type": "object"
    },
    "AtlasRelationshipAttributeDef": {
      "description": "An entity attribute that a relationship type adds; read-only, derived from the relationship types.",
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
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "isOptional": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "cardinality": {
          "anyOf": [
            {
              "$ref": "#/$defs/Cardinality"
            },
            {
              "type": "null"
            }
          ],
          "default": "SINGLE"
        },
        "valuesMinCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "valuesMaxCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "isUnique": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "isIndexable": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "includeInNotification": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "defaultValue": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Defaultvalue"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "searchWeight": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "indexType": {
          "anyOf": [
            {
              "$ref": "#/$defs/IndexType"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "constraints": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasConstraintDef"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Constraints"
        },
        "options": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Options"
        },
        "displayName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displayname"
        },
        "relationshipTypeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Relationshiptypename"
        },
        "isLegacyAttribute": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        }
      },
      "title": "AtlasRelationshipAttributeDef",
      "type": "object"
    },
    "AttributeDefs": {
      "items": {
        "$ref": "#/$defs/AtlasAttributeDef"
      },
      "type": "array"
    },
    "Cardinality": {
      "description": "How many values an attribute or relationship end holds.",
      "enum": [
        "SINGLE",
        "LIST",
        "SET"
      ],
      "title": "Cardinality",
      "type": "string"
    },
    "IndexType": {
      "description": "How an attribute is indexed.",
      "enum": [
        "DEFAULT",
        "STRING"
      ],
      "title": "IndexType",
      "type": "string"
    },
    "JavaBool": {
      "type": "boolean"
    },
    "JavaInt": {
      "type": "integer"
    },
    "NameSet": {
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "OptionalNameSet": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "Timestamp": {
      "format": "date-time",
      "type": "string"
    }
  },
  "description": "An entity type.",
  "properties": {
    "guid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Guid"
    },
    "createdBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Createdby"
    },
    "updatedBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Updatedby"
    },
    "createTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "updateTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "version": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Version"
    },
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
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "typeVersion": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Typeversion"
    },
    "serviceType": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Servicetype"
    },
    "options": {
      "anyOf": [
        {
          "additionalProperties": {
            "type": "string"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Options"
    },
    "attributeDefs": {
      "$ref": "#/$defs/AttributeDefs"
    },
    "superTypes": {
      "$ref": "#/$defs/NameSet"
    },
    "subTypes": {
      "$ref": "#/$defs/OptionalNameSet",
      "default": null
    },
    "relationshipAttributeDefs": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/AtlasRelationshipAttributeDef"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Relationshipattributedefs"
    },
    "businessAttributeDefs": {
      "anyOf": [
        {
          "additionalProperties": {
            "items": {
              "$ref": "#/$defs/AtlasAttributeDef"
            },
            "type": "array"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Businessattributedefs"
    }
  },
  "title": "AtlasEntityDef",
  "type": "object"
}
```

Fields:

- `guid` (`str | None`)
- `created_by` (`str | None`)
- `updated_by` (`str | None`)
- `create_time` (`Timestamp | None`)
- `update_time` (`Timestamp | None`)
- `version` (`int | None`)
- `name` (`str | None`)
- `description` (`str | None`)
- `type_version` (`str | None`)
- `service_type` (`str | None`)
- `options` (`dict[str, str] | None`)
- `attribute_defs` (`AttributeDefs`)
- `super_types` (`NameSet`)
- `sub_types` (`OptionalNameSet`)
- `relationship_attribute_defs` (`list[AtlasRelationshipAttributeDef] | None`)
- `business_attribute_defs` (`dict[str, list[AtlasAttributeDef]] | None`)

#### CATEGORY

```
CATEGORY: TypeCategory = TypeCategory.ENTITY
```

#### attribute\_defs

```
attribute_defs: AttributeDefs
```

#### business\_attribute\_defs

```
business_attribute_defs: dict[str, list[AtlasAttributeDef]] | None = None
```

Derived from the business metadata types that apply to this one; ignored on create and update.

#### category

```
category: TypeCategory
```

The kind of this type definition, fixed by its class; never read from input (TDM-04).

#### create\_time

```
create_time: Timestamp | None = None
```

#### created\_by

```
created_by: str | None = None
```

#### description

```
description: str | None = None
```

#### guid

```
guid: str | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### name

```
name: str | None = None
```

#### options

```
options: dict[str, str] | None = None
```

#### relationship\_attribute\_defs

```
relationship_attribute_defs: list[AtlasRelationshipAttributeDef] | None = None
```

Derived from the relationship types that refer to this one; ignored on create and update.

#### service\_type

```
service_type: str | None = None
```

#### sub\_types

```
sub_types: OptionalNameSet = None
```

Derived from the super types of all entity types; ignored on create and update.

#### super\_types

```
super_types: NameSet
```

#### type\_version

```
type_version: str | None = None
```

#### update\_time

```
update_time: Timestamp | None = None
```

#### updated\_by

```
updated_by: str | None = None
```

#### version

```
version: int | None = None
```

#### add\_attribute

```
add_attribute(attribute: AtlasAttributeDef) -> None
```

Add `attribute` at the end, replacing one with the same name (TDM-16).

#### add\_super\_type

```
add_super_type(name: str) -> None
```

Add the super type `name` (TDM-16).

#### get\_attribute

```
get_attribute(name: str | None) -> AtlasAttributeDef | None
```

The attribute definition named `name`, compared without case, or None (TDM-16).

#### get\_option

```
get_option(name: str) -> str | None
```

The value of option `name`, or None.

#### has\_attribute

```
has_attribute(name: str | None) -> bool
```

Whether an attribute definition is named `name`, compared without case (TDM-16).

#### has\_super\_type

```
has_super_type(name: str) -> bool
```

Whether `name` is a super type, compared exactly (TDM-16).

#### remove\_attribute

```
remove_attribute(name: str | None) -> None
```

Remove the attribute definitions named `name`, compared without case (TDM-16).

#### remove\_super\_type

```
remove_super_type(name: str) -> None
```

Remove the super type `name` (TDM-16).

#### set\_option

```
set_option(name: str, value: str) -> None
```

Set option `name` to `value`.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasEnumDef

Bases: `AtlasBaseTypeDef`

An enum type.

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasEnumElementDef": {
      "description": "One value of an enum type.",
      "properties": {
        "value": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Value"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "ordinal": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Ordinal"
        }
      },
      "title": "AtlasEnumElementDef",
      "type": "object"
    },
    "Timestamp": {
      "format": "date-time",
      "type": "string"
    }
  },
  "description": "An enum type.",
  "properties": {
    "guid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Guid"
    },
    "createdBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Createdby"
    },
    "updatedBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Updatedby"
    },
    "createTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "updateTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "version": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Version"
    },
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
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "typeVersion": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Typeversion"
    },
    "serviceType": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Servicetype"
    },
    "options": {
      "anyOf": [
        {
          "additionalProperties": {
            "type": "string"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Options"
    },
    "elementDefs": {
      "items": {
        "$ref": "#/$defs/AtlasEnumElementDef"
      },
      "title": "Elementdefs",
      "type": "array"
    },
    "defaultValue": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Defaultvalue"
    }
  },
  "title": "AtlasEnumDef",
  "type": "object"
}
```

Fields:

- `guid` (`str | None`)
- `created_by` (`str | None`)
- `updated_by` (`str | None`)
- `create_time` (`Timestamp | None`)
- `update_time` (`Timestamp | None`)
- `version` (`int | None`)
- `name` (`str | None`)
- `description` (`str | None`)
- `type_version` (`str | None`)
- `service_type` (`str | None`)
- `options` (`dict[str, str] | None`)
- `element_defs` (`list[AtlasEnumElementDef]`)
- `default_value` (`str | None`)

#### CATEGORY

```
CATEGORY: TypeCategory = TypeCategory.ENUM
```

#### category

```
category: TypeCategory
```

The kind of this type definition, fixed by its class; never read from input (TDM-04).

#### create\_time

```
create_time: Timestamp | None = None
```

#### created\_by

```
created_by: str | None = None
```

#### default\_value

```
default_value: str | None = None
```

#### description

```
description: str | None = None
```

#### element\_defs

```
element_defs: list[AtlasEnumElementDef]
```

#### guid

```
guid: str | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### name

```
name: str | None = None
```

#### options

```
options: dict[str, str] | None = None
```

#### service\_type

```
service_type: str | None = None
```

#### type\_version

```
type_version: str | None = None
```

#### update\_time

```
update_time: Timestamp | None = None
```

#### updated\_by

```
updated_by: str | None = None
```

#### version

```
version: int | None = None
```

#### add\_element

```
add_element(element: AtlasEnumElementDef) -> None
```

Add `element` at the end, replacing an element with the same value (TDM-16).

#### get\_element

```
get_element(value: str | None) -> AtlasEnumElementDef | None
```

The element with `value`, compared without case, or None (TDM-16).

#### get\_option

```
get_option(name: str) -> str | None
```

The value of option `name`, or None.

#### has\_element

```
has_element(value: str | None) -> bool
```

Whether an element has `value`, compared without case (TDM-16).

#### remove\_element

```
remove_element(value: str | None) -> None
```

Remove the elements with `value`, compared without case (TDM-16).

#### set\_option

```
set_option(name: str, value: str) -> None
```

Set option `name` to `value`.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasEnumElementDef

Bases: `AtlasModel`

One value of an enum type.

**Show JSON schema:**

```
{
  "description": "One value of an enum type.",
  "properties": {
    "value": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Value"
    },
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "ordinal": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Ordinal"
    }
  },
  "title": "AtlasEnumElementDef",
  "type": "object"
}
```

Fields:

- `value` (`str | None`)
- `description` (`str | None`)
- `ordinal` (`int | None`)

#### description

```
description: str | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### ordinal

```
ordinal: int | None = None
```

#### value

```
value: str | None = None
```

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasRelationshipAttributeDef

Bases: `AtlasAttributeDef`

An entity attribute that a relationship type adds; read-only, derived from the relationship types.

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasConstraintDef": {
      "description": "A constraint on an attribute, such as ``ownedRef`` or ``inverseRef``.",
      "properties": {
        "type": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Type"
        },
        "params": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Params"
        }
      },
      "title": "AtlasConstraintDef",
      "type": "object"
    },
    "Cardinality": {
      "description": "How many values an attribute or relationship end holds.",
      "enum": [
        "SINGLE",
        "LIST",
        "SET"
      ],
      "title": "Cardinality",
      "type": "string"
    },
    "IndexType": {
      "description": "How an attribute is indexed.",
      "enum": [
        "DEFAULT",
        "STRING"
      ],
      "title": "IndexType",
      "type": "string"
    },
    "JavaBool": {
      "type": "boolean"
    },
    "JavaInt": {
      "type": "integer"
    }
  },
  "description": "An entity attribute that a relationship type adds; read-only, derived from the relationship types.",
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
    "typeName": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Typename"
    },
    "isOptional": {
      "$ref": "#/$defs/JavaBool",
      "default": false
    },
    "cardinality": {
      "anyOf": [
        {
          "$ref": "#/$defs/Cardinality"
        },
        {
          "type": "null"
        }
      ],
      "default": "SINGLE"
    },
    "valuesMinCount": {
      "$ref": "#/$defs/JavaInt",
      "default": -1
    },
    "valuesMaxCount": {
      "$ref": "#/$defs/JavaInt",
      "default": -1
    },
    "isUnique": {
      "$ref": "#/$defs/JavaBool",
      "default": false
    },
    "isIndexable": {
      "$ref": "#/$defs/JavaBool",
      "default": false
    },
    "includeInNotification": {
      "$ref": "#/$defs/JavaBool",
      "default": false
    },
    "defaultValue": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Defaultvalue"
    },
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "searchWeight": {
      "$ref": "#/$defs/JavaInt",
      "default": -1
    },
    "indexType": {
      "anyOf": [
        {
          "$ref": "#/$defs/IndexType"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "constraints": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/AtlasConstraintDef"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Constraints"
    },
    "options": {
      "anyOf": [
        {
          "additionalProperties": {
            "type": "string"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Options"
    },
    "displayName": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Displayname"
    },
    "relationshipTypeName": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Relationshiptypename"
    },
    "isLegacyAttribute": {
      "$ref": "#/$defs/JavaBool",
      "default": false
    }
  },
  "title": "AtlasRelationshipAttributeDef",
  "type": "object"
}
```

Fields:

- `name` (`str | None`)
- `type_name` (`str | None`)
- `is_optional` (`JavaBool`)
- `cardinality` (`Cardinality | None`)
- `values_min_count` (`JavaInt`)
- `values_max_count` (`JavaInt`)
- `is_unique` (`JavaBool`)
- `is_indexable` (`JavaBool`)
- `include_in_notification` (`JavaBool`)
- `default_value` (`str | None`)
- `description` (`str | None`)
- `search_weight` (`JavaInt`)
- `index_type` (`IndexType | None`)
- `constraints` (`list[AtlasConstraintDef] | None`)
- `options` (`dict[str, str] | None`)
- `display_name` (`str | None`)
- `relationship_type_name` (`str | None`)
- `is_legacy_attribute` (`JavaBool`)

#### cardinality

```
cardinality: Cardinality | None = Cardinality.SINGLE
```

#### constraints

```
constraints: list[AtlasConstraintDef] | None = None
```

#### default\_value

```
default_value: str | None = None
```

#### description

```
description: str | None = None
```

#### display\_name

```
display_name: str | None = None
```

#### include\_in\_notification

```
include_in_notification: JavaBool = False
```

#### index\_type

```
index_type: IndexType | None = None
```

#### is\_indexable

```
is_indexable: JavaBool = False
```

#### is\_legacy\_attribute

```
is_legacy_attribute: JavaBool = False
```

#### is\_optional

```
is_optional: JavaBool = False
```

#### is\_unique

```
is_unique: JavaBool = False
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### name

```
name: str | None = None
```

#### options

```
options: dict[str, str] | None = None
```

#### relationship\_type\_name

```
relationship_type_name: str | None = None
```

#### search\_weight

```
search_weight: JavaInt = DEFAULT_SEARCH_WEIGHT
```

#### type\_name

```
type_name: str | None = None
```

#### values\_max\_count

```
values_max_count: JavaInt = COUNT_NOT_SET
```

#### values\_min\_count

```
values_min_count: JavaInt = COUNT_NOT_SET
```

#### add\_constraint

```
add_constraint(constraint: AtlasConstraintDef) -> None
```

Append a constraint.

#### get\_option

```
get_option(name: str) -> str | None
```

The value of option `name`, or None.

#### is\_append\_on\_partial\_update

```
is_append_on_partial_update() -> bool
```

Whether the `isAppendOnPartialUpdate` option is true.

#### is\_soft\_referenced

```
is_soft_referenced() -> bool
```

Whether the `isSoftReference` option is true.

#### set\_option

```
set_option(name: str, value: str) -> None
```

Set option `name` to `value`.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasRelationshipDef

Bases: `AtlasStructDef`

A relationship type between two entity types (TDM-12).

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasAttributeDef": {
      "description": "An attribute of a struct, classification, entity, relationship or business metadata type (TDM-10).",
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
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "isOptional": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "cardinality": {
          "anyOf": [
            {
              "$ref": "#/$defs/Cardinality"
            },
            {
              "type": "null"
            }
          ],
          "default": "SINGLE"
        },
        "valuesMinCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "valuesMaxCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "isUnique": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "isIndexable": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "includeInNotification": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "defaultValue": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Defaultvalue"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "searchWeight": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "indexType": {
          "anyOf": [
            {
              "$ref": "#/$defs/IndexType"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "constraints": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasConstraintDef"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Constraints"
        },
        "options": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Options"
        },
        "displayName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displayname"
        }
      },
      "title": "AtlasAttributeDef",
      "type": "object"
    },
    "AtlasConstraintDef": {
      "description": "A constraint on an attribute, such as ``ownedRef`` or ``inverseRef``.",
      "properties": {
        "type": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Type"
        },
        "params": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Params"
        }
      },
      "title": "AtlasConstraintDef",
      "type": "object"
    },
    "AtlasRelationshipEndDef": {
      "description": "One end of a relationship type: the entity type there and the attribute it gets (TDM-12).",
      "properties": {
        "type": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Type"
        },
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
        "isContainer": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "cardinality": {
          "anyOf": [
            {
              "$ref": "#/$defs/Cardinality"
            },
            {
              "type": "null"
            }
          ],
          "default": "SINGLE"
        },
        "isLegacyAttribute": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        }
      },
      "title": "AtlasRelationshipEndDef",
      "type": "object"
    },
    "AttributeDefs": {
      "items": {
        "$ref": "#/$defs/AtlasAttributeDef"
      },
      "type": "array"
    },
    "Cardinality": {
      "description": "How many values an attribute or relationship end holds.",
      "enum": [
        "SINGLE",
        "LIST",
        "SET"
      ],
      "title": "Cardinality",
      "type": "string"
    },
    "IndexType": {
      "description": "How an attribute is indexed.",
      "enum": [
        "DEFAULT",
        "STRING"
      ],
      "title": "IndexType",
      "type": "string"
    },
    "JavaBool": {
      "type": "boolean"
    },
    "JavaInt": {
      "type": "integer"
    },
    "PropagateTags": {
      "description": "The direction in which classifications propagate over a relationship.",
      "enum": [
        "NONE",
        "ONE_TO_TWO",
        "TWO_TO_ONE",
        "BOTH"
      ],
      "title": "PropagateTags",
      "type": "string"
    },
    "RelationshipCategory": {
      "description": "How the two ends of a relationship depend on each other.",
      "enum": [
        "ASSOCIATION",
        "AGGREGATION",
        "COMPOSITION"
      ],
      "title": "RelationshipCategory",
      "type": "string"
    },
    "Timestamp": {
      "format": "date-time",
      "type": "string"
    }
  },
  "description": "A relationship type between two entity types (TDM-12).",
  "properties": {
    "guid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Guid"
    },
    "createdBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Createdby"
    },
    "updatedBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Updatedby"
    },
    "createTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "updateTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "version": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Version"
    },
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
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "typeVersion": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Typeversion"
    },
    "serviceType": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Servicetype"
    },
    "options": {
      "anyOf": [
        {
          "additionalProperties": {
            "type": "string"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Options"
    },
    "attributeDefs": {
      "$ref": "#/$defs/AttributeDefs"
    },
    "relationshipCategory": {
      "anyOf": [
        {
          "$ref": "#/$defs/RelationshipCategory"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "relationshipLabel": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Relationshiplabel"
    },
    "propagateTags": {
      "anyOf": [
        {
          "$ref": "#/$defs/PropagateTags"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "endDef1": {
      "anyOf": [
        {
          "$ref": "#/$defs/AtlasRelationshipEndDef"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "endDef2": {
      "anyOf": [
        {
          "$ref": "#/$defs/AtlasRelationshipEndDef"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "title": "AtlasRelationshipDef",
  "type": "object"
}
```

Fields:

- `guid` (`str | None`)
- `created_by` (`str | None`)
- `updated_by` (`str | None`)
- `create_time` (`Timestamp | None`)
- `update_time` (`Timestamp | None`)
- `version` (`int | None`)
- `name` (`str | None`)
- `description` (`str | None`)
- `type_version` (`str | None`)
- `service_type` (`str | None`)
- `options` (`dict[str, str] | None`)
- `attribute_defs` (`AttributeDefs`)
- `relationship_category` (`RelationshipCategory | None`)
- `relationship_label` (`str | None`)
- `propagate_tags` (`PropagateTags | None`)
- `end_def1` (`AtlasRelationshipEndDef | None`)
- `end_def2` (`AtlasRelationshipEndDef | None`)

#### CATEGORY

```
CATEGORY: TypeCategory = TypeCategory.RELATIONSHIP
```

#### attribute\_defs

```
attribute_defs: AttributeDefs
```

#### category

```
category: TypeCategory
```

The kind of this type definition, fixed by its class; never read from input (TDM-04).

#### create\_time

```
create_time: Timestamp | None = None
```

#### created\_by

```
created_by: str | None = None
```

#### description

```
description: str | None = None
```

#### end\_def1

```
end_def1: AtlasRelationshipEndDef | None = None
```

#### end\_def2

```
end_def2: AtlasRelationshipEndDef | None = None
```

#### guid

```
guid: str | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### name

```
name: str | None = None
```

#### options

```
options: dict[str, str] | None = None
```

#### propagate\_tags

```
propagate_tags: PropagateTags | None = None
```

#### relationship\_category

```
relationship_category: RelationshipCategory | None = None
```

#### relationship\_label

```
relationship_label: str | None = None
```

#### service\_type

```
service_type: str | None = None
```

#### type\_version

```
type_version: str | None = None
```

#### update\_time

```
update_time: Timestamp | None = None
```

#### updated\_by

```
updated_by: str | None = None
```

#### version

```
version: int | None = None
```

#### add\_attribute

```
add_attribute(attribute: AtlasAttributeDef) -> None
```

Add `attribute` at the end, replacing one with the same name (TDM-16).

#### get\_attribute

```
get_attribute(name: str | None) -> AtlasAttributeDef | None
```

The attribute definition named `name`, compared without case, or None (TDM-16).

#### get\_option

```
get_option(name: str) -> str | None
```

The value of option `name`, or None.

#### has\_attribute

```
has_attribute(name: str | None) -> bool
```

Whether an attribute definition is named `name`, compared without case (TDM-16).

#### remove\_attribute

```
remove_attribute(name: str | None) -> None
```

Remove the attribute definitions named `name`, compared without case (TDM-16).

#### set\_option

```
set_option(name: str, value: str) -> None
```

Set option `name` to `value`.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasRelationshipEndDef

Bases: `AtlasModel`

One end of a relationship type: the entity type there and the attribute it gets (TDM-12).

**Show JSON schema:**

```
{
  "$defs": {
    "Cardinality": {
      "description": "How many values an attribute or relationship end holds.",
      "enum": [
        "SINGLE",
        "LIST",
        "SET"
      ],
      "title": "Cardinality",
      "type": "string"
    },
    "JavaBool": {
      "type": "boolean"
    }
  },
  "description": "One end of a relationship type: the entity type there and the attribute it gets (TDM-12).",
  "properties": {
    "type": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Type"
    },
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
    "isContainer": {
      "$ref": "#/$defs/JavaBool",
      "default": false
    },
    "cardinality": {
      "anyOf": [
        {
          "$ref": "#/$defs/Cardinality"
        },
        {
          "type": "null"
        }
      ],
      "default": "SINGLE"
    },
    "isLegacyAttribute": {
      "$ref": "#/$defs/JavaBool",
      "default": false
    },
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    }
  },
  "title": "AtlasRelationshipEndDef",
  "type": "object"
}
```

Fields:

- `type` (`str | None`)
- `name` (`str | None`)
- `is_container` (`JavaBool`)
- `cardinality` (`Cardinality | None`)
- `is_legacy_attribute` (`JavaBool`)
- `description` (`str | None`)

#### cardinality

```
cardinality: Cardinality | None = Cardinality.SINGLE
```

#### description

```
description: str | None = None
```

#### is\_container

```
is_container: JavaBool = False
```

#### is\_legacy\_attribute

```
is_legacy_attribute: JavaBool = False
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### name

```
name: str | None = None
```

#### type

```
type: str | None = None
```

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasStructDef

Bases: `AtlasBaseTypeDef`

A struct type, and the base of the types that have attributes.

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasAttributeDef": {
      "description": "An attribute of a struct, classification, entity, relationship or business metadata type (TDM-10).",
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
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "isOptional": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "cardinality": {
          "anyOf": [
            {
              "$ref": "#/$defs/Cardinality"
            },
            {
              "type": "null"
            }
          ],
          "default": "SINGLE"
        },
        "valuesMinCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "valuesMaxCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "isUnique": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "isIndexable": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "includeInNotification": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "defaultValue": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Defaultvalue"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "searchWeight": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "indexType": {
          "anyOf": [
            {
              "$ref": "#/$defs/IndexType"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "constraints": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasConstraintDef"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Constraints"
        },
        "options": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Options"
        },
        "displayName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displayname"
        }
      },
      "title": "AtlasAttributeDef",
      "type": "object"
    },
    "AtlasConstraintDef": {
      "description": "A constraint on an attribute, such as ``ownedRef`` or ``inverseRef``.",
      "properties": {
        "type": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Type"
        },
        "params": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Params"
        }
      },
      "title": "AtlasConstraintDef",
      "type": "object"
    },
    "AttributeDefs": {
      "items": {
        "$ref": "#/$defs/AtlasAttributeDef"
      },
      "type": "array"
    },
    "Cardinality": {
      "description": "How many values an attribute or relationship end holds.",
      "enum": [
        "SINGLE",
        "LIST",
        "SET"
      ],
      "title": "Cardinality",
      "type": "string"
    },
    "IndexType": {
      "description": "How an attribute is indexed.",
      "enum": [
        "DEFAULT",
        "STRING"
      ],
      "title": "IndexType",
      "type": "string"
    },
    "JavaBool": {
      "type": "boolean"
    },
    "JavaInt": {
      "type": "integer"
    },
    "Timestamp": {
      "format": "date-time",
      "type": "string"
    }
  },
  "description": "A struct type, and the base of the types that have attributes.",
  "properties": {
    "guid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Guid"
    },
    "createdBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Createdby"
    },
    "updatedBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Updatedby"
    },
    "createTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "updateTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "version": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Version"
    },
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
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "typeVersion": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Typeversion"
    },
    "serviceType": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Servicetype"
    },
    "options": {
      "anyOf": [
        {
          "additionalProperties": {
            "type": "string"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Options"
    },
    "attributeDefs": {
      "$ref": "#/$defs/AttributeDefs"
    }
  },
  "title": "AtlasStructDef",
  "type": "object"
}
```

Fields:

- `guid` (`str | None`)
- `created_by` (`str | None`)
- `updated_by` (`str | None`)
- `create_time` (`Timestamp | None`)
- `update_time` (`Timestamp | None`)
- `version` (`int | None`)
- `name` (`str | None`)
- `description` (`str | None`)
- `type_version` (`str | None`)
- `service_type` (`str | None`)
- `options` (`dict[str, str] | None`)
- `attribute_defs` (`AttributeDefs`)

#### CATEGORY

```
CATEGORY: TypeCategory = TypeCategory.STRUCT
```

#### attribute\_defs

```
attribute_defs: AttributeDefs
```

#### category

```
category: TypeCategory
```

The kind of this type definition, fixed by its class; never read from input (TDM-04).

#### create\_time

```
create_time: Timestamp | None = None
```

#### created\_by

```
created_by: str | None = None
```

#### description

```
description: str | None = None
```

#### guid

```
guid: str | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### name

```
name: str | None = None
```

#### options

```
options: dict[str, str] | None = None
```

#### service\_type

```
service_type: str | None = None
```

#### type\_version

```
type_version: str | None = None
```

#### update\_time

```
update_time: Timestamp | None = None
```

#### updated\_by

```
updated_by: str | None = None
```

#### version

```
version: int | None = None
```

#### add\_attribute

```
add_attribute(attribute: AtlasAttributeDef) -> None
```

Add `attribute` at the end, replacing one with the same name (TDM-16).

#### get\_attribute

```
get_attribute(name: str | None) -> AtlasAttributeDef | None
```

The attribute definition named `name`, compared without case, or None (TDM-16).

#### get\_option

```
get_option(name: str) -> str | None
```

The value of option `name`, or None.

#### has\_attribute

```
has_attribute(name: str | None) -> bool
```

Whether an attribute definition is named `name`, compared without case (TDM-16).

#### remove\_attribute

```
remove_attribute(name: str | None) -> None
```

Remove the attribute definitions named `name`, compared without case (TDM-16).

#### set\_option

```
set_option(name: str, value: str) -> None
```

Set option `name` to `value`.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasTypeDefHeader

Bases: `AtlasModel`

The identity of a type definition, as `/v2/types/typedefs/headers` lists it.

**Show JSON schema:**

```
{
  "$defs": {
    "TypeCategory": {
      "description": "The kinds of Atlas types (``org.apache.atlas.model.TypeCategory``).",
      "enum": [
        "PRIMITIVE",
        "OBJECT_ID_TYPE",
        "ENUM",
        "STRUCT",
        "CLASSIFICATION",
        "ENTITY",
        "ARRAY",
        "MAP",
        "RELATIONSHIP",
        "BUSINESS_METADATA"
      ],
      "title": "TypeCategory",
      "type": "string"
    }
  },
  "description": "The identity of a type definition, as ``/v2/types/typedefs/headers`` lists it.",
  "properties": {
    "guid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Guid"
    },
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
    "serviceType": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Servicetype"
    },
    "category": {
      "anyOf": [
        {
          "$ref": "#/$defs/TypeCategory"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "title": "AtlasTypeDefHeader",
  "type": "object"
}
```

Fields:

- `guid` (`str | None`)
- `name` (`str | None`)
- `service_type` (`str | None`)
- `category` (`TypeCategory | None`)

#### category

```
category: TypeCategory | None = None
```

#### guid

```
guid: str | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### name

```
name: str | None = None
```

#### service\_type

```
service_type: str | None = None
```

#### of

```
of(typedef: AtlasBaseTypeDef) -> Self
```

The header of `typedef` (TDM-18).

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### AtlasTypesDef

Bases: `AtlasModel`

Type definitions of every kind: the body of `/v2/types/typedefs` (TDM-13).

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasAttributeDef": {
      "description": "An attribute of a struct, classification, entity, relationship or business metadata type (TDM-10).",
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
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "isOptional": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "cardinality": {
          "anyOf": [
            {
              "$ref": "#/$defs/Cardinality"
            },
            {
              "type": "null"
            }
          ],
          "default": "SINGLE"
        },
        "valuesMinCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "valuesMaxCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "isUnique": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "isIndexable": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "includeInNotification": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "defaultValue": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Defaultvalue"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "searchWeight": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "indexType": {
          "anyOf": [
            {
              "$ref": "#/$defs/IndexType"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "constraints": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasConstraintDef"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Constraints"
        },
        "options": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Options"
        },
        "displayName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displayname"
        }
      },
      "title": "AtlasAttributeDef",
      "type": "object"
    },
    "AtlasBusinessMetadataDef": {
      "description": "A business metadata type: attributes that apply to the entity types its options name.",
      "properties": {
        "guid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Guid"
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "updatedBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Updatedby"
        },
        "createTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "updateTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "version": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Version"
        },
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
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "typeVersion": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typeversion"
        },
        "serviceType": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Servicetype"
        },
        "options": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Options"
        },
        "attributeDefs": {
          "$ref": "#/$defs/AttributeDefs"
        }
      },
      "title": "AtlasBusinessMetadataDef",
      "type": "object"
    },
    "AtlasClassificationDef": {
      "description": "A classification type: attributes, super types and the entity types it may be applied to.",
      "properties": {
        "guid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Guid"
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "updatedBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Updatedby"
        },
        "createTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "updateTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "version": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Version"
        },
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
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "typeVersion": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typeversion"
        },
        "serviceType": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Servicetype"
        },
        "options": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Options"
        },
        "attributeDefs": {
          "$ref": "#/$defs/AttributeDefs"
        },
        "superTypes": {
          "$ref": "#/$defs/NameSet"
        },
        "entityTypes": {
          "$ref": "#/$defs/NameSet"
        },
        "subTypes": {
          "$ref": "#/$defs/OptionalNameSet",
          "default": null
        }
      },
      "title": "AtlasClassificationDef",
      "type": "object"
    },
    "AtlasConstraintDef": {
      "description": "A constraint on an attribute, such as ``ownedRef`` or ``inverseRef``.",
      "properties": {
        "type": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Type"
        },
        "params": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Params"
        }
      },
      "title": "AtlasConstraintDef",
      "type": "object"
    },
    "AtlasEntityDef": {
      "description": "An entity type.",
      "properties": {
        "guid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Guid"
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "updatedBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Updatedby"
        },
        "createTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "updateTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "version": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Version"
        },
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
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "typeVersion": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typeversion"
        },
        "serviceType": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Servicetype"
        },
        "options": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Options"
        },
        "attributeDefs": {
          "$ref": "#/$defs/AttributeDefs"
        },
        "superTypes": {
          "$ref": "#/$defs/NameSet"
        },
        "subTypes": {
          "$ref": "#/$defs/OptionalNameSet",
          "default": null
        },
        "relationshipAttributeDefs": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasRelationshipAttributeDef"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Relationshipattributedefs"
        },
        "businessAttributeDefs": {
          "anyOf": [
            {
              "additionalProperties": {
                "items": {
                  "$ref": "#/$defs/AtlasAttributeDef"
                },
                "type": "array"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Businessattributedefs"
        }
      },
      "title": "AtlasEntityDef",
      "type": "object"
    },
    "AtlasEnumDef": {
      "description": "An enum type.",
      "properties": {
        "guid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Guid"
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "updatedBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Updatedby"
        },
        "createTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "updateTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "version": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Version"
        },
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
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "typeVersion": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typeversion"
        },
        "serviceType": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Servicetype"
        },
        "options": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Options"
        },
        "elementDefs": {
          "items": {
            "$ref": "#/$defs/AtlasEnumElementDef"
          },
          "title": "Elementdefs",
          "type": "array"
        },
        "defaultValue": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Defaultvalue"
        }
      },
      "title": "AtlasEnumDef",
      "type": "object"
    },
    "AtlasEnumElementDef": {
      "description": "One value of an enum type.",
      "properties": {
        "value": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Value"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "ordinal": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Ordinal"
        }
      },
      "title": "AtlasEnumElementDef",
      "type": "object"
    },
    "AtlasRelationshipAttributeDef": {
      "description": "An entity attribute that a relationship type adds; read-only, derived from the relationship types.",
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
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "isOptional": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "cardinality": {
          "anyOf": [
            {
              "$ref": "#/$defs/Cardinality"
            },
            {
              "type": "null"
            }
          ],
          "default": "SINGLE"
        },
        "valuesMinCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "valuesMaxCount": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "isUnique": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "isIndexable": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "includeInNotification": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "defaultValue": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Defaultvalue"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "searchWeight": {
          "$ref": "#/$defs/JavaInt",
          "default": -1
        },
        "indexType": {
          "anyOf": [
            {
              "$ref": "#/$defs/IndexType"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "constraints": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasConstraintDef"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Constraints"
        },
        "options": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Options"
        },
        "displayName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displayname"
        },
        "relationshipTypeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Relationshiptypename"
        },
        "isLegacyAttribute": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        }
      },
      "title": "AtlasRelationshipAttributeDef",
      "type": "object"
    },
    "AtlasRelationshipDef": {
      "description": "A relationship type between two entity types (TDM-12).",
      "properties": {
        "guid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Guid"
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "updatedBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Updatedby"
        },
        "createTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "updateTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "version": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Version"
        },
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
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "typeVersion": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typeversion"
        },
        "serviceType": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Servicetype"
        },
        "options": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Options"
        },
        "attributeDefs": {
          "$ref": "#/$defs/AttributeDefs"
        },
        "relationshipCategory": {
          "anyOf": [
            {
              "$ref": "#/$defs/RelationshipCategory"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "relationshipLabel": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Relationshiplabel"
        },
        "propagateTags": {
          "anyOf": [
            {
              "$ref": "#/$defs/PropagateTags"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "endDef1": {
          "anyOf": [
            {
              "$ref": "#/$defs/AtlasRelationshipEndDef"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "endDef2": {
          "anyOf": [
            {
              "$ref": "#/$defs/AtlasRelationshipEndDef"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "title": "AtlasRelationshipDef",
      "type": "object"
    },
    "AtlasRelationshipEndDef": {
      "description": "One end of a relationship type: the entity type there and the attribute it gets (TDM-12).",
      "properties": {
        "type": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Type"
        },
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
        "isContainer": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "cardinality": {
          "anyOf": [
            {
              "$ref": "#/$defs/Cardinality"
            },
            {
              "type": "null"
            }
          ],
          "default": "SINGLE"
        },
        "isLegacyAttribute": {
          "$ref": "#/$defs/JavaBool",
          "default": false
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        }
      },
      "title": "AtlasRelationshipEndDef",
      "type": "object"
    },
    "AtlasStructDef": {
      "description": "A struct type, and the base of the types that have attributes.",
      "properties": {
        "guid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Guid"
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "updatedBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Updatedby"
        },
        "createTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "updateTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "version": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Version"
        },
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
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "typeVersion": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typeversion"
        },
        "serviceType": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Servicetype"
        },
        "options": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Options"
        },
        "attributeDefs": {
          "$ref": "#/$defs/AttributeDefs"
        }
      },
      "title": "AtlasStructDef",
      "type": "object"
    },
    "AttributeDefs": {
      "items": {
        "$ref": "#/$defs/AtlasAttributeDef"
      },
      "type": "array"
    },
    "Cardinality": {
      "description": "How many values an attribute or relationship end holds.",
      "enum": [
        "SINGLE",
        "LIST",
        "SET"
      ],
      "title": "Cardinality",
      "type": "string"
    },
    "IndexType": {
      "description": "How an attribute is indexed.",
      "enum": [
        "DEFAULT",
        "STRING"
      ],
      "title": "IndexType",
      "type": "string"
    },
    "JavaBool": {
      "type": "boolean"
    },
    "JavaInt": {
      "type": "integer"
    },
    "NameSet": {
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "OptionalNameSet": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "PropagateTags": {
      "description": "The direction in which classifications propagate over a relationship.",
      "enum": [
        "NONE",
        "ONE_TO_TWO",
        "TWO_TO_ONE",
        "BOTH"
      ],
      "title": "PropagateTags",
      "type": "string"
    },
    "RelationshipCategory": {
      "description": "How the two ends of a relationship depend on each other.",
      "enum": [
        "ASSOCIATION",
        "AGGREGATION",
        "COMPOSITION"
      ],
      "title": "RelationshipCategory",
      "type": "string"
    },
    "Timestamp": {
      "format": "date-time",
      "type": "string"
    }
  },
  "description": "Type definitions of every kind: the body of ``/v2/types/typedefs`` (TDM-13).",
  "properties": {
    "enumDefs": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/AtlasEnumDef"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "title": "Enumdefs"
    },
    "structDefs": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/AtlasStructDef"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "title": "Structdefs"
    },
    "classificationDefs": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/AtlasClassificationDef"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "title": "Classificationdefs"
    },
    "entityDefs": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/AtlasEntityDef"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "title": "Entitydefs"
    },
    "relationshipDefs": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/AtlasRelationshipDef"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "title": "Relationshipdefs"
    },
    "businessMetadataDefs": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/AtlasBusinessMetadataDef"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "title": "Businessmetadatadefs"
    }
  },
  "title": "AtlasTypesDef",
  "type": "object"
}
```

Fields:

- `enum_defs` (`list[AtlasEnumDef] | None`)
- `struct_defs` (`list[AtlasStructDef] | None`)
- `classification_defs` (`list[AtlasClassificationDef] | None`)
- `entity_defs` (`list[AtlasEntityDef] | None`)
- `relationship_defs` (`list[AtlasRelationshipDef] | None`)
- `business_metadata_defs` (`list[AtlasBusinessMetadataDef] | None`)

#### business\_metadata\_defs

```
business_metadata_defs: list[AtlasBusinessMetadataDef] | None
```

#### classification\_defs

```
classification_defs: list[AtlasClassificationDef] | None
```

#### entity\_defs

```
entity_defs: list[AtlasEntityDef] | None
```

#### enum\_defs

```
enum_defs: list[AtlasEnumDef] | None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### relationship\_defs

```
relationship_defs: list[AtlasRelationshipDef] | None
```

#### struct\_defs

```
struct_defs: list[AtlasStructDef] | None
```

#### has\_business\_metadata\_def

```
has_business_metadata_def(name: str) -> bool
```

Whether a business metadata definition is named `name` (TDM-17).

#### has\_classification\_def

```
has_classification_def(name: str) -> bool
```

Whether a classification definition is named `name` (TDM-17).

#### has\_entity\_def

```
has_entity_def(name: str) -> bool
```

Whether an entity definition is named `name` (TDM-17).

#### has\_enum\_def

```
has_enum_def(name: str) -> bool
```

Whether an enum definition is named `name` (TDM-17).

#### has\_relationship\_def

```
has_relationship_def(name: str) -> bool
```

Whether a relationship definition is named `name` (TDM-17).

#### has\_struct\_def

```
has_struct_def(name: str) -> bool
```

Whether a struct definition is named `name` (TDM-17).

#### is\_empty

```
is_empty() -> bool
```

Whether every list is empty or null (TDM-17).

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### Cardinality

Bases: `StrEnum`

How many values an attribute or relationship end holds.

Attributes:

- **`LIST`** –
- **`SET`** –
- **`SINGLE`** –

#### LIST

```
LIST = 'LIST'
```

#### SET

```
SET = 'SET'
```

#### SINGLE

```
SINGLE = 'SINGLE'
```

### IndexType

Bases: `StrEnum`

How an attribute is indexed.

Attributes:

- **`DEFAULT`** –
- **`STRING`** –

#### DEFAULT

```
DEFAULT = 'DEFAULT'
```

#### STRING

```
STRING = 'STRING'
```

### PropagateTags

Bases: `StrEnum`

The direction in which classifications propagate over a relationship.

Attributes:

- **`BOTH`** –
- **`NONE`** –
- **`ONE_TO_TWO`** –
- **`TWO_TO_ONE`** –

#### BOTH

```
BOTH = 'BOTH'
```

#### NONE

```
NONE = 'NONE'
```

#### ONE\_TO\_TWO

```
ONE_TO_TWO = 'ONE_TO_TWO'
```

#### TWO\_TO\_ONE

```
TWO_TO_ONE = 'TWO_TO_ONE'
```

### RelationshipCategory

Bases: `StrEnum`

How the two ends of a relationship depend on each other.

Attributes:

- **`AGGREGATION`** –
- **`ASSOCIATION`** –
- **`COMPOSITION`** –

#### AGGREGATION

```
AGGREGATION = 'AGGREGATION'
```

#### ASSOCIATION

```
ASSOCIATION = 'ASSOCIATION'
```

#### COMPOSITION

```
COMPOSITION = 'COMPOSITION'
```

### TypeCategory

Bases: `StrEnum`

The kinds of Atlas types (`org.apache.atlas.model.TypeCategory`).

Attributes:

- **`ARRAY`** –
- **`BUSINESS_METADATA`** –
- **`CLASSIFICATION`** –
- **`ENTITY`** –
- **`ENUM`** –
- **`MAP`** –
- **`OBJECT_ID_TYPE`** –
- **`PRIMITIVE`** –
- **`RELATIONSHIP`** –
- **`STRUCT`** –

#### ARRAY

```
ARRAY = 'ARRAY'
```

#### BUSINESS\_METADATA

```
BUSINESS_METADATA = 'BUSINESS_METADATA'
```

#### CLASSIFICATION

```
CLASSIFICATION = 'CLASSIFICATION'
```

#### ENTITY

```
ENTITY = 'ENTITY'
```

#### ENUM

```
ENUM = 'ENUM'
```

#### MAP

```
MAP = 'MAP'
```

#### OBJECT\_ID\_TYPE

```
OBJECT_ID_TYPE = 'OBJECT_ID_TYPE'
```

#### PRIMITIVE

```
PRIMITIVE = 'PRIMITIVE'
```

#### RELATIONSHIP

```
RELATIONSHIP = 'RELATIONSHIP'
```

#### STRUCT

```
STRUCT = 'STRUCT'
```

### array\_type\_name

```
array_type_name(element_type_name: str) -> str
```

The name of the array type of `element_type_name`: `array<T>` (TDM-19).

### find\_attribute

```
find_attribute(attributes: Iterable[AtlasAttributeDef], name: str | None) -> AtlasAttributeDef | None
```

The first attribute definition named `name`, compared without case, or None (TDM-16).

### map\_type\_name

```
map_type_name(key_type_name: str, value_type_name: str) -> str
```

The name of the map type from `key_type_name` to `value_type_name`: `map<K,V>` (TDM-19).

## aurelius\_atlas\_model.patches

Patch records: which patch was applied, and how it ended (`org.apache.atlas.model.patches`, MDL-06).

Classes:

- **`AtlasPatch`** –

  The record of one patch (`AtlasPatch`); the times are epoch milliseconds.
- **`PatchStatus`** –

  How a patch ended (`AtlasPatch.PatchStatus`).

Attributes:

- **`TYPEDEF_PATCH_TYPE`** –

  The `type` of a typedef patch's record (`AtlasTypeDefStoreInitializer.TYPEDEF_PATCH_TYPE`).

### TYPEDEF\_PATCH\_TYPE

```
TYPEDEF_PATCH_TYPE = 'TYPEDEF_PATCH'
```

The `type` of a typedef patch's record (`AtlasTypeDefStoreInitializer.TYPEDEF_PATCH_TYPE`).

### AtlasPatch

Bases: `AtlasModel`

The record of one patch (`AtlasPatch`); the times are epoch milliseconds.

**Show JSON schema:**

```
{
  "$defs": {
    "PatchStatus": {
      "description": "How a patch ended (``AtlasPatch.PatchStatus``).",
      "enum": [
        "UNKNOWN",
        "APPLIED",
        "SKIPPED",
        "FAILED"
      ],
      "title": "PatchStatus",
      "type": "string"
    }
  },
  "description": "The record of one patch (``AtlasPatch``); the times are epoch milliseconds.",
  "properties": {
    "id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Id"
    },
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "type": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Type"
    },
    "action": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Action"
    },
    "updatedBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Updatedby"
    },
    "createdBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Createdby"
    },
    "createdTime": {
      "default": 0,
      "title": "Createdtime",
      "type": "integer"
    },
    "updatedTime": {
      "default": 0,
      "title": "Updatedtime",
      "type": "integer"
    },
    "status": {
      "anyOf": [
        {
          "$ref": "#/$defs/PatchStatus"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "title": "AtlasPatch",
  "type": "object"
}
```

Config:

- `alias_generator`: `to_camel`
- `validate_by_alias`: `True`
- `validate_by_name`: `True`
- `validate_assignment`: `True`
- `extra`: `ignore`
- `coerce_numbers_to_str`: `True`

Fields:

- `id` (`str | None`)
- `description` (`str | None`)
- `type` (`str | None`)
- `action` (`str | None`)
- `updated_by` (`str | None`)
- `created_by` (`str | None`)
- `created_time` (`int`)
- `updated_time` (`int`)
- `status` (`PatchStatus | None`)

#### action

```
action: str | None = None
```

#### created\_by

```
created_by: str | None = None
```

#### created\_time

```
created_time: int = 0
```

#### description

```
description: str | None = None
```

#### id

```
id: str | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### status

```
status: PatchStatus | None = None
```

#### type

```
type: str | None = None
```

#### updated\_by

```
updated_by: str | None = None
```

#### updated\_time

```
updated_time: int = 0
```

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### PatchStatus

Bases: `StrEnum`

How a patch ended (`AtlasPatch.PatchStatus`).

Attributes:

- **`APPLIED`** –
- **`FAILED`** –
- **`SKIPPED`** –
- **`UNKNOWN`** –

#### APPLIED

```
APPLIED = 'APPLIED'
```

#### FAILED

```
FAILED = 'FAILED'
```

#### SKIPPED

```
SKIPPED = 'SKIPPED'
```

#### UNKNOWN

```
UNKNOWN = 'UNKNOWN'
```

## aurelius\_atlas\_model.base

The JSON conventions every Atlas model shares: names, nulls, timestamps and Java scalars (DD-020, DD-037).

Used by the typedef models (`typedef`) and the instance models (`instance`) alike.

Type Aliases:

- **`JavaBool`** –

  A Java `boolean`: an explicit null reads as false (TDM-10).
- **`JavaInt`** –

  A Java `int`: an explicit null reads as 0 (TDM-10).
- **`NameSet`** –

  A Java `Set<String>` that is never null (TDM-06, TDM-09).
- **`OptionalNameSet`** –

  A Java `Set<String>` that may be null (TDM-09).
- **`Timestamp`** –

  A `java.util.Date`: an aware datetime, written as epoch milliseconds (TDM-05).

Classes:

- **`AtlasModel`** –

  The JSON conventions of every Atlas model (TDM-01 to TDM-03, TDM-15, DD-020).

Functions:

- **`empty_when_null`** –

  Read a null list as empty: a field Java never leaves null (TDM-06).
- **`null_when_empty`** –

  Read an empty list as null: a field Java leaves null when empty (TDM-11).

### JavaBool

```
JavaBool = bool
```

A Java `boolean`: an explicit null reads as false (TDM-10).

### JavaInt

```
JavaInt = int
```

A Java `int`: an explicit null reads as 0 (TDM-10).

### NameSet

```
NameSet = list[str]
```

A Java `Set<String>` that is never null (TDM-06, TDM-09).

### OptionalNameSet

```
OptionalNameSet = list[str] | None
```

A Java `Set<String>` that may be null (TDM-09).

### Timestamp

```
Timestamp = datetime
```

A `java.util.Date`: an aware datetime, written as epoch milliseconds (TDM-05).

### AtlasModel

Bases: `BaseModel`

The JSON conventions of every Atlas model (TDM-01 to TDM-03, TDM-15, DD-020).

**Show JSON schema:**

```
{
  "description": "The JSON conventions of every Atlas model (TDM-01 to TDM-03, TDM-15, DD-020).",
  "properties": {},
  "title": "AtlasModel",
  "type": "object"
}
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### empty\_when\_null

```
empty_when_null(value: object) -> object
```

Read a null list as empty: a field Java never leaves null (TDM-06).

### null\_when\_empty

```
null_when_empty(values: list[T] | None) -> list[T] | None
```

Read an empty list as null: a field Java leaves null when empty (TDM-11).

## aurelius\_atlas\_model.codec

Atlas's JSON: numbers with a fraction read as decimals, decimals and dates written as Jackson writes them.

Atlas's REST mapper reads floats as `BigDecimal` (`USE_BIG_DECIMAL_FOR_FLOATS`) and writes a `BigDecimal` with its digits and a `Date` as epoch milliseconds (VAL-01, DD-039).

Functions:

- **`dumps`** –

  Write `value` as Atlas's REST mapper does, compactly, in UTF-8 (VAL-01).
- **`loads`** –

  Read JSON as Jackson does with `USE_BIG_DECIMAL_FOR_FLOATS`: every float is a `Decimal` with its digits.

Attributes:

- **`NOT_JSON_ERROR`** –

### NOT\_JSON\_ERROR

```
NOT_JSON_ERROR = '{type} is not a JSON value'
```

### dumps

```
dumps(value: Any) -> bytes
```

Write `value` as Atlas's REST mapper does, compactly, in UTF-8 (VAL-01).

A `Decimal` keeps its digits, a `datetime` is epoch milliseconds, NaN and infinities are strings, a model is its `to_json`, and map keys are Java's text of the key.

### loads

```
loads(text: str | bytes) -> Any
```

Read JSON as Jackson does with `USE_BIG_DECIMAL_FOR_FLOATS`: every float is a `Decimal` with its digits.

Raises:

- `ValueError` –

  The text is not JSON.

## aurelius\_atlas\_model.instance.struct

`AtlasStruct`: a type name and attribute values, the base of entities, classifications and headers.

Classes:

- **`AtlasStruct`** –

  An instance of a struct type: its name and its attribute values (ENT-02, ENT-03).

### AtlasStruct

Bases: `AtlasModel`

An instance of a struct type: its name and its attribute values (ENT-02, ENT-03).

Attribute values are JSON values as read, null included, until their types normalise them (DD-038).

**Show JSON schema:**

```
{
  "description": "An instance of a struct type: its name and its attribute values (ENT-02, ENT-03).\n\nAttribute values are JSON values as read, null included, until their types normalise them (DD-038).",
  "properties": {
    "typeName": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Typename"
    },
    "attributes": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Attributes"
    }
  },
  "title": "AtlasStruct",
  "type": "object"
}
```

Fields:

- `type_name` (`str | None`)
- `attributes` (`dict[str, Any] | None`)

#### attributes

```
attributes: dict[str, Any] | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### type\_name

```
type_name: str | None = None
```

#### from\_map

```
from_map(values: Mapping[str, Any]) -> Self
```

`AtlasStruct(Map)`: `typeName`, and `attributes` or, without an `attributes` map, the whole map.

Not how a body is read, which is Jackson's (ENT-02); Atlas's code makes structs from maps (VAL-14).

#### get\_attribute

```
get_attribute(name: str) -> Any
```

The value of attribute `name`, or None.

#### has\_attribute

```
has_attribute(name: str) -> bool
```

Whether attribute `name` is present, even with a null value.

#### remove\_attribute

```
remove_attribute(name: str) -> Any
```

Remove attribute `name` and return its value, or None.

#### set\_attribute

```
set_attribute(name: str, value: Any) -> None
```

Set attribute `name`, creating the attributes when there are none.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

## aurelius\_atlas\_model.instance.entity

`AtlasEntity`: an instance of an entity type, with its system fields (ENT-04 to ENT-08).

Classes:

- **`AtlasEntity`** –

  An entity: a struct with a GUID, a status, audit fields, relationships, classifications and labels.

Functions:

- **`next_internal_id`** –

  A new temporary GUID: `-` and a number counted up from the clock (`AtlasEntity.nextInternalId`, ENT-04).

### AtlasEntity

Bases: `AtlasStruct`

An entity: a struct with a GUID, a status, audit fields, relationships, classifications and labels.

Read with the defaults of Java's no-argument constructor, whose `init()` assigns a temporary GUID and clears `status` (ENT-04). `isProxy` is read under that name and written as `proxy` (ENT-05).

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasClassification": {
      "description": "An instance of a classification type attached to an entity.\n\n``propagate`` is written once: Java's ``getPropagate`` and ``isPropagate`` name the same property.",
      "properties": {
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "attributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Attributes"
        },
        "entityGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Entityguid"
        },
        "entityStatus": {
          "anyOf": [
            {
              "$ref": "#/$defs/EntityStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": "ACTIVE"
        },
        "propagate": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Propagate"
        },
        "validityPeriods": {
          "anyOf": [
            {
              "items": {
                "anyOf": [
                  {
                    "$ref": "#/$defs/TimeBoundary"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Validityperiods"
        },
        "removePropagationsOnEntityDelete": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Removepropagationsonentitydelete"
        }
      },
      "title": "AtlasClassification",
      "type": "object"
    },
    "AtlasTermAssignmentHeader": {
      "description": "The term, the assignment's relationship and how it was made (``glossary.relations``).\n\nAtlas writes it with ``@AtlasJSON``, ``NON_EMPTY``: null fields and empty strings are left out, but the\n``int`` ``confidence`` is always written.",
      "properties": {
        "termGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Termguid"
        },
        "relationGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Relationguid"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "displayText": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displaytext"
        },
        "expression": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Expression"
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "steward": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Steward"
        },
        "source": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Source"
        },
        "confidence": {
          "$ref": "#/$defs/JavaInt",
          "default": 0
        },
        "status": {
          "anyOf": [
            {
              "$ref": "#/$defs/AtlasTermAssignmentStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "qualifiedName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Qualifiedname"
        }
      },
      "title": "AtlasTermAssignmentHeader",
      "type": "object"
    },
    "AtlasTermAssignmentStatus": {
      "description": "The status of a term assignment, written by its Java name (``glossary.enums.AtlasTermAssignmentStatus``).",
      "enum": [
        "DISCOVERED",
        "PROPOSED",
        "IMPORTED",
        "VALIDATED",
        "DEPRECATED",
        "OBSOLETE",
        "OTHER"
      ],
      "title": "AtlasTermAssignmentStatus",
      "type": "string"
    },
    "EntityStatus": {
      "description": "Whether an entity is active, soft-deleted or purged (``AtlasEntity.Status``).",
      "enum": [
        "ACTIVE",
        "DELETED",
        "PURGED"
      ],
      "title": "EntityStatus",
      "type": "string"
    },
    "JavaInt": {
      "type": "integer"
    },
    "OptionalNameSet": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "TimeBoundary": {
      "description": "A period in which a classification applies; the times are strings in ``TIME_FORMAT``.\n\n``timeZone`` is a Java time zone id, or null for the server's local time.",
      "properties": {
        "startTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Starttime"
        },
        "endTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Endtime"
        },
        "timeZone": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Timezone"
        }
      },
      "title": "TimeBoundary",
      "type": "object"
    },
    "Timestamp": {
      "format": "date-time",
      "type": "string"
    }
  },
  "description": "An entity: a struct with a GUID, a status, audit fields, relationships, classifications and labels.\n\nRead with the defaults of Java's no-argument constructor, whose ``init()`` assigns a temporary GUID and\nclears ``status`` (ENT-04). ``isProxy`` is read under that name and written as ``proxy`` (ENT-05).",
  "properties": {
    "typeName": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Typename"
    },
    "attributes": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Attributes"
    },
    "guid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "title": "Guid"
    },
    "homeId": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Homeid"
    },
    "isProxy": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": false,
      "title": "Isproxy"
    },
    "isIncomplete": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": false,
      "title": "Isincomplete"
    },
    "provenanceType": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": 0,
      "title": "Provenancetype"
    },
    "status": {
      "anyOf": [
        {
          "$ref": "#/$defs/EntityStatus"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "createdBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Createdby"
    },
    "updatedBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Updatedby"
    },
    "createTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "updateTime": {
      "anyOf": [
        {
          "$ref": "#/$defs/Timestamp"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "version": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": 0,
      "title": "Version"
    },
    "relationshipAttributes": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Relationshipattributes"
    },
    "classifications": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/AtlasClassification"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Classifications"
    },
    "meanings": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/AtlasTermAssignmentHeader"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Meanings"
    },
    "customAttributes": {
      "anyOf": [
        {
          "additionalProperties": {
            "type": "string"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Customattributes"
    },
    "businessAttributes": {
      "anyOf": [
        {
          "additionalProperties": {
            "additionalProperties": true,
            "type": "object"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Businessattributes"
    },
    "labels": {
      "$ref": "#/$defs/OptionalNameSet",
      "default": null
    },
    "pendingTasks": {
      "$ref": "#/$defs/OptionalNameSet",
      "default": null
    }
  },
  "title": "AtlasEntity",
  "type": "object"
}
```

Fields:

- `type_name` (`str | None`)
- `attributes` (`dict[str, Any] | None`)
- `guid` (`str | None`)
- `home_id` (`str | None`)
- `is_proxy` (`bool | None`)
- `is_incomplete` (`bool | None`)
- `provenance_type` (`int | None`)
- `status` (`EntityStatus | None`)
- `created_by` (`str | None`)
- `updated_by` (`str | None`)
- `create_time` (`Timestamp | None`)
- `update_time` (`Timestamp | None`)
- `version` (`int | None`)
- `relationship_attributes` (`dict[str, Any] | None`)
- `classifications` (`list[AtlasClassification] | None`)
- `meanings` (`list[AtlasTermAssignmentHeader] | None`)
- `custom_attributes` (`dict[str, str] | None`)
- `business_attributes` (`dict[str, dict[str, Any]] | None`)
- `labels` (`OptionalNameSet`)
- `pending_tasks` (`OptionalNameSet`)

#### attributes

```
attributes: dict[str, Any] | None = None
```

#### business\_attributes

```
business_attributes: dict[str, dict[str, Any]] | None = None
```

#### classifications

```
classifications: list[AtlasClassification] | None = None
```

#### create\_time

```
create_time: Timestamp | None = None
```

#### created\_by

```
created_by: str | None = None
```

#### custom\_attributes

```
custom_attributes: dict[str, str] | None = None
```

#### guid

```
guid: str | None
```

#### home\_id

```
home_id: str | None = None
```

#### is\_incomplete

```
is_incomplete: bool | None = False
```

#### is\_proxy

```
is_proxy: bool | None = False
```

#### labels

```
labels: OptionalNameSet = None
```

#### meanings

```
meanings: list[AtlasTermAssignmentHeader] | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### pending\_tasks

```
pending_tasks: OptionalNameSet = None
```

#### provenance\_type

```
provenance_type: int | None = 0
```

#### relationship\_attributes

```
relationship_attributes: dict[str, Any] | None = None
```

#### status

```
status: EntityStatus | None = None
```

#### type\_name

```
type_name: str | None = None
```

#### update\_time

```
update_time: Timestamp | None = None
```

#### updated\_by

```
updated_by: str | None = None
```

#### version

```
version: int | None = 0
```

#### add\_classifications

```
add_classifications(classifications: list[AtlasClassification]) -> None
```

Append classifications, creating the list.

#### add\_meaning

```
add_meaning(meaning: AtlasTermAssignmentHeader) -> None
```

Append a meaning, creating the list.

#### from\_map

```
from_map(values: Mapping[str, Any]) -> Self
```

`AtlasStruct(Map)`: `typeName`, and `attributes` or, without an `attributes` map, the whole map.

Not how a body is read, which is Jackson's (ENT-02); Atlas's code makes structs from maps (VAL-14).

#### get\_attribute

```
get_attribute(name: str) -> Any
```

The value of attribute `name`, or None.

#### get\_business\_attribute

```
get_business_attribute(business_metadata: str, name: str) -> Any
```

The value of attribute `name` of business metadata `business_metadata`, or None.

#### get\_relationship\_attribute

```
get_relationship_attribute(name: str) -> Any
```

The value of relationship attribute `name`, or None.

#### has\_attribute

```
has_attribute(name: str) -> bool
```

Whether attribute `name` is present, even with a null value.

#### has\_relationship\_attribute

```
has_relationship_attribute(name: str) -> bool
```

Whether relationship attribute `name` is present, even with a null value.

#### remove\_attribute

```
remove_attribute(name: str) -> Any
```

Remove attribute `name` and return its value, or None.

#### set\_attribute

```
set_attribute(name: str, value: Any) -> None
```

Set attribute `name`, creating the attributes when there are none.

#### set\_business\_attribute

```
set_business_attribute(business_metadata: str, name: str, value: Any) -> None
```

Set attribute `name` of business metadata `business_metadata`, creating the maps it needs.

#### set\_relationship\_attribute

```
set_relationship_attribute(name: str, value: Any) -> None
```

Set relationship attribute `name`, creating the map when there is none.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

### next\_internal\_id

```
next_internal_id() -> str
```

A new temporary GUID: `-` and a number counted up from the clock (`AtlasEntity.nextInternalId`, ENT-04).

A client names entities it has not created yet by such GUIDs; the store replaces them on creation.

## aurelius\_atlas\_model.instance.entity\_status

`AtlasEntity.Status`: the life-cycle state of an entity (ENT-09).

Classes:

- **`EntityStatus`** –

  Whether an entity is active, soft-deleted or purged (`AtlasEntity.Status`).

### EntityStatus

Bases: `StrEnum`

Whether an entity is active, soft-deleted or purged (`AtlasEntity.Status`).

Attributes:

- **`ACTIVE`** –
- **`DELETED`** –
- **`PURGED`** –

#### ACTIVE

```
ACTIVE = 'ACTIVE'
```

#### DELETED

```
DELETED = 'DELETED'
```

#### PURGED

```
PURGED = 'PURGED'
```

## aurelius\_atlas\_model.instance.entity\_ext\_info

`AtlasEntity.AtlasEntityExtInfo`: the entities a request or response refers to, by GUID (ENT-10).

Classes:

- **`AtlasEntityExtInfo`** –

  `referredEntities`: the entities that the main entity or entities refer to, by their GUIDs.

### AtlasEntityExtInfo

Bases: `AtlasModel`

`referredEntities`: the entities that the main entity or entities refer to, by their GUIDs.

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasClassification": {
      "description": "An instance of a classification type attached to an entity.\n\n``propagate`` is written once: Java's ``getPropagate`` and ``isPropagate`` name the same property.",
      "properties": {
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "attributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Attributes"
        },
        "entityGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Entityguid"
        },
        "entityStatus": {
          "anyOf": [
            {
              "$ref": "#/$defs/EntityStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": "ACTIVE"
        },
        "propagate": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Propagate"
        },
        "validityPeriods": {
          "anyOf": [
            {
              "items": {
                "anyOf": [
                  {
                    "$ref": "#/$defs/TimeBoundary"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Validityperiods"
        },
        "removePropagationsOnEntityDelete": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Removepropagationsonentitydelete"
        }
      },
      "title": "AtlasClassification",
      "type": "object"
    },
    "AtlasEntity": {
      "description": "An entity: a struct with a GUID, a status, audit fields, relationships, classifications and labels.\n\nRead with the defaults of Java's no-argument constructor, whose ``init()`` assigns a temporary GUID and\nclears ``status`` (ENT-04). ``isProxy`` is read under that name and written as ``proxy`` (ENT-05).",
      "properties": {
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "attributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Attributes"
        },
        "guid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Guid"
        },
        "homeId": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Homeid"
        },
        "isProxy": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": false,
          "title": "Isproxy"
        },
        "isIncomplete": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": false,
          "title": "Isincomplete"
        },
        "provenanceType": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": 0,
          "title": "Provenancetype"
        },
        "status": {
          "anyOf": [
            {
              "$ref": "#/$defs/EntityStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "updatedBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Updatedby"
        },
        "createTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "updateTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "version": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": 0,
          "title": "Version"
        },
        "relationshipAttributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Relationshipattributes"
        },
        "classifications": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasClassification"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Classifications"
        },
        "meanings": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasTermAssignmentHeader"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Meanings"
        },
        "customAttributes": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Customattributes"
        },
        "businessAttributes": {
          "anyOf": [
            {
              "additionalProperties": {
                "additionalProperties": true,
                "type": "object"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Businessattributes"
        },
        "labels": {
          "$ref": "#/$defs/OptionalNameSet",
          "default": null
        },
        "pendingTasks": {
          "$ref": "#/$defs/OptionalNameSet",
          "default": null
        }
      },
      "title": "AtlasEntity",
      "type": "object"
    },
    "AtlasTermAssignmentHeader": {
      "description": "The term, the assignment's relationship and how it was made (``glossary.relations``).\n\nAtlas writes it with ``@AtlasJSON``, ``NON_EMPTY``: null fields and empty strings are left out, but the\n``int`` ``confidence`` is always written.",
      "properties": {
        "termGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Termguid"
        },
        "relationGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Relationguid"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "displayText": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displaytext"
        },
        "expression": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Expression"
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "steward": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Steward"
        },
        "source": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Source"
        },
        "confidence": {
          "$ref": "#/$defs/JavaInt",
          "default": 0
        },
        "status": {
          "anyOf": [
            {
              "$ref": "#/$defs/AtlasTermAssignmentStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "qualifiedName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Qualifiedname"
        }
      },
      "title": "AtlasTermAssignmentHeader",
      "type": "object"
    },
    "AtlasTermAssignmentStatus": {
      "description": "The status of a term assignment, written by its Java name (``glossary.enums.AtlasTermAssignmentStatus``).",
      "enum": [
        "DISCOVERED",
        "PROPOSED",
        "IMPORTED",
        "VALIDATED",
        "DEPRECATED",
        "OBSOLETE",
        "OTHER"
      ],
      "title": "AtlasTermAssignmentStatus",
      "type": "string"
    },
    "EntityStatus": {
      "description": "Whether an entity is active, soft-deleted or purged (``AtlasEntity.Status``).",
      "enum": [
        "ACTIVE",
        "DELETED",
        "PURGED"
      ],
      "title": "EntityStatus",
      "type": "string"
    },
    "JavaInt": {
      "type": "integer"
    },
    "OptionalNameSet": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "TimeBoundary": {
      "description": "A period in which a classification applies; the times are strings in ``TIME_FORMAT``.\n\n``timeZone`` is a Java time zone id, or null for the server's local time.",
      "properties": {
        "startTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Starttime"
        },
        "endTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Endtime"
        },
        "timeZone": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Timezone"
        }
      },
      "title": "TimeBoundary",
      "type": "object"
    },
    "Timestamp": {
      "format": "date-time",
      "type": "string"
    }
  },
  "description": "``referredEntities``: the entities that the main entity or entities refer to, by their GUIDs.",
  "properties": {
    "referredEntities": {
      "anyOf": [
        {
          "additionalProperties": {
            "$ref": "#/$defs/AtlasEntity"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Referredentities"
    }
  },
  "title": "AtlasEntityExtInfo",
  "type": "object"
}
```

Fields:

- `referred_entities` (`dict[str, AtlasEntity] | None`)

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### referred\_entities

```
referred_entities: dict[str, AtlasEntity] | None = None
```

#### add\_referred\_entity

```
add_referred_entity(entity: AtlasEntity) -> None
```

Refer to `entity` under its own GUID (`addReferredEntity(AtlasEntity)`).

#### add\_referred\_entity\_as

```
add_referred_entity_as(guid: str | None, entity: AtlasEntity) -> None
```

Refer to `entity` under `guid`; without a GUID nothing is added, but the map is still created.

#### compact

```
compact() -> None
```

Remove referred entities that are also main entities; there are none here.

#### get\_entity

```
get_entity(guid: str | None) -> AtlasEntity | None
```

The entity with `guid` among those this holds; here, the referred ones.

#### get\_referred\_entity

```
get_referred_entity(guid: str | None) -> AtlasEntity | None
```

The referred entity with `guid`, or None.

#### has\_entity

```
has_entity(guid: str | None) -> bool
```

Whether this holds an entity with `guid`.

#### remove\_entity

```
remove_entity(guid: str | None) -> AtlasEntity | None
```

Remove and return the referred entity with `guid`, or None.

#### remove\_referred\_entity

```
remove_referred_entity(guid: str | None) -> AtlasEntity | None
```

Remove and return the referred entity with `guid`, or None.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

#### update\_entity\_guid

```
update_entity_guid(old_guid: str, new_guid: str) -> None
```

Give the entity with `old_guid` the GUID `new_guid`; a referred one is moved to it in the map.

## aurelius\_atlas\_model.instance.entity\_with\_ext\_info

`AtlasEntity.AtlasEntityWithExtInfo`: one entity and the entities it refers to (ENT-10).

Classes:

- **`AtlasEntityWithExtInfo`** –

  The body of a single-entity read or write: `entity` and `referredEntities`.

### AtlasEntityWithExtInfo

Bases: `AtlasEntityExtInfo`

The body of a single-entity read or write: `entity` and `referredEntities`.

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasClassification": {
      "description": "An instance of a classification type attached to an entity.\n\n``propagate`` is written once: Java's ``getPropagate`` and ``isPropagate`` name the same property.",
      "properties": {
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "attributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Attributes"
        },
        "entityGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Entityguid"
        },
        "entityStatus": {
          "anyOf": [
            {
              "$ref": "#/$defs/EntityStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": "ACTIVE"
        },
        "propagate": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Propagate"
        },
        "validityPeriods": {
          "anyOf": [
            {
              "items": {
                "anyOf": [
                  {
                    "$ref": "#/$defs/TimeBoundary"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Validityperiods"
        },
        "removePropagationsOnEntityDelete": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Removepropagationsonentitydelete"
        }
      },
      "title": "AtlasClassification",
      "type": "object"
    },
    "AtlasEntity": {
      "description": "An entity: a struct with a GUID, a status, audit fields, relationships, classifications and labels.\n\nRead with the defaults of Java's no-argument constructor, whose ``init()`` assigns a temporary GUID and\nclears ``status`` (ENT-04). ``isProxy`` is read under that name and written as ``proxy`` (ENT-05).",
      "properties": {
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "attributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Attributes"
        },
        "guid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Guid"
        },
        "homeId": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Homeid"
        },
        "isProxy": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": false,
          "title": "Isproxy"
        },
        "isIncomplete": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": false,
          "title": "Isincomplete"
        },
        "provenanceType": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": 0,
          "title": "Provenancetype"
        },
        "status": {
          "anyOf": [
            {
              "$ref": "#/$defs/EntityStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "updatedBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Updatedby"
        },
        "createTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "updateTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "version": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": 0,
          "title": "Version"
        },
        "relationshipAttributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Relationshipattributes"
        },
        "classifications": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasClassification"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Classifications"
        },
        "meanings": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasTermAssignmentHeader"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Meanings"
        },
        "customAttributes": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Customattributes"
        },
        "businessAttributes": {
          "anyOf": [
            {
              "additionalProperties": {
                "additionalProperties": true,
                "type": "object"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Businessattributes"
        },
        "labels": {
          "$ref": "#/$defs/OptionalNameSet",
          "default": null
        },
        "pendingTasks": {
          "$ref": "#/$defs/OptionalNameSet",
          "default": null
        }
      },
      "title": "AtlasEntity",
      "type": "object"
    },
    "AtlasTermAssignmentHeader": {
      "description": "The term, the assignment's relationship and how it was made (``glossary.relations``).\n\nAtlas writes it with ``@AtlasJSON``, ``NON_EMPTY``: null fields and empty strings are left out, but the\n``int`` ``confidence`` is always written.",
      "properties": {
        "termGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Termguid"
        },
        "relationGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Relationguid"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "displayText": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displaytext"
        },
        "expression": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Expression"
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "steward": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Steward"
        },
        "source": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Source"
        },
        "confidence": {
          "$ref": "#/$defs/JavaInt",
          "default": 0
        },
        "status": {
          "anyOf": [
            {
              "$ref": "#/$defs/AtlasTermAssignmentStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "qualifiedName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Qualifiedname"
        }
      },
      "title": "AtlasTermAssignmentHeader",
      "type": "object"
    },
    "AtlasTermAssignmentStatus": {
      "description": "The status of a term assignment, written by its Java name (``glossary.enums.AtlasTermAssignmentStatus``).",
      "enum": [
        "DISCOVERED",
        "PROPOSED",
        "IMPORTED",
        "VALIDATED",
        "DEPRECATED",
        "OBSOLETE",
        "OTHER"
      ],
      "title": "AtlasTermAssignmentStatus",
      "type": "string"
    },
    "EntityStatus": {
      "description": "Whether an entity is active, soft-deleted or purged (``AtlasEntity.Status``).",
      "enum": [
        "ACTIVE",
        "DELETED",
        "PURGED"
      ],
      "title": "EntityStatus",
      "type": "string"
    },
    "JavaInt": {
      "type": "integer"
    },
    "OptionalNameSet": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "TimeBoundary": {
      "description": "A period in which a classification applies; the times are strings in ``TIME_FORMAT``.\n\n``timeZone`` is a Java time zone id, or null for the server's local time.",
      "properties": {
        "startTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Starttime"
        },
        "endTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Endtime"
        },
        "timeZone": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Timezone"
        }
      },
      "title": "TimeBoundary",
      "type": "object"
    },
    "Timestamp": {
      "format": "date-time",
      "type": "string"
    }
  },
  "description": "The body of a single-entity read or write: ``entity`` and ``referredEntities``.",
  "properties": {
    "referredEntities": {
      "anyOf": [
        {
          "additionalProperties": {
            "$ref": "#/$defs/AtlasEntity"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Referredentities"
    },
    "entity": {
      "anyOf": [
        {
          "$ref": "#/$defs/AtlasEntity"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "title": "AtlasEntityWithExtInfo",
  "type": "object"
}
```

Fields:

- `referred_entities` (`dict[str, AtlasEntity] | None`)
- `entity` (`AtlasEntity | None`)

#### entity

```
entity: AtlasEntity | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### referred\_entities

```
referred_entities: dict[str, AtlasEntity] | None = None
```

#### add\_referred\_entity

```
add_referred_entity(entity: AtlasEntity) -> None
```

Refer to `entity` under its own GUID (`addReferredEntity(AtlasEntity)`).

#### add\_referred\_entity\_as

```
add_referred_entity_as(guid: str | None, entity: AtlasEntity) -> None
```

Refer to `entity` under `guid`; without a GUID nothing is added, but the map is still created.

#### compact

```
compact() -> None
```

Remove the main entity from the referred entities.

#### get\_entity

```
get_entity(guid: str | None) -> AtlasEntity | None
```

The referred entity with `guid`, else the main entity when it has that GUID.

#### get\_referred\_entity

```
get_referred_entity(guid: str | None) -> AtlasEntity | None
```

The referred entity with `guid`, or None.

#### has\_entity

```
has_entity(guid: str | None) -> bool
```

Whether this holds an entity with `guid`.

#### remove\_entity

```
remove_entity(guid: str | None) -> AtlasEntity | None
```

Remove and return the referred entity with `guid`, or None.

#### remove\_referred\_entity

```
remove_referred_entity(guid: str | None) -> AtlasEntity | None
```

Remove and return the referred entity with `guid`, or None.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

#### update\_entity\_guid

```
update_entity_guid(old_guid: str, new_guid: str) -> None
```

Give the entity with `old_guid` the GUID `new_guid`; a referred one is moved to it in the map.

## aurelius\_atlas\_model.instance.entities\_with\_ext\_info

`AtlasEntity.AtlasEntitiesWithExtInfo`: several entities and the entities they refer to (ENT-10).

Classes:

- **`AtlasEntitiesWithExtInfo`** –

  The body of a bulk read or write: `entities` and `referredEntities`.

### AtlasEntitiesWithExtInfo

Bases: `AtlasEntityExtInfo`

The body of a bulk read or write: `entities` and `referredEntities`.

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasClassification": {
      "description": "An instance of a classification type attached to an entity.\n\n``propagate`` is written once: Java's ``getPropagate`` and ``isPropagate`` name the same property.",
      "properties": {
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "attributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Attributes"
        },
        "entityGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Entityguid"
        },
        "entityStatus": {
          "anyOf": [
            {
              "$ref": "#/$defs/EntityStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": "ACTIVE"
        },
        "propagate": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Propagate"
        },
        "validityPeriods": {
          "anyOf": [
            {
              "items": {
                "anyOf": [
                  {
                    "$ref": "#/$defs/TimeBoundary"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Validityperiods"
        },
        "removePropagationsOnEntityDelete": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Removepropagationsonentitydelete"
        }
      },
      "title": "AtlasClassification",
      "type": "object"
    },
    "AtlasEntity": {
      "description": "An entity: a struct with a GUID, a status, audit fields, relationships, classifications and labels.\n\nRead with the defaults of Java's no-argument constructor, whose ``init()`` assigns a temporary GUID and\nclears ``status`` (ENT-04). ``isProxy`` is read under that name and written as ``proxy`` (ENT-05).",
      "properties": {
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "attributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Attributes"
        },
        "guid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "title": "Guid"
        },
        "homeId": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Homeid"
        },
        "isProxy": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": false,
          "title": "Isproxy"
        },
        "isIncomplete": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": false,
          "title": "Isincomplete"
        },
        "provenanceType": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": 0,
          "title": "Provenancetype"
        },
        "status": {
          "anyOf": [
            {
              "$ref": "#/$defs/EntityStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "updatedBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Updatedby"
        },
        "createTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "updateTime": {
          "anyOf": [
            {
              "$ref": "#/$defs/Timestamp"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "version": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ],
          "default": 0,
          "title": "Version"
        },
        "relationshipAttributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Relationshipattributes"
        },
        "classifications": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasClassification"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Classifications"
        },
        "meanings": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasTermAssignmentHeader"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Meanings"
        },
        "customAttributes": {
          "anyOf": [
            {
              "additionalProperties": {
                "type": "string"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Customattributes"
        },
        "businessAttributes": {
          "anyOf": [
            {
              "additionalProperties": {
                "additionalProperties": true,
                "type": "object"
              },
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Businessattributes"
        },
        "labels": {
          "$ref": "#/$defs/OptionalNameSet",
          "default": null
        },
        "pendingTasks": {
          "$ref": "#/$defs/OptionalNameSet",
          "default": null
        }
      },
      "title": "AtlasEntity",
      "type": "object"
    },
    "AtlasTermAssignmentHeader": {
      "description": "The term, the assignment's relationship and how it was made (``glossary.relations``).\n\nAtlas writes it with ``@AtlasJSON``, ``NON_EMPTY``: null fields and empty strings are left out, but the\n``int`` ``confidence`` is always written.",
      "properties": {
        "termGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Termguid"
        },
        "relationGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Relationguid"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "displayText": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displaytext"
        },
        "expression": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Expression"
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "steward": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Steward"
        },
        "source": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Source"
        },
        "confidence": {
          "$ref": "#/$defs/JavaInt",
          "default": 0
        },
        "status": {
          "anyOf": [
            {
              "$ref": "#/$defs/AtlasTermAssignmentStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "qualifiedName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Qualifiedname"
        }
      },
      "title": "AtlasTermAssignmentHeader",
      "type": "object"
    },
    "AtlasTermAssignmentStatus": {
      "description": "The status of a term assignment, written by its Java name (``glossary.enums.AtlasTermAssignmentStatus``).",
      "enum": [
        "DISCOVERED",
        "PROPOSED",
        "IMPORTED",
        "VALIDATED",
        "DEPRECATED",
        "OBSOLETE",
        "OTHER"
      ],
      "title": "AtlasTermAssignmentStatus",
      "type": "string"
    },
    "EntityStatus": {
      "description": "Whether an entity is active, soft-deleted or purged (``AtlasEntity.Status``).",
      "enum": [
        "ACTIVE",
        "DELETED",
        "PURGED"
      ],
      "title": "EntityStatus",
      "type": "string"
    },
    "JavaInt": {
      "type": "integer"
    },
    "OptionalNameSet": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "TimeBoundary": {
      "description": "A period in which a classification applies; the times are strings in ``TIME_FORMAT``.\n\n``timeZone`` is a Java time zone id, or null for the server's local time.",
      "properties": {
        "startTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Starttime"
        },
        "endTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Endtime"
        },
        "timeZone": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Timezone"
        }
      },
      "title": "TimeBoundary",
      "type": "object"
    },
    "Timestamp": {
      "format": "date-time",
      "type": "string"
    }
  },
  "description": "The body of a bulk read or write: ``entities`` and ``referredEntities``.",
  "properties": {
    "referredEntities": {
      "anyOf": [
        {
          "additionalProperties": {
            "$ref": "#/$defs/AtlasEntity"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Referredentities"
    },
    "entities": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/AtlasEntity"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Entities"
    }
  },
  "title": "AtlasEntitiesWithExtInfo",
  "type": "object"
}
```

Fields:

- `referred_entities` (`dict[str, AtlasEntity] | None`)
- `entities` (`list[AtlasEntity] | None`)

#### entities

```
entities: list[AtlasEntity] | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### referred\_entities

```
referred_entities: dict[str, AtlasEntity] | None = None
```

#### add\_entity

```
add_entity(entity: AtlasEntity) -> None
```

Append a main entity, creating the list.

#### add\_referred\_entity

```
add_referred_entity(entity: AtlasEntity) -> None
```

Refer to `entity` under its own GUID (`addReferredEntity(AtlasEntity)`).

#### add\_referred\_entity\_as

```
add_referred_entity_as(guid: str | None, entity: AtlasEntity) -> None
```

Refer to `entity` under `guid`; without a GUID nothing is added, but the map is still created.

#### compact

```
compact() -> None
```

Remove the main entities from the referred entities.

#### get\_entity

```
get_entity(guid: str | None) -> AtlasEntity | None
```

The referred entity with `guid`, else the first main entity with that GUID.

#### get\_referred\_entity

```
get_referred_entity(guid: str | None) -> AtlasEntity | None
```

The referred entity with `guid`, or None.

#### has\_entity

```
has_entity(guid: str | None) -> bool
```

Whether this holds an entity with `guid`.

#### remove\_entity

```
remove_entity(guid: str | None) -> AtlasEntity | None
```

```
remove_entity(guid: AtlasEntity) -> None
```

```
remove_entity(guid: str | AtlasEntity | None) -> AtlasEntity | None
```

Remove a referred entity by GUID, or the first main entity equal to an entity (Java's two overloads).

#### remove\_referred\_entity

```
remove_referred_entity(guid: str | None) -> AtlasEntity | None
```

Remove and return the referred entity with `guid`, or None.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

#### update\_entity\_guid

```
update_entity_guid(old_guid: str, new_guid: str) -> None
```

Give the entity with `old_guid` the GUID `new_guid`; a referred one is moved to it in the map.

## aurelius\_atlas\_model.instance.object\_id

`AtlasObjectId`: a reference to an entity, by GUID or by type and unique attributes (ENT-11).

Classes:

- **`AtlasObjectId`** –

  An entity reference: its GUID, or its type name and the unique attribute values that identify it.

### AtlasObjectId

Bases: `AtlasModel`

An entity reference: its GUID, or its type name and the unique attribute values that identify it.

**Show JSON schema:**

```
{
  "description": "An entity reference: its GUID, or its type name and the unique attribute values that identify it.",
  "properties": {
    "guid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Guid"
    },
    "typeName": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Typename"
    },
    "uniqueAttributes": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Uniqueattributes"
    }
  },
  "title": "AtlasObjectId",
  "type": "object"
}
```

Fields:

- `guid` (`str | None`)
- `type_name` (`str | None`)
- `unique_attributes` (`dict[str, Any] | None`)

#### \_\_hash\_\_

```
__hash__ = None
```

#### guid

```
guid: str | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### type\_name

```
type_name: str | None = None
```

#### unique\_attributes

```
unique_attributes: dict[str, Any] | None = None
```

#### \_\_eq\_\_

```
__eq__(other: object) -> bool
```

`AtlasObjectId.equals`: by GUID when either has a non-empty one, else by type and unique attributes.

#### from\_map

```
from_map(values: Mapping[str, Any]) -> Self
```

`AtlasObjectId(Map)`: `guid` and `typeName` as text, `uniqueAttributes` when it is a map (VAL-14).

#### java\_string

```
java_string() -> str
```

`AtlasObjectId.toString`, as errors name an object id: `AtlasObjectId{guid='…', …}` (EWR-05).

#### read\_map

```
read_map(values: Mapping[str, Any]) -> None
```

Set the fields Java's map constructor reads from `values`.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

## aurelius\_atlas\_model.instance.related\_object\_id

`AtlasRelatedObjectId`: a related entity as a relationship attribute shows it (ENT-12).

Classes:

- **`AtlasRelatedObjectId`** –

  The other end of a relationship: the entity, its status and display text, and the relationship.

### AtlasRelatedObjectId

Bases: `AtlasObjectId`

The other end of a relationship: the entity, its status and display text, and the relationship.

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasStruct": {
      "description": "An instance of a struct type: its name and its attribute values (ENT-02, ENT-03).\n\nAttribute values are JSON values as read, null included, until their types normalise them (DD-038).",
      "properties": {
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "attributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Attributes"
        }
      },
      "title": "AtlasStruct",
      "type": "object"
    },
    "EntityStatus": {
      "description": "Whether an entity is active, soft-deleted or purged (``AtlasEntity.Status``).",
      "enum": [
        "ACTIVE",
        "DELETED",
        "PURGED"
      ],
      "title": "EntityStatus",
      "type": "string"
    },
    "RelationshipStatus": {
      "description": "Whether a relationship is active or soft-deleted (``AtlasRelationship.Status``).",
      "enum": [
        "ACTIVE",
        "DELETED"
      ],
      "title": "RelationshipStatus",
      "type": "string"
    }
  },
  "description": "The other end of a relationship: the entity, its status and display text, and the relationship.",
  "properties": {
    "guid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Guid"
    },
    "typeName": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Typename"
    },
    "uniqueAttributes": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Uniqueattributes"
    },
    "entityStatus": {
      "anyOf": [
        {
          "$ref": "#/$defs/EntityStatus"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "displayText": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Displaytext"
    },
    "relationshipType": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Relationshiptype"
    },
    "relationshipGuid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Relationshipguid"
    },
    "relationshipStatus": {
      "anyOf": [
        {
          "$ref": "#/$defs/RelationshipStatus"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "relationshipAttributes": {
      "anyOf": [
        {
          "$ref": "#/$defs/AtlasStruct"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "qualifiedName": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Qualifiedname"
    }
  },
  "title": "AtlasRelatedObjectId",
  "type": "object"
}
```

Fields:

- `guid` (`str | None`)
- `type_name` (`str | None`)
- `unique_attributes` (`dict[str, Any] | None`)
- `entity_status` (`EntityStatus | None`)
- `display_text` (`str | None`)
- `relationship_type` (`str | None`)
- `relationship_guid` (`str | None`)
- `relationship_status` (`RelationshipStatus | None`)
- `relationship_attributes` (`AtlasStruct | None`)
- `qualified_name` (`str | None`)

Validators:

- `_relationship_type_in_order`

#### \_\_hash\_\_

```
__hash__ = None
```

#### display\_text

```
display_text: str | None = None
```

#### entity\_status

```
entity_status: EntityStatus | None = None
```

#### guid

```
guid: str | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### qualified\_name

```
qualified_name: str | None = None
```

#### relationship\_attributes

```
relationship_attributes: AtlasStruct | None = None
```

#### relationship\_guid

```
relationship_guid: str | None = None
```

#### relationship\_status

```
relationship_status: RelationshipStatus | None = None
```

#### relationship\_type

```
relationship_type: str | None = None
```

#### type\_name

```
type_name: str | None = None
```

#### unique\_attributes

```
unique_attributes: dict[str, Any] | None = None
```

#### \_\_eq\_\_

```
__eq__(other: object) -> bool
```

`AtlasRelatedObjectId.equals`: the object id's equality, then the relationship's fields.

#### from\_map

```
from_map(values: Mapping[str, Any]) -> Self
```

`AtlasObjectId(Map)`: `guid` and `typeName` as text, `uniqueAttributes` when it is a map (VAL-14).

#### java\_string

```
java_string() -> str
```

`AtlasObjectId.toString`, as errors name an object id: `AtlasObjectId{guid='…', …}` (EWR-05).

#### read\_map

```
read_map(values: Mapping[str, Any]) -> None
```

`AtlasRelatedObjectId(Map)`: the object id's fields, then the relationship's (VAL-14).

In Java's order: the GUID, the attributes as a struct (which set the type), the type and the status.

Raises:

- `ValueError` –

  `relationshipStatus` is not a relationship status, as Java's `valueOf` fails.

#### set\_relationship\_attributes

```
set_relationship_attributes(relationship_attributes: AtlasStruct | None) -> None
```

Set the relationship's attributes; their type name, when set, becomes the relationship type.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

## aurelius\_atlas\_model.instance.relationship\_status

`AtlasRelationship.Status`: the life-cycle state of a relationship (ENT-09).

Classes:

- **`RelationshipStatus`** –

  Whether a relationship is active or soft-deleted (`AtlasRelationship.Status`).

### RelationshipStatus

Bases: `StrEnum`

Whether a relationship is active or soft-deleted (`AtlasRelationship.Status`).

Attributes:

- **`ACTIVE`** –
- **`DELETED`** –

#### ACTIVE

```
ACTIVE = 'ACTIVE'
```

#### DELETED

```
DELETED = 'DELETED'
```

## aurelius\_atlas\_model.instance.classification

`AtlasClassification`: a classification of an entity, with its propagation and validity (ENT-13).

Classes:

- **`AtlasClassification`** –

  An instance of a classification type attached to an entity.

### AtlasClassification

Bases: `AtlasStruct`

An instance of a classification type attached to an entity.

`propagate` is written once: Java's `getPropagate` and `isPropagate` name the same property.

**Show JSON schema:**

```
{
  "$defs": {
    "EntityStatus": {
      "description": "Whether an entity is active, soft-deleted or purged (``AtlasEntity.Status``).",
      "enum": [
        "ACTIVE",
        "DELETED",
        "PURGED"
      ],
      "title": "EntityStatus",
      "type": "string"
    },
    "TimeBoundary": {
      "description": "A period in which a classification applies; the times are strings in ``TIME_FORMAT``.\n\n``timeZone`` is a Java time zone id, or null for the server's local time.",
      "properties": {
        "startTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Starttime"
        },
        "endTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Endtime"
        },
        "timeZone": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Timezone"
        }
      },
      "title": "TimeBoundary",
      "type": "object"
    }
  },
  "description": "An instance of a classification type attached to an entity.\n\n``propagate`` is written once: Java's ``getPropagate`` and ``isPropagate`` name the same property.",
  "properties": {
    "typeName": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Typename"
    },
    "attributes": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Attributes"
    },
    "entityGuid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Entityguid"
    },
    "entityStatus": {
      "anyOf": [
        {
          "$ref": "#/$defs/EntityStatus"
        },
        {
          "type": "null"
        }
      ],
      "default": "ACTIVE"
    },
    "propagate": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Propagate"
    },
    "validityPeriods": {
      "anyOf": [
        {
          "items": {
            "anyOf": [
              {
                "$ref": "#/$defs/TimeBoundary"
              },
              {
                "type": "null"
              }
            ]
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Validityperiods"
    },
    "removePropagationsOnEntityDelete": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Removepropagationsonentitydelete"
    }
  },
  "title": "AtlasClassification",
  "type": "object"
}
```

Fields:

- `type_name` (`str | None`)
- `attributes` (`dict[str, Any] | None`)
- `entity_guid` (`str | None`)
- `entity_status` (`EntityStatus | None`)
- `propagate` (`bool | None`)
- `validity_periods` (`list[TimeBoundary | None] | None`)
- `remove_propagations_on_entity_delete` (`bool | None`)

#### attributes

```
attributes: dict[str, Any] | None = None
```

#### entity\_guid

```
entity_guid: str | None = None
```

#### entity\_status

```
entity_status: EntityStatus | None = EntityStatus.ACTIVE
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### propagate

```
propagate: bool | None = None
```

#### remove\_propagations\_on\_entity\_delete

```
remove_propagations_on_entity_delete: bool | None = None
```

#### type\_name

```
type_name: str | None = None
```

#### validity\_periods

```
validity_periods: list[TimeBoundary | None] | None = None
```

#### add\_validity\_period

```
add_validity_period(validity_period: TimeBoundary) -> None
```

Append a validity period, creating the list (`addValityPeriod`).

#### from\_map

```
from_map(values: Mapping[str, Any]) -> Self
```

`AtlasStruct(Map)`: `typeName`, and `attributes` or, without an `attributes` map, the whole map.

Not how a body is read, which is Jackson's (ENT-02); Atlas's code makes structs from maps (VAL-14).

#### get\_attribute

```
get_attribute(name: str) -> Any
```

The value of attribute `name`, or None.

#### has\_attribute

```
has_attribute(name: str) -> bool
```

Whether attribute `name` is present, even with a null value.

#### remove\_attribute

```
remove_attribute(name: str) -> Any
```

Remove attribute `name` and return its value, or None.

#### set\_attribute

```
set_attribute(name: str, value: Any) -> None
```

Set attribute `name`, creating the attributes when there are none.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

## aurelius\_atlas\_model.instance.time\_boundary

`TimeBoundary`: one validity period of a classification (ENT-13).

Classes:

- **`TimeBoundary`** –

  A period in which a classification applies; the times are strings in `TIME_FORMAT`.

Attributes:

- **`TIME_FORMAT`** –

  The Java date format of `startTime` and `endTime` (`TimeBoundary.TIME_FORMAT`); checked in 2.1b.

### TIME\_FORMAT

```
TIME_FORMAT = 'yyyy/MM/dd HH:mm:ss'
```

The Java date format of `startTime` and `endTime` (`TimeBoundary.TIME_FORMAT`); checked in 2.1b.

### TimeBoundary

Bases: `AtlasModel`

A period in which a classification applies; the times are strings in `TIME_FORMAT`.

`timeZone` is a Java time zone id, or null for the server's local time.

**Show JSON schema:**

```
{
  "description": "A period in which a classification applies; the times are strings in ``TIME_FORMAT``.\n\n``timeZone`` is a Java time zone id, or null for the server's local time.",
  "properties": {
    "startTime": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Starttime"
    },
    "endTime": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Endtime"
    },
    "timeZone": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Timezone"
    }
  },
  "title": "TimeBoundary",
  "type": "object"
}
```

Fields:

- `start_time` (`str | None`)
- `end_time` (`str | None`)
- `time_zone` (`str | None`)

#### end\_time

```
end_time: str | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### start\_time

```
start_time: str | None = None
```

#### time\_zone

```
time_zone: str | None = None
```

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

## aurelius\_atlas\_model.instance.entity\_header

`AtlasEntityHeader`: an entity's identity and summary, as lists and mutation responses show it (ENT-14).

Classes:

- **`AtlasEntityHeader`** –

  An entity's type, GUID, status, display text, classifications, meanings and labels.

### AtlasEntityHeader

Bases: `AtlasStruct`

An entity's type, GUID, status, display text, classifications, meanings and labels.

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasClassification": {
      "description": "An instance of a classification type attached to an entity.\n\n``propagate`` is written once: Java's ``getPropagate`` and ``isPropagate`` name the same property.",
      "properties": {
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "attributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Attributes"
        },
        "entityGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Entityguid"
        },
        "entityStatus": {
          "anyOf": [
            {
              "$ref": "#/$defs/EntityStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": "ACTIVE"
        },
        "propagate": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Propagate"
        },
        "validityPeriods": {
          "anyOf": [
            {
              "items": {
                "anyOf": [
                  {
                    "$ref": "#/$defs/TimeBoundary"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Validityperiods"
        },
        "removePropagationsOnEntityDelete": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Removepropagationsonentitydelete"
        }
      },
      "title": "AtlasClassification",
      "type": "object"
    },
    "AtlasTermAssignmentHeader": {
      "description": "The term, the assignment's relationship and how it was made (``glossary.relations``).\n\nAtlas writes it with ``@AtlasJSON``, ``NON_EMPTY``: null fields and empty strings are left out, but the\n``int`` ``confidence`` is always written.",
      "properties": {
        "termGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Termguid"
        },
        "relationGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Relationguid"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "displayText": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displaytext"
        },
        "expression": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Expression"
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "steward": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Steward"
        },
        "source": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Source"
        },
        "confidence": {
          "$ref": "#/$defs/JavaInt",
          "default": 0
        },
        "status": {
          "anyOf": [
            {
              "$ref": "#/$defs/AtlasTermAssignmentStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "qualifiedName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Qualifiedname"
        }
      },
      "title": "AtlasTermAssignmentHeader",
      "type": "object"
    },
    "AtlasTermAssignmentStatus": {
      "description": "The status of a term assignment, written by its Java name (``glossary.enums.AtlasTermAssignmentStatus``).",
      "enum": [
        "DISCOVERED",
        "PROPOSED",
        "IMPORTED",
        "VALIDATED",
        "DEPRECATED",
        "OBSOLETE",
        "OTHER"
      ],
      "title": "AtlasTermAssignmentStatus",
      "type": "string"
    },
    "EntityStatus": {
      "description": "Whether an entity is active, soft-deleted or purged (``AtlasEntity.Status``).",
      "enum": [
        "ACTIVE",
        "DELETED",
        "PURGED"
      ],
      "title": "EntityStatus",
      "type": "string"
    },
    "JavaInt": {
      "type": "integer"
    },
    "OptionalNameSet": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "TimeBoundary": {
      "description": "A period in which a classification applies; the times are strings in ``TIME_FORMAT``.\n\n``timeZone`` is a Java time zone id, or null for the server's local time.",
      "properties": {
        "startTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Starttime"
        },
        "endTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Endtime"
        },
        "timeZone": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Timezone"
        }
      },
      "title": "TimeBoundary",
      "type": "object"
    }
  },
  "description": "An entity's type, GUID, status, display text, classifications, meanings and labels.",
  "properties": {
    "typeName": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Typename"
    },
    "attributes": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Attributes"
    },
    "guid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Guid"
    },
    "status": {
      "anyOf": [
        {
          "$ref": "#/$defs/EntityStatus"
        },
        {
          "type": "null"
        }
      ],
      "default": "ACTIVE"
    },
    "displayText": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Displaytext"
    },
    "classificationNames": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Classificationnames"
    },
    "classifications": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/AtlasClassification"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Classifications"
    },
    "meaningNames": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Meaningnames"
    },
    "meanings": {
      "anyOf": [
        {
          "items": {
            "$ref": "#/$defs/AtlasTermAssignmentHeader"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Meanings"
    },
    "isIncomplete": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": false,
      "title": "Isincomplete"
    },
    "labels": {
      "$ref": "#/$defs/OptionalNameSet",
      "default": null
    }
  },
  "title": "AtlasEntityHeader",
  "type": "object"
}
```

Fields:

- `type_name` (`str | None`)
- `attributes` (`dict[str, Any] | None`)
- `guid` (`str | None`)
- `status` (`EntityStatus | None`)
- `display_text` (`str | None`)
- `classification_names` (`list[str] | None`)
- `classifications` (`list[AtlasClassification] | None`)
- `meaning_names` (`list[str] | None`)
- `meanings` (`list[AtlasTermAssignmentHeader] | None`)
- `is_incomplete` (`bool | None`)
- `labels` (`OptionalNameSet`)

#### attributes

```
attributes: dict[str, Any] | None = None
```

#### classification\_names

```
classification_names: list[str] | None = None
```

#### classifications

```
classifications: list[AtlasClassification] | None = None
```

#### display\_text

```
display_text: str | None = None
```

#### guid

```
guid: str | None = None
```

#### is\_incomplete

```
is_incomplete: bool | None = False
```

#### labels

```
labels: OptionalNameSet = None
```

#### meaning\_names

```
meaning_names: list[str] | None = None
```

#### meanings

```
meanings: list[AtlasTermAssignmentHeader] | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### status

```
status: EntityStatus | None = EntityStatus.ACTIVE
```

#### type\_name

```
type_name: str | None = None
```

#### from\_map

```
from_map(values: Mapping[str, Any]) -> Self
```

`AtlasStruct(Map)`: `typeName`, and `attributes` or, without an `attributes` map, the whole map.

Not how a body is read, which is Jackson's (ENT-02); Atlas's code makes structs from maps (VAL-14).

#### get\_attribute

```
get_attribute(name: str) -> Any
```

The value of attribute `name`, or None.

#### has\_attribute

```
has_attribute(name: str) -> bool
```

Whether attribute `name` is present, even with a null value.

#### of

```
of(entity: AtlasEntity) -> Self
```

The header of `entity` (`AtlasEntityHeader(AtlasEntity)`); its meanings are not carried over.

#### remove\_attribute

```
remove_attribute(name: str) -> Any
```

Remove attribute `name` and return its value, or None.

#### set\_attribute

```
set_attribute(name: str, value: Any) -> None
```

Set attribute `name`, creating the attributes when there are none.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

## aurelius\_atlas\_model.instance.entity\_headers

`AtlasEntityHeaders`: entity headers by GUID, the body of `/v2/entity/bulk/headers` (ENT-16).

Classes:

- **`AtlasEntityHeaders`** –

  `guidHeaderMap`: the header of each entity, by GUID.

### AtlasEntityHeaders

Bases: `AtlasModel`

`guidHeaderMap`: the header of each entity, by GUID.

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasClassification": {
      "description": "An instance of a classification type attached to an entity.\n\n``propagate`` is written once: Java's ``getPropagate`` and ``isPropagate`` name the same property.",
      "properties": {
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "attributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Attributes"
        },
        "entityGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Entityguid"
        },
        "entityStatus": {
          "anyOf": [
            {
              "$ref": "#/$defs/EntityStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": "ACTIVE"
        },
        "propagate": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Propagate"
        },
        "validityPeriods": {
          "anyOf": [
            {
              "items": {
                "anyOf": [
                  {
                    "$ref": "#/$defs/TimeBoundary"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Validityperiods"
        },
        "removePropagationsOnEntityDelete": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Removepropagationsonentitydelete"
        }
      },
      "title": "AtlasClassification",
      "type": "object"
    },
    "AtlasEntityHeader": {
      "description": "An entity's type, GUID, status, display text, classifications, meanings and labels.",
      "properties": {
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "attributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Attributes"
        },
        "guid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Guid"
        },
        "status": {
          "anyOf": [
            {
              "$ref": "#/$defs/EntityStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": "ACTIVE"
        },
        "displayText": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displaytext"
        },
        "classificationNames": {
          "anyOf": [
            {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Classificationnames"
        },
        "classifications": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasClassification"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Classifications"
        },
        "meaningNames": {
          "anyOf": [
            {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Meaningnames"
        },
        "meanings": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasTermAssignmentHeader"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Meanings"
        },
        "isIncomplete": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": false,
          "title": "Isincomplete"
        },
        "labels": {
          "$ref": "#/$defs/OptionalNameSet",
          "default": null
        }
      },
      "title": "AtlasEntityHeader",
      "type": "object"
    },
    "AtlasTermAssignmentHeader": {
      "description": "The term, the assignment's relationship and how it was made (``glossary.relations``).\n\nAtlas writes it with ``@AtlasJSON``, ``NON_EMPTY``: null fields and empty strings are left out, but the\n``int`` ``confidence`` is always written.",
      "properties": {
        "termGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Termguid"
        },
        "relationGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Relationguid"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "displayText": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displaytext"
        },
        "expression": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Expression"
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "steward": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Steward"
        },
        "source": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Source"
        },
        "confidence": {
          "$ref": "#/$defs/JavaInt",
          "default": 0
        },
        "status": {
          "anyOf": [
            {
              "$ref": "#/$defs/AtlasTermAssignmentStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "qualifiedName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Qualifiedname"
        }
      },
      "title": "AtlasTermAssignmentHeader",
      "type": "object"
    },
    "AtlasTermAssignmentStatus": {
      "description": "The status of a term assignment, written by its Java name (``glossary.enums.AtlasTermAssignmentStatus``).",
      "enum": [
        "DISCOVERED",
        "PROPOSED",
        "IMPORTED",
        "VALIDATED",
        "DEPRECATED",
        "OBSOLETE",
        "OTHER"
      ],
      "title": "AtlasTermAssignmentStatus",
      "type": "string"
    },
    "EntityStatus": {
      "description": "Whether an entity is active, soft-deleted or purged (``AtlasEntity.Status``).",
      "enum": [
        "ACTIVE",
        "DELETED",
        "PURGED"
      ],
      "title": "EntityStatus",
      "type": "string"
    },
    "JavaInt": {
      "type": "integer"
    },
    "OptionalNameSet": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "TimeBoundary": {
      "description": "A period in which a classification applies; the times are strings in ``TIME_FORMAT``.\n\n``timeZone`` is a Java time zone id, or null for the server's local time.",
      "properties": {
        "startTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Starttime"
        },
        "endTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Endtime"
        },
        "timeZone": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Timezone"
        }
      },
      "title": "TimeBoundary",
      "type": "object"
    }
  },
  "description": "``guidHeaderMap``: the header of each entity, by GUID.",
  "properties": {
    "guidHeaderMap": {
      "anyOf": [
        {
          "additionalProperties": {
            "$ref": "#/$defs/AtlasEntityHeader"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Guidheadermap"
    }
  },
  "title": "AtlasEntityHeaders",
  "type": "object"
}
```

Fields:

- `guid_header_map` (`dict[str, AtlasEntityHeader] | None`)

#### guid\_header\_map

```
guid_header_map: dict[str, AtlasEntityHeader] | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

## aurelius\_atlas\_model.instance.entity\_operation

`EntityMutations.EntityOperation`: what a write did to an entity (ENT-09).

Classes:

- **`EntityOperation`** –

  The kinds of entity mutation a response reports (`EntityMutations.EntityOperation`).

### EntityOperation

Bases: `StrEnum`

The kinds of entity mutation a response reports (`EntityMutations.EntityOperation`).

Attributes:

- **`CREATE`** –
- **`DELETE`** –
- **`PARTIAL_UPDATE`** –
- **`PURGE`** –
- **`UPDATE`** –

#### CREATE

```
CREATE = 'CREATE'
```

#### DELETE

```
DELETE = 'DELETE'
```

#### PARTIAL\_UPDATE

```
PARTIAL_UPDATE = 'PARTIAL_UPDATE'
```

#### PURGE

```
PURGE = 'PURGE'
```

#### UPDATE

```
UPDATE = 'UPDATE'
```

## aurelius\_atlas\_model.instance.entity\_mutation\_response

`EntityMutationResponse`: what an entity write did, by operation (ENT-17).

Classes:

- **`EntityMutationResponse`** –

  The headers of the created, updated, deleted and purged entities, and the GUIDs given to new ones.

### EntityMutationResponse

Bases: `AtlasModel`

The headers of the created, updated, deleted and purged entities, and the GUIDs given to new ones.

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasClassification": {
      "description": "An instance of a classification type attached to an entity.\n\n``propagate`` is written once: Java's ``getPropagate`` and ``isPropagate`` name the same property.",
      "properties": {
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "attributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Attributes"
        },
        "entityGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Entityguid"
        },
        "entityStatus": {
          "anyOf": [
            {
              "$ref": "#/$defs/EntityStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": "ACTIVE"
        },
        "propagate": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Propagate"
        },
        "validityPeriods": {
          "anyOf": [
            {
              "items": {
                "anyOf": [
                  {
                    "$ref": "#/$defs/TimeBoundary"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Validityperiods"
        },
        "removePropagationsOnEntityDelete": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Removepropagationsonentitydelete"
        }
      },
      "title": "AtlasClassification",
      "type": "object"
    },
    "AtlasEntityHeader": {
      "description": "An entity's type, GUID, status, display text, classifications, meanings and labels.",
      "properties": {
        "typeName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Typename"
        },
        "attributes": {
          "anyOf": [
            {
              "additionalProperties": true,
              "type": "object"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Attributes"
        },
        "guid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Guid"
        },
        "status": {
          "anyOf": [
            {
              "$ref": "#/$defs/EntityStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": "ACTIVE"
        },
        "displayText": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displaytext"
        },
        "classificationNames": {
          "anyOf": [
            {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Classificationnames"
        },
        "classifications": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasClassification"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Classifications"
        },
        "meaningNames": {
          "anyOf": [
            {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Meaningnames"
        },
        "meanings": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/AtlasTermAssignmentHeader"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Meanings"
        },
        "isIncomplete": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": false,
          "title": "Isincomplete"
        },
        "labels": {
          "$ref": "#/$defs/OptionalNameSet",
          "default": null
        }
      },
      "title": "AtlasEntityHeader",
      "type": "object"
    },
    "AtlasTermAssignmentHeader": {
      "description": "The term, the assignment's relationship and how it was made (``glossary.relations``).\n\nAtlas writes it with ``@AtlasJSON``, ``NON_EMPTY``: null fields and empty strings are left out, but the\n``int`` ``confidence`` is always written.",
      "properties": {
        "termGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Termguid"
        },
        "relationGuid": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Relationguid"
        },
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Description"
        },
        "displayText": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Displaytext"
        },
        "expression": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Expression"
        },
        "createdBy": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Createdby"
        },
        "steward": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Steward"
        },
        "source": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Source"
        },
        "confidence": {
          "$ref": "#/$defs/JavaInt",
          "default": 0
        },
        "status": {
          "anyOf": [
            {
              "$ref": "#/$defs/AtlasTermAssignmentStatus"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        },
        "qualifiedName": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Qualifiedname"
        }
      },
      "title": "AtlasTermAssignmentHeader",
      "type": "object"
    },
    "AtlasTermAssignmentStatus": {
      "description": "The status of a term assignment, written by its Java name (``glossary.enums.AtlasTermAssignmentStatus``).",
      "enum": [
        "DISCOVERED",
        "PROPOSED",
        "IMPORTED",
        "VALIDATED",
        "DEPRECATED",
        "OBSOLETE",
        "OTHER"
      ],
      "title": "AtlasTermAssignmentStatus",
      "type": "string"
    },
    "EntityOperation": {
      "description": "The kinds of entity mutation a response reports (``EntityMutations.EntityOperation``).",
      "enum": [
        "CREATE",
        "UPDATE",
        "PARTIAL_UPDATE",
        "DELETE",
        "PURGE"
      ],
      "title": "EntityOperation",
      "type": "string"
    },
    "EntityStatus": {
      "description": "Whether an entity is active, soft-deleted or purged (``AtlasEntity.Status``).",
      "enum": [
        "ACTIVE",
        "DELETED",
        "PURGED"
      ],
      "title": "EntityStatus",
      "type": "string"
    },
    "JavaInt": {
      "type": "integer"
    },
    "OptionalNameSet": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "TimeBoundary": {
      "description": "A period in which a classification applies; the times are strings in ``TIME_FORMAT``.\n\n``timeZone`` is a Java time zone id, or null for the server's local time.",
      "properties": {
        "startTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Starttime"
        },
        "endTime": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Endtime"
        },
        "timeZone": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Timezone"
        }
      },
      "title": "TimeBoundary",
      "type": "object"
    }
  },
  "description": "The headers of the created, updated, deleted and purged entities, and the GUIDs given to new ones.",
  "properties": {
    "mutatedEntities": {
      "anyOf": [
        {
          "additionalProperties": {
            "items": {
              "$ref": "#/$defs/AtlasEntityHeader"
            },
            "type": "array"
          },
          "propertyNames": {
            "$ref": "#/$defs/EntityOperation"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Mutatedentities"
    },
    "guidAssignments": {
      "anyOf": [
        {
          "additionalProperties": {
            "type": "string"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Guidassignments"
    }
  },
  "title": "EntityMutationResponse",
  "type": "object"
}
```

Fields:

- `mutated_entities` (`dict[EntityOperation, list[AtlasEntityHeader]] | None`)
- `guid_assignments` (`dict[str, str] | None`)

#### guid\_assignments

```
guid_assignments: dict[str, str] | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### mutated\_entities

```
mutated_entities: dict[EntityOperation, list[AtlasEntityHeader]] | None = None
```

#### partial\_updated\_entities

```
partial_updated_entities: list[AtlasEntityHeader] | None
```

The partially updated entities, also written as `partialUpdatedEntities` (ENT-17).

Java's `getPartialUpdatedEntities` lacks the `@JsonIgnore` its other lookups have.

#### add\_entity

```
add_entity(operation: EntityOperation, header: AtlasEntityHeader) -> None
```

Record `operation` on an entity, once per GUID; an update of an entity created here counts as created.

#### get\_created\_entities

```
get_created_entities() -> list[AtlasEntityHeader] | None
```

The created entities, or None.

#### get\_deleted\_entities

```
get_deleted_entities() -> list[AtlasEntityHeader] | None
```

The deleted entities, or None.

#### get\_entities\_by\_operation

```
get_entities_by_operation(operation: EntityOperation) -> list[AtlasEntityHeader] | None
```

The headers of the entities `operation` was applied to, or None.

#### get\_entities\_by\_type\_name

```
get_entities_by_type_name(operation: EntityOperation, type_name: str) -> list[AtlasEntityHeader]
```

The entities of `type_name` that `operation` was applied to (`getCreatedEntitiesByTypeName`, …).

#### get\_entity\_by\_type\_name\_and\_attribute

```
get_entity_by_type_name_and_attribute(
    operation: EntityOperation, type_name: str, name: str, value: str | None
) -> AtlasEntityHeader | None
```

The first entity of `type_name` whose attribute `name` is `value`.

`getCreatedEntityByTypeNameAndAttribute` and `getUpdatedEntityByTypeNameAndAttribute`.

#### get\_first\_entity\_by\_operation

```
get_first_entity_by_operation(operation: EntityOperation) -> AtlasEntityHeader | None
```

The first entity `operation` was applied to (`getFirstEntityCreated`, …), or None.

#### get\_first\_entity\_by\_type\_name

```
get_first_entity_by_type_name(operation: EntityOperation, type_name: str) -> AtlasEntityHeader | None
```

The first entity of `type_name` `operation` was applied to (`getFirstCreatedEntityByTypeName`, …).

#### get\_purged\_entities

```
get_purged_entities() -> list[AtlasEntityHeader] | None
```

The purged entities, or None.

#### get\_purged\_entities\_ids

```
get_purged_entities_ids() -> str | None
```

The GUIDs of the purged entities joined by commas, or None when there are none.

#### get\_updated\_entities

```
get_updated_entities() -> list[AtlasEntityHeader] | None
```

The updated entities, or None.

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

## aurelius\_atlas\_model.instance.term\_assignment\_header

`AtlasTermAssignmentHeader`: a glossary term assigned to an entity, as the entity lists it (ENT-15).

Classes:

- **`AtlasTermAssignmentHeader`** –

  The term, the assignment's relationship and how it was made (`glossary.relations`).

### AtlasTermAssignmentHeader

Bases: `AtlasModel`

The term, the assignment's relationship and how it was made (`glossary.relations`).

Atlas writes it with `@AtlasJSON`, `NON_EMPTY`: null fields and empty strings are left out, but the `int` `confidence` is always written.

**Show JSON schema:**

```
{
  "$defs": {
    "AtlasTermAssignmentStatus": {
      "description": "The status of a term assignment, written by its Java name (``glossary.enums.AtlasTermAssignmentStatus``).",
      "enum": [
        "DISCOVERED",
        "PROPOSED",
        "IMPORTED",
        "VALIDATED",
        "DEPRECATED",
        "OBSOLETE",
        "OTHER"
      ],
      "title": "AtlasTermAssignmentStatus",
      "type": "string"
    },
    "JavaInt": {
      "type": "integer"
    }
  },
  "description": "The term, the assignment's relationship and how it was made (``glossary.relations``).\n\nAtlas writes it with ``@AtlasJSON``, ``NON_EMPTY``: null fields and empty strings are left out, but the\n``int`` ``confidence`` is always written.",
  "properties": {
    "termGuid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Termguid"
    },
    "relationGuid": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Relationguid"
    },
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Description"
    },
    "displayText": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Displaytext"
    },
    "expression": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Expression"
    },
    "createdBy": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Createdby"
    },
    "steward": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Steward"
    },
    "source": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Source"
    },
    "confidence": {
      "$ref": "#/$defs/JavaInt",
      "default": 0
    },
    "status": {
      "anyOf": [
        {
          "$ref": "#/$defs/AtlasTermAssignmentStatus"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "qualifiedName": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Qualifiedname"
    }
  },
  "title": "AtlasTermAssignmentHeader",
  "type": "object"
}
```

Fields:

- `term_guid` (`str | None`)
- `relation_guid` (`str | None`)
- `description` (`str | None`)
- `display_text` (`str | None`)
- `expression` (`str | None`)
- `created_by` (`str | None`)
- `steward` (`str | None`)
- `source` (`str | None`)
- `confidence` (`JavaInt`)
- `status` (`AtlasTermAssignmentStatus | None`)
- `qualified_name` (`str | None`)

#### confidence

```
confidence: JavaInt = 0
```

#### created\_by

```
created_by: str | None = None
```

#### description

```
description: str | None = None
```

#### display\_text

```
display_text: str | None = None
```

#### expression

```
expression: str | None = None
```

#### model\_config

```
model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_alias=True,
    validate_by_name=True,
    validate_assignment=True,
    extra="ignore",
    coerce_numbers_to_str=True,
)
```

#### qualified\_name

```
qualified_name: str | None = None
```

#### relation\_guid

```
relation_guid: str | None = None
```

#### source

```
source: str | None = None
```

#### status

```
status: AtlasTermAssignmentStatus | None = None
```

#### steward

```
steward: str | None = None
```

#### term\_guid

```
term_guid: str | None = None
```

#### to\_json

```
to_json() -> dict[str, Any]
```

The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02).

Untyped values keep their Python types (`Decimal`, `datetime`) for `codec.dumps` (VAL-01, DD-039).

## aurelius\_atlas\_model.instance.term\_assignment\_status

`AtlasTermAssignmentStatus`: how far a glossary term's assignment to an entity got (ENT-09).

Classes:

- **`AtlasTermAssignmentStatus`** –

  The status of a term assignment, written by its Java name (`glossary.enums.AtlasTermAssignmentStatus`).

### AtlasTermAssignmentStatus

Bases: `StrEnum`

The status of a term assignment, written by its Java name (`glossary.enums.AtlasTermAssignmentStatus`).

Attributes:

- **`DEPRECATED`** –
- **`DISCOVERED`** –
- **`IMPORTED`** –
- **`OBSOLETE`** –
- **`OTHER`** –
- **`PROPOSED`** –
- **`VALIDATED`** –

#### DEPRECATED

```
DEPRECATED = 'DEPRECATED'
```

#### DISCOVERED

```
DISCOVERED = 'DISCOVERED'
```

#### IMPORTED

```
IMPORTED = 'IMPORTED'
```

#### OBSOLETE

```
OBSOLETE = 'OBSOLETE'
```

#### OTHER

```
OTHER = 'OTHER'
```

#### PROPOSED

```
PROPOSED = 'PROPOSED'
```

#### VALIDATED

```
VALIDATED = 'VALIDATED'
```
