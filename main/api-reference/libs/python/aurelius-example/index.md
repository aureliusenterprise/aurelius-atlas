# aurelius-example

This library provides common utilities for example projects.

## Installation

You can include `aurelius-example` in your project by adding it to your `pyproject.toml`:

```
dependencies = ["aurelius-example"]

[tool.uv.sources.aurelius-example]
workspace = true
```

Ensure the path points to the correct location of the `aurelius-example` library.

## Documentation

## aurelius\_example.Entity

Bases: `AvroBase`, `SQLModel`

A model that represents an simple entity that can be serialized to Avro and stored in a SQL database.

**Show JSON schema:**

```
{
  "description": "A model that represents an simple entity that can be serialized to Avro and stored in a SQL database.",
  "properties": {
    "description": {
      "anyOf": [
        {
          "maxLength": 255,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "A description of the entity",
      "title": "Description"
    },
    "guid": {
      "description": "The unique identifier for the entity",
      "format": "uuid",
      "title": "Guid",
      "type": "string"
    },
    "name": {
      "anyOf": [
        {
          "maxLength": 100,
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The name of the entity",
      "title": "Name"
    },
    "time_created": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The timestamp when the entity was created with timezone info",
      "title": "Time Created"
    },
    "time_modified": {
      "anyOf": [
        {
          "format": "date-time",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The timestamp when the entity was last modified with timezone info",
      "title": "Time Modified"
    }
  },
  "title": "Entity",
  "type": "object"
}
```

Fields:

- `description` (`str | None`)
- `guid` (`UUID`)
- `name` (`str | None`)
- `time_created` (`datetime | None`)
- `time_modified` (`datetime | None`)

### \_\_mapper\_args\_\_

```
__mapper_args__ = {'confirm_deleted_rows': False}
```

### description

```
description: str | None = None
```

A description of the entity

### guid

```
guid: UUID
```

The unique identifier for the entity

### name

```
name: str | None = None
```

The name of the entity

### time\_created

```
time_created: datetime | None = None
```

The timestamp when the entity was created with timezone info

### time\_modified

```
time_modified: datetime | None = None
```

The timestamp when the entity was last modified with timezone info

### \_\_lt\_\_

```
__lt__(other: Entity) -> bool
```

Compare entities based on their latest change timestamp.

## aurelius\_example.models.EntityNotification

Bases: `BaseModel`

A model that represents the payload of a notification about changes to the Entity table.

**Show JSON schema:**

```
{
  "$defs": {
    "Entity": {
      "description": "A model that represents an simple entity that can be serialized to Avro and stored in a SQL database.",
      "properties": {
        "description": {
          "anyOf": [
            {
              "maxLength": 255,
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "A description of the entity",
          "title": "Description"
        },
        "guid": {
          "description": "The unique identifier for the entity",
          "format": "uuid",
          "title": "Guid",
          "type": "string"
        },
        "name": {
          "anyOf": [
            {
              "maxLength": 100,
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The name of the entity",
          "title": "Name"
        },
        "time_created": {
          "anyOf": [
            {
              "format": "date-time",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The timestamp when the entity was created with timezone info",
          "title": "Time Created"
        },
        "time_modified": {
          "anyOf": [
            {
              "format": "date-time",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The timestamp when the entity was last modified with timezone info",
          "title": "Time Modified"
        }
      },
      "title": "Entity",
      "type": "object"
    }
  },
  "description": "A model that represents the payload of a notification about changes to the Entity table.",
  "properties": {
    "guid": {
      "description": "The primary key of the affected row",
      "format": "uuid",
      "title": "Guid",
      "type": "string"
    },
    "op": {
      "description": "The type of operation that triggered the notification",
      "enum": [
        "INSERT",
        "UPDATE",
        "DELETE"
      ],
      "title": "Op",
      "type": "string"
    },
    "schema_name": {
      "description": "The database schema where the change occurred",
      "title": "Schema Name",
      "type": "string"
    },
    "table_name": {
      "description": "The database table where the change occurred",
      "title": "Table Name",
      "type": "string"
    },
    "timestamp": {
      "description": "The timestamp when the change occurred with timezone info",
      "format": "date-time",
      "title": "Timestamp",
      "type": "string"
    },
    "value": {
      "anyOf": [
        {
          "$ref": "#/$defs/Entity"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The current state of the affected row; null for DELETE operations"
    }
  },
  "required": [
    "guid",
    "op",
    "schema_name",
    "table_name"
  ],
  "title": "EntityNotification",
  "type": "object"
}
```

Fields:

- `guid` (`UUID`)
- `op` (`Literal['INSERT', 'UPDATE', 'DELETE']`)
- `schema_name` (`str`)
- `table_name` (`str`)
- `timestamp` (`datetime`)
- `value` (`Entity | None`)

### guid

```
guid: UUID
```

The primary key of the affected row

### op

```
op: Literal['INSERT', 'UPDATE', 'DELETE']
```

The type of operation that triggered the notification

### schema\_name

```
schema_name: str
```

The database schema where the change occurred

### table\_name

```
table_name: str
```

The database table where the change occurred

### timestamp

```
timestamp: datetime
```

The timestamp when the change occurred with timezone info

### value

```
value: Entity | None = None
```

The current state of the affected row; null for DELETE operations
