# aurelius-kafka

This library provides common utilities for working with Apache Kafka.

## Installation

You can include `aurelius-kafka` in your project by adding it to your `pyproject.toml`:

```
dependencies = ["aurelius-kafka"]

[tool.uv.sources.aurelius-kafka]
workspace = true
```

Ensure the path points to the correct location of the `aurelius-kafka` library.

## Documentation

## aurelius\_kafka

Modules:

- **`admin`** –
- **`msk`** –

  This module provides auth utilities for Amazon MSK (Managed Streaming for Apache Kafka).
- **`producer`** –
- **`schema_registry`** –

Classes:

- **`KafkaAdminClient`** –

  A wrapper around the `AdminClient` from `confluent_kafka` that handles common workflows.
- **`KafkaProducer`** –

  A generic Kafka producer that implements basic control flow for producing messages to a Kafka topic.

Functions:

- **`build_schema_registry_header`** –

  Builds a message header compatible with the Confluent Schema Registry wire format.

### \_\_all\_\_

```
__all__ = ['KafkaAdminClient', 'KafkaProducer', 'build_schema_registry_header']
```

### KafkaAdminClient

```
KafkaAdminClient(admin_client: AdminClient)
```

A wrapper around the `AdminClient` from `confluent_kafka` that handles common workflows.

Parameters:

- #### **`admin_client`**

  (`AdminClient`) –

  The AdminClient instance to use internally.

Methods:

- **`create_topics`** –

  Create the given Kafka topics.
- **`delete_topics`** –

  Delete the given Kafka topics.

Attributes:

- **`admin_client`** –

#### admin\_client

```
admin_client = admin_client
```

#### create\_topics

```
create_topics(*topics: NewTopic) -> None
```

Create the given Kafka topics.

Parameters:

- ##### **`topics`**

  (`NewTopic`, default: `()` ) –

  The topics to create.

#### delete\_topics

```
delete_topics(*topics: str) -> None
```

Delete the given Kafka topics.

Parameters:

- ##### **`topics`**

  (`str`, default: `()` ) –

  The names of the topics to delete.

### KafkaProducer

```
KafkaProducer(producer: Producer, *, callback: KafkaProducerCallbackFn | None = None)
```

A generic Kafka producer that implements basic control flow for producing messages to a Kafka topic.

Parameters:

- #### **`producer`**

  (`Producer`) –

  An instance of confluent\_kafka.Producer to send messages.
- #### **`callback`**

  (`KafkaProducerCallbackFn | None`, default: `None` ) –

  An optional callback function to handle message delivery status.

Methods:

- **`batch`** –

  Produce a batch of messages to the Kafka topic.
- **`flush`** –

  Flush the producer to ensure all messages are sent.
- **`produce`** –

  Produce the given message to the Kafka topic.

#### batch

```
batch(topic: str, messages: Iterable[tuple[bytes | None, bytes | None]], *, flush: bool = True) -> None
```

Produce a batch of messages to the Kafka topic.

This method flushes the producer only after all messages have been produced.

Parameters:

- ##### **`topic`**

  (`str`) –

  The Kafka topic to produce the messages to.
- ##### **`messages`**

  (`Iterable[tuple[bytes | None, bytes | None]]`) –

  An iterable of tuples containing the key and value of each message.
- ##### **`flush`**

  (`bool`, default: `True` ) –

  Whether to flush the producer after sending the messages.

#### flush

```
flush() -> None
```

Flush the producer to ensure all messages are sent.

#### produce

```
produce(topic: str, message: tuple[bytes | None, bytes | None], *, flush: bool = True) -> None
```

Produce the given message to the Kafka topic.

Parameters:

- ##### **`topic`**

  (`str`) –

  The Kafka topic to produce the message to.
- ##### **`message`**

  (`tuple[bytes | None, bytes | None]`) –

  A tuple containing the key and value of the message.
- ##### **`flush`**

  (`bool`, default: `True` ) –

  Whether to flush the producer after sending the message.

### build\_schema\_registry\_header

```
build_schema_registry_header(
    schema_id: int, *, is_protobuf: bool = False, message_indexes: list[int] | None = None
) -> bytes
```

Builds a message header compatible with the Confluent Schema Registry wire format.

The header consists of a magic byte (0) and the schema ID encoded as 4 big-endian bytes. For Protobuf messages, the header also includes the message indexes as zigzag-encoded integers.

[See the Confluent documentation for more details](<https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html#wire-format>).

Parameters:

- #### **`schema_id`**

  (`int`) –

  Schema registry ID for the message schema.
- #### **`is_protobuf`**

  (`bool`, default: `False` ) –

  Whether or not the header is for a Protobuf message.
- #### **`message_indexes`**

  (`list[int] | None`, default: `None` ) –

  An array of indexes that corresponds to the message type.

Returns:

- **`bytes`** ( `bytes` ) –

  The schema registry header.

## aurelius\_kafka.msk

This module provides auth utilities for Amazon MSK (Managed Streaming for Apache Kafka).

> [!NOTE]
>
> Please install the `msk` extra to use this module.

Classes:

- **`MSKOAuthTokenProvider`** –

  A class to handle OAuth authentication for Amazon MSK (Managed Streaming for Apache Kafka).

### MSKOAuthTokenProvider

```
MSKOAuthTokenProvider(aws_region: str)
```

A class to handle OAuth authentication for Amazon MSK (Managed Streaming for Apache Kafka).

This class generates OAuth tokens for MSK. It implements the signature required by `confluent_kafka` clients for OAUTHBEARER authentication.

Parameters:

- #### **`aws_region`**

  (`str`) –

  The AWS region to use for token generation.

Methods:

- **`__call__`** –

  Generate an OAuth token for MSK using the stored AWS region.

Attributes:

- **`aws_region`** –

#### aws\_region

```
aws_region = aws_region
```

#### \_\_call\_\_

```
__call__(_: dict) -> tuple[str, float]
```

Generate an OAuth token for MSK using the stored AWS region.

Parameters:

- ##### **`_`**

  (`dict`) –

  dict: A configuration dictionary (unused).

Returns:

- `tuple[str, float]` –

  tuple\[str, float\]: A tuple containing the OAuth token and its expiry time in seconds.
