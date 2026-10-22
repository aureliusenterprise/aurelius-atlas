# aurelius-atlas-model

Atlas data shapes for Aurelius Atlas, without I/O ([DD-002](<https://aureliusenterprise.github.io/feat-webapp-details-components/architecture/conversion/design-log/#dd-002-atlas-code-lives-in-aurelius-atlas-projects-split-by-layer>)). Since increment [1.1](<https://aureliusenterprise.github.io/feat-webapp-details-components/architecture/conversion/increments/1-1-typedef-models/index.md>): the Apache Atlas 2.4.0 type definitions (enum, struct, classification, entity, relationship and business metadata), their header and `AtlasTypesDef`, as Pydantic models that read and write Atlas's REST JSON. Since [1.5](<https://aureliusenterprise.github.io/feat-webapp-details-components/architecture/conversion/increments/1-5-builtin-models/index.md>): the patch record `AtlasPatch`.

```
from aurelius_atlas_model.typedef import AtlasTypesDef

types = AtlasTypesDef.model_validate(request_body)  # Atlas's normalisations apply
response_body = types.to_json()  # Java names, nulls left out, epoch-millisecond dates
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
- **`AtlasModel`** –

  The JSON conventions of every Atlas model (TDM-01 to TDM-03, TDM-15, DD-020).
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

Config:

- `alias_generator`: `to_camel`
- `validate_by_alias`: `True`
- `validate_by_name`: `True`
- `validate_assignment`: `True`
- `extra`: `ignore`
- `coerce_numbers_to_str`: `True`

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
