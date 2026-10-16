# aurelius-aws-lambda

This library provides common utilities for working with AWS lambda functions.

## Installation

You can include `aurelius-aws-lambda` in your project by adding it to your `pyproject.toml`:

```
dependencies = ["aurelius-aws-lambda"]

[tool.uv.sources.aurelius-aws-lambda]
workspace = true
```

Ensure the path points to the correct location of the `aurelius-aws-lambda` library.

## Documentation

## aurelius\_aws\_lambda

Modules:

- **`kafka`** –
- **`testing`** –

Classes:

- **`AWSLambdaKafkaEvent`** –

  Model for the Kafka events received by AWS Lambda.
- **`AWSLambdaKafkaRecord`** –

  Model representing a Kafka record.

### \_\_all\_\_

```
__all__ = ['AWSLambdaKafkaEvent', 'AWSLambdaKafkaRecord']
```

### AWSLambdaKafkaEvent

Bases: `BaseModel`

Model for the Kafka events received by AWS Lambda.

**Show JSON schema:**

```
{
  "$defs": {
    "AWSLambdaKafkaRecord": {
      "description": "Model representing a Kafka record.",
      "properties": {
        "headers": {
          "description": "A list of headers for the record.",
          "items": {
            "additionalProperties": {
              "format": "binary",
              "type": "string"
            },
            "type": "object"
          },
          "title": "Headers",
          "type": "array"
        },
        "offset": {
          "description": "The offset of the record in the partition.",
          "title": "Offset",
          "type": "integer"
        },
        "partition": {
          "description": "The partition from which the record was read.",
          "title": "Partition",
          "type": "integer"
        },
        "timestamp": {
          "description": "The timestamp of the record.",
          "format": "date-time",
          "title": "Timestamp",
          "type": "string"
        },
        "timestampType": {
          "description": "The type of timestamp for the record.",
          "title": "Timestamptype",
          "type": "string"
        },
        "topic": {
          "description": "The topic from which the record was read.",
          "title": "Topic",
          "type": "string"
        },
        "key": {
          "anyOf": [
            {
              "format": "binary",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The key of the record.",
          "title": "Key"
        },
        "value": {
          "anyOf": [
            {
              "format": "binary",
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "description": "The value of the record.",
          "title": "Value"
        }
      },
      "required": [
        "offset",
        "partition",
        "timestamp",
        "timestampType",
        "topic"
      ],
      "title": "AWSLambdaKafkaRecord",
      "type": "object"
    }
  },
  "description": "Model for the Kafka events received by AWS Lambda.",
  "properties": {
    "records": {
      "additionalProperties": {
        "items": {
          "$ref": "#/$defs/AWSLambdaKafkaRecord"
        },
        "type": "array"
      },
      "description": "A dictionary where the key is the partition name and the value is a list of records.",
      "title": "Records",
      "type": "object"
    }
  },
  "title": "AWSLambdaKafkaEvent",
  "type": "object"
}
```

Fields:

- `records` (`dict[str, list[T]]`)

#### records

```
records: dict[str, list[T]]
```

A dictionary where the key is the partition name and the value is a list of records.

### AWSLambdaKafkaRecord

Bases: `AWSLambdaKafkaRecordBase`

Model representing a Kafka record.

**Show JSON schema:**

```
{
  "description": "Model representing a Kafka record.",
  "properties": {
    "headers": {
      "description": "A list of headers for the record.",
      "items": {
        "additionalProperties": {
          "format": "binary",
          "type": "string"
        },
        "type": "object"
      },
      "title": "Headers",
      "type": "array"
    },
    "offset": {
      "description": "The offset of the record in the partition.",
      "title": "Offset",
      "type": "integer"
    },
    "partition": {
      "description": "The partition from which the record was read.",
      "title": "Partition",
      "type": "integer"
    },
    "timestamp": {
      "description": "The timestamp of the record.",
      "format": "date-time",
      "title": "Timestamp",
      "type": "string"
    },
    "timestampType": {
      "description": "The type of timestamp for the record.",
      "title": "Timestamptype",
      "type": "string"
    },
    "topic": {
      "description": "The topic from which the record was read.",
      "title": "Topic",
      "type": "string"
    },
    "key": {
      "anyOf": [
        {
          "format": "binary",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The key of the record.",
      "title": "Key"
    },
    "value": {
      "anyOf": [
        {
          "format": "binary",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "The value of the record.",
      "title": "Value"
    }
  },
  "required": [
    "offset",
    "partition",
    "timestamp",
    "timestampType",
    "topic"
  ],
  "title": "AWSLambdaKafkaRecord",
  "type": "object"
}
```

Fields:

- `headers` (`list[dict[str, bytes]]`)
- `offset` (`int`)
- `partition` (`int`)
- `timestamp` (`datetime`)
- `timestamp_type` (`str`)
- `topic` (`str`)
- `key` (`bytes | None`)
- `value` (`bytes | None`)

Validators:

- `decode_headers` → `headers`
- `deserialize_key` → `key`
- `deserialize_value` → `value`

#### headers

```
headers: list[dict[str, bytes]]
```

A list of headers for the record.

#### key

```
key: bytes | None = None
```

The key of the record.

#### offset

```
offset: int
```

The offset of the record in the partition.

#### partition

```
partition: int
```

The partition from which the record was read.

#### timestamp

```
timestamp: datetime
```

The timestamp of the record.

#### timestamp\_type

```
timestamp_type: str
```

The type of timestamp for the record.

#### topic

```
topic: str
```

The topic from which the record was read.

#### value

```
value: bytes | None = None
```

The value of the record.

#### decode\_headers

```
decode_headers(headers: list[dict[str, str]]) -> list[dict[str, bytes]]
```

Decode headers to bytes.

#### deserialize\_key

```
deserialize_key(key: str | None) -> bytes | None
```

Deserialize the key from base64 to bytes.

#### deserialize\_value

```
deserialize_value(value: str | None) -> bytes | None
```

Deserialize the value from base64 to bytes.

## aurelius\_aws\_lambda.testing

Type Aliases:

- **`EncodedHeaders`** –
- **`Headers`** –

Functions:

- **`encode_headers`** –

  Encode headers to AWS Lambda format (list of byte values).
- **`generate_payload`** –

  Generate a test payload compatible with the Kafka event structure expected by AWS Lambda.

### EncodedHeaders

```
EncodedHeaders = list[dict[str, list[int]]]
```

### Headers

```
Headers = list[tuple[str, str | bytes | None]]
```

### encode\_headers

```
encode_headers(headers: Headers) -> EncodedHeaders | None
```

Encode headers to AWS Lambda format (list of byte values).

This encoding is compatible with how AWS Lambda expects Kafka record headers to be formatted, where each header value is represented as a list of byte values.

Parameters:

- #### **`headers`**

  (`Headers`) –

  A list of tuples containing header key-value pairs.

Returns:

- `EncodedHeaders | None` –

  EncodedHeaders | None: A list of dictionaries with header keys and byte value lists.

### generate\_payload

```
generate_payload(topic: str, *records: tuple[Headers | None, bytes | None, bytes | None]) -> str
```

Generate a test payload compatible with the Kafka event structure expected by AWS Lambda.
